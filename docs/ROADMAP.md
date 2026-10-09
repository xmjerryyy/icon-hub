# 路线图 · Roadmap

> 本文件记录**已决定、但尚未开发**的规划。里面的技术决策是拍过板的，动手时按此执行，不要重新发明。
>
> 最后更新：2026-10-09

---

## 一、接入更多图标源（当前最高优先级）

**为什么优先**：这个库的核心卖点是"把分散的图标库整合起来"，但**目前只有 Lucide 一个源** —— 卖点还没兑现。
接入第二个源同时能验证「统一数据契约」是否真的可复用（加源不改数据库和界面代码）。

**为什么排在 skill 前面**：skill 的价值与**库里的源数量**正相关。只有 Lucide 时，做出来的 skill 就是个"Lucide 查询器"，
别人直接看 lucide.dev 更省事。等有 3–4 个源，"跨库统一检索"这个真需求才成立。

**候选与采集难度评估**

| 源 | 图标量 | 许可 | 分类体系 | 采集难度 |
|---|---|---|---|---|
| **Tabler** | ~5,900 | MIT | 有 categories + tags（结构最像 Lucide） | **低 —— 首选** |
| Bootstrap Icons | ~2,000 | MIT | 8 个分类 | 低 |
| Heroicons | ~1,300 | MIT | 只有 outline / solid 分组，无分类 | 中（分类需自建） |
| Phosphor | ~9,000 | MIT | 6 种字重 × 多分类，结构复杂 | 中高 |

**做法**：写 `scripts/fetch_<源>.py`，产出与 Lucide 相同的三份文件
（`source.json` / `categories.json` / `icons.jsonl`），SVG 放 `icons/<源>/`，然后跑 `build_db.py` + `export_web.py`。

---

## 二、Icon Hub Skill（方案已定，待开发）

**目标**：别人装一个 skill，就能用自然语言找图标 —— 例如"给这个页面配几个表示上传、删除的图标"，
AI 直接给出图标名与 SVG，不需要记各库的分类和命名。

### 已拍板的技术决策

| 决策 | 结论 | 理由 |
|---|---|---|
| **数据形态** | ✅ **skill 自带完整 SVG** | 不依赖网络，也不要求别人先 clone 本仓库 |
| **数据来源** | 从 `web/data/catalog.json` 打包（全量内联 SVG，约 1.4 MB） | 现成产物，零额外加工 |
| **运行方式** | 本地脚本查询，不发网络请求 | 离线可靠、零延迟 |
| **依赖** | Python 标准库（`sqlite3` / `json`） | 不要求装包 |

### 形态

```
icon-hub-skill/
├── SKILL.md            触发条件 + 调用方式
├── scripts/query.py    查询接口：中英关键词 / 分类 / 标签筛选
└── data/catalog.json   打包进去的完整数据（含全部 SVG）
```

### 为什么不设计成联网取数（重要，别再讨论一遍）

本机（AI 沙箱）实测域名可达性：

| 域名 | 状态 |
|---|---|
| `raw.githubusercontent.com` | ❌ 不通 |
| `api.github.com` | ❌ 不通 |
| `github.com` | ❌ 不通 |
| `cdn.jsdelivr.net` | ✅ 通（可代理 GitHub 仓库文件） |
| `codeload.github.com` | ✅ 通（整包 tar.gz） |

所以"运行时去 GitHub 拉数据"在沙箱里做不到；而别人机器网络环境也不确定。
**自带数据是唯一稳的方案。**

> 如果以后要加"检查数据更新"，走 jsdelivr 而不是 raw 直链：
> `https://cdn.jsdelivr.net/gh/xmjerryyy/icon-hub@<commit>/catalog/lucide/source.json`
> （用 commit hash 而不是 `@main`，避开 CDN 缓存）

### 待办清单

- [ ] `query.py`：支持中英关键词、分类筛选、标签筛选；输出 名称 / 分类 / 标签 / SVG
- [ ] 数据打包脚本：从 `web/data/catalog.json` 生成 skill 用的数据文件
- [ ] `SKILL.md`：写清**触发条件**（找图标 / 选图标 / 这个界面配什么图标 / 有没有表示 XX 的图标）
- [ ] 分发：提交到 WorkBuddy skill 市场，或 GitHub 仓库 + 手动安装说明
- [ ] 触发描述要覆盖中英文提问方式（用户可能用中文问，也可能用英文问）

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
