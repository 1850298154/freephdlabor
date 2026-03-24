# BibTeX MCP Server

基于 Semantic Scholar API 的 BibTeX 搜索与引用验证 MCP 服务。

## 文件清单

### 核心代码（运行必需）

| 文件 | 作用 | 依赖 |
|------|------|------|
| `server.py` | MCP 服务入口，定义两个工具 | config, mcp_tools/search, mcp_tools/verify |
| `config.py` | 配置项（端口、API地址、密钥） | 无 |
| `api.py` | Semantic Scholar API 封装，带限流和重试 | config |
| `cache.py` | 缓存管理（单例模式，线程安全） | 无 |
| `mcp_tools/__init__.py` | 包初始化 | 无 |
| `mcp_tools/search.py` | 搜索工具实现 | api, cache |
| `mcp_tools/verify.py` | 验证工具实现 | cache |

### 配置文件（可选）

| 文件 | 作用 |
|------|------|
| `.env` | 环境变量（S2_API_KEY、HOST、PORT），有默认值可不提供 |
| `.bibtex.json` | 缓存数据，运行时自动生成，无需手动创建 |

### 测试代码（不需要）

| 文件 | 说明 |
|------|------|
| `test_mcp.py` | 测试脚本 |
| `test_mcp_final.py` | 测试脚本 |
| `test_mcp_sse.py` | 测试脚本 |
| `test_mcp_post_sse.py` | 测试脚本 |
| `test_mcp_session.py` | 测试脚本 |
| `test_verify.py` | 测试脚本 |

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        server.py                            │
│                     (MCP 服务入口)                           │
│                                                             │
│   @tool: search_bibtex_and_cache()  @tool: verify_citations()│
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────┐      ┌──────────────────────┐
│  mcp_tools/search.py │      │  mcp_tools/verify.py │
│    (搜索并缓存)       │      │    (验证引用)         │
└──────────┬───────────┘      └──────────┬───────────┘
           │                             │
           ├──────────┬──────────────────┤
           ▼          ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   api.py     │  │   cache.py   │  │   cache.py   │
│ (API调用)    │  │  (单例缓存)   │  │  (单例缓存)   │
└──────┬───────┘  └──────┬───────┘  └──────────────┘
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────────────┐
│  config.py   │  │   .bibtex.json       │
│   (配置)     │  │   (持久化缓存文件)    │
└──────────────┘  └──────────────────────┘
```

## 调用流程

### 1. 搜索流程

```
用户调用 search_bibtex_and_cache("attention is all you need", 5)
    │
    ▼
server.py -> mcp_tools/search.py: search_and_cache()
    │
    ├──► api.py: search() ──► Semantic Scholar API
    │                            │
    │                            ▼
    │                        返回论文列表
    │
    └──► cache.py: Cache.add() ──► 写入 .bibtex.json
    │
    ▼
返回 JSON 结果（含 title, bibtex, abstract 等）
```

### 2. 验证流程

```
用户调用 verify_citations_with_mismatches(bibtex_content)
    │
    ▼
server.py -> mcp_tools/verify.py: verify_citations()
    │
    ├──► 提取所有引用键 (@article{key, ...)
    │
    └──► cache.py: Cache.get(key) ──► 从 .bibtex.json 读取
            │
            ├──► 命中：比较 BibTeX 内容
            │       ├──► 一致 → matched
            │       └──► 不一致 → mismatched
            │
            └──► 未命中 → not_found
    │
    ▼
返回验证结果 JSON
```

## 启动方式

```bash
cd D:\zyt\git_ln\freephdlabor\tests\playground\bibtex_mcp
python server.py
```

服务地址：`http://localhost:7000/mcp`

## MCP 工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `search_bibtex_and_cache` | 搜索论文并自动缓存 | `query`: 搜索词, `limit`: 返回数量(默认5) |
| `verify_citations_with_mismatches` | 验证 BibTeX 引用是否与缓存一致 | `bibtex_content`: 完整 .bib 文件内容 |

## 依赖安装

```bash
pip install mcp requests ratelimit tenacity python-dotenv
```

## 最小文件集

如需部署，只需以下 **7 个 Python 文件**：

```
server.py
config.py
api.py
cache.py
mcp_tools/__init__.py
mcp_tools/search.py
mcp_tools/verify.py
```

`.env` 可选（有默认值），`.bibtex.json` 运行时自动生成。
