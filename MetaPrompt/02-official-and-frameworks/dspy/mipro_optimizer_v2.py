"""
DSPy MIPROv2 Optimizer (Multi-prompt Instruction Proposal Optimizer v2)
Source: https://github.com/stanfordnlp/dspy/blob/main/dspy/teleprompt/mipro_optimizer_v2.py

Core Architecture:
1. Step 1 — Bootstrap Few-Shot Examples (`_bootstrap_fewshot_examples`):
   Runs the student/teacher DSPy program across `trainset` inputs, filtering only trajectories
   that pass `self.metric` to construct `N` candidate few-shot demonstration sets.
2. Step 2 — Grounded Instruction Proposal (`_propose_instructions`):
   Instantiates `GroundedProposer` using 4 grounding dimensions:
   - `program_aware`: Summarizes the entire DSPy program's control flow and predictor roles
   - `use_dataset_summary`: Summarizes batch properties of `trainset`
   - `use_task_demos`: Feeds high-scoring bootstrapped traces from Step 1
   - `use_tip`: Injects randomized prompting heuristics to encourage candidate diversity
3. Step 3 — Bayesian Surrogate Discrete Search (`_optimize_prompt_parameters`):
   Uses Optuna's Multivariate Tree-structured Parzen Estimator (`TPESampler(multivariate=True)`)
   with minibatch evaluation and periodic full-valset checkpoints to find the optimal joint
   combination of `(instruction_idx, demos_idx)` across all predictors in the pipeline.
"""

import logging
import math
import random
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Literal

import dspy
from dspy.evaluate.evaluate import Evaluate
from dspy.propose import GroundedProposer
from dspy.teleprompt.teleprompt import Teleprompter
from dspy.teleprompt.utils import (
    create_minibatch,
    create_n_fewshot_demo_sets,
    eval_candidate_program,
    get_program_with_highest_avg_score,
    get_signature,
    print_full_program,
    save_candidate_program,
    set_signature,
)

if TYPE_CHECKING:
    import optuna

logger = logging.getLogger(__name__)


def _import_optuna():
    try:
        import optuna
    except ModuleNotFoundError as exc:
        if exc.name == "optuna":
            raise ImportError(
                "MIPROv2 requires optional dependency 'optuna'. "
                "Install it with `pip install dspy[optuna]`."
            ) from exc
        raise
    return optuna


BOOTSTRAPPED_FEWSHOT_EXAMPLES_IN_CONTEXT = 3
LABELED_FEWSHOT_EXAMPLES_IN_CONTEXT = 0
MIN_MINIBATCH_SIZE = 50

AUTO_RUN_SETTINGS = {
    "light": {"n": 6, "val_size": 100},
    "medium": {"n": 12, "val_size": 300},
    "heavy": {"n": 18, "val_size": 1000},
}


class MIPROv2(Teleprompter):
    def __init__(
        self,
        metric: Callable,
        prompt_model: Any | None = None,
        task_model: Any | None = None,
        teacher_settings: dict | None = None,
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 4,
        auto: Literal["light", "medium", "heavy"] | None = "light",
        num_candidates: int | None = None,
        num_threads: int | None = None,
        max_errors: int | None = None,
        seed: int = 9,
        init_temperature: float = 1.0,
        verbose: bool = False,
        track_stats: bool = True,
        log_dir: str | None = None,
        metric_threshold: float | None = None,
    ):
        allowed_modes = {None, "light", "medium", "heavy"}
        if auto not in allowed_modes:
            raise ValueError(f"Invalid value for auto: {auto}. Must be one of {allowed_modes}.")
        self.auto = auto
        self.num_fewshot_candidates = num_candidates
        self.num_instruct_candidates = num_candidates
        self.num_candidates = num_candidates
        self.metric = metric
        self.init_temperature = init_temperature
        self.task_model = task_model if task_model else dspy.settings.lm
        self.prompt_model = prompt_model if prompt_model else dspy.settings.lm
        self.max_bootstrapped_demos = max_bootstrapped_demos
        self.max_labeled_demos = max_labeled_demos
        self.verbose = verbose
        self.track_stats = track_stats
        self.log_dir = log_dir
        self.teacher_settings = teacher_settings or {}
        self.prompt_model_total_calls = 0
        self.total_calls = 0
        self.num_threads = num_threads
        self.max_errors = max_errors
        self.metric_threshold = metric_threshold
        self.seed = seed
        self.rng = None

        if not self.prompt_model or not self.task_model:
            raise ValueError(
                "Either provide both prompt_model and task_model or set a default LM through dspy.configure(lm=...)"
            )

    def compile(
        self,
        student: Any,
        *,
        trainset: list,
        teacher: Any = None,
        valset: list | None = None,
        num_trials: int | None = None,
        max_bootstrapped_demos: int | None = None,
        max_labeled_demos: int | None = None,
        seed: int | None = None,
        minibatch: bool = True,
        minibatch_size: int = 35,
        minibatch_full_eval_steps: int = 5,
        program_aware_proposer: bool = True,
        data_aware_proposer: bool = True,
        view_data_batch_size: int = 10,
        tip_aware_proposer: bool = True,
        fewshot_aware_proposer: bool = True,
        provide_traceback: bool | None = None,
    ) -> Any:
        effective_max_errors = (
            self.max_errors if self.max_errors is not None else dspy.settings.max_errors
        )
        effective_max_bootstrapped_demos = (
            max_bootstrapped_demos
            if max_bootstrapped_demos is not None
            else self.max_bootstrapped_demos
        )
        effective_max_labeled_demos = (
            max_labeled_demos if max_labeled_demos is not None else self.max_labeled_demos
        )
        zeroshot_opt = (effective_max_bootstrapped_demos == 0) and (effective_max_labeled_demos == 0)

        seed = seed or self.seed
        self._set_random_seeds(seed)
        trainset, valset = self._set_and_validate_datasets(trainset, valset)

        num_instruct_candidates = (
            self.num_instruct_candidates
            if self.num_instruct_candidates is not None
            else self.num_candidates
        )
        num_fewshot_candidates = (
            self.num_fewshot_candidates
            if self.num_fewshot_candidates is not None
            else self.num_candidates
        )

        (
            num_trials,
            valset,
            minibatch,
            num_instruct_candidates,
            num_fewshot_candidates,
        ) = self._set_hyperparams_from_run_mode(
            student,
            num_trials,
            minibatch,
            zeroshot_opt,
            valset,
            num_instruct_candidates,
            num_fewshot_candidates,
        )

        program = student.deepcopy()
        evaluate = Evaluate(
            devset=valset,
            metric=self.metric,
            num_threads=self.num_threads,
            max_errors=effective_max_errors,
            display_table=False,
            display_progress=True,
            provide_traceback=provide_traceback,
        )

        with dspy.context(lm=self.task_model):
            # Step 1: Bootstrap few-shot examples
            demo_candidates = self._bootstrap_fewshot_examples(
                program,
                trainset,
                seed,
                teacher,
                num_fewshot_candidates=num_fewshot_candidates,
                max_bootstrapped_demos=effective_max_bootstrapped_demos,
                max_labeled_demos=effective_max_labeled_demos,
                max_errors=effective_max_errors,
                metric_threshold=self.metric_threshold,
            )

        # Step 2: Propose instruction candidates
        instruction_candidates = self._propose_instructions(
            program,
            trainset,
            demo_candidates,
            view_data_batch_size,
            program_aware_proposer,
            data_aware_proposer,
            tip_aware_proposer,
            fewshot_aware_proposer,
            num_instruct_candidates=num_instruct_candidates,
        )

        if zeroshot_opt:
            demo_candidates = None

        with dspy.context(lm=self.task_model):
            # Step 3: Find optimal prompt parameters via Bayesian Optimization
            best_program = self._optimize_prompt_parameters(
                program,
                instruction_candidates,
                demo_candidates,
                evaluate,
                valset,
                num_trials,
                minibatch,
                minibatch_size,
                minibatch_full_eval_steps,
                seed,
            )

        return best_program

    def _set_random_seeds(self, seed):
        self.rng = random.Random(seed)

    def _set_num_trials_from_num_candidates(self, program, zeroshot_opt, num_candidates):
        num_vars = len(program.predictors())
        if not zeroshot_opt:
            num_vars *= 2  # Account for few-shot examples + instruction variables
        # Trials = MAX(c*M*log(N), c=2, 3/2*N)
        num_trials = int(max(2 * num_vars * math.log2(num_candidates), 1.5 * num_candidates))
        return num_trials

    def _set_hyperparams_from_run_mode(
        self,
        program: Any,
        num_trials: int | None,
        minibatch: bool,
        zeroshot_opt: bool,
        valset: list,
        num_instruct_candidates: int | None,
        num_fewshot_candidates: int | None,
    ) -> tuple[int, list, bool, int, int]:
        if self.auto is None:
            return num_trials, valset, minibatch, num_instruct_candidates, num_fewshot_candidates

        auto_settings = AUTO_RUN_SETTINGS[self.auto]
        valset = create_minibatch(valset, batch_size=auto_settings["val_size"], rng=self.rng)
        minibatch = len(valset) > MIN_MINIBATCH_SIZE
        num_instruct_candidates = (
            auto_settings["n"] if zeroshot_opt else int(auto_settings["n"] * 0.5)
        )
        num_fewshot_candidates = auto_settings["n"]
        num_trials = self._set_num_trials_from_num_candidates(
            program, zeroshot_opt, auto_settings["n"]
        )
        return num_trials, valset, minibatch, num_instruct_candidates, num_fewshot_candidates

    def _set_and_validate_datasets(self, trainset: list, valset: list | None):
        if not trainset:
            raise ValueError("Trainset cannot be empty.")
        if valset is None:
            if len(trainset) < 2:
                raise ValueError("Trainset must have at least 2 examples if no valset specified.")
            valset_size = min(1000, max(1, int(len(trainset) * 0.80)))
            cutoff = len(trainset) - valset_size
            valset = trainset[cutoff:]
            trainset = trainset[:cutoff]
        return trainset, valset

    def _bootstrap_fewshot_examples(
        self,
        program: Any,
        trainset: list,
        seed: int,
        teacher: Any,
        *,
        num_fewshot_candidates: int,
        max_bootstrapped_demos: int,
        max_labeled_demos: int,
        max_errors: int | None,
        metric_threshold: float | None,
    ) -> list | None:
        zeroshot = max_bootstrapped_demos == 0 and max_labeled_demos == 0
        demo_candidates = create_n_fewshot_demo_sets(
            student=program,
            num_candidate_sets=num_fewshot_candidates,
            trainset=trainset,
            max_labeled_demos=(
                LABELED_FEWSHOT_EXAMPLES_IN_CONTEXT if zeroshot else max_labeled_demos
            ),
            max_bootstrapped_demos=(
                BOOTSTRAPPED_FEWSHOT_EXAMPLES_IN_CONTEXT if zeroshot else max_bootstrapped_demos
            ),
            metric=self.metric,
            max_errors=max_errors,
            teacher=teacher,
            teacher_settings=self.teacher_settings,
            seed=seed,
            metric_threshold=metric_threshold,
            rng=self.rng,
        )
        return demo_candidates

    def _propose_instructions(
        self,
        program: Any,
        trainset: list,
        demo_candidates: list | None,
        view_data_batch_size: int,
        program_aware_proposer: bool,
        data_aware_proposer: bool,
        tip_aware_proposer: bool,
        fewshot_aware_proposer: bool,
        num_instruct_candidates: int,
    ) -> dict[int, list[str]]:
        proposer = GroundedProposer(
            program=program,
            trainset=trainset,
            prompt_model=self.prompt_model,
            view_data_batch_size=view_data_batch_size,
            program_aware=program_aware_proposer,
            use_dataset_summary=data_aware_proposer,
            use_task_demos=fewshot_aware_proposer,
            num_demos_in_context=BOOTSTRAPPED_FEWSHOT_EXAMPLES_IN_CONTEXT,
            use_tip=tip_aware_proposer,
            set_tip_randomly=tip_aware_proposer,
            use_instruct_history=False,
            set_history_randomly=False,
            verbose=self.verbose,
            rng=self.rng,
            init_temperature=self.init_temperature,
        )
        instruction_candidates = proposer.propose_instructions_for_program(
            trainset=trainset,
            program=program,
            demo_candidates=demo_candidates,
            N=num_instruct_candidates,
            trial_logs={},
        )
        for i, pred in enumerate(program.predictors()):
            instruction_candidates[i][0] = get_signature(pred).instructions
        return instruction_candidates

    def _select_and_insert_instructions_and_demos(
        self,
        candidate_program: Any,
        instruction_candidates: dict[int, list[str]],
        demo_candidates: list | None,
        trial: "optuna.trial.Trial",
        trial_logs: dict,
        trial_num: int,
    ) -> tuple[list[str], dict]:
        chosen_params = []
        raw_chosen_params = {}
        for i, predictor in enumerate(candidate_program.predictors()):
            instruction_idx = trial.suggest_categorical(
                f"{i}_predictor_instruction", range(len(instruction_candidates[i]))
            )
            selected_instruction = instruction_candidates[i][instruction_idx]
            updated_signature = get_signature(predictor).with_instructions(selected_instruction)
            set_signature(predictor, updated_signature)
            trial_logs[trial_num][f"{i}_predictor_instruction"] = instruction_idx
            chosen_params.append(f"Predictor {i}: Instruction {instruction_idx}")
            raw_chosen_params[f"{i}_predictor_instruction"] = instruction_idx

            if demo_candidates:
                demos_idx = trial.suggest_categorical(
                    f"{i}_predictor_demos", range(len(demo_candidates[i]))
                )
                predictor.demos = demo_candidates[i][demos_idx]
                trial_logs[trial_num][f"{i}_predictor_demos"] = demos_idx
                chosen_params.append(f"Predictor {i}: Few-Shot Set {demos_idx}")
                raw_chosen_params[f"{i}_predictor_demos"] = demos_idx

        return chosen_params, raw_chosen_params
