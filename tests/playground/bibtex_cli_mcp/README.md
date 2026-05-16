# BibTeX CLI MCP Server

基于 stdio 传输的 BibTeX MCP 服务器，无需 HTTP 连接，更简单稳定。

## 特点

- ✅ 使用 stdio 传输，无需管理 HTTP 连接和 session
- ✅ 自动速率限制（每秒一次请求）
- ✅ 本地缓存，避免重复请求
- ✅ 单文件实现，易于部署

## 安装依赖

```bash
pip install mcp requests ratelimit tenacity
```

## MCP 配置

在 Claude Code 或其他 MCP 客户端中添加以下配置：

```json
{
  "mcpServers": {
    "bibtex": {
      "command": "python",
      "args": [
        "D:\\zyt\\git_ln\\freephdlabor\\tests\\playground\\bibtex_cli_mcp\\server.py"
      ],
      "env": {
        "S2_API_KEY": "s2k-Fa0SA2LjDGWZ1iYaHgpwp7GqUQHrHkmv05EWFh9v"
      },
      "type": "stdio"
    }
  }
}
```

## 可用工具

### 1. search_bibtex_and_abstract

搜索论文并获取 BibTeX 格式引用。

**参数**：
- `query` (string): 搜索关键词
- `limit` (int, 可选): 返回数量，默认 5

**返回**：
```json
{
  "query": "machine learning",
  "count": 1,
  "papers": [
    {
      "title": "论文标题",
      "bibtex": "@Article{...}",
      "abstract": "摘要内容",
      "authors": ["作者1", "作者2"],
      "venue": "会议/期刊名称",
      "year": 2024,
      "url": "https://..."
    }
  ]
}
```

### 2. verify_citations_with_mismatches

验证 BibTeX 引用的准确性。

**参数**：
- `bibtex_content` (string): 完整的 .bib 文件内容

**返回**：
```json
{
  "valid": true,
  "total": 3,
  "matched_count": 2,
  "mismatched_count": 1,
  "not_found_count": 0,
  "matched": [...],
  "mismatched": [...],
  "not_found": [...]
}
```

## 文件结构

```
bibtex_cli_mcp/
├── server.py          # 主服务器文件（单文件实现）
├── README.md          # 本文档
└── .bibtex.json       # 缓存文件（自动生成）
```

## 与 HTTP 版本的区别

| 特性 | CLI 版本 (stdio) | HTTP 版本 |
|------|-----------------|-----------|
| 传输方式 | 标准输入输出 | HTTP + SSE |
| 连接管理 | 无需管理 | 需要管理 session |
| 端口占用 | 无 | 需要（如 7000） |
| 配置复杂度 | 简单 | 较复杂 |
| 稳定性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 使用示例

### 在 Claude Code 中使用

配置好后，可以直接调用工具：

```
请搜索关于 "attention mechanism" 的论文
```

Claude 会自动调用 `search_bibtex_and_abstract` 工具搜索论文。

### 验证引用

```
请验证以下 BibTeX 引用是否正确：

@Article{Vaswani2017AttentionIA,
 author = {Ashish Vaswani},
 title = {Attention Is All You Need},
 year = {2017}
}
```

Claude 会调用 `verify_citations_with_mismatches` 验证引用的完整性。

## 环境变量

- `S2_API_KEY`: Semantic Scholar API 密钥（可选，但建议设置以提高速率限制）

## 注意事项

1. **速率限制**：Semantic Scholar API 有速率限制，已设置为每秒一次请求
2. **缓存**：搜索结果会自动缓存到 `.bibtex.json` 文件
3. **API Key**：建议设置 `S2_API_KEY` 环境变量以获得更高的速率限制

## 故障排除

### 问题：搜索失败

**可能原因**：
- 未设置 API Key
- 达到速率限制
- 网络连接问题

**解决方案**：
1. 检查环境变量 `S2_API_KEY` 是否设置
2. 等待几秒后重试
3. 检查网络连接

### 问题：验证失败

**可能原因**：
- 缓存中未找到对应的论文

**解决方案**：
1. 先使用搜索工具搜索该论文
2. 然后再进行验证
