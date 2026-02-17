"""
Standalone BibTeX Generator - 提取自 FreePhD Labor 项目

这是一个独立的BibTeX生成工具，可以从论文元数据生成标准的BibTeX条目。

用法示例：
    from standalone_bibtex_generator import generate_bibtex

    citation = {
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        "year": "2017",
        "venue": "NeurIPS",
        "url": "https://arxiv.org/abs/1706.03762"
    }
    bibtex = generate_bibtex(citation)
    print(bibtex)
"""

import re
from typing import Dict, Any, Optional


def generate_bibtex(citation: Dict[str, Any]) -> Optional[str]:
    """
    Generate BibTeX entry for a citation.

    Args:
        citation: Dictionary containing paper metadata with keys:
            - title (required): Paper title
            - authors (optional): List of author names
            - year (optional): Publication year
            - venue (optional): Conference/Journal name
            - arxiv_id (optional): arXiv identifier
            - url (optional): Paper URL

    Returns:
        BibTeX formatted string or None if generation fails
    """
    try:
        title = citation.get("title", "").strip()
        if not title:
            return None

        # Generate citation key
        first_author = citation.get("authors", ["Unknown"])[0] if citation.get("authors") else "Unknown"
        first_author_last = first_author.split()[-1] if " " in first_author else first_author
        year = citation.get("year", "")

        # Clean author name for key
        clean_author = re.sub(r'[^\w]', '', first_author_last.lower())
        citation_key = f"{clean_author}{year}"

        # Choose entry type
        if citation.get("arxiv_id"):
            entry_type = "misc"
            note_field = f"arXiv preprint arXiv:{citation['arxiv_id']}"
        elif citation.get("venue") and "conference" in citation.get("venue", "").lower():
            entry_type = "inproceedings"
            note_field = ""
        elif citation.get("venue") and "journal" in citation.get("venue", "").lower():
            entry_type = "article"
            note_field = ""
        else:
            entry_type = "misc"
            note_field = ""

        # Format authors
        authors = citation.get("authors", [])
        if authors:
            author_str = " and ".join(authors)
        else:
            author_str = "Unknown"

        # Build BibTeX entry
        bibtex_lines = [f"@{entry_type}{{{citation_key},"]
        bibtex_lines.append(f'  title = {{{title}}},')
        bibtex_lines.append(f'  author = {{{author_str}}},')

        if year:
            bibtex_lines.append(f'  year = {{{year}}},')

        if citation.get("venue"):
            if entry_type == "inproceedings":
                bibtex_lines.append(f'  booktitle = {{{citation["venue"]}}},')
            elif entry_type == "article":
                bibtex_lines.append(f'  journal = {{{citation["venue"]}}},')

        if note_field:
            bibtex_lines.append(f'  note = {{{note_field}}},')

        if citation.get("url"):
            bibtex_lines.append(f'  url = {{{citation["url"]}}},')

        bibtex_lines.append("}")

        return "\n".join(bibtex_lines)

    except Exception as e:
        print(f"Warning: Failed to generate BibTeX for citation: {e}")
        return None


def extract_citation_key(bibtex: str) -> Optional[str]:
    """
    Extract citation key from BibTeX entry.

    Args:
        bibtex: BibTeX formatted string

    Returns:
        Citation key (e.g., "smith2024") or None
    """
    try:
        match = re.search(r'@\w+\{([^,]+),', bibtex)
        return match.group(1) if match else None
    except:
        return None


def generate_bibtex_batch(citations: list[Dict[str, Any]]) -> list[str]:
    """
    Generate multiple BibTeX entries from a list of citations.

    Args:
        citations: List of citation dictionaries

    Returns:
        List of BibTeX formatted strings
    """
    entries = []
    for citation in citations:
        bibtex = generate_bibtex(citation)
        if bibtex:
            entries.append(bibtex)
    return entries


# 示例使用
if __name__ == "__main__":
    # 示例1: arXiv预印本
    arxiv_citation = {
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Lukasz Kaiser", "Illia Polosukhin"],
        "year": "2017",
        "arxiv_id": "1706.03762",
        "url": "https://arxiv.org/abs/1706.03762"
    }

    # 示例2: 会议论文
    conference_citation = {
        "title": "Deep Residual Learning for Image Recognition",
        "authors": ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
        "year": "2016",
        "venue": "CVPR",
        "url": "https://arxiv.org/abs/1512.03385"
    }

    # 示例3: 期刊论文
    journal_citation = {
        "title": "A Universal Approximation Theorem for Deep Neural Networks",
        "authors": ["Kurt Hornik", "Stinchcombe Maxwell", "Halbert White"],
        "year": "1989",
        "venue": "Neural Networks Journal",
        "url": "https://doi.org/10.1016/0893-6080(89)90020-8"
    }

    print("=" * 60)
    print("示例1: arXiv预印本")
    print("=" * 60)
    print(generate_bibtex(arxiv_citation))
    print()

    print("=" * 60)
    print("示例2: 会议论文")
    print("=" * 60)
    print(generate_bibtex(conference_citation))
    print()

    print("=" * 60)
    print("示例3: 期刊论文")
    print("=" * 60)
    print(generate_bibtex(journal_citation))
