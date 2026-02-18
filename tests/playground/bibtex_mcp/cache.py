"""
缓存管理（有状态）
"""

import json
import os
import re
from datetime import datetime


class Cache:
    """引用缓存"""

    def __init__(self):
        self.file = "cache"
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, bibtex: str, paper: dict):
        """添加论文到缓存"""
        key = self._extract_key(bibtex)
        if not key:
            return

        self.data[key] = {
            "title": paper.get("title", ""),
            "bibtex": bibtex,
            "abstract": paper.get("abstract", ""),
            "authors": paper.get("authors", []),
            "venue": paper.get("venue", ""),
            "year": paper.get("year", ""),
            "url": paper.get("url", ""),
        }
        self._save()

    def get(self, key: str) -> dict:
        """获取缓存的论文"""
        return self.data.get(key)

    def verify(self, bibtex_content: str) -> dict:
        """
        验证BibTeX内容

        返回: {
            "valid": bool,
            "matched": [{"key": "...", "title": "..."}],
            "not_found": [{"key": "..."}]
        }
        """
        keys = self._extract_all_keys(bibtex_content)
        matched = []
        not_found = []

        for key in keys:
            cached = self.get(key)
            if cached:
                matched.append({
                    "key": key,
                    "title": cached["title"]
                })
            else:
                not_found.append({
                    "key": key,
                    "message": "此引用不在缓存中"
                })

        return {
            "valid": len(not_found) == 0,
            "total": len(keys),
            "matched_count": len(matched),
            "not_found_count": len(not_found),
            "matched": matched,
            "not_found": not_found
        }

    def _extract_key(self, bibtex: str) -> str:
        """从BibTeX提取引用键"""
        m = re.search(r'@\w+\{([^,]+),', bibtex)
        return m.group(1) if m else ""

    def _extract_all_keys(self, content: str) -> list[str]:
        """从BibTeX提取所有引用键"""
        return re.findall(r'@\w+\{([^,]+),', content)
