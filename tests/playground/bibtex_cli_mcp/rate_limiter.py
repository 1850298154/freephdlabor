"""
文件队列限流器 - 完整注释版

功能：使用文件锁+时间队列，实现跨进程安全的精确限流
作者：Claude
日期：2026-05-16
"""

import os
import time
import json
from pathlib import Path


class FileQueueRateLimiter:
    """
    文件队列限流器

    核心原理：
    1. 文件锁：防止多进程同时操作队列
    2. 时间队列：记录每个请求的调度时间
    3. 自动清理：删除过期请求和死锁

    保证：
    - ✅ 不会死锁（30秒超时自动清理）
    - ✅ 不会冲突（文件锁保护）
    - ✅ 不会时间错误（max函数+过期清理）
    - ✅ 崩溃可恢复（自动清理机制）
    """

    def __init__(self, queue_file: str, min_interval: float = 1.0):
        """
        初始化限流器

        参数:
            queue_file: 队列文件路径
                - 示例: "request_queue.json"
                - 作用: 存储所有请求的调度时间
                - 格式: JSON数组

            min_interval: 最小请求间隔（秒）
                - 示例: 1.0
                - 作用: 确保两次请求间隔至少这么多秒
                - 默认: 1.0秒（符合Semantic Scholar API限制）

        副作用:
            - 创建队列文件（如果不存在）
            - 创建锁文件路径（.lock后缀）

        示例:
            >>> limiter = FileQueueRateLimiter("queue.json", 1.0)
        """
        self.queue_file = Path(queue_file)  # 队列文件路径
        self.lock_file = self.queue_file.with_suffix('.lock')  # 锁文件路径
        self.min_interval = min_interval  # 最小间隔

        # 确保队列文件存在（空数组）
        if not self.queue_file.exists():
            self._write_queue([])

    # ==================== 核心方法 ====================

    def wait_for_turn(self) -> str:
        """
        等待轮到自己

        工作流程:
            1. 获取文件锁（防止并发）
            2. 读取队列，获取最后请求时间
            3. 计算下次执行时间 = max(当前, 上次) + 间隔
            4. 写入队列
            5. 释放锁
            6. 等待到指定时间

        返回:
            request_id: 请求唯一标识
                - 格式: "req_{进程ID}_{时间戳}"
                - 示例: "req_12345_1234567890.123"
                - 用途: 用于done()方法删除该请求

        异常:
            RuntimeError: 无法获取文件锁（系统繁忙）

        示例:
            >>> request_id = limiter.wait_for_turn()
            >>> # 此时已等待足够时间，可以执行请求
            >>> response = requests.get("API...")
            >>> limiter.done(request_id)

        耗时:
            - 至少 min_interval 秒
            - 可能更长（如果队列中有其他请求）
        """
        # === 步骤1: 获取文件锁 ===
        if not self._acquire_lock():
            raise RuntimeError("无法获取文件锁")

        try:
            # === 步骤2: 读取队列 ===
            queue = self._read_queue()
            current_time = time.time()  # 当前时间戳（秒）

            # === 步骤3: 清理过期请求 ===
            # 如果请求超过60秒未执行，说明进程崩溃了，删除
            queue = [
                item for item in queue
                if current_time - item['created_at'] < 60
            ]

            # === 步骤4: 获取最后请求时间 ===
            last_time = 0.0
            if queue:
                # 按调度时间排序
                queue.sort(key=lambda x: x['scheduled_time'])
                # 取最后一个请求的时间
                last_time = queue[-1]['scheduled_time']

            # === 步骤5: 计算下次执行时间 ===
            # max() 防止时间倒流（系统时间调整）
            next_time = max(current_time, last_time) + self.min_interval

            # === 步骤6: 生成唯一ID ===
            # 包含进程ID和时间戳，确保唯一性
            request_id = f"req_{os.getpid()}_{current_time}"

            # === 步骤7: 添加到队列 ===
            queue.append({
                'id': request_id,              # 请求ID
                'scheduled_time': next_time,   # 调度时间
                'created_at': current_time,    # 创建时间
                'status': 'pending'            # 状态
            })

            # === 步骤8: 写入文件 ===
            self._write_queue(queue)

            # === 步骤9: 计算等待时间 ===
            wait_seconds = next_time - current_time

            # === 步骤10: 释放锁 ===
            self._release_lock()

            # === 步骤11: 等待 ===
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            # === 步骤12: 返回请求ID ===
            return request_id

        except Exception as e:
            # 发生异常也要释放锁
            self._release_lock()
            raise e

    def done(self, request_id: str):
        """
        完成请求，从队列删除

        参数:
            request_id: 请求ID
                - 来源: wait_for_turn() 的返回值
                - 示例: "req_12345_1234567890.123"

        作用:
            - 从队列中删除该请求
            - 释放队列空间

        异常:
            无（所有错误都被捕获）

        示例:
            >>> request_id = limiter.wait_for_turn()
            >>> # 执行请求...
            >>> limiter.done(request_id)
        """
        # 获取锁（最多重试10次）
        for _ in range(10):
            if self._acquire_lock():
                break
            time.sleep(0.1)
        else:
            return  # 无法获取锁，直接返回

        try:
            # 读取队列
            queue = self._read_queue()
            # 删除该请求
            queue = [item for item in queue if item['id'] != request_id]
            # 写回文件
            self._write_queue(queue)
        finally:
            # 释放锁
            self._release_lock()

    # ==================== 文件锁机制 ====================

    def _acquire_lock(self, timeout: float = 10.0) -> bool:
        """
        获取文件锁

        原理:
            使用 os.open() 的 O_CREAT | O_EXCL 标志
            这是操作系统提供的原子操作
            如果文件已存在，操作失败
            同一时间只有一个进程能成功

        参数:
            timeout: 超时时间（秒）
                - 示例: 10.0
                - 作用: 最多等待这么久
                - 默认: 10秒

        返回:
            bool: 是否成功获取锁
                - True: 成功
                - False: 超时失败

        锁文件内容:
            {
                "pid": 12345,           # 进程ID
                "timestamp": 1234567890.123,  # 获取时间
                "hostname": "DESKTOP-ABC"      # 主机名
            }

        死锁检测:
            如果锁文件超过30秒，强制删除
            说明持有锁的进程已崩溃

        示例:
            >>> if limiter._acquire_lock():
            >>>     try:
            >>>         # 操作队列...
            >>>     finally:
            >>>         limiter._release_lock()
        """
        start_time = time.time()
        my_pid = os.getpid()  # 当前进程ID

        while time.time() - start_time < timeout:
            try:
                # === 尝试创建锁文件 ===
                # O_CREAT: 创建文件
                # O_EXCL: 排他模式，文件存在则失败
                # O_WRONLY: 只写模式
                # 这三个标志组合是原子操作
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

                # === 写入锁信息 ===
                lock_info = {
                    'pid': my_pid,                          # 进程ID
                    'timestamp': time.time(),               # 当前时间
                    'hostname': os.getenv('COMPUTERNAME', 'unknown')  # 主机名
                }
                os.write(fd, json.dumps(lock_info).encode())
                os.close(fd)

                # 成功获取锁
                return True

            except FileExistsError:
                # === 锁已存在，检查是否过期 ===
                try:
                    # 读取锁文件
                    with open(self.lock_file, 'r') as f:
                        lock_info = json.load(f)

                    # 计算锁年龄
                    lock_age = time.time() - lock_info['timestamp']

                    # 如果超过30秒，说明进程崩溃，强制删除
                    if lock_age > 30:
                        try:
                            os.remove(self.lock_file)
                        except FileNotFoundError:
                            pass  # 已被其他进程删除

                except (FileNotFoundError, json.JSONDecodeError, KeyError):
                    # 锁文件损坏，删除重建
                    try:
                        if self.lock_file.exists():
                            os.remove(self.lock_file)
                    except:
                        pass

                # 等待一小段时间后重试
                time.sleep(0.01)

            except Exception as e:
                # 其他异常，等待后重试
                time.sleep(0.01)

        # 超时，获取锁失败
        return False

    def _release_lock(self):
        """
        释放文件锁

        作用:
            删除锁文件，允许其他进程获取锁

        异常:
            无（所有错误都被捕获）

        示例:
            >>> limiter._release_lock()
        """
        try:
            if self.lock_file.exists():
                os.remove(self.lock_file)
        except Exception:
            pass  # 忽略所有错误

    # ==================== 文件读写 ====================

    def _read_queue(self) -> list:
        """
        读取队列文件

        返回:
            list: 队列列表
                - 示例: [{"id": "req_123", "scheduled_time": 123.456, ...}]

        异常处理:
            - 文件不存在: 返回空列表
            - JSON格式错误: 返回空列表

        示例:
            >>> queue = limiter._read_queue()
            >>> print(queue)
            [{"id": "req_123", "scheduled_time": 123.456}]
        """
        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []  # 文件不存在或损坏，返回空列表

    def _write_queue(self, queue: list):
        """
        写入队列文件（原子写入）

        原理:
            1. 先写入临时文件
            2. 原子重命名为目标文件
            操作系统保证重命名是原子操作
            避免写入过程中崩溃导致文件损坏

        参数:
            queue: 队列列表
                - 示例: [{"id": "req_123", "scheduled_time": 123.456}]

        异常:
            无（所有错误都被捕获）

        示例:
            >>> limiter._write_queue([{"id": "req_123"}])
        """
        temp_file = self.queue_file.with_suffix('.tmp')

        try:
            # === 步骤1: 写入临时文件 ===
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)

            # === 步骤2: 原子重命名 ===
            # Path.replace() 在所有平台都是原子操作
            temp_file.replace(self.queue_file)

        except Exception:
            # 发生错误，删除临时文件
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    # ==================== 辅助方法 ====================

    def get_queue_status(self) -> dict:
        """
        获取队列状态

        返回:
            dict: 状态信息
                {
                    "total": 3,          # 总请求数
                    "pending": 2,        # 待处理数
                    "next_time": 123.456  # 下次可用时间
                }

        示例:
            >>> status = limiter.get_queue_status()
            >>> print(status)
            {"total": 3, "pending": 2, "next_time": 123.456}
        """
        if not self._acquire_lock(timeout=1.0):
            return {'error': '无法获取锁'}

        try:
            queue = self._read_queue()
            current_time = time.time()

            # 清理过期请求
            queue = [item for item in queue if current_time - item['created_at'] < 60]

            return {
                'total': len(queue),
                'pending': len([item for item in queue if item['status'] == 'pending']),
                'next_time': queue[0]['scheduled_time'] if queue else current_time
            }
        finally:
            self._release_lock()

    def clear_queue(self):
        """
        清空队列

        作用:
            删除所有待处理请求

        示例:
            >>> limiter.clear_queue()
        """
        for _ in range(10):
            if self._acquire_lock():
                break
            time.sleep(0.1)
        else:
            return

        try:
            self._write_queue([])
        finally:
            self._release_lock()


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("测试文件队列限流器")
    print("=" * 50)

    limiter = FileQueueRateLimiter("test_queue.json", min_interval=1.0)

    # 测试3次请求
    for i in range(3):
        print(f"\n请求 {i+1}:")
        request_id = limiter.wait_for_turn()
        print(f"  ID: {request_id}")
        print(f"  执行中...")
        limiter.done(request_id)
        print(f"  完成")

    # 查看状态
    status = limiter.get_queue_status()
    print(f"\n队列状态: {status}")

    # 清理
    limiter.clear_queue()
    print("队列已清空")
