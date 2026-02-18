# Semantic Scholar Academic Graph API 完整汇总表

| 接口分类 | API 路径 | 作用 | 适用场景 | 解决什么问题 | 可配合使用的 API |
|--------|---------|------|---------|------------|----------------|
| 论文搜索 | GET /paper/autocomplete | 论文标题/关键词补全 | 搜索框联想、快速输入 | 减少输入错误，提升检索体验 | /paper/search、/paper/search/match |
| 论文搜索 | GET /paper/search | 相关性论文搜索 | 普通文献检索、按关键词查论文 | 快速找到相关领域论文 | /paper/batch、/paper/{paper_id} |
| 论文搜索 | GET /paper/search/bulk | 批量论文检索（无排序） | 大规模拉取论文、数据集构建 | 高效获取大量论文基础信息 | /author/batch、/paper/{paper_id} |
| 论文搜索 | GET /paper/search/match | 按标题精确匹配单篇论文 | 已知标题找论文、去重校验 | 精准定位某一篇文献 | /paper/{paper_id} |
| 单篇论文 | GET /paper/{paper_id} | 获取单篇论文详情 | 查看论文摘要、作者、引用、发表信息 | 全面了解一篇论文的所有元数据 | /paper/{id}/authors、/citations、/references |
| 单篇论文 | GET /paper/{paper_id}/authors | 获取某篇论文的所有作者 | 分析论文作者、团队、机构 | 快速提取一篇论文的作者列表 | /author/{author_id} |
| 单篇论文 | GET /paper/{paper_id}/citations | 获取引用该论文的所有论文 | 引文分析、研究影响力分析 | 知道谁在引用这篇论文 | /paper/search、/paper/batch |
| 单篇论文 | GET /paper/{paper_id}/references | 获取该论文引用的参考文献 | 文献溯源、梳理研究脉络 | 快速拿到论文的参考文献列表 | /paper/{paper_id}、/paper/batch |
| 批量论文 | POST /paper/batch | 批量获取多篇论文详情 | 一次性查多篇论文、批量解析 | 避免循环单查，提升效率 | /paper/search、/paper/search/bulk |
| 作者信息 | POST /author/batch | 批量获取多位作者详情 | 批量查学者信息、统计作者指标 | 高效获取多名作者的h指数、引用量 | /paper/{id}/authors |
| 作者信息 | GET /author/search | 按姓名搜索作者 | 找研究者、核实作者身份 | 快速定位研究者 | /author/batch、/author/{author_id} |
| 作者信息 | GET /author/{author_id} | 获取单个作者详情 | 学者画像、发表记录、h指数 | 全面了解一位作者的学术成果 | /paper/search、/paper/batch |
| 作者信息 | GET /author/{author_id}/papers | 获取某位作者的所有论文 | 统计学者产出、代表作 | 一键拉取学者发表的所有论文 | /paper/batch、/paper/search |

---

# 核心使用逻辑（必看）
1. **先搜索 → 再批量查详情**
   - /paper/search 或 /paper/search/bulk → 拿到 paperId
   - 再用 POST /paper/batch 批量拉取完整信息
2. **先查论文 → 再分析引用/作者**
   - /paper/{id} → 获取一篇论文
   - 再查 /authors /citations /references 做引文网络分析
3. **先找作者 → 再拉其所有论文**
   - /author/search 找到作者
   - /author/{id}/papers 拿到其论文列表
   - 再用 /paper/batch 批量解析
4. **最常用组合**
   - 搜索：/paper/search
   - 批量查：/paper/batch
   - 查引用：/paper/{id}/citations
