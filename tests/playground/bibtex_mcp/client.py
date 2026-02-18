"""
BibTeX MCP 客户端 - 测试用

功能:
    1. 搜索论文并缓存
    2. 输入完整BibTeX内容进行验证
"""

import sys
sys.path.insert(0, '.')

import json
from tools import search_and_cache, verify_citations


def main():
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║           BibTeX MCP Client - 测试                            ║
    ╠═════════════════════════════════════════════════════╣
    ║  功能:                                                    ║
    ║    1. search_bibtex - 搜索论文并缓存                ║
    ║    2. verify_citations - 验证BibTeX内容                ║
    ╚═════════════════════════════════════════════════════════╝
    """)

    print("\n" + "=" * 60)
    print("【操作选择】")
    print("1. 搜索论文")
    print("2. 验证BibTeX")
    print("=" * 60)

    choice = input("请选择 (1/2): ").strip()

    if choice == "1":
        # 搜索论文
        query = input("请输入搜索关键词: ").strip()
        limit = int(input("返回结果数量 (默认5): ") or 5)

        print(f"\n正在搜索: {query}...")
        result = search_and_cache(query, limit)
        data = json.loads(result)

        print(f"\n找到 {data['count']} 篇论文:\n")
        for i, paper in enumerate(data['papers'], 1):
            print(f"{i}. {paper['title']}")
            print(f"   引用键: (复制使用)")
            print(f"   BibTeX: {paper['bibtex'][:80]}...")
            print()

    elif choice == "2":
        # 验证BibTeX
        print("\n" + "=" * 60)
        print("【验证BibTeX】")
        print("请输入完整的BibTeX文件内容（多行，以空行结束）:")
        print("=" * 60)

        # # 读取多行输入
        # lines = []
        # while True:
        #     line = input("> ")
        #     if line.strip() == "":
        #         break
        #     lines.append(line)

        # bibtex_content = "\n".join(lines)
        bibtex_content = """@Article{Vaswani2017AttentionIA, title = {Attention Is All You Need}, author = {Ashish Vaswani}, year = {2017}}
        """
        bibtex_content = """@Article{Xiong2016一种基于多智能体的二层路径规划模型研究O,\n author = {Muzhou Xiong and Yong Li},\n booktitle = {计算机科学},\n journal = {计算机科学},\n pages = {59-64},\n title = {一种基于多智能体的二层路径规划模型研究 (Research on Two-layered Path Planning System Based on Multi-agent Simulation)},\n volume = {43},\n year = {2016}\n}\n"""

        print(f"\n收到 {len(bibtex_content)} 字符内容")

        # 调用验证
        result = verify_citations(bibtex_content)
        data = json.loads(result)

        print("\n" + "=" * 60)
        print("【验证结果】")
        print("=" * 60)

        # 判断结果
        if data['valid']:
            print("✓ 验证通过！所有引用都匹配且内容一致\n")

            print("匹配的引用 (完整BibTeX):")
            print("-" * 50)
            for m in data['matched']:
                print(f"【{m['key']}】")
                print(f"  标题: {m['title']}")
                print(f"  BibTeX:")
                # 逐行打印BibTeX
                for line in m['bibtex'].split('\n'):
                    print(f"    {line}")
                print()

        else:
            print(f"✗ 验证失败！\n")

            if data['not_found']:
                print("未找到的引用:")
                for n in data['not_found']:
                    print(f"  ✗ {n['key']}: {n['message']}")
                print()

            if data['mismatched']:
                print("内容不一致的引用:")
                for m in data['mismatched']:
                    print(f"  ✗ {m['key']}: {m['title']}")
                    print(f"     原因: {m['reason']}")
                    print(f"     缓存的BibTeX:")
                    for line in m['cached_bibtex'].split('\n'):
                        print(f"       {line}")
                    print(f"     输入的BibTeX:")
                    for line in m['input_bibtex'].split('\n'):
                        print(f"       {line}")
                    print()

        print("=" * 60)

    else:
        print("无效选择")


if __name__ == "__main__":
    main()
