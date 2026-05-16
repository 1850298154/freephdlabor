"""
文件队列限流演示

展示文件队列限流器如何工作
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rate_limiter import FileQueueRateLimiter


def demo_single_process():
    """单进程演示"""
    print("=" * 60)
    print("单进程演示：文件队列限流")
    print("=" * 60)

    limiter = FileQueueRateLimiter("demo_queue.json", min_interval=1.0)

    print("\n清空队列...")
    limiter.clear_queue()

    print("\n开始发送 5 个请求...\n")

    start_time = time.time()

    for i in range(5):
        print(f"[请求 {i+1}] 准备发送...")
        request_id = limiter.wait_for_turn()

        elapsed = time.time() - start_time
        print(f"[请求 {i+1}] 开始执行 (耗时: {elapsed:.2f}秒)")

        # 模拟 API 请求
        time.sleep(0.05)

        limiter.done(request_id)
        print(f"[请求 {i+1}] 完成\n")

    total_time = time.time() - start_time
    print(f"总耗时: {total_time:.2f}秒")
    print(f"平均每个请求: {total_time/5:.2f}秒")

    # 查看队列状态
    status = limiter.get_queue_status()
    print(f"\n队列状态:")
    print(f"  总请求数: {status['total_requests']}")
    print(f"  待处理: {status['pending_requests']}")

    # 清理
    limiter.clear_queue()
    print("\n队列已清空")


def demo_queue_visualization():
    """队列可视化演示"""
    print("\n" + "=" * 60)
    print("队列可视化演示")
    print("=" * 60)

    limiter = FileQueueRateLimiter("demo_queue.json", min_interval=1.0)
    limiter.clear_queue()

    print("\n模拟多个请求进入队列...\n")

    # 快速添加 3 个请求到队列
    request_ids = []
    for i in range(3):
        request_id = limiter.wait_for_turn()
        request_ids.append(request_id)

        # 查看队列状态
        status = limiter.get_queue_status()
        print(f"请求 {i+1} 已加入队列")
        print(f"  队列中有 {status['pending_requests']} 个待处理请求")
        print()

    print("开始处理队列中的请求...\n")

    # 处理请求
    for i, request_id in enumerate(request_ids):
        print(f"处理请求 {i+1}/{len(request_ids)}")
        time.sleep(0.1)  # 模拟处理
        limiter.done(request_id)

        status = limiter.get_queue_status()
        print(f"  剩余 {status['pending_requests']} 个待处理请求\n")

    limiter.clear_queue()


def demo_concurrent_safety():
    """并发安全演示"""
    print("\n" + "=" * 60)
    print("并发安全演示")
    print("=" * 60)

    print("\n提示：此演示需要运行多个进程才能看到效果")
    print("在多个终端中同时运行此脚本，可以看到队列按顺序处理请求")

    limiter = FileQueueRateLimiter("demo_queue.json", min_interval=1.0)

    print("\n尝试获取队列位置...")
    request_id = limiter.wait_for_turn()

    import os
    print(f"\n进程 {os.getpid()} 获得执行权限")
    print(f"请求 ID: {request_id}")

    time.sleep(0.5)  # 模拟处理

    limiter.done(request_id)
    print("请求已完成")

    limiter.clear_queue()


if __name__ == "__main__":
    print("\n文件队列限流器演示\n")

    # 单进程演示
    demo_single_process()

    # 队列可视化
    demo_queue_visualization()

    # 并发安全（需要多进程）
    # demo_concurrent_safety()

    print("\n演示完成！")
