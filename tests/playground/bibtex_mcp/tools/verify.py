"""
BibTeX 验证工具模块（无状态，纯函数）
"""

import json
import sys
import os
from typing import Dict, Any

# 添加当前目录到路径以支持直接运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cache import CitationCache


def verify_citations(latex_content: str = "", bibtex_content: str = "", cache: CitationCache = None) -> str:
    """
    验证LaTeX内容中的引用是否与缓存一致

    Args:
        latex_content: LaTeX文档内容（提取\cite{}引用）
        bibtex_content: .bib文件内容（验证BibTeX条目是否一致）
        cache: 缓存管理器实例

    Returns:
        验证结果，包括匹配和未匹配的引用
    """
    if not cache:
        return json.dumps({
            "error": "Cache not provided",
            "suggestion": "Pass a CitationCache instance"
        }, ensure_ascii=False)

    result = cache.verify(latex_content, bibtex_content)
    return json.dumps(result, ensure_ascii=False, indent=2)
