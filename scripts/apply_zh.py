# -*- coding: utf-8 -*-
"""
把 _zh_work/ 下的逐块译文合并进 catalog/<源>/zh.json（**合并式**，不覆盖未涉及的部分）。

强校验：逐行比对输入清单与译文的序号，任何错位/缺失/多余都会报错退出。
序号对齐是唯一保证 key 不错位的手段（译文文件只写「序号 + 中文」，不重复写 key）。

用法：
  python scripts/apply_zh.py --source lucide
  python scripts/apply_zh.py --source tabler --only tags
  python scripts/apply_zh.py --source tabler --check      # 只校验不写
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_pairs(path: Path) -> dict[str, str]:
    """读「序号\t内容」，返回 {序号: 内容}"""
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        if "\t" not in raw:
            raise SystemExit(f"[x] {path.name} 第 {len(out) + 1} 行缺少制表符：{raw!r}")
        num, val = raw.split("\t", 1)
        out[num.strip()] = val.strip()
    return out


def merge_pair(work: Path, in_name: str, out_name: str, pick) -> tuple[dict[str, str], int]:
    """把 in.txt 的序号对齐到 out.txt 的译文；pick 从 in 行里取出要用的 key"""
    ins: dict[str, str] = {}
    for raw in (work / in_name).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        num, _, rest = raw.partition("\t")
        ins[num.strip()] = rest
    outs = read_pairs(work / out_name)

    miss = sorted(set(ins) - set(outs))
    extra = sorted(set(outs) - set(ins))
    if miss or extra:
        raise SystemExit(f"[x] {out_name} 序号不匹配：缺 {miss[:5]} / 多 {extra[:5]}")

    return {pick(line): outs[num] for num, line in ins.items()}, len(ins)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="lucide", help="源 key，对应 catalog/<source>/")
    ap.add_argument("--only", choices=["all", "tags", "categories"], default="all")
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    ap.add_argument("--allow-partial", action="store_true",
                    help="允许部分分块尚未翻译（跳过缺失的 *.out.txt 而不是报错）")
    args = ap.parse_args()

    src = ROOT / "catalog" / args.source
    work = src / "_zh_work"
    out_path = src / "zh.json"

    # 合并式：先读现有 zh.json，只覆盖本次涉及的部分（Tabler 的分类是手工补的，必须保住）
    payload = {"source_name_zh": None, "categories": {}, "tags": {}}
    if out_path.exists():
        payload.update(json.loads(out_path.read_text(encoding="utf-8")))

    n_cat = n_desc = n_tags = 0

    if args.only in ("all", "categories") and (work / "categories.out.txt").exists():
        cats, n_cat = merge_pair(work, "categories.in.txt", "categories.out.txt",
                                 lambda line: line.split("\t")[0])
        descs, n_desc = merge_pair(work, "categories-desc.in.txt", "categories-desc.out.txt",
                                   lambda line: line.split("\t")[0] + ".description")
        payload.setdefault("categories", {}).update(cats)
        payload["categories"].update(descs)

    if args.only in ("all", "tags"):
        for i in range(1, 100):
            in_name, out_name = f"tags-{i:02d}.in.txt", f"tags-{i:02d}.out.txt"
            if not (work / in_name).exists():
                break
            if not (work / out_name).exists():
                if args.allow_partial:
                    print(f"[!] 跳过未翻译的分块 {in_name}（--allow-partial）")
                    continue
                raise SystemExit(f"[x] 缺少译文文件 {out_name}（清单有 {in_name}）")
            part, n = merge_pair(work, in_name, out_name, lambda line: line.split("\t")[0])
            payload["tags"].update(part)
            n_tags += n

    print(f"[ok] {args.source}: 分类标题 {n_cat} / 分类描述 {n_desc} / 标签 {n_tags}")
    merged = {**payload.get("categories", {}), **payload.get("tags", {})}
    empty = [k for k, v in merged.items() if not v]
    if empty:
        print(f"[!] 有 {len(empty)} 条译文为空：{empty[:5]}")
    print(f"[ok] 合并后 zh.json：{len(payload.get('categories', {}))} 条分类 + "
          f"{len(payload.get('tags', {}))} 条标签")

    if args.check:
        print("[ok] 仅校验，未写入")
        return 0

    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[ok] 写入 {out_path}（{out_path.stat().st_size / 1024:.0f} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
