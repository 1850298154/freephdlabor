# 文件队列限流器 - 实现逻辑详解

## 🎯 核心思想

**用文件作为共享队列，通过文件锁确保跨进程安全，实现精确的请求限流。**

---

## 📋 工作流程图

```
┌─────────────────────────────────────────────────────────────┐
│                     请求开始                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  创建文件锁文件         │  ← 防止并发冲突
         │  request_queue.lock    │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  读取队列文件           │
         │  request_queue.json    │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  获取最后请求时间       │  例如：last_time = 100.5秒
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────────────────┐
         │  计算下一个请求时间                 │
         │  next_time = max(当前, 上次) + 1秒 │
         │  例如：max(101.2, 100.5) + 1 = 102.2秒
         └───────────┬───────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  写入队列文件           │
         │  {                     │
         │    "id": "req_xxx",    │
         │    "scheduled_time":   │
         │      102.2,            │
         │    "status": "pending" │
         │  }                     │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  删除文件锁             │  ← 释放锁，允许其他进程
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  计算等待时间           │
         │  wait = 102.2 - 101.2  │
         │       = 1.0秒          │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  等待 wait 秒           │  ← 确保每秒一次
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  执行 API 请求          │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  从队列删除该请求       │
         └───────────┬───────────┘
                     │
                     ▼
                 请求完成
```

---

## 🔍 关键代码解析

### 1. 文件锁机制

```python
def _acquire_lock(self, timeout: float = 10.0) -> bool:
    """
    获取文件锁（跨平台）

    原理：
    1. 尝试创建一个特殊的锁文件 request_queue.lock
    2. 使用 O_CREAT | O_EXCL 标志（原子操作）
    3. 如果文件已存在，说明其他进程持有锁
    4. 等待并重试
    """
    while time.time() - start_time < timeout:
        try:
            # Windows 方式
            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            #                ↑ 创建      ↑ 排他      ↑ 只写
            # 如果成功，说明获得了锁
            os.close(fd)
            return True
        except FileExistsError:
            # 文件已存在，其他进程持有锁
            # 检查锁是否过期（超过10秒认为死锁）
            if self.lock_file.exists():
                lock_age = time.time() - self.lock_file.stat().st_mtime
                if lock_age > 10:
                    # 锁已过期，强制删除
                    os.remove(self.lock_file)
            # 等待一小段时间后重试
            time.sleep(0.01)
```

**为什么这样设计？**
- `O_CREAT | O_EXCL` 是原子操作，操作系统保证不会有并发问题
- 如果两个进程同时创建，只有一个能成功
- 死锁检测：如果进程崩溃没释放锁，10秒后自动清理

---

### 2. 队列管理

```python
def _get_next_request_time(self) -> float:
    """
    计算下一个请求时间

    例子：
    - 当前时间：101.2秒
    - 上次请求：100.5秒
    - 下次请求：max(101.2, 100.5) + 1 = 102.2秒
    - 等待时间：102.2 - 101.2 = 1.0秒
    """
    current_time = time.time()

    # 获取锁
    if not self._acquire_lock():
        raise RuntimeError("无法获取文件锁")

    try:
        # 读取队列
        queue = self._read_queue()  # 从 request_queue.json 读取

        # 找到最后一个请求时间
        last_request_time = 0.0
        if queue:
            queue.sort(key=lambda x: x.get('scheduled_time', 0))
            last_request_time = queue[-1].get('scheduled_time', 0)

        # 关键计算：确保至少间隔 1 秒
        next_time = max(current_time, last_request_time) + self.min_interval

        # 添加到队列
        request_id = f"req_{int(current_time * 1000000)}"
        queue.append({
            'id': request_id,
            'scheduled_time': next_time,    # 调度时间
            'created_at': current_time,     # 创建时间
            'status': 'pending'             # 状态
        })

        # 写入文件
        self._write_queue(queue)

        return next_time

    finally:
        # 释放锁
        self._release_lock()
```

**关键点：**
1. `max(current_time, last_request_time)` - 确保不会回退时间
2. `+ self.min_interval` - 加上最小间隔（1秒）
3. 文件锁保护整个读写过程

---

### 3. 等待执行

```python
def wait_for_turn(self) -> str:
    """
    等待轮到自己

    返回请求ID，用于后续删除
    """
    # 获取调度时间
    next_time = self._get_next_request_time()
    current_time = time.time()

    # 计算需要等待多久
    wait_seconds = next_time - current_time

    if wait_seconds > 0:
        print(f"[限流] 等待 {wait_seconds:.2f} 秒...")
        time.sleep(wait_seconds)  # 真正等待

    # 返回请求ID
    request_id = f"req_{int(current_time * 1000000)}"
    return request_id
```

---

### 4. 清理队列

```python
def done(self, request_id: str):
    """
    请求完成，从队列删除
    """
    # 再次获取锁
    if not self._acquire_lock():
        return

    try:
        queue = self._read_queue()
        # 过滤掉已完成的请求
        queue = [item for item in queue if item.get('id') != request_id]
        self._write_queue(queue)
    finally:
        self._release_lock()
```

---

## 📊 实际运行示例

### 场景：连续发送 3 个请求

```
时间线：
0.0秒 - 请求1 开始
  ├─ 获取锁
  ├─ 读取队列：[]
  ├─ 计算时间：max(0.0, 0) + 1 = 1.0秒
  ├─ 写入队列：[{id: req_1, time: 1.0}]
  ├─ 释放锁
  └─ 等待 1.0 秒

1.0秒 - 请求1 执行
  └─ 请求1 完成，从队列删除

1.1秒 - 请求2 开始
  ├─ 获取锁
  ├─ 读取队列：[]
  ├─ 计算时间：max(1.1, 0) + 1 = 2.1秒
  ├─ 写入队列：[{id: req_2, time: 2.1}]
  ├─ 释放锁
  └─ 等待 1.0 秒

2.1秒 - 请求2 执行
  └─ 请求2 完成，从队列删除

2.2秒 - 请求3 开始
  ├─ 获取锁
  ├─ 读取队列：[]
  ├─ 计算时间：max(2.2, 0) + 1 = 3.2秒
  ├─ 写入队列：[{id: req_3, time: 3.2}]
  ├─ 释放锁
  └─ 等待 1.0 秒

3.2秒 - 请求3 执行
  └─ 请求3 完成，从队列删除
```

**结果：**
- 总耗时：3.2秒
- 每个请求间隔：约1秒
- 符合速率限制要求

---

## 🔐 并发安全示例

### 场景：两个进程同时请求

```
进程A (时间 0.0秒)           进程B (时间 0.05秒)
     │                            │
     ├─ 尝试创建锁                 │
     ├─ 成功！✓                    │
     │                            ├─ 尝试创建锁
     │                            ├─ 失败！✗ (文件已存在)
     ├─ 读取队列                   │
     ├─ 计算时间: 1.0秒            ├─ 等待...
     ├─ 写入队列                   │
     ├─ 删除锁                     │
     │                            ├─ 成功获取锁！✓
     │                            ├─ 读取队列 (看到进程A的请求)
     │                            ├─ 计算时间: max(0.05, 1.0) + 1 = 2.0秒
     │                            ├─ 写入队列
     │                            ├─ 删除锁
     ├─ 等待 1.0 秒                │
     │                            ├─ 等待 1.95 秒
     ├─ 执行请求 (1.0秒)           │
     │                            ├─ 执行请求 (2.0秒)
```

**关键：**
- 文件锁保证同一时间只有一个进程能修改队列
- 进程B看到进程A的请求时间（1.0秒），所以计算出2.0秒
- 确保不会同时执行

---

## 📁 文件结构

```
request_queue.json          # 队列数据文件
├─ [
│    {
│      "id": "req_123456",        # 唯一ID
│      "scheduled_time": 102.2,   # 调度时间戳
│      "created_at": 101.2,       # 创建时间戳
│      "status": "pending"        # 状态
│    }
│  ]

request_queue.lock          # 锁文件（存在=被锁）
```

---

## ✅ 优势总结

| 特性 | 实现方式 | 效果 |
|------|---------|------|
| **跨进程安全** | 文件锁（O_CREAT\|O_EXCL） | ✅ 多进程安全 |
| **精确限流** | 时间戳队列 | ✅ 精确到毫秒 |
| **可视化** | JSON 文件 | ✅ 可随时查看 |
| **死锁处理** | 超时自动清理 | ✅ 健壮性强 |
| **跨平台** | Windows/Linux 适配 | ✅ 兼容性好 |

---

## 🎓 核心要点

1. **文件锁是关键** - 保证跨进程安全
2. **时间戳队列** - 精确控制请求时间
3. **原子操作** - 操作系统保证不会冲突
4. **两阶段执行** - 先排队，后执行
5. **自动清理** - 防止死锁和资源泄漏

这就是完整的实现逻辑！🎉
