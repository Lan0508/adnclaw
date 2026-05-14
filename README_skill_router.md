# skill_router — 本地场景 RAG（Hermes 外挂）

在仓库根目录 `/Users/lan/work/adnclaw` 下使用；**Top-K 固定为 3**，仅向量检索（无额外相似度阈值）。Embedding 使用 **sentence-transformers**（默认 `all-MiniLM-L6-v2`），向量库为 **Chroma 本地持久化**。

## 安装

```bash
cd /Users/lan/work/adnclaw
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

可选环境变量：

- `SKILL_ROUTER_MODEL`：覆盖默认 embedding 模型名（与 `sentence-transformers` 兼容的模型 id）。

## 数据格式（JSONL）

每行一个 JSON 对象，字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 稳定 id，`build` 时 upsert |
| `text` | 是 | 检索用自然语言 |
| `skill_view_name` | 是 | 传给 Hermes `skill_view(name='...')` 的字符串 |
| `file_path` | 否 | 若有，hints 中会多一行带 `file_path` 的 `skill_view` |
| `negative` | 否 | 字符串数组，易混 skill 名 |
| `notes` | 否 | 附加说明，进入 hints |

示例：`data/scenarios.example.jsonl`。

## 命令

在 **`adnclaw` 根目录**执行（使 `skill_router` 在 `sys.path` 中）：

### `build` — 建库 / 更新索引

```bash
python -m skill_router build --input data/scenarios.example.jsonl --chroma-dir ./chroma_data
```

首次或需清空重建：

```bash
python -m skill_router build --input data/scenarios.example.jsonl --chroma-dir ./chroma_data --reset
```

### `query` — 仅输出 `[Skill routing hints]`

```bash
python -m skill_router query --chroma-dir ./chroma_data --question "用户要在内网用 Helm 部署并回滚"
```

### `wrap` — 输出 hints + 空行 + 原用户话（便于管道）

```bash
python -m skill_router wrap --chroma-dir ./chroma_data --question "用户问题全文"
```

从 stdin 读用户话：

```bash
echo "用户问题全文" | python -m skill_router wrap --chroma-dir ./chroma_data
```

下游自行把 `wrap` 的 stdout 作为 Hermes 的 user 消息（或首条 user）。

## 与总览文档的关系

策略背景见 **`skill-invocation-accuracy-overview.md`** 与 **`hermes-skill-routing-from-scenarios.md`**。

## 注意

- `chroma_data/` 已列入 `.gitignore`。
- 首次下载 `sentence-transformers` 模型会联网；之后可离线使用缓存模型。
