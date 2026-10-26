"""
DSPy Signature Core Contract (Declarative Input/Output & Instruction Binding)
Source: https://github.com/stanfordnlp/dspy/blob/main/dspy/signatures/signature.py

Core Principle:
- Replaces brittle free-form prompt strings with a declarative, typed Pydantic contract (`Signature` + `SignatureMeta`).
- Separates "what the module must compute" (`input_fields -> output_fields` with types and descriptions)
  from "how the LM should be instructed" (`cls.instructions`, stored in `cls.__doc__`).
- Exposes immutable transformation methods (`with_instructions`, `append_instructions`, `with_updated_fields`,
  `prepend`, `append`, `insert`, `delete`, `dump_state`, `load_state`) so optimizers like MIPROv2 and GEPA
  can programmatically mutate and serialize prompt instructions and field descriptions as hyperparameters.
"""

import ast
import inspect
import re
import typing
from copy import deepcopy
from typing import Any, Iterator

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo

from dspy.signatures.field import InputField, OutputField
from dspy.utils.constants import IS_TYPE_UNDEFINED


def _default_instructions(cls) -> str:
    inputs_ = ", ".join([f"`{field}`" for field in cls.input_fields])
    outputs_ = ", ".join([f"`{field}`" for field in cls.output_fields])
    return f"Given the fields {inputs_}, produce the fields {outputs_}."


class SignatureMeta(type(BaseModel)):
    def __call__(cls, *args, **kwargs):
        if cls is Signature:
            custom_types = kwargs.pop("custom_types", None)
            return make_signature(*args, custom_types=custom_types, **kwargs)
        return super().__call__(*args, **kwargs)

    def __new__(mcs, signature_name, bases, namespace, **kwargs):
        field_order = [name for name, value in namespace.items() if isinstance(value, FieldInfo)]
        raw_annotations = namespace.get("__annotations__", {})
        for name, field in namespace.items():
            if not isinstance(field, FieldInfo):
                continue
            if not name.startswith("__") and name not in raw_annotations:
                raw_annotations[name] = str
                field.json_schema_extra[IS_TYPE_UNDEFINED] = True
        ordered_annotations = {
            name: raw_annotations[name] for name in field_order if name in raw_annotations
        }
        ordered_annotations.update(
            {k: v for k, v in raw_annotations.items() if k not in ordered_annotations}
        )
        namespace["__annotations__"] = ordered_annotations

        cls = super().__new__(mcs, signature_name, bases, namespace, **kwargs)

        if cls.__doc__ is None:
            for base in bases:
                if isinstance(base, SignatureMeta):
                    doc = getattr(base, "__doc__", "")
                    if doc != "":
                        cls.__doc__ = doc
        if cls.__doc__ is None:
            cls.__doc__ = _default_instructions(cls)

        cls._validate_fields()

        for name, field in cls.model_fields.items():
            if "prefix" not in field.json_schema_extra:
                field.json_schema_extra["prefix"] = infer_prefix(name) + ":"
            if "desc" not in field.json_schema_extra:
                field.json_schema_extra["desc"] = f"${{{name}}}"

        return cls

    def _validate_fields(cls):
        for name, field in cls.model_fields.items():
            extra = field.json_schema_extra or {}
            field_type = extra.get("__dspy_field_type")
            if field_type not in ["input", "output"]:
                raise TypeError(
                    f"Field `{name}` in `{cls.__name__}` must be declared with InputField or OutputField."
                )

    @property
    def instructions(cls) -> str:
        return inspect.cleandoc(getattr(cls, "__doc__", ""))

    @instructions.setter
    def instructions(cls, instructions: str) -> None:
        cls.__doc__ = instructions

    @property
    def input_fields(cls) -> dict[str, FieldInfo]:
        return cls._get_fields_with_type("input")

    @property
    def output_fields(cls) -> dict[str, FieldInfo]:
        return cls._get_fields_with_type("output")

    @property
    def fields(cls) -> dict[str, FieldInfo]:
        return {**cls.input_fields, **cls.output_fields}

    @property
    def signature(cls) -> str:
        input_fields = ", ".join(cls.input_fields.keys())
        output_fields = ", ".join(cls.output_fields.keys())
        return f"{input_fields} -> {output_fields}"

    def _get_fields_with_type(cls, field_type) -> dict[str, FieldInfo]:
        return {
            k: v
            for k, v in cls.model_fields.items()
            if v.json_schema_extra["__dspy_field_type"] == field_type
        }


class Signature(BaseModel, metaclass=SignatureMeta):
    """"""

    @classmethod
    def with_instructions(cls, instructions: str) -> type["Signature"]:
        """Return a new Signature class with identical fields and new instructions."""
        return Signature(cls.fields, instructions)

    @classmethod
    def append_instructions(cls, instructions: str) -> type["Signature"]:
        """Return a new Signature class with instructions appended to existing instructions."""
        return Signature(cls.fields, f"{cls.instructions}\n\n{instructions}")

    @classmethod
    def with_updated_fields(
        cls, name: str, type_: type | None = None, **kwargs: dict[str, Any]
    ) -> type["Signature"]:
        """Create a new Signature class with updated field description/prefix/type."""
        fields_copy = deepcopy(cls.fields)
        fields_copy[name].json_schema_extra = {
            **fields_copy[name].json_schema_extra,
            **kwargs,
        }
        if type_ is not None:
            fields_copy[name].annotation = type_
        return Signature(fields_copy, cls.instructions)

    @classmethod
    def dump_state(cls) -> dict[str, Any]:
        """Serialize the compiled instructions and field prefixes/descriptions to JSON-compatible dict."""
        state = {"instructions": cls.instructions, "fields": []}
        for field in cls.fields:
            state["fields"].append(
                {
                    "prefix": cls.fields[field].json_schema_extra["prefix"],
                    "description": cls.fields[field].json_schema_extra["desc"],
                }
            )
        return state

    @classmethod
    def load_state(cls, state: dict[str, Any]) -> type["Signature"]:
        """Restore compiled instructions and field metadata from a saved state dict."""
        signature_copy = Signature(deepcopy(cls.fields), cls.instructions)
        signature_copy.instructions = state["instructions"]
        for field, saved_field in zip(
            signature_copy.fields.values(), state["fields"], strict=False
        ):
            field.json_schema_extra["prefix"] = saved_field["prefix"]
            field.json_schema_extra["desc"] = saved_field["description"]
        return signature_copy


def infer_prefix(attribute_name: str) -> str:
    """Convert camelCase or snake_case field names into human-readable Title Case prefixes."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", attribute_name)
    intermediate_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    with_underscores_around_numbers = re.sub(r"([a-zA-Z])(\d)", r"\1_\2", intermediate_name)
    with_underscores_around_numbers = re.sub(
        r"(\d)([a-zA-Z])", r"\1_\2", with_underscores_around_numbers
    )
    words = with_underscores_around_numbers.split("_")
    title_cased_words = [w if w.isupper() else w.capitalize() for w in words]
    return " ".join(title_cased_words)
