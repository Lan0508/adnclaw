# 大量 Skill 与真实场景：如何提升 Hermes 调用准确性

核心矛盾：**技能一多，仅靠系统提示里那行 `name + 短 description`，模型很容易「看起来像」就选错**。要「有效利用大量真实场景」，本质是把场景从**模糊记忆**变成**可检索、可约束、可验收**的三层结构。

以下策略**不要求修改 LLM 权重**。

---

## 1. 把「场景」变成路由资产，而不是只当聊天记录

对每条**真实场景**，在数据集里固化成结构化记录（比纯对话有用得多）：

| 字段 | 说明 |
|------|------|
| `scenario_text` | 用户原话或归纳后的多种说法（多版本更好检索） |
| `skill_view_name` | **必须与 Hermes 解析一致**（目录名、`category/skill`、`plugin:ns` 等） |
| `optional_file_path` | 若标准路径是先看主文档再拉 `references/...` |
| `negative_skills` | 易混淆时明确写「不要用 X」 |
| `confidence / tier` | 强规则 vs 仅建议 |

检索时用 **向量 + 关键词（BM25）混合** 往往比纯向量更稳，因为场景里常有专有名词、命令、产品名。

---

## 2. 三层路由：减少「全靠模型扫一遍索引」

### 层 A — 硬约束（几乎零偏差）

- 固定入口：**频道 / 项目 / 客户** → `channel_skill_bindings`（网关配置）或你们网关外的路由表。
- **关键词 / 正则 / 小分类器**（哪怕很浅）：命中则直接注入「必须先 `skill_view(name=…)`」。

### 层 B — 场景 RAG（处理长尾）

- 用户话 → Top-K 场景片段 → 拼成短块 **`[Routing hints]`**，插在**首条用户消息前**或作为单独 system 补充。
- 只给 **K 很小（例如 3）且带 `skill_view_name` 原文**，避免堆砌技能目录把模型搞晕。

### 层 C — Hermes 自带索引

- 仍保留 `skills_list` / 系统提示索引作兜底；可对模型约定：**若 RAG 未命中且不确定，先 `skills_list(category=…)` 再 `skill_view`**。

大量技能时，**不要让模型在脑子里维护几百个名字的相似度**；让它在层 A/B 已经缩小的集合里选。

---

## 3. 控制「索引噪音」：让少而准的进系统提示

Hermes 会把**所有可见技能**塞进 `<available_skills>`。技能特别多时：

- 用 **`requires_tools` / `requires_toolsets` / `fallback_for_*`**（SKILL.md frontmatter 里 `metadata.hermes`）把**当前会话不可能用到的技能从索引里藏起来**（框架原生能力）。
- 多 profile / 多 `external_dirs`：按**团队或产品线**拆技能树，别把所有 skill 挂在一个 profile 上。
- 对「仅某环境用」的 skill，用 **`skills.disabled` / `platform_disabled`** 在非目标环境关掉。

目标：**模型在提示里看到的候选越少，RAG / 规则越有效**。

---

## 4. 命名与元数据：降低「长得像」的误召

- **`description` 写触发条件**，不要只写「关于某某」；易混技能在 description 里写 **「与 X 的区别：…」**。
- 对外只暴露**稳定、唯一的 `skill_view` 字符串**，在组织文档 / RAG 里也只教这一种写法。
- 插件技能坚持 **`namespace:skill`**，避免与本地 `category:skill` 路径语义混淆。

---

## 5. 闭环：用「错例」持续喂数据集

- 记录：**用户场景摘要、模型选的 skill、实际应选的 skill**（可由人标，或自动：`skill_view` 失败后修正路径）。
- 把错例写成 **`scenario_text` + 正确 `skill_view_name` + `negative_skills`** 写回 RAG。
- 定期抽测：固定一批场景跑「仅路由层」或完整 Agent，看 Top-1 命中率。

---

## 6. 一句话策略

**大量技能 + 大量真实场景**时，不要依赖「模型读完整技能索引」；应：

1. **规则和绑定**砍掉确定场景；
2. **场景库 RAG** 把「这句话 → 唯一 `skill_view` 字符串」钉进上下文；
3. **frontmatter / 禁用 / 拆分目录**控制索引规模；
4. **错例迭代**数据集。

Hermes 仍负责执行 `skill_view` 与任务本身；**准确性主要由路由资产和索引工程承担**，而不是单靠模型扫几百条描述。

---

## 7. 场景 RAG 如何实现（工程路径）

### 7.1 数据与分块

每条记录建议是一个 **chunk**，例如：

- **`text`**：给 embedding 用的自然语言（可含多种同义表述）。
- **`skill_view_name`**：检索后**原样**写入提示，必须与 Hermes `skill_view` 可解析字符串一致。
- **`file_path`**（可选）：标准路径若需二次调用 `skill_view(..., file_path=...)`。
- **`negative`**（可选）：易混淆时写「不要用某 skill」。

导出 **JSONL** 或表，供离线建索引。

### 7.2 离线：Embedding + 索引

1. 对 `text`（可拼接说明字段）生成向量。
2. 存储：`id`、`vector`、`skill_view_name`、可选 `file_path`、`negative`、原文（便于 debug）。

**检索增强**：向量 Top-N 再叠 **BM25 / 关键词**（如 `rank_bm25`、Elasticsearch），**RRF 或加权合并** 得到最终 Top-K（K 建议 3～5），专有名词场景通常更稳。

### 7.3 在线：检索 → 路由块

1. 用户当前句 → 检索 Top-K。
2. 格式化为固定头 **`[Skill routing hints — from scenario playbook; follow when relevant]`**，每条命中包含：场景摘要、`skill_view(name='…')` 原文、可选 `file_path`、可选 negative。
3. 将该字符串拼在**首条用户消息之前**（或单独一条 user / system 补充），再进入 Hermes。

### 7.4 与 Hermes 的挂载点

Hermes **无内置 RAG 钩子**：在**外侧**统一处理即可：

- 自写网关 / 中间件：收消息 → RAG → 拼接 → 调 Hermes（CLI / SDK / 网关 API）。
- 或 CLI 包装：读入用户话 → RAG → 再启动会话。

可约定：若 routing hints 与模型猜测冲突，**以 hints 为准**。

### 7.5 质量与成本

- **K 要小**（约 3），控制 token 与误选。
- **相似度阈值**：过低则不注入，交给 `skills_list` 兜底。
- **会话内缓存**：同主题短时可复用检索结果。
- **观测**：记录 query、Top-1 skill、后续实际 `skill_view` 参数，供迭代数据集。

---

## 8. 本地部署 + 本地库：最快调测的外挂方式

目标：**本机向量库、尽量不启独立数据库服务、尽快验证「前缀 hints → Hermes 行为」**。

### 8.1 推荐组合

| 组件 | 建议 | 原因 |
|------|------|------|
| 向量库 | **Chroma `PersistentClient` + 本地目录** | `pip` 可用，无单独 DB 进程，数据落盘可反复调 |
| Embedding | **`sentence-transformers` + 小模型**（如 `all-MiniLM-L6-v2`） | 全离线、无 API、CPU 可跑 |
| 外挂 | **薄 Python**：检索 → 拼 `[Routing hints]` → 再调用 Hermes | 不改 Hermes 源码 |

**第一天只验证通路**：可先用 Chroma **内存模式**（不落盘），确认后再改为持久化路径。

### 8.2 三步立起

1. **环境**：`pip install chromadb sentence-transformers`（建议使用 venv）。
2. **建库**：读 JSONL（含 `text`、`skill_view_name` 等）→ 嵌入 → `collection.add(...)`；metadata 存 `skill_view_name` 等供检索后格式化。
3. **在线**：对用户句 `query` → 取 Top-3 → 生成路由块 → 与原始用户内容拼接后送入 Hermes。

### 8.3 为何优于一上来 pgvector / Milvus（针对调测阶段）

- 无需 Docker、少配置，**分钟级**可检索。
- 与 Hermes **零耦合**：RAG 只产出文本前缀。
- 调 chunk、K、阈值可快速重放同一会话。

### 8.4 更极简的 smoke test

连 Chroma 也可暂缓：用 **`sentence-transformers` + NumPy/sklearn 余弦相似度**，内存里放几百条场景向量，**单文件脚本**对比「加 hints / 不加」即可；验证有效后再换 Chroma 持久化。

### 8.5 集成时注意

1. **`skill_view_name` 与 Hermes 完全一致**；在 hints 里用引号给出，减少模型改写。
2. **K 取 2～3**；可加阈值，避免低相关乱配 skill。

---

*整理自对话（含场景 RAG 实现与本地快速外挂方案），保存于 `/Users/lan/work/0509/hermes-skill-routing-from-scenarios.md`。*
