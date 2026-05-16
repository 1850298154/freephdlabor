# BibTeX CLI MCP Server - 文件队列限流版

## 🎯 核心特性

### 1. 文件队列限流
- **跨进程安全**：多个进程共享同一个队列
- **精确控制**：每秒一次请求，严格遵守 API 限制
- **可视化**：可查看队列状态和等待时间
- **自动清理**：支持手动清空队列

### 2. 三个工具

#### ① search_bibtex_and_abstract
搜索论文并获取 BibTeX 格式引用。

#### ② verify_citations_with_mismatches
验证 BibTeX 引用的准确性。

#### ③ get_queue_status（新增）
查看请求队列状态。

#### ④ clear_request_queue（新增）
清空请求队列。

## 📁 文件结构

```
bibtex_cli_mcp/
├── server.py              # 主服务器（集成文件队列限流）
├── rate_limiter.py        # 文件队列限流器
├── README.md              # 本文档
├── SETUP.md              # 安装配置指南
├── mcp_config_example.json # MCP 配置示例
└── test_server.py        # 测试脚本
```

## 🔧 工作原理

### 文件队列限流机制

```
请求流程：
1. 客户端发起搜索请求
   ↓
2. 创建文件锁（防止并发冲突）
   ↓
3. 读取队列文件，获取上一个请求时间
   ↓
4. 计算下一个请求时间 = max(当前时间, 上次时间) + 1秒
   ↓
5. 将请求写入队列文件
   ↓
6. 释放文件锁
   ↓
7. 等待到指定时间
   ↓
8. 执行 API 请求
   ↓
9. 从队列中删除请求记录
```

### 队列文件示例

`request_queue.json`:
```json
[
  {
    "id": "req_1778941209150309",
    "scheduled_time": 1778941210.1495564,
    "created_at": 1778941209.150309,
    "status": "pending"
  },
  {
    "id": "req_1778941210252361",
    "scheduled_time": 1778941211.1495564,
    "created_at": 1778941210.252361,
    "status": "pending"
  }
]
```

## 🚀 使用方法

### 1. 配置 MCP

将以下内容添加到 MCP 客户端配置：

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

### 2. 使用工具

#### 搜索论文
```
请搜索关于 "attention mechanism" 的论文
```

#### 验证引用
```
请验证以下 BibTeX 引用：
@Article{Vaswani2017AttentionIA,
 author = {Ashish Vaswani},
 title = {Attention Is All You Need},
 year = {2017}
}
```

#### 查看队列状态
```
请查看请求队列状态
```

#### 清空队列
```
请清空请求队列
```

## 📊 优势对比

### vs 内存限流

| 特性 | 文件队列限流 | 内存限流 |
|------|------------|---------|
| 跨进程安全 | ✅ 是 | ❌ 否 |
| 可视化队列 | ✅ 是 | ❌ 否 |
| 持久化 | ✅ 是 | ❌ 否 |
| 动态调整 | ✅ 是 | ⚠️ 难 |
| 性能开销 | ⚠️ 略高 | ✅ 低 |

### vs HTTP 版本

| 特性 | CLI + 文件队列 | HTTP 版本 |
|------|---------------|-----------|
| 传输方式 | stdio | HTTP + SSE |
| 连接管理 | ✅ 无需 | ❌ 需要 |
| 跨进程限流 | ✅ 支持 | ❌ 不支持 |
| 队列可视化 | ✅ 支持 | ❌ 不支持 |

## ⚙️ 配置选项

### 修改限流间隔

在 `server.py` 中修改：

```python
# 默认每秒一次
rate_limiter = FileQueueRateLimiter(str(QUEUE_FILE), min_interval=1.0)

# 改为每 2 秒一次
rate_limiter = FileQueueRateLimiter(str(QUEUE_FILE), min_interval=2.0)
```

### 修改队列文件位置

```python
# 默认在当前目录
QUEUE_FILE = Path(__file__).parent / "request_queue.json"

# 改为指定目录
QUEUE_FILE = Path("D:/my_queue/request_queue.json")
```

## 🐛 故障排除

### 问题：队列文件损坏

**解决方案**：
```bash
# 删除队列文件，让程序重新创建
rm request_queue.json
rm request_queue.lock
```

### 问题：锁文件未释放

**解决方案**：
程序会自动检测超过 10 秒的锁文件并清理，也可以手动删除：
```bash
rm request_queue.lock
```

### 问题：队列太长

**解决方案**：
使用 `clear_request_queue` 工具清空队列，或手动删除：
```bash
echo "[]" > request_queue.json
```

## 📝 测试

运行测试脚本：
```bash
cd D:\zyt\git_ln\freephdlabor\tests\playground\bibtex_cli_mcp
set S2_API_KEY=s2k-Fa0SA2LjDGWZ1iYaHgpwp7GqUQHrHkmv05EWFh9v
python test_server.py
```

## 💡 最佳实践

1. **设置 API Key**：提高速率限制到 5000 次/5分钟
2. **查看队列状态**：在批量操作前检查队列
3. **定期清理**：长时间运行后清空队列
4. **监控队列**：查看 `request_queue.json` 了解请求模式

## 📚 相关文档

- [Semantic Scholar API 文档](https://api.semanticscholar.org/api-docs/graph)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [SETUP.md](./SETUP.md) - 详细安装配置指南
