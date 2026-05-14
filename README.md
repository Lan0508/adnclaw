# skill_router

本地场景 RAG 系统，为 Hermes AI Agent 提供技能路由提示。支持评估反馈闭环自动调优。

## 功能特性

- **向量检索**: 基于 sentence-transformers 的语义相似度匹配
- **BM25 混合检索**: 向量 + BM25 关键词检索，RRF 融合排序
- **阈值过滤**: 过滤低置信度结果，避免误导
- **Golden Cases 评估**: 基于标准答案集的准确率评估
- **自动诊断**: 分析未命中原因，生成优化建议
- **阈值调优**: 自动搜索最优阈值参数
- **闭环优化**: 新增 case 立即验证，自动补充缺失场景

## 安装

```bash
pip install -r requirements.txt
```

## 目录结构

```
.
├── README.md                # 本文档
├── requirements.txt         # 依赖
├── skill_router/            # 核心模块
│   ├── cli.py               # CLI 入口
│   ├── core/                # 基础模块
│   │   ├── schema.py        # 数据结构定义
│   │   ├── store.py         # ChromaDB 存储
│   │   ├── embedder.py      # 向量编码
│   │   └── hints.py         # 提示格式化
│   ├── retrieval/           # 检索模块
│   │   ├── query.py         # 查询执行
│   │   ├── build.py         # 索引构建
│   │   ├── bm25.py          # BM25 索引
│   │   └── wrap_cmd.py      # 消息包装
│   └── optimization/        # 评估优化模块
│       ├── eval.py          # 批量评估
│       ├── diagnose.py      # 问题诊断
│       ├── suggest.py       # 优化建议
│       ├── tune.py          # 阈值调优
│       └── golden.py        # Golden Cases 管理
├── data/                    # 数据目录
│   ├── scenarios.jsonl      # 场景库
│   ├── golden_cases.jsonl   # 标准答案集
│   └ suggestions.jsonl      # 优化建议
├── docs/                    # 详细文档
│   ├── README_skill_router.md
│   ├── skill-invocation-accuracy-overview.md
│   └── hermes-skill-routing-from-scenarios.md
└── chroma_data/             # 向量索引（自动生成）
```

## 使用方法

### 1. 构建索引

```bash
python -m skill_router build --input data/scenarios.jsonl --reset
```

### 2. 查询路由提示

```bash
# 基础查询
python -m skill_router query --question "Helm部署应用"

# 启用混合检索
python -m skill_router query --question "Helm部署" --hybrid

# 设置阈值过滤
python -m skill_router query --question "检查代码" --threshold 1.5
```

### 3. Golden Cases 管理

```bash
# 列出所有 golden cases
python -m skill_router golden list

# 添加新的 golden case
python -m skill_router golden add \
  --id gc-006 \
  --query "写Go语言单元测试" \
  --skill software-development/go-testing
```

### 4. 评估与优化

```bash
# 执行评估
python -m skill_router eval --threshold 2.0

# 诊断未命中原因
python -m skill_router diagnose --threshold 2.0

# 生成优化建议并自动应用
python -m skill_router suggest --threshold 2.0 --apply

# 自动调优阈值
python -m skill_router tune --min 0.5 --max 2.0 --step 0.1
```

### 5. 完整闭环流程

```bash
# 1. 添加新的 golden case
python -m skill_router golden add --id gc-new --query "xxx" --skill yyy

# 2. 立即评估验证
python -m skill_router eval --threshold 2.0

# 3. 如果未命中，生成建议并应用
python -m skill_router suggest --apply

# 4. 再次评估验证效果
python -m skill_router eval
```

## 数据格式

### 场景库 (scenarios.jsonl)

```json
{"id": "s-001", "text": "用户要在内网用Helm部署应用", "skill_view_name": "devops/k8s-helm", "negative": [], "notes": ""}
```

### Golden Cases (golden_cases.jsonl)

```json
{"id": "gc-001", "query": "Helm部署应用", "correct_skill": "devops/k8s-helm", "context": ""}
```

## 评估指标

| 指标 | 说明 |
|------|------|
| Hit Top-1 | 正确 skill 在第一位 |
| Hit Top-3 | 正确 skill 在前三 |
| Skip | 阈值过滤导致无结果 |
| Miss | 完全未命中 |

## 配置

- `HF_ENDPOINT`: HuggingFace 镜像地址（默认内置 hf-mirror.com）
- `SKILL_ROUTER_MODEL`: 自定义 embedding 模型

## 详细文档

- [功能概述](docs/README_skill_router.md)
- [技能调用准确性策略](docs/skill-invocation-accuracy-overview.md)
- [从场景到技能路由](docs/hermes-skill-routing-from-scenarios.md)