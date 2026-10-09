# -*- coding: utf-8 -*-
"""
把 _zh_work/ 下的逐块译文合并成 catalog/lucide/zh.json（中文覆盖层）。

强校验：逐行比对输入清单与译文的序号，任何错位/缺失/多余都会报错退出。
序号对齐是唯一保证 key 不错位的手段（译文文件只写「序号 + 中文」，不重复写 key）。

用法：
  python scripts/apply_zh.py            # 合并
  python scripts/apply_zh.py --check    # 只校验不写文件
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "catalog" / "lucide"
WORK = SRC / "_zh_work"


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


def merge_pair(in_name: str, out_name: str, pick) -> tuple[dict[str, str], int]:
    """把 in.txt 的序号对齐到 out.txt 的译文，pick 从 in 行里取要用的 key"""
    ins = {}
    for raw in (WORK / in_name).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        num, _, rest = raw.partition("\t")
        ins[num.strip()] = rest
    outs = read_pairs(WORK / out_name)

    miss = sorted(set(ins) - set(outs))
    extra = sorted(set(outs) - set(ins))
    if miss or extra:
        raise SystemExit(f"[x] {out_name} 序号不匹配：缺 {miss[:5]} / 多 {extra[:5]}")

    result = {}
    for num, line in ins.items():
        key = pick(line)
        result[key] = outs[num]
    return result, len(result)


def main() -> int:
    cats, n_cat = merge_pair("categories.in.txt", "categories.out.txt",
                             lambda line: line.split("\t")[0])
    descs, n_desc = merge_pair("categories-desc.in.txt", "categories-desc.out.txt",
                               lambda line: line.split("\t")[0] + ".description")

    tags: dict[str, str] = {}
    n_tags = 0
    for i in range(1, 40):
        in_name, out_name = f"tags-{i:02d}.in.txt", f"tags-{i:02d}.out.txt"
        if not (WORK / in_name).exists():
            break
        if not (WORK / out_name).exists():
            raise SystemExit(f"[x] 缺少译文文件 {out_name}")
        part, n = merge_pair(in_name, out_name, lambda line: line.split("\t")[0])
        tags.update(part)
        n_tags += n

    payload = {
        "source_name_zh": "Lucide",
        "categories": {**cats, **descs},
        "tags": tags,
    }

    print(f"[ok] 分类标题 {n_cat} / 分类描述 {n_desc} / 标签 {n_tags}")
    empty = [k for k, v in {**cats, **descs, **tags}.items() if not v]
    if empty:
        print(f"[!] 有 {len(empty)} 条译文为空：{empty[:5]}")

    if "--check" in sys.argv:
        print("[ok] 仅校验，未写入")
        return 0

    out = SRC / "zh.json"
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[ok] 写入 {out}（{out.stat().st_size / 1024:.0f} KB）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
