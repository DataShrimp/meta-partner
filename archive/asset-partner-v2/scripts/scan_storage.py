#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""scan_storage.py — asset-partner 确定性存储盘点扫描器（Track-1 工具）。

对显式声明的根目录做只读遍历，输出 append-only JSONL 台账 + 汇总报告。
遍历/统计/哈希不消耗 LLM token；LLM 只读 summary 与 diff。

用法:
  python3 scan_storage.py --roots "/Users/ryan/Documents,/Users/ryan/Downloads"
  python3 scan_storage.py --roots-file <role>/state/roots.json
  python3 scan_storage.py --self-test

台账记录字段: p=path k=kind(file|dir|link|pkg|skip|err) s=size m=mtime e=ext
              r=skip 原因(exclude|secret) dl=dataless(0|1|null) h=sha256(可选)

安全不变量:
  - 只读：从不打开文件内容（可选哈希除外，且跳过 dataless 文件以防触发 iCloud 下载）
  - 永不跟随符号链接；package bundle(.app/.photoslibrary 等)只作为单条 opaque 记录
  - 默认跳过噪音目录与密钥目录(.ssh/.gnupg/Keychains)；拒绝扫描 / 与 /System
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time

ROLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT_DIR = os.path.join(ROLE_DIR, "state", "inventory")

EXCLUDE_DIR_NAMES = {
    ".git", ".svn", ".Trash", "Caches", "node_modules", "__pycache__",
    ".venv", "venv", ".cache", ".npm", ".pnpm-store", "OrbStack",
}
SECRET_DIR_NAMES = {".ssh", ".gnupg", ".aws", ".kube", "Keychains"}
PACKAGE_SUFFIXES = (
    ".app", ".photoslibrary", ".photolibrary", ".bundle", ".framework",
    ".kext", ".imovielibrary", ".fcpbundle", ".mmodlibrary", ".docset",
)
FORBIDDEN_ROOT_PREFIXES = ("/System", "/private", "/dev", "/Volumes/Recovery")
FORBIDDEN_ROOTS = {"/"}
MTIME_BUCKETS = (("7d", 7), ("30d", 30), ("180d", 180), ("1y", 365))
ERROR_CAP = 50
TOP_N = 20


def ext_of(name):
    i = name.rfind(".")
    return name[i + 1:].lower() if i > 0 else ""


def is_package(name):
    return name.lower().endswith(PACKAGE_SUFFIXES)


def subtree_size(path):
    """包体积：只 stat 不读内容；符号链接跳过。"""
    total = 0
    stack = [path]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def dataless_flag(st):
    """iCloud 未落地文件：size>0 但 0 blocks。属性缺失时返回 None（未知）。"""
    blocks = getattr(st, "st_blocks", None)
    if blocks is None:
        return None
    return 1 if (st.st_size > 0 and blocks == 0) else 0


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_roots(roots):
    clean = []
    for r in roots:
        rp = os.path.realpath(r)
        if rp in FORBIDDEN_ROOTS or any(rp == p or rp.startswith(p + "/") for p in FORBIDDEN_ROOT_PREFIXES):
            print("REFUSED root (system path): %s" % r, file=sys.stderr)
            continue
        if not os.path.isdir(rp):
            print("SKIP root (missing/offline): %s" % r, file=sys.stderr)
            continue
        clean.append(rp)
    return clean


def scan(roots, out_path, hash_under, collect_dirs):
    now = time.time()
    started = datetime.datetime.now()
    stats = {
        "files": 0, "dirs": 0, "links": 0, "pkgs": 0, "skips": 0, "errors": 0,
        "bytes": 0, "dataless_files": 0, "dataless_bytes": 0,
    }
    by_ext = {}
    largest = []
    mtime_b = {k: [0, 0] for k, _ in MTIME_BUCKETS}
    mtime_b["older"] = [0, 0]
    per_root = {}
    errors = []

    with open(out_path, "w", encoding="utf-8") as out:
        def emit(rec):
            out.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")

        for root in roots:
            label = os.path.basename(root) or root
            rs = per_root.setdefault(label, {"files": 0, "bytes": 0, "tops": {}})
            for cur, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
                rel = os.path.relpath(cur, root)
                top = rel.split(os.sep)[0] if rel != "." else "."
                # 目录分类与剪枝
                for d in list(dirnames):
                    full = os.path.join(cur, d)
                    if d in SECRET_DIR_NAMES:
                        emit({"p": full, "k": "skip", "r": "secret", "s": 0})
                        dirnames.remove(d)
                        stats["skips"] += 1
                    elif is_package(d):
                        size = subtree_size(full)
                        try:
                            m = os.stat(full, follow_symlinks=False).st_mtime
                        except OSError:
                            m = 0
                        emit({"p": full, "k": "pkg", "s": size, "m": int(m)})
                        rs["files"] += 1
                        rs["bytes"] += size
                        rs["tops"].setdefault(top, [0, 0])
                        rs["tops"][top][0] += 1
                        rs["tops"][top][1] += size
                        stats["pkgs"] += 1
                        stats["bytes"] += size
                        dirnames.remove(d)
                    elif d in EXCLUDE_DIR_NAMES:
                        emit({"p": full, "k": "skip", "r": "exclude", "s": 0})
                        dirnames.remove(d)
                        stats["skips"] += 1
                if collect_dirs:
                    emit({"p": cur, "k": "dir", "s": 0})
                    stats["dirs"] += 1
                # 文件
                for fn in filenames:
                    full = os.path.join(cur, fn)
                    if os.path.islink(full):
                        emit({"p": full, "k": "link", "s": 0})
                        stats["links"] += 1
                        continue
                    try:
                        st = os.stat(full, follow_symlinks=False)
                    except OSError as e:
                        emit({"p": full, "k": "err", "r": str(e)})
                        stats["errors"] += 1
                        if len(errors) < ERROR_CAP:
                            errors.append({"p": full, "err": str(e)})
                        continue
                    dl = dataless_flag(st)
                    rec = {"p": full, "k": "file", "s": st.st_size,
                           "m": int(st.st_mtime), "e": ext_of(fn), "dl": dl}
                    if hash_under and dl != 1 and st.st_size <= hash_under:
                        try:
                            rec["h"] = sha256_of(full)
                        except OSError:
                            pass
                    emit(rec)
                    rs["files"] += 1
                    rs["bytes"] += st.st_size
                    rs["tops"].setdefault(top, [0, 0])
                    rs["tops"][top][0] += 1
                    rs["tops"][top][1] += st.st_size
                    stats["files"] += 1
                    stats["bytes"] += st.st_size
                    if dl == 1:
                        stats["dataless_files"] += 1
                        stats["dataless_bytes"] += st.st_size
                    key = rec["e"] or "(none)"
                    slot = by_ext.setdefault(key, [0, 0])
                    slot[0] += 1
                    slot[1] += st.st_size
                    largest.append((st.st_size, full))
                    age_days = (now - st.st_mtime) / 86400.0
                    bucket = "older"
                    for name, days in MTIME_BUCKETS:
                        if age_days <= days:
                            bucket = name
                            break
                    mtime_b[bucket][0] += 1
                    mtime_b[bucket][1] += st.st_size

    largest.sort(reverse=True)
    ext_top = sorted(by_ext.items(), key=lambda kv: -kv[1][1])[:TOP_N]
    summary = {
        "schema": 1,
        "started": started.isoformat(timespec="seconds"),
        "duration_s": round(time.time() - time.mktime(started.timetuple()), 2),
        "roots": [{"root": r, **per_root.get(os.path.basename(r) or r, {})} for r in roots],
        "totals": stats,
        "by_ext_top": [{"ext": k, "files": v[0], "bytes": v[1]} for k, v in ext_top],
        "mtime_buckets": {k: {"files": v[0], "bytes": v[1]} for k, v in mtime_b.items()},
        "largest_files": [{"bytes": s, "p": p} for s, p in largest[:TOP_N]],
        "errors_sample": errors,
        "ledger": out_path,
    }
    return summary


def self_test():
    """10 秒验证门：构造已知 fixture，断言台账与 summary 精确匹配。"""
    tmp = tempfile.mkdtemp(prefix="asset-partner-selftest-")
    try:
        sub = os.path.join(tmp, "sub")
        pkg = os.path.join(tmp, "MyTool.app")
        nm = os.path.join(tmp, "node_modules")
        ssh = os.path.join(tmp, ".ssh")
        for d in (sub, os.path.join(pkg, "Contents", "MacOS"), nm, ssh):
            os.makedirs(d)
        w = lambda p, n: open(p, "wb").write(b"x" * n)  # noqa: E731
        w(os.path.join(tmp, "a.txt"), 100)
        w(os.path.join(sub, "b.bin"), 1000)
        w(os.path.join(pkg, "Contents", "MacOS", "run"), 500)
        w(os.path.join(nm, "junk.js"), 9999)
        w(os.path.join(ssh, "id_ed25519"), 444)
        os.symlink(os.path.join(tmp, "a.txt"), os.path.join(tmp, "link"))

        led_dir = tempfile.mkdtemp(prefix="asset-partner-led-")  # 台账必须在被扫目录之外
        led = os.path.join(led_dir, "ledger.jsonl")
        s = scan([tmp], led, hash_under=0, collect_dirs=True)
        recs = [json.loads(l) for l in open(led, encoding="utf-8")]
        byk = {}
        for r in recs:
            byk.setdefault(r["k"], []).append(r)

        checks = [
            ("files == 2", s["totals"]["files"] == 2),
            ("pkg bytes == 500", byk["pkg"][0]["s"] == 500 and s["totals"]["pkgs"] == 1),
            ("total bytes == 1600", s["totals"]["bytes"] == 1600),
            ("symlink recorded", any(r["k"] == "link" for r in recs)),
            ("node_modules skipped", any(r["k"] == "skip" and r["p"].endswith("node_modules") for r in recs)),
            (".ssh skipped as secret", any(r.get("r") == "secret" for r in recs)),
            ("no records inside package", not any(r["p"].find("MyTool.app/") >= 0 and r["k"] in ("file", "dir") for r in recs)),
        ]
        ok = True
        for name, passed in checks:
            print(("PASS  " if passed else "FAIL  ") + name)
            ok = ok and passed
        print("SELF-TEST: " + ("PASS" if ok else "FAIL"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(led_dir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="asset-partner storage inventory scanner")
    ap.add_argument("--roots", action="append", default=[], help="逗号分隔或多次出现的扫描根")
    ap.add_argument("--roots-file", help="JSON: {\"roots\": [...]} 或 [{path...}]")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--hash-under", type=int, default=0, help="对 <=N 字节的文件计算 sha256（0=关闭）")
    ap.add_argument("--no-dirs", action="store_true", help="不记录目录条目")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    roots = []
    for chunk in args.roots:
        roots.extend(x for x in chunk.split(",") if x.strip())
    if args.roots_file:
        cfg = json.load(open(args.roots_file, encoding="utf-8"))
        items = cfg["roots"] if isinstance(cfg, dict) else cfg
        for it in items:
            roots.append(it["path"] if isinstance(it, dict) else it)
    if not roots:
        ap.error("必须通过 --roots 或 --roots-file 提供至少一个扫描根")

    os.makedirs(args.out_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(args.out_dir, "scan-%s.jsonl" % stamp)
    clean_roots = validate_roots(roots)
    if not clean_roots:
        print("ERROR: 没有可用扫描根（全部被拒/离线）", file=sys.stderr)
        sys.exit(2)

    summary = scan(clean_roots, out_path, args.hash_under, not args.no_dirs)
    sum_path = out_path.replace(".jsonl", "-summary.json")
    with open(sum_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    t = summary["totals"]
    gb = t["bytes"] / 1e9
    print("LEDGER : %s" % out_path)
    print("SUMMARY: %s" % sum_path)
    print("files=%d dirs=%d pkgs=%d bytes=%.2fGB dataless=%d(%.2fGB) skips=%d errors=%d"
          % (t["files"], t["dirs"], t["pkgs"], gb, t["dataless_files"],
             t["dataless_bytes"] / 1e9, t["skips"], t["errors"]))
    print("top ext  :", ", ".join("%s=%.1fGB" % (e["ext"], e["bytes"] / 1e9) for e in summary["by_ext_top"][:6]))
    for r in summary["roots"]:
        print("root %-14s files=%-7d bytes=%.2fGB" % (r["root"], r.get("files", 0), r.get("bytes", 0) / 1e9))


if __name__ == "__main__":
    main()
