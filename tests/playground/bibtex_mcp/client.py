"""
BibTeX MCP 客户端 - 测试用

功能:
    1. 搜索论文并缓存
    2. 提取BibTeX
    3. 提交验证
"""

import sys
import time

sys.path.insert(0, '.')

from tools import search_bibtex, verify_citations


def search_paper(query: str, limit: int = 2):
    """搜索论文"""
    print(f"\n[1/3] 搜索论文: {query}")
    print("-" * 50)

    result = search_bibtex(query, limit)
    data = eval(result)

    print(f"找到 {data['count']} 篇论文:")
    for i, paper in enumerate(data['papers'], 1):
        print(f"  {i}. {paper['title']}")
        print(f"     引用键: (需手动提取)")
        print(f"     年份: {paper['year']}, 会议/期刊: {paper['venue']}")
        print()

    # 返回BibTeX列表供后续提取
    return [p['bibtex'] for p in data['papers']]


def extract_bibtex_from_content(content: str) -> str:
    """
    从内容中提取所有BibTeX条目

    支持两种格式:
    1. @Article{...} ...
    2. 包在 \\begin{filecontents}...\\end{filecontents} 中
    """
    import re

    # 方法1: 直接提取 @Article{...} 格式
    bibtex_pattern = r'@[A-Za-z]+\{[^}]+(?:\n\s*[^@]*?\})+'
    matches = re.findall(bibtex_pattern, content, re.DOTALL)

    if matches:
        return '\n\n'.join(matches)

    # 方法2: 从 filecontents 中提取
    fc_pattern = r'\\begin\{filecontents\*?\}\{.*?\}([^@]*?)\\end\{filecontents\*?\}'
    fc_match = re.search(fc_pattern, content, re.DOTALL)
    if fc_match:
        return fc_match.group(1).strip()

    # 没找到BibTeX，返回空
    return ""


def verify(bibtex_content: str):
    """提交验证"""
    print(f"\n[2/3] 验证引用")
    print("-" * 50)

    result = verify_citations(bibtex_content)
    data = eval(result)

    print(f"总计: {data['total']} 个引用")
    print(f"匹配: {data['matched_count']} 个")
    print(f"未找到: {data['not_found_count']} 个")
    print(f"验证结果: {'通过' if data['valid'] else '失败'}")
    print()

    if data['matched']:
        print("匹配的引用:")
        for m in data['matched']:
            print(f"  ✓ {m['key']}: {m['title']}")
        print()

    if data['not_found']:
        print("未找到的引用:")
        for n in data['not_found']:
            print(f"  ✗ {n['key']}: {n['message']}")
        print()

    return data


def main():
    print("""
    ╔═════════════════════════════════════════════════════╗
    ║           BibTeX MCP Client - 测试                          ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    # 步骤1: 搜索论文
    query = "attention"
    bibtex_list = search_paper(query, limit=2)

    # 步骤2: 用户手动提取BibTeX
    print("\n" + "=" * 50)
    print("【步骤2】请提供BibTeX内容")
    print("提示: 从搜索结果中复制BibTeX条目")
    print("或者输入完整的.bib文件内容")
    print("按 Enter 继续...")
    print("=" * 50)

    # 步骤3: 用户输入BibTeX并验证
    user_input = input("BibTeX内容 (多行输入，以空行结束): ")

    if not user_input.strip():
        print("未输入BibTeX，跳过验证")
        return

    bibtex_content = user_input

    # 去掉可能的 filecontents 包装
    cleaned_content = extract_bibtex_from_content(bibtex_content)

    if not cleaned_content:
        print("错误: 未找到BibTeX内容")
        return

    print("\n提取到的BibTeX:")
    print("-" * 50)
    print(cleaned_content)
    print("-" * 50)

    # 步骤4: 验证
    verify_result = verify(cleaned_content)

    # 步骤5: 汇总
    print("\n" + "=" * 50)
    print("【汇总】")
    if verify_result['valid']:
        print("✓ 所有引用都匹配")
    else:
        print(f"✗ {verify_result['not_found_count']} 个引用未找到")
        print("   请使用 search_bibtex 先搜索并缓存这些论文")


if __name__ == "__main__":
    main()
