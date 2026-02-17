from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests
from requests.exceptions import RequestException

# 重试装饰器：最多重试3次，退避等待1s、2s、4s
@retry(stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=4),
       retry=retry_if_exception_type(RequestException))
# 限流装饰器：1分钟最多3次请求
@sleep_and_retry
@limits(calls=3, period=60)
def limited_retry_request(url):
    print('Making request to:', url)
    response = requests.get(url)
    response.raise_for_status()  # 非200状态码抛出异常触发重试
    return response

# 测试：连续调用4次，第4次会被限流，触发重试但仍会失败
for i in range(4):
    try:
        # res = limited_retry_request("https://httpbin.org/get")
        res = limited_retry_request("https://example.org/get")
        print(f"第{i+1}次请求成功")
    except Exception as e:
        print(f"第{i+1}次请求失败：{e}")