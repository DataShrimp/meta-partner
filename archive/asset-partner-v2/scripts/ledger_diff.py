#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""ledger_diff.py — 对比两份 scan_storage.py 台账，输出增量 JSON（asset-partner Track-1 工具）。

用法:
  python3 ledger_diff.py --old scan-A.jsonl --new scan-B.jsonl [--top 15]

输出（stdout, JSON）:
  summary      : added/removed/changed/unchanged 计数与字节差
  added/removed: 变更清单（每列表截断到 --cap 条）
  changed      : size 或 mtime 变化的共有文件
  rename_candidates : removed×added 按 (size[,hash]) 匹配的疑似移动/改名
  by_top_delta : 按根下一级目录聚合的字节增减热点
注意: 离线根会造成全量 removed——diff 前先确认根可达（AGENTS.md Gotcha 4）。
"""

import argparse
import json
import os
import sys

CAP_DEFAULT = 500


def load_files(path):
    """只加载 file 记录：path -> (size, mtime, ext, hash)。"""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("k") == "file":
                out[r["p"]] = (r.get("s", 0), r.get("m", 0), r.get("e", ""), r.get("h"))
    return out


def top_of(p, roots):
    for root in roots:
        if p.startswith(root):
            rel = os.path.relpath(p, root)
            return os.path.join(os.path.basename(root), rel.split(os.sep)[0])
    parts = p.split(os.sep)
    return os.path.join(parts[-2] if len(parts) > 1 else "", parts[-1])


def main():
    ap = argparse.ArgumentParser(description="diff two scan_storage ledgers")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--cap", type=int, default=CAP_DEFAULT, help="每个输出列表的最大条数")
    ap.add_argument("--top", type=int, default=15, help="热点目录条数")
    args = ap.parse_args()

    old = load_files(args.old)
    new = load_files(args.new)
    def bucket(p):
        parts = p.rstrip("/").split(os.sep)
        return "/".join(parts[-2:]) if len(parts) >= 2 else p

    added_k = set(new) - set(old)
    removed_k = set(old) - set(new)
    common = set(old) & set(new)
    changed = [p for p in common if old[p][0] != new[p][0] or old[p][1] != new[p][1]]
    added_bytes = sum(new[p][0] for p in added_k)
    removed_bytes = sum(old[p][0] for p in removed_k)

    # 重命名候选：优先 (size, hash)，退化 (size, ext)
    rem_by_key = {}
    for p in removed_k:
        s, m, e, h = old[p]
        rem_by_key.setdefault((s, h) if h else (s, e), []).append(p)
    renames = []
    for p in sorted(added_k):
        s, m, e, h = new[p]
        key = (s, h) if h else (s, e)
        if key in rem_by_key and rem_by_key[key]:
            renames.append({"from": rem_by_key[key].pop(), "to": p,
                            "confidence": "high" if h else "size-ext-only"})

    delta = {}
    for p in added_k:
        delta[bucket(p)] = delta.get(bucket(p), 0) + new[p][0]
    for p in removed_k:
        delta[bucket(p)] = delta.get(bucket(p), 0) - old[p][0]
    for p in changed:
        delta[bucket(p)] = delta.get(bucket(p), 0) + new[p][0] - old[p][0]
    hotspots = sorted(delta.items(), key=lambda kv: -abs(kv[1]))[: args.top]

    def lst(keys, src, cap):
        keys = sorted(keys)
        return {
            "truncated": len(keys) > cap,
            "items": [{"p": p, "s": src[p][0], "e": src[p][2]} for p in keys[:cap]],
        }

    result = {
        "old": args.old,
        "new": args.new,
        "summary": {
            "added": {"count": len(added_k), "bytes": added_bytes},
            "removed": {"count": len(removed_k), "bytes": removed_bytes},
            "changed": {"count": len(changed)},
            "unchanged": {"count": len(common) - len(changed)},
            "rename_candidates": {"count": len(renames)},
            "net_bytes": added_bytes - removed_bytes,
        },
        "added": lst(added_k, new, args.cap),
        "removed": lst(removed_k, old, args.cap),
        "changed": lst(changed, new, args.cap),
        "rename_candidates": renames[: args.cap],
        "by_top_delta": [{"bucket": b, "bytes": v} for b, v in hotspots],
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
