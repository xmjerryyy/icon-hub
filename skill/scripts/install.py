#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 skill 数据并安装到用户级 skill 目录。

做两件事：
  1. 把仓库主库 `data/icon-hub.db` 复制一份，**把 SVG 源码内联进 icons 表** ——
     这样 skill 完全自包含，不依赖仓库里的 icons/ 目录，也不需要联网。
  2. 把 SKILL.md + scripts/ + data/ 复制到 `~/.workbuddy/skills/icon-hub/`。

用法：
  python skill/scripts/install.py                # 生成数据 + 安装到用户目录
  python skill/scripts/install.py --local-only   # 只生成 skill/data/，不安装
  python skill/scripts/install.py --force        # 数据已存在时强制重建
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parent
SRC_DB = ROOT / "data" / "icon-hub.db"
DST_DB = SKILL_DIR / "data" / "icon-hub.db"
USER_SKILLS = Path.home() / ".workbuddy" / "skills"
INSTALL_DIR = USER_SKILLS / "icon-hub"


def build_data(force: bool = False) -> None:
    """复制主库并把 SVG 内联进去"""
    if not SRC_DB.exists():
        sys.exit(f"[x] 找不到主库 {SRC_DB}\n    先跑：python scripts/build_db.py")

    if DST_DB.exists() and not force:
        print(f"[ok] 数据已存在，跳过生成（要重建加 --force）：{DST_DB}")
        return

    DST_DB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_DB, DST_DB)
    print(f"[ok] 复制主库 -> {DST_DB}")

    conn = sqlite3.connect(DST_DB)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(icons)")}
        if "svg" not in cols:
            conn.execute("ALTER TABLE icons ADD COLUMN svg TEXT")

        rows = conn.execute("SELECT id, svg_path FROM icons WHERE svg IS NULL").fetchall()
        done = missing = 0
        for icon_id, rel in rows:
            path = ROOT / rel
            if path.exists():
                conn.execute("UPDATE icons SET svg = ? WHERE id = ?",
                             (path.read_text(encoding="utf-8").strip(), icon_id))
                done += 1
            else:
                missing += 1
        conn.commit()
        conn.execute("VACUUM")
        print(f"[ok] 内联 SVG {done} 个" + (f"，缺失 {missing} 个" if missing else ""))
    finally:
        conn.close()

    size = DST_DB.stat().st_size / 1024 / 1024
    print(f"[ok] skill 数据就绪：{size:.1f} MB")


def install() -> None:
    """复制到 ~/.workbuddy/skills/icon-hub/"""
    if not DST_DB.exists():
        sys.exit("[x] 数据还没生成，先跑 build_data")

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    (INSTALL_DIR / "scripts").mkdir(exist_ok=True)
    (INSTALL_DIR / "data").mkdir(exist_ok=True)

    shutil.copy2(SKILL_DIR / "SKILL.md", INSTALL_DIR / "SKILL.md")
    for f in (SKILL_DIR / "scripts").glob("*.py"):
        shutil.copy2(f, INSTALL_DIR / "scripts" / f.name)
    shutil.copy2(DST_DB, INSTALL_DIR / "data" / "icon-hub.db")

    total = sum(f.stat().st_size for f in INSTALL_DIR.rglob("*") if f.is_file())
    print(f"[ok] 已安装到 {INSTALL_DIR}")
    print(f"[ok] 体积 {total / 1024 / 1024:.1f} MB")
    print("[ok] 新开一个会话即可触发（当前会话可能不会重新扫描 skill）")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-only", action="store_true", help="只生成 skill/data/，不安装")
    ap.add_argument("--force", action="store_true", help="数据已存在时强制重建")
    args = ap.parse_args()

    build_data(force=args.force)
    if not args.local_only:
        install()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
