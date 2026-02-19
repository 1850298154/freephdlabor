"""
测试验证功能
"""

import sys
sys.path.insert(0, '.')

from cache import Cache
from mcp_tools.verify import verify_citations

cache = Cache()

# 添加测试数据
paper1 = {
    'title': 'Attention Is All You Need',
    'bibtex': '@Article{Vaswani2017AttentionIA, title = {Attention Is All You Need}, author = {Ashish Vaswani}, year = {2017}}',
    'abstract': 'Abstract...',
    'authors': ['Ashish Vaswani'],
    'venue': 'NeurIPS',
    'year': '2017',
    'url': 'https://arxiv.org/abs/1706.03762'
}
cache.add(paper1['bibtex'], paper1)

print('=== 测试1: AI写对 ===')
test_correct = '''@Article{Vaswani2017AttentionIA, title = {Attention Is All You Need}, author = {Ashish Vaswani}, year = {2017}}
'''
import json

result1 = verify_citations(test_correct)
data1 = json.loads(result1)
print('结果:', '通过' if data1['valid'] else '失败')
print('匹配数:', data1['matched_count'])

print()
print('=== 测试2: AI写错 ===')
test_wrong = '''@Article{Vaswani2017AttentionIA, title = {Attention Is All You Need}, author = {Wrong Author}, year = {2017}}
'''
result2 = verify_citations(test_wrong)
data2 = json.loads(result2)
print('结果:', '通过' if data2['valid'] else '失败')
print('不匹配数:', data2['mismatched_count'])
