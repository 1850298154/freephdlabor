# BibTeX CLI MCP Server - 安装配置指南

## ✅ 已完成

CLI 版本的 MCP 服务器已创建完成，包含以下文件：

```
D:\zyt\git_ln\freephdlabor\tests\playground\bibtex_cli_mcp\
├── server.py              # 主服务器文件（单文件实现）
├── README.md              # 使用文档
└── mcp_config_example.json # MCP 配置示例
```

## 📋 MCP 配置

### 配置示例

将以下配置添加到您的 MCP 客户端配置文件中：

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

### 配置文件位置

根据您的客户端类型，配置文件位置如下：

**Claude Code CLI**
- 位置：`~/.config/claude-code/mcp.json` 或项目根目录的 `.claude/mcp.json`
- 格式：JSON

**Claude Desktop**
- 位置：`%APPDATA%\Claude\claude_desktop_config.json` (Windows)
- 格式：JSON

## 🔧 核心特性

### 1. 单文件实现
- 所有功能集成在一个 Python 文件中
- 无需复杂的模块管理
- 易于维护和部署

### 2. stdio 传输
- 使用标准输入输出通信
- 无需 HTTP 服务器和端口管理
- 更稳定可靠

### 3. 自动速率限制
- 每秒一次请求限制
- 符合 Semantic Scholar API 规范
- 避免被封禁

### 4. 本地缓存
- 搜索结果自动缓存到 `.bibtex.json`
- 验证功能无需重复请求 API
- 提高响应速度

## 🛠️ 依赖安装

```bash
pip install mcp requests ratelimit tenacity
```

## 📝 使用方法

### 启动服务器

服务器会在 MCP 客户端调用时自动启动，无需手动运行。

如果需要手动测试：

```bash
cd D:\zyt\git_ln\freephdlabor\tests\playground\bibtex_cli_mcp
set S2_API_KEY=s2k-Fa0SA2LjDGWZ1iYaHgpwp7GqUQHrHkmv05EWFh9v
python server.py
```

### 可用工具

#### 1. search_bibtex_and_abstract

搜索论文并获取 BibTeX 格式引用。

**示例调用**：
```
请搜索关于 "attention mechanism" 的论文
```

#### 2. verify_citations_with_mismatches

验证 BibTeX 引用的准确性。

**示例调用**：
```
请验证以下引用：
@Article{Vaswani2017AttentionIA,
 author = {Ashish Vaswani},
 title = {Attention Is All You Need},
 year = {2017}
}
```

## ⚠️ 注意事项

### API 速率限制

Semantic Scholar API 有以下限制：

1. **无 API Key**：
   - 限制：100 次请求 / 5 分钟
   - 建议：设置 `S2_API_KEY` 环境变量

2. **有 API Key**：
   - 限制：5000 次请求 / 5 分钟
   - 建议：使用正确的 API Key

### 当前 API Key

配置中使用的 API Key：
```
s2k-Fa0SA2LjDGWZ1iYaHgpwp7GqUQHrHkmv05EWFh9v
```

如果遇到 403 Forbidden 错误，可能的原因：
1. API 临时速率限制
2. API Key 临时被封禁
3. 请求过于频繁

**解决方案**：
- 等待 5-10 分钟后重试
- 检查 API Key 是否有效
- 确保遵循每秒一次的速率限制

## 🔄 与 HTTP 版本对比

| 特性 | CLI 版本 (stdio) | HTTP 版本 |
|------|-----------------|-----------|
| 传输方式 | 标准输入输出 | HTTP + SSE |
| 连接管理 | ✅ 无需管理 | ❌ 需要管理 session |
| 端口占用 | ✅ 无 | ❌ 需要（如 7000） |
| 配置复杂度 | ✅ 简单 | ⚠️ 较复杂 |
| 稳定性 | ✅ 高 | ⚠️ 中等 |
| 调试难度 | ⚠️ 较难 | ✅ 较容易 |

## 📞 故障排除

### 问题：MCP 工具未出现

**检查清单**：
1. 确认配置文件位置正确
2. 确认 JSON 格式无误
3. 重启 MCP 客户端
4. 检查 Python 环境和依赖

### 问题：搜索失败

**检查清单**：
1. 检查网络连接
2. 确认 API Key 是否设置
3. 等待一段时间后重试（可能是速率限制）
4. 查看 `.bibtex.json` 缓存文件是否存在

### 问题：验证失败

**解决方案**：
1. 先使用搜索工具搜索该论文
2. 然后再进行验证
3. 检查 BibTeX 格式是否正确

## 🎯 下一步

1. **配置 MCP 客户端**：按照上述配置示例添加服务器
2. **重启客户端**：使配置生效
3. **测试工具**：尝试搜索和验证功能
4. **调整配置**：根据需要修改参数

## 📚 相关文档

- [Semantic Scholar API 文档](https://api.semanticscholar.org/api-docs/graph)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [Claude Code 文档](https://docs.anthropic.com/claude-code)
