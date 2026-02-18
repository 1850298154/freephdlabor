"""
论文引用缓存管理模块
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, Any

# 添加父目录到路径以支持直接运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config


class CitationCache:
    """论文引用缓存管理器（有状态，需要类）"""

    def __init__(self, cache_file: str = None):
        """初始化缓存"""
        self.cache_file = cache_file or Config.CACHE_FILE
        self.cache = self._load()

    def _load(self) -> Dict[str, Any]:
        """从文件加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        """保存缓存到文件"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def add(self, paper: Dict[str, Any]) -> str:
        """
        添加论文到缓存

        Returns:
            引用键
        """
        bibtex = paper.get('bibtex', '')
        citation_key = _extract_citation_key(bibtex)

        if not citation_key:
            citation_key = f"unknown_{datetime.now().timestamp()}"

        self.cache[citation_key] = {
            "title": paper.get('title', ''),
            "bibtex": bibtex,
            "abstract": paper.get('abstract', ''),
            "authors": paper.get('authors', []),
            "venue": paper.get('venue', ''),
            "year": paper.get('year', ''),
            "url": paper.get('url', ''),
            "cached_at": datetime.now().isoformat()
        }
        self._save()
        return citation_key

    def get(self, citation_key: str) -> Dict[str, Any]:
        """根据引用键获取论文"""
        return self.cache.get(citation_key)

    def list_all(self) -> Dict[str, Any]:
        """列出所有缓存的论文"""
        return self.cache

    def clear(self):
        """清空缓存"""
        self.cache = {}
        self._save()

    def verify(self, latex_content: str = "", bibtex_content: str = "") -> Dict[str, Any]:
        r"""
        验证LaTeX内容中的引用是否与缓存一致

        Args:
            latex_content: LaTeX文档内容（提取\cite{}引用）
            bibtex_content: .bib文件内容（验证BibTeX条目是否一致）

        Returns:
            验证结果
        """
        # 合并内容进行分析
        content = latex_content + "\n" + bibtex_content
        citation_keys = _extract_all_citation_keys(content)

        matched = []
        mismatched = []

        for key in citation_keys:
            cached = self.get(key)
            if cached:
                cached_bibtex = cached.get('bibtex', '')

                if key in bibtex_content:
                    entry = _extract_bibtex_entry(bibtex_content, key)
                    if entry:
                        if _bibtex_similar(entry, cached_bibtex):
                            matched.append({
                                "key": key,
                                "title": cached.get('title'),
                                "status": "matched"
                            })
                        else:
                            mismatched.append({
                                "key": key,
                                "title": cached.get('title'),
                                "status": "modified",
                                "cached": cached_bibtex[:100] + "...",
                                "provided": entry[:100] + "..."
                            })
                    else:
                        matched.append({
                            "key": key,
                            "title": cached.get('title'),
                            "status": "cite_only"
                        })
                else:
                    matched.append({
                        "key": key,
                        "title": cached.get('title'),
                        "status": "cite_only"
                    })
            else:
                mismatched.append({
                    "key": key,
                    "status": "not_cached",
                    "message": "此引用不在缓存中"
                })

        return {
            "valid": len(mismatched) == 0,
            "total": len(citation_keys),
            "matched_count": len(matched),
            "mismatched_count": len(mismatched),
            "matched": matched,
            "mismatched": mismatched
        }


# ========== 纯函数（无状态辅助函数） ==========

def _extract_citation_key(bibtex: str) -> str:
    """从BibTeX中提取引用键"""
    match = re.search(r'@\w+\{([^,]+),', bibtex)
    return match.group(1) if match else ""


def _extract_all_citation_keys(content: str) -> list[str]:
    """从LaTeX/BibTeX内容中提取所有引用键"""
    patterns = [
        r'\\cite\{([^}]+)\}',
        r'\\citep\{([^}]+)\}',
        r'\\citet\{([^}]+)\}',
        r'\\citeauthor\{([^}]+)\}',
        r'\\citeyear\{([^}]+)\}'
    ]
    keys = []
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            keys.extend([k.strip() for k in match.split(',')])
    bibtex_keys = re.findall(r'@\w+\{([^,]+),', content)
    keys.extend(bibtex_keys)
    return list(set(k.strip() for k in keys if k.strip()))


def _extract_bibtex_entry(content: str, citation_key: str) -> str:
    """从BibTeX内容中提取指定键的完整条目"""
    pattern = rf'@\w+\{{{re.escape(citation_key)},.*?\n\}}'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(0) if match else ""


def _bibtex_similar(bibtex1: str, bibtex2: str) -> bool:
    """比较两个BibTeX是否相似（忽略空格和大小写）"""
    normalize = lambda s: re.sub(r'\s+', ' ', s).strip().lower()
    return normalize(bibtex1) == normalize(bibtex2)
