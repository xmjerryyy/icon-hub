# 路线图 · Roadmap

> 本文件记录**已决定、但尚未开发**的规划。里面的技术决策是拍过板的，动手时按此执行，不要重新发明。
>
> 最后更新：2026-10-09

---

## 一、接入更多图标源

**为什么优先**：这个库的核心卖点是"把分散的图标库整合起来"。
**已于 2026-10-09 接入 Tabler，卖点兑现** —— 数据库结构完全未改；界面因**跨源重名**需小改（见下方坑）。

### ✅ 已完成：Tabler Icons（2026-10-09）

| 项 | 结果 |
|---|---|
| 图标 | 6,238（outline 5,184 + filled 1,054） |
| 分类 | 41（中文已补） |
| 别名 | 66 |
| 标签 | 7597 个唯一值，其中 68% 自动复用 Lucide 译文 |

采集要点（后续加源可参考）：
- Tabler 把 `category` / `tags` 写在 **SVG 文件开头的 `<!-- -->` front-matter 注释**里，不是独立 json
- Tabler 的分类是**单数 `category`**（一个图标只属一个分类），映射到契约时包成单元素数组
- `filled` 那套**完全没有元数据且与 outline 100% 同名** →
  以 `<name>-filled` 导入（与官方 `IconXxxFilled` 命名一致），元数据从同名 outline 继承

### 待接入的候选

| 源 | 图标量 | 许可 | 分类体系 | 采集难度 |
|---|---|---|---|---|
| Bootstrap Icons | ~2,000 | MIT | 8 个分类 | 低 |
| Heroicons | ~1,300 | MIT | 只有 outline / solid 分组，无分类 | 中（分类需自建） |
| Phosphor | ~9,000 | MIT | 6 种字重 × 多分类，结构复杂 | 中高 |

**做法**：写 `scripts/fetch_<源>.py`，产出与 Lucide / Tabler 相同的三份文件
（`source.json` / `categories.json` / `icons.jsonl`），SVG 放 `icons/<源>/`，然后跑 `build_db.py` + `export_web.py`。

### 接新源时的已知坑（都已踩过）

1. **分类 key 会跨源重名**（`animals` / `arrows` / `design`…）→ 界面已改用「源:key」复合键，新源无需再处理
2. **图标名也会跨源重名**（`user` / `settings`…）→ 同上，已用复合键
3. **标签表跨源共享**：同名标签自动复用已有译文，不必重复翻译（但要注意两源给不同译名时的冲突，`build_db.py` 会报告）
4. **中文译文待补**：新源的标签先回退英文，界面不会空白

---

## 二、Icon Hub Skill ✅ 已完成（2026-10-09）

**目标**：别人装一个 skill，就能用自然语言找图标 —— 例如"给这个页面配几个表示上传、删除的图标"，
AI 直接给出图标名与 SVG，不需要记各库的分类和命名。

### 已交付

| 文件 | 作用 |
|---|---|
| `skill/SKILL.md` | 触发条件（含「不该触发」）+ 用法 + 6 条使用建议 |
| `skill/scripts/query.py` | 检索接口：中英关键词 / 源 / 分类 / 风格筛选 / 取 SVG / 统计 |
| `skill/scripts/install.py` | 生成自包含数据 + 安装到 `~/.workbuddy/skills/icon-hub/` |
| `skill/data/icon-hub.db` | 生成物（10.5 MB，**内联全部 8108 个 SVG**），不入库 |

安装：`python skill/scripts/install.py`

### 最终技术决策

| 决策 | 结论 | 理由 |
|---|---|---|
| **数据形态** | ✅ **自带完整 SVG**（内联进 SQLite） | 不依赖仓库目录、不联网，安装后即可独立运行 |
| **数据来源** | 从 `data/icon-hub.db` 复制并 `ALTER TABLE icons ADD COLUMN svg` | 复用已有索引与结构，零重复开发 |
| **依赖** | Python 标准库（sqlite3 / json / argparse） | 不要求装包 |
| **匹配策略** | 标签分「精确命中 +45 / 包含 +12」两档 | 否则「关闭」会被「关闭字幕」等复合标签淹没 |

### 实测

| 输入 | 结果 |
|---|---|
| `query.py "关闭"` | 首选 `lucide:x` ✓ |
| `query.py arrow left` | 首选 `arrow-left` ✓ |
| `query.py --category brand --source tabler` | 411 个品牌图标 ✓ |
| `query.py --get x --source lucide --svg` | 返回完整 SVG 源码 ✓（安装后仍可用，验证自包含） |

### 待办（分发，尚未做）

- [ ] 提交到 WorkBuddy skill 市场，让别人一句话就能装
- [ ] 或在 README 里补一节「手动安装」说明（拷贝 `skill/` 到 `~/.workbuddy/skills/icon-hub/`）
- [ ] 中文提问方式也写进 `description`（现在中英触发词都有了，可再补几个口语说法）

---

## 三、细节打磨（随手做）

- **README 默认语言**：现在是 `README.md` 英文主、`README.zh-CN.md` 中文副；如需中文优先，两份互换并调整互链
- **复核冷门译文**：`mistwarp`（保留原文）、`snake holder`（意译）、`sophistry`（诡辩）三个词值得再确认
- **前端分页**：网格现在一次渲染全部结果，源变多后需要改分页或虚拟滚动
- **别名展示**：264 个别名目前只能从详情抽屉看到，没有独立卡片

---

## 四、已明确不做

- **不做图标编辑器** —— 定位是索引与检索，编辑交给专业工具
- **不接入商业图标库** —— 许可不允许再分发（见 `LICENSES.md` 第 3 节）
- **不做在线服务 / 后端** —— 离线可用是核心特性，加服务会破坏它
