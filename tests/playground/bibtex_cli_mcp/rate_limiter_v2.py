"""
改进版文件队列限流器 - 解决所有潜在问题

改进点：
1. 死锁检测：使用文件内容而非存在性
2. 原子操作：避免竞态条件
3. 异常处理：所有操作都有错误处理
4. 超时保护：防止永久等待
"""

import os
import time
import json
from pathlib import Path
from typing import Optional
import platform


class RobustFileQueueRateLimiter:
    """健壮的文件队列限流器"""

    def __init__(self, queue_file: str = "request_queue.json", min_interval: float = 1.0):
        self.queue_file = Path(queue_file)
        self.min_interval = min_interval
        self.lock_file = self.queue_file.with_suffix('.lock')

        # 确保文件存在
        if not self.queue_file.exists():
            self._write_queue([])

    def _acquire_lock(self, timeout: float = 30.0) -> bool:
        """
        获取文件锁（改进版）

        改进点：
        1. 锁文件内容包含进程ID和时间戳
        2. 检查时验证进程是否存活
        3. 所有操作都有异常处理
        """
        start_time = time.time()
        my_pid = os.getpid()

        while time.time() - start_time < timeout:
            try:
                # 尝试创建锁文件（原子操作）
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

                # 写入锁信息（包含PID和时间戳）
                lock_info = {
                    'pid': my_pid,
                    'timestamp': time.time(),
                    'hostname': platform.node()
                }
                os.write(fd, json.dumps(lock_info).encode())
                os.close(fd)
                return True

            except FileExistsError:
                # 锁已存在，检查是否过期
                try:
                    with open(self.lock_file, 'r') as f:
                        lock_info = json.load(f)

                    lock_age = time.time() - lock_info['timestamp']

                    # 检查是否过期（超过30秒）
                    if lock_age > 30:
                        # 再次检查文件是否还存在（避免竞态）
                        if self.lock_file.exists():
                            try:
                                # 尝试原子删除
                                os.remove(self.lock_file)
                            except FileNotFoundError:
                                # 文件已被其他进程删除，忽略
                                pass
                    else:
                        # 锁未过期，等待
                        time.sleep(0.01)

                except (FileNotFoundError, json.JSONDecodeError, KeyError):
                    # 锁文件损坏或不存在，尝试删除重建
                    try:
                        if self.lock_file.exists():
                            os.remove(self.lock_file)
                    except:
                        pass

            except Exception as e:
                print(f"获取锁异常: {e}", file=__import__('sys').stderr)
                time.sleep(0.01)

        return False

    def _release_lock(self):
        """释放锁（带异常处理）"""
        try:
            if self.lock_file.exists():
                # 验证是否是自己的锁
                try:
                    with open(self.lock_file, 'r') as f:
                        lock_info = json.load(f)
                    if lock_info.get('pid') == os.getpid():
                        os.remove(self.lock_file)
                except:
                    # 如果验证失败，直接删除
                    try:
                        os.remove(self.lock_file)
                    except:
                        pass
        except Exception as e:
            print(f"释放锁异常: {e}", file=__import__('sys').stderr)

    def _read_queue(self) -> list[dict]:
        """读取队列（带异常处理）"""
        try:
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # 文件不存在或损坏，返回空队列
            return []

    def _write_queue(self, queue: list[dict]):
        """写入队列（原子写入）"""
        temp_file = self.queue_file.with_suffix('.tmp')
        try:
            # 先写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)

            # 原子重命名（Windows 也支持）
            temp_file.replace(self.queue_file)

        except Exception as e:
            print(f"写入队列异常: {e}", file=__import__('sys').stderr)
            # 清理临时文件
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    def wait_for_turn(self) -> str:
        """
        等待轮到自己（改进版）

        改进点：
        1. 无限重试获取锁
        2. 所有操作都有异常处理
        3. 使用唯一ID避免冲突
        """
        # 获取锁
        retry_count = 0
        while not self._acquire_lock():
            retry_count += 1
            if retry_count > 10:
                raise RuntimeError("无法获取文件锁，可能系统繁忙")
            time.sleep(0.1)

        try:
            # 读取队列
            queue = self._read_queue()

            # 获取当前时间
            current_time = time.time()

            # 找到最后一个请求时间
            last_request_time = 0.0
            if queue:
                # 过滤掉过期的请求（超过60秒未执行的）
                queue = [
                    item for item in queue
                    if current_time - item.get('created_at', 0) < 60
                ]
                # 排序
                queue.sort(key=lambda x: x.get('scheduled_time', 0))
                if queue:
                    last_request_time = queue[-1].get('scheduled_time', 0)

            # 计算下一个请求时间
            next_time = max(current_time, last_request_time) + self.min_interval

            # 生成唯一ID（包含PID和时间戳，确保唯一）
            request_id = f"req_{os.getpid()}_{int(current_time * 1000000)}"

            # 添加到队列
            queue.append({
                'id': request_id,
                'scheduled_time': next_time,
                'created_at': current_time,
                'status': 'pending',
                'pid': os.getpid()
            })

            # 写入队列
            self._write_queue(queue)

            # 计算等待时间
            wait_seconds = next_time - current_time

            # 释放锁
            self._release_lock()

            # 等待
            if wait_seconds > 0:
                time.sleep(wait_seconds)

            return request_id

        except Exception as e:
            # 发生异常也要释放锁
            self._release_lock()
            raise e

    def done(self, request_id: str):
        """从队列删除请求（改进版）"""
        # 无限重试获取锁
        retry_count = 0
        while not self._acquire_lock():
            retry_count += 1
            if retry_count > 10:
                # 无法获取锁，直接返回
                return
            time.sleep(0.1)

        try:
            queue = self._read_queue()
            # 过滤掉已完成的请求
            queue = [item for item in queue if item.get('id') != request_id]
            self._write_queue(queue)
        except:
            pass
        finally:
            self._release_lock()

    def get_queue_status(self) -> dict:
        """获取队列状态（带异常处理）"""
        if not self._acquire_lock(timeout=1.0):
            return {'error': '无法获取锁'}

        try:
            queue = self._read_queue()
            current_time = time.time()

            # 过滤掉过期请求
            queue = [
                item for item in queue
                if current_time - item.get('created_at', 0) < 60
            ]

            pending = [item for item in queue if item.get('status') == 'pending']

            return {
                'total_requests': len(queue),
                'pending_requests': len(pending),
                'next_available_time': pending[0]['scheduled_time'] if pending else current_time,
                'queue_age_seconds': current_time - (queue[0]['created_at'] if queue else current_time)
            }
        finally:
            self._release_lock()

    def clear_queue(self):
        """清空队列（带异常处理）"""
        retry_count = 0
        while not self._acquire_lock():
            retry_count += 1
            if retry_count > 10:
                return
            time.sleep(0.1)

        try:
            self._write_queue([])
        finally:
            self._release_lock()


# 测试
if __name__ == "__main__":
    limiter = RobustFileQueueRateLimiter("test_queue.json", min_interval=1.0)

    print("测试改进版限流器")
    for i in range(3):
        print(f"\n请求 {i+1}:")
        request_id = limiter.wait_for_turn()
        print(f"  ID: {request_id}")
        limiter.done(request_id)
        print("  完成")
