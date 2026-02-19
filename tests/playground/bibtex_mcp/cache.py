"""
缓存管理（有状态，单例，线程安全）
"""

import json
import os
import re
import threading


class Cache:
    """引用缓存（单例，线程安全）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.file = ".bibtex.json"
            self._data_lock = threading.Lock()
            self.data = self._load()
            self._initialized = True

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
        with self._data_lock:
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
        with self._data_lock:
            return self.data.get(key)

    def _extract_key(self, bibtex: str) -> str:
        """从BibTeX提取引用键"""
        m = re.search(r'@\w+\{([^,]+),', bibtex)
        return m.group(1) if m else ""
