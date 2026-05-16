# BibTeX CLI MCP - 快速开始

## 📚 文档导航

### 🎯 新手入门
1. **[ARCHITECTURE.md](./ARCHITECTURE.md)** - 完整架构文档
   - 文件结构说明
   - 数据流程图
   - 配置参数说明

### 🔧 实现细节
2. **[PROBLEMS_SOLUTIONS.md](./PROBLEMS_SOLUTIONS.md)** - 问题-解决方案对照表
   - 6大问题详解
   - 代码位置标注
   - 关键参数说明

### 📖 代码文档
3. **[rate_limiter.py](./rate_limiter.py)** - 文件队列限流器（完整注释版）
   - 每个函数都有详细文档字符串
   - 每个参数都有说明
   - 每个操作都有注释

4. **[server.py](./server.py)** - MCP服务器（完整注释版）
   - 4个工具的完整文档
   - 参数说明和示例
   - 返回值格式说明

### 🚀 使用指南
5. **[SETUP.md](./SETUP.md)** - 安装配置指南
   - 依赖安装
   - MCP配置方法
   - 故障排查

---

## 🏃 5分钟快速开始

### 1. 安装依赖
```bash
pip install mcp requests
```

### 2. 配置MCP
```json
{
  "mcpServers": {
    "bibtex": {
      "command": "python",
      "args": ["D:\\zyt\\git_ln\\freephdlabor\\tests\\playground\\bibtex_cli_mcp\\server.py"],
      "env": {"S2_API_KEY": "your_api_key"},
      "type": "stdio"
    }
  }
}
```

### 3. 使用工具
```
请搜索关于 "attention mechanism" 的论文
请验证这个BibTeX引用
请查看队列状态
```

---

## 📊 核心特性

| 特性 | 说明 | 文档位置 |
|------|------|---------|
| **跨进程安全** | 文件锁机制 | PROBLEMS_SOLUTIONS.md#问题2并发冲突 |
| **精确限流** | 每秒一次请求 | rate_limiter.py:45 |
| **自动恢复** | 崩溃后自动清理 | PROBLEMS_SOLUTIONS.md#问题4进程崩溃 |
| **队列可视化** | 随时查看状态 | server.py:165 |

---

## 🔍 快速查找

### 我想了解...
- **文件结构** → [ARCHITECTURE.md#文件结构](./ARCHITECTURE.md#📁-文件结构)
- **数据流程** → [ARCHITECTURE.md#数据流程](./ARCHITECTURE.md#🔄-数据流程)
- **死锁解决** → [PROBLEMS_SOLUTIONS.md#问题1死锁](./PROBLEMS_SOLUTIONS.md#问题1死锁)
- **并发安全** → [PROBLEMS_SOLUTIONS.md#问题2并发冲突](./PROBLEMS_SOLUTIONS.md#问题2并发冲突)
- **时间计算** → [rate_limiter.py:88](./rate_limiter.py#L88)
- **文件锁** → [rate_limiter.py:155](./rate_limiter.py#L155)
- **API调用** → [server.py:97](./server.py#L97)

---

## 🎓 核心概念

### 文件队列限流器
```
请求 → 加锁 → 排队 → 等待 → 执行 → 完成
        ↓      ↓      ↓
      防冲突  精确限流  跨进程安全
```

### 关键参数
- **30秒**：锁超时（死锁检测）
- **60秒**：请求过期（崩溃恢复）
- **1.0秒**：限流间隔（API要求）

---

## 📞 故障排查

### 问题：队列堵塞
```bash
# 方法1：清空队列
python -c "from rate_limiter import FileQueueRateLimiter; FileQueueRateLimiter('queue.json').clear_queue()"

# 方法2：删除文件
rm request_queue.json request_queue.lock
```

### 问题：锁未释放
```bash
rm request_queue.lock
```

### 问题：API失败
- 检查API_KEY是否正确
- 等待几秒后重试（可能触发限流）
- 查看队列状态

---

## ✅ 质量保证

### 代码质量
- ✅ 每个函数都有文档字符串
- ✅ 每个参数都有说明
- ✅ 每个操作都有注释
- ✅ 所有异常都被处理

### 安全保证
- ✅ 不会死锁（30秒超时）
- ✅ 不会冲突（文件锁）
- ✅ 不会时间错误（max函数）
- ✅ 崩溃可恢复（自动清理）

### 文档质量
- ✅ 架构图清晰
- ✅ 问题-解决方案对照
- ✅ 代码位置标注
- ✅ 参数说明完整

---

**开始使用 → [ARCHITECTURE.md](./ARCHITECTURE.md)**
