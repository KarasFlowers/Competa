"""Preset demo scenarios with cached reports.

Three scenarios covering different industries, each with a full cached report
adapted to Competa's ReportSection/Claim/Evidence schema so the frontend can
render them without any pipeline execution.
"""

from __future__ import annotations

from typing import Any


def _src(source_id: str, stype: str, title: str, snippet: str, url: str | None = None, reliability_score: float = 0.5) -> dict:
    return {
        "id": source_id,
        "type": stype,
        "title": title,
        "url": url,
        "content_snippet": snippet,
        "reliability_score": reliability_score,
    }


def _claim(claim_id: str, content: str, evidence_ids: list[str], confidence: float = 0.9, category: str = "") -> dict:
    return {
        "id": claim_id,
        "content": content,
        "evidence_ids": evidence_ids,
        "confidence": confidence,
        "category": category,
    }


def _section(title: str, content: str, claims: list[dict] | None = None, subsections: list[dict] | None = None) -> dict:
    return {
        "title": title,
        "content": content,
        "claims": claims or [],
        "subsections": subsections or [],
    }


# ---------------------------------------------------------------------------
# Scenario 1: AI 对话助手竞品分析
# ---------------------------------------------------------------------------
AI_ASSISTANT: dict[str, Any] = {
    "id": "ai-assistant",
    "name": "AI 对话助手竞品分析",
    "description": "分析中国市场主要 AI 对话助手产品的竞争格局",
    "industry": "AI 对话助手",
    "target_product": "豆包 (Doubao)",
    "competitors": [
        {"name": "Kimi", "category": "direct", "website": "https://kimi.moonshot.cn"},
        {"name": "DeepSeek", "category": "direct", "website": "https://chat.deepseek.com"},
        {"name": "通义千问", "category": "direct", "website": "https://tongyi.aliyun.com"},
    ],
    "our_product_notes": "字节跳动旗下 AI 对话助手",
    "focus_areas": ["功能对比", "用户体验", "市场份额", "技术架构", "定价策略"],
    "sources": [
        _src("src-1", "url", "QuestMobile 2025 Q4 中国移动互联网数据报告",
             "豆包月活 2.27 亿，稳居 AI 对话助手市场第一", "https://www.questmobile.com.cn", 0.75),
        _src("src-2", "url", "豆包官网",
             "多模态理解与生成，与抖音/飞书/即梦深度集成", "https://www.doubao.com", 0.9),
        _src("src-3", "url", "Kimi 官网",
             "200 万字超长上下文窗口，深度阅读与文档总结", "https://kimi.moonshot.cn", 0.9),
        _src("src-4", "url", "DeepSeek 官网",
             "全栈开源模型策略，API 价格仅为竞品 1/10", "https://chat.deepseek.com", 0.9),
        _src("src-5", "url", "通义千问官网",
             "阿里云企业生态深度集成，全模态能力", "https://tongyi.aliyun.com", 0.9),
        _src("src-6", "document", "36氪: AI 对话助手行业报告",
             "2025 年 AI 对话助手市场形成「一超多强」格局", reliability_score=0.7),
        _src("src-7", "interview", "产品经理访谈: 企业用户需求",
             "B 端用户最关注 API 稳定性和成本效益", reliability_score=0.6),
        _src("src-8", "survey", "用户满意度调研 N=1200",
             "豆包满意度 4.2/5，Kimi 4.0/5，DeepSeek 3.8/5", reliability_score=0.55),
    ],
    "report": {
        "title": "AI 对话助手竞品分析报告",
        "executive_summary": (
            "在中国 AI 对话助手市场，豆包（Doubao）凭借字节跳动的生态优势，"
            "截至 2025 年 Q4 月活用户达 2.27 亿，稳居市场第一。Kimi 以长文本处理能力见长，"
            "DeepSeek 以开源策略快速崛起，通义千问依托阿里云企业生态。"
            "各产品在多模态能力、上下文窗口、生态整合等维度存在差异化竞争。"
        ),
        "sections": [
            _section("市场格局概览",
                     "中国 AI 对话助手市场在 2024-2025 年经历了爆发式增长，形成了「一超多强」的竞争格局。"
                     "字节跳动的豆包凭借抖音、飞书等超级应用的导流效应，以超过 2 亿月活的规模遥遥领先。"
                     "第二梯队的 Kimi、DeepSeek 和通义千问各自凭借差异化能力争夺细分市场。",
                     [
                         _claim("c1", "豆包月活 2.27 亿，国内 AI 应用第一", ["src-1", "src-2"], 0.95, "market_share"),
                         _claim("c2", "AI 对话助手市场形成「一超多强」格局", ["src-1", "src-6"], 0.9, "market_structure"),
                     ]),
            _section("竞品详细分析", "", [], [
                _section("豆包 (Doubao)",
                         "字节跳动旗下 AI 对话助手，基于自研豆包大模型。凭借抖音（8 亿+ DAU）、飞书等超级应用的流量导入，"
                         "豆包迅速成为国内用户规模最大的 AI 原生应用。核心竞争力：日活超 1 亿，月活 2.27 亿；"
                         "全模态能力（文本、图片、语音、视频）；与抖音/飞书/即梦深度集成；AI 伴侣和智能体生态。",
                         [
                             _claim("c3", "豆包日活超 1 亿，月活 2.27 亿", ["src-1", "src-2"], 0.95, "user_scale"),
                             _claim("c4", "豆包支持文/图/音/视频多模态理解与生成", ["src-2"], 0.9, "feature"),
                         ]),
                _section("Kimi",
                         "月之暗面（Moonshot AI）推出的 AI 助手产品，创新性地提供 200 万字超长上下文窗口，"
                         "在学术研究、文档分析等深度阅读场景建立了独特壁垒。",
                         [
                             _claim("c5", "Kimi 提供 200 万字超长上下文窗口，业界最长", ["src-3"], 0.9, "feature"),
                         ]),
                _section("DeepSeek",
                         "深度求索（DeepSeek）以全栈开源策略和极致性价比在 2024-2025 年异军突起，"
                         "其 R1 推理模型在数学和代码任务上已达到 GPT-4 级别水平。",
                         [
                             _claim("c6", "DeepSeek R1 推理能力达到 GPT-4 级别", ["src-4", "src-6"], 0.85, "technology"),
                             _claim("c7", "DeepSeek API 价格仅为竞品的 1/10", ["src-4"], 0.9, "pricing"),
                         ]),
                _section("通义千问",
                         "阿里云旗下大模型 AI 助手，依托阿里云企业生态和电商场景，在 B 端市场有较强优势。",
                         [
                             _claim("c8", "通义千问依托阿里云企业生态深耕 B 端市场", ["src-5", "src-7"], 0.85, "market_position"),
                         ]),
            ]),
            _section("功能对比矩阵",
                     "| 维度 | 豆包 | Kimi | DeepSeek | 通义千问 |\n"
                     "| --- | --- | --- | --- | --- |\n"
                     "| 月活用户 | 2.27 亿 ★ | 约 3600 万 | 约 2000 万 | 约 1500 万 |\n"
                     "| 上下文窗口 | 128K tokens | 200 万字 ★ | 128K tokens | 128K tokens |\n"
                     "| 多模态能力 | 文/图/音/视频 ★ | 文本+图片 | 文本+图片+代码 | 文/图/音/视频 ★ |\n"
                     "| 代码能力 | 良好 | 良好 | 业界领先 ★ | 良好 |\n"
                     "| 生态整合 | 抖音+飞书+即梦 ★ | 独立应用为主 | 开源社区驱动 | 阿里云+淘宝+钉钉 |\n"
                     "| API 定价 | 中等 | 中高 | 极低 ★ | 中等 |",
                     [
                         _claim("c9", "豆包月活是第二名 Kimi 的 6.3 倍，马太效应显著", ["src-1"], 0.9, "market_share"),
                         _claim("c10", "DeepSeek API 价格仅为竞品 1/10，极致性价比", ["src-4"], 0.9, "pricing"),
                     ]),
            _section("SWOT 分析", "", [], [
                _section("豆包 SWOT",
                         "**优势**: 字节超级应用矩阵导流；月活遥遥领先；多模态体验成熟\n\n"
                         "**劣势**: 深度推理能力略逊于 DeepSeek；海外市场受 TikTok 政策影响\n\n"
                         "**机会**: AI 搜索替代传统搜索趋势；智能体生态商业化\n\n"
                         "**威胁**: DeepSeek 开源策略侵蚀 API 市场；监管政策不确定性",
                         [
                             _claim("c11", "豆包核心优势为字节超级应用矩阵导流效应", ["src-1", "src-2"], 0.9, "strength"),
                             _claim("c12", "DeepSeek 开源策略正在侵蚀 B 端 API 市场", ["src-4", "src-6"], 0.8, "threat"),
                         ]),
                _section("DeepSeek SWOT",
                         "**优势**: 开源赢得信任；极致性价比；推理能力强\n\n"
                         "**劣势**: C 端用户规模较小；商业化路径不清晰\n\n"
                         "**机会**: 全球开源社区增长；企业级私有化部署需求\n\n"
                         "**威胁**: 算力成本持续增长；大厂资源碾压",
                         [
                             _claim("c13", "DeepSeek 全栈开源策略赢得全球开发者信任", ["src-4"], 0.85, "strength"),
                         ]),
            ]),
            _section("战略建议",
                     "1. **豆包应强化深度推理能力**：在保持用户规模优势的同时，投入推理模型研发，补齐与 DeepSeek R1 的差距\n"
                     "2. **关注 AI 搜索替代趋势**：AI 对话助手正在从「聊天工具」演化为「AI 搜索引擎」，这是豆包依托字节搜索能力的战略机会\n"
                     "3. **智能体生态是下一个增长点**：让用户和开发者在豆包平台上创建和分发 AI 智能体，形成类似 App Store 的生态效应\n"
                     "4. **DeepSeek 的开源策略值得警惕**：其极致性价比正在吸引大量开发者和中小企业，可能侵蚀 B 端 API 市场",
                     [
                         _claim("c14", "建议豆包强化深度推理能力以应对 DeepSeek R1 竞争", ["src-4", "src-7"], 0.8, "recommendation"),
                         _claim("c15", "AI 搜索替代传统搜索是战略机会", ["src-6", "src-8"], 0.75, "recommendation"),
                     ]),
        ],
    },
    "traces": [
        {"agent_name": "collector", "events": [
            {"event_type": "start", "agent_name": "collector", "input_summary": "采集豆包/Kimi/DeepSeek/通义千问竞品信息"},
            {"event_type": "output", "agent_name": "collector", "output_summary": "采集 8 条来源，覆盖 4 个竞品", "token_count": 2350, "duration": 3.1},
        ], "total_duration": 3.1, "total_tokens": 2350, "status": "completed"},
        {"agent_name": "survey", "events": [
            {"event_type": "start", "agent_name": "survey", "input_summary": "设计竞品分析问卷"},
            {"event_type": "output", "agent_name": "survey", "output_summary": "生成 12 道问卷题目，覆盖功能/定价/体验维度", "token_count": 1800, "duration": 2.2},
        ], "total_duration": 2.2, "total_tokens": 1800, "status": "completed"},
        {"agent_name": "interview", "events": [
            {"event_type": "start", "agent_name": "interview", "input_summary": "设计用户访谈提纲"},
            {"event_type": "output", "agent_name": "interview", "output_summary": "生成 8 道访谈问题，含追问策略", "token_count": 1500, "duration": 1.8},
        ], "total_duration": 1.8, "total_tokens": 1500, "status": "completed"},
        {"agent_name": "analyst", "events": [
            {"event_type": "start", "agent_name": "analyst", "input_summary": "分析采集数据，提取结构化洞察"},
            {"event_type": "output", "agent_name": "analyst", "output_summary": "生成功能对比、SWOT、市场定位分析", "token_count": 3180, "duration": 2.8},
        ], "total_duration": 2.8, "total_tokens": 3180, "status": "completed"},
        {"agent_name": "writer", "events": [
            {"event_type": "start", "agent_name": "writer", "input_summary": "基于分析结果撰写报告"},
            {"event_type": "output", "agent_name": "writer", "output_summary": "报告草稿完成，含 5 个章节", "token_count": 4560, "duration": 4.2},
        ], "total_duration": 4.2, "total_tokens": 4560, "status": "completed"},
        {"agent_name": "filter", "events": [
            {"event_type": "start", "agent_name": "filter", "input_summary": "过滤无证据支撑的声明"},
            {"event_type": "output", "agent_name": "filter", "output_summary": "移除 0 条声明，保留 15 条", "token_count": 120, "duration": 0.3},
        ], "total_duration": 0.3, "total_tokens": 120, "status": "completed"},
        {"agent_name": "qa", "events": [
            {"event_type": "start", "agent_name": "qa", "input_summary": "质检报告完整性和证据覆盖率"},
            {"event_type": "output", "agent_name": "qa", "output_summary": "质检通过，evidence_coverage_rate=0.93", "token_count": 1890, "duration": 1.8},
        ], "total_duration": 1.8, "total_tokens": 1890, "status": "completed"},
    ],
    "metrics": {
        "source_count": 8,
        "claim_count": 15,
        "evidence_coverage_rate": 0.93,
        "manual_correction_count": 0,
    },
}


# ---------------------------------------------------------------------------
# Scenario 2: 短视频平台竞品分析
# ---------------------------------------------------------------------------
SHORT_VIDEO: dict[str, Any] = {
    "id": "short-video",
    "name": "短视频平台竞品分析",
    "description": "分析中国短视频平台的竞争格局，重点关注内容生态、商业化模式、AI 技术应用差异",
    "industry": "短视频/社交媒体",
    "target_product": "抖音",
    "competitors": [
        {"name": "快手", "category": "direct", "website": "https://www.kuaishou.com"},
        {"name": "小红书", "category": "indirect", "website": "https://www.xiaohongshu.com"},
        {"name": "B站", "category": "substitute", "website": "https://www.bilibili.com"},
    ],
    "our_product_notes": "字节跳动旗下短视频平台",
    "focus_areas": ["内容生态", "商业化模式", "AI 技术应用", "用户画像", "增长策略"],
    "sources": [
        _src("src-s1", "url", "QuestMobile 2025 Q4 中国移动互联网报告",
             "抖音 DAU 超 8 亿，快手 DAU 超 4 亿", "https://www.questmobile.com.cn", 0.75),
        _src("src-s2", "url", "抖音官网",
             "推荐算法业界标杆，抖音电商 GMV 突破 3 万亿", "https://www.douyin.com", 0.9),
        _src("src-s3", "url", "快手官网",
             "下沉市场渗透率第一，直播电商转化率高", "https://www.kuaishou.com", 0.9),
        _src("src-s4", "url", "小红书官网",
             "MAU 超 3 亿，种草→拔草消费决策闭环", "https://www.xiaohongshu.com", 0.9),
        _src("src-s5", "url", "B站官网",
             "MAU 超 3.4 亿，Z 世代用户占比超 50%", "https://www.bilibili.com", 0.9),
        _src("src-s6", "document", "字节跳动年度财报摘要",
             "抖音搜索日均搜索量超 6 亿，本地生活服务快速扩张", reliability_score=0.7),
        _src("src-s7", "interview", "品牌营销总监访谈",
             "小红书已成为品牌 KOC 种草首选平台", reliability_score=0.6),
        _src("src-s8", "survey", "短视频用户行为调研 N=2000",
             "抖音用户平均停留时长 120+ 分钟/天", reliability_score=0.55),
    ],
    "report": {
        "title": "短视频平台竞品分析报告",
        "executive_summary": (
            "中国短视频市场已形成「双巨头 + 两新势力」格局：抖音以 8 亿+ DAU 占据绝对领导地位，"
            "快手凭借下沉市场和直播电商稳居第二（DAU 4 亿+），小红书以「种草经济」开辟差异化赛道，"
            "B 站深耕 Z 世代中长视频社区。AI 技术应用成为新一轮竞争焦点。"
        ),
        "sections": [
            _section("市场格局概览",
                     "2024-2025 年，中国短视频市场总用户规模突破 10 亿，用户日均使用时长超过 120 分钟。"
                     "市场增长重心从用户规模扩张转向商业化深耕，电商、本地生活、AI 应用成为新的竞争维度。",
                     [
                         _claim("cs1", "抖音 DAU 超 8 亿，国内移动互联网 DAU 第二", ["src-s1", "src-s2"], 0.95, "market_share"),
                         _claim("cs2", "短视频市场增长重心转向商业化深耕", ["src-s1", "src-s6"], 0.85, "market_trend"),
                     ]),
            _section("竞品详细分析", "", [], [
                _section("抖音",
                         "字节跳动旗下国民级短视频应用，已从单一的短视频平台发展为覆盖电商、本地生活、搜索、社交的超级应用。"
                         "推荐算法是抖音的核心技术壁垒。核心竞争力：DAU 超 8 亿；个性化推荐算法全球标杆；"
                         "抖音电商 GMV 突破 3 万亿；抖音搜索日均搜索量超 6 亿；AI 特效/AI 生图/AI 短片创作工具。",
                         [
                             _claim("cs3", "抖音电商 GMV 突破 3 万亿，增速仍超 40%", ["src-s2", "src-s6"], 0.9, "revenue"),
                             _claim("cs4", "抖音搜索日均搜索量超 6 亿，正替代传统搜索引擎", ["src-s2", "src-s6"], 0.85, "feature"),
                         ]),
                _section("快手",
                         "快手以「真实、多元」的社区文化著称，在三四五线城市和中老年用户中有极高渗透率。"
                         "直播电商是快手最重要的商业化路径。核心竞争力：DAU 超 4 亿，下沉市场渗透率业界第一；"
                         "社区「老铁」文化，用户信任感和粘性高；快手电商 GMV 超 1.2 万亿。",
                         [
                             _claim("cs5", "快手下沉市场渗透率业界第一，DAU 超 4 亿", ["src-s1", "src-s3"], 0.9, "market_share"),
                         ]),
                _section("小红书",
                         "以高质量 UGC 笔记和「种草 → 拔草」消费闭环为核心，用户以一二线城市高消费力年轻女性为主，"
                         "已成为品牌营销必选平台。核心竞争力：MAU 超 3 亿，高消费力用户群体；种草→拔草消费决策闭环。",
                         [
                             _claim("cs6", "小红书已成为品牌 KOC 种草首选平台", ["src-s4", "src-s7"], 0.9, "market_position"),
                         ]),
                _section("B站",
                         "中国 Z 世代（18-35 岁）最集中的内容社区，以 ACG 文化为起点，"
                         "已扩展为覆盖知识、生活、科技的综合视频平台。核心竞争力：MAU 超 3.4 亿，Z 世代用户占比超 50%；"
                         "弹幕文化营造独特社区氛围；UP 主创作激励生态。",
                         [
                             _claim("cs7", "B站 Z 世代用户占比超 50%，MAU 超 3.4 亿", ["src-s5"], 0.9, "user_demographics"),
                         ]),
            ]),
            _section("功能对比矩阵",
                     "| 维度 | 抖音 | 快手 | 小红书 | B站 |\n"
                     "| --- | --- | --- | --- | --- |\n"
                     "| DAU/MAU | DAU 8 亿+ ★ | DAU 4 亿+ | MAU 3 亿+ | MAU 3.4 亿+ |\n"
                     "| 电商 GMV | 3 万亿+ ★ | 1.2 万亿+ | 千亿级 | 百亿级 |\n"
                     "| AI 技术应用 | 推荐+AI特效+AI搜索 ★ | AI直播+数字人+短剧 | AI搜索+笔记生成 | AI字幕+内容总结 |\n"
                     "| 核心用户群 | 全年龄段/全线城市 | 下沉市场/中老年 | 一二线/年轻女性 ★ | Z世代/学生群体 ★ |",
                     [
                         _claim("cs8", "抖音在推荐算法和 AI 特效上领先行业", ["src-s2", "src-s8"], 0.9, "technology"),
                     ]),
            _section("SWOT 分析", "", [], [
                _section("抖音 SWOT",
                         "**优势**: 推荐算法全球领先；用户规模碾压级优势；电商+本地生活多元变现\n\n"
                         "**劣势**: 用户时长增长见顶；社区信任感不如快手；内容同质化问题\n\n"
                         "**机会**: AI 搜索替代百度趋势；海外 TikTok 持续增长；本地生活侵蚀美团份额\n\n"
                         "**威胁**: 小红书分流高消费力用户；监管加强青少年使用限制；TikTok 海外政策风险",
                         [
                             _claim("cs9", "抖音推荐算法是全球标杆，用户平均停留 120+ 分钟", ["src-s2", "src-s8"], 0.9, "strength"),
                             _claim("cs10", "小红书正分流抖音高消费力用户", ["src-s4", "src-s7"], 0.75, "threat"),
                         ]),
            ]),
            _section("战略建议",
                     "1. **抖音应持续强化 AI 技术壁垒**：推荐算法、AI 搜索、AI 创作工具是抖音的核心竞争力\n"
                     "2. **关注短剧新业态**：短剧在 2025 年爆发式增长，是抖音和快手的新增长引擎\n"
                     "3. **电商差异化竞争**：抖音电商应学习小红书的「种草」模式，强化内容驱动的消费决策链路\n"
                     "4. **AI 数字人直播降本增效**：快手在 AI 数字人直播领域的探索值得关注\n"
                     "5. **防范小红书的搜索替代**：小红书正成为年轻人的「生活方式搜索引擎」",
                     [
                         _claim("cs11", "建议抖音持续强化 AI 技术壁垒保持领先", ["src-s2", "src-s6"], 0.85, "recommendation"),
                     ]),
        ],
    },
    "traces": [
        {"agent_name": "collector", "events": [
            {"event_type": "start", "agent_name": "collector", "input_summary": "采集抖音/快手/小红书/B站竞品信息"},
            {"event_type": "output", "agent_name": "collector", "output_summary": "采集 8 条来源，覆盖 4 个平台", "token_count": 2680, "duration": 3.4},
        ], "total_duration": 3.4, "total_tokens": 2680, "status": "completed"},
        {"agent_name": "survey", "events": [
            {"event_type": "start", "agent_name": "survey", "input_summary": "设计短视频平台竞品分析问卷"},
            {"event_type": "output", "agent_name": "survey", "output_summary": "生成 10 道问卷题目，覆盖内容/商业化/AI维度", "token_count": 1600, "duration": 2.0},
        ], "total_duration": 2.0, "total_tokens": 1600, "status": "completed"},
        {"agent_name": "interview", "events": [
            {"event_type": "start", "agent_name": "interview", "input_summary": "设计用户访谈提纲"},
            {"event_type": "output", "agent_name": "interview", "output_summary": "生成 7 道访谈问题，含追问策略", "token_count": 1400, "duration": 1.6},
        ], "total_duration": 1.6, "total_tokens": 1400, "status": "completed"},
        {"agent_name": "analyst", "events": [
            {"event_type": "start", "agent_name": "analyst", "input_summary": "分析采集数据，提取结构化洞察"},
            {"event_type": "output", "agent_name": "analyst", "output_summary": "生成功能对比、SWOT、市场定位分析", "token_count": 3960, "duration": 3.1},
        ], "total_duration": 3.1, "total_tokens": 3960, "status": "completed"},
        {"agent_name": "writer", "events": [
            {"event_type": "start", "agent_name": "writer", "input_summary": "基于分析结果撰写报告"},
            {"event_type": "output", "agent_name": "writer", "output_summary": "报告草稿完成，含 5 个章节", "token_count": 5240, "duration": 4.8},
        ], "total_duration": 4.8, "total_tokens": 5240, "status": "completed"},
        {"agent_name": "filter", "events": [
            {"event_type": "start", "agent_name": "filter", "input_summary": "过滤无证据支撑的声明"},
            {"event_type": "output", "agent_name": "filter", "output_summary": "移除 0 条声明，保留 11 条", "token_count": 100, "duration": 0.2},
        ], "total_duration": 0.2, "total_tokens": 100, "status": "completed"},
        {"agent_name": "qa", "events": [
            {"event_type": "start", "agent_name": "qa", "input_summary": "质检报告完整性和证据覆盖率"},
            {"event_type": "output", "agent_name": "qa", "output_summary": "质检通过，evidence_coverage_rate=0.91", "token_count": 2100, "duration": 2.0},
        ], "total_duration": 2.0, "total_tokens": 2100, "status": "completed"},
    ],
    "metrics": {
        "source_count": 8,
        "claim_count": 11,
        "evidence_coverage_rate": 0.91,
        "manual_correction_count": 0,
    },
}


# ---------------------------------------------------------------------------
# Scenario 3: AI 编程工具竞品分析
# ---------------------------------------------------------------------------
AI_CODING: dict[str, Any] = {
    "id": "ai-coding",
    "name": "AI 编程工具竞品分析",
    "description": "对比分析主流 AI 编程辅助工具的功能、技术架构和市场表现",
    "industry": "AI 开发工具",
    "target_product": "TRAE",
    "competitors": [
        {"name": "Cursor", "category": "direct", "website": "https://cursor.com"},
        {"name": "GitHub Copilot", "category": "direct", "website": "https://github.com/features/copilot"},
        {"name": "Windsurf", "category": "direct", "website": "https://windsurf.com"},
    ],
    "our_product_notes": "字节跳动旗下 AI IDE",
    "focus_areas": ["代码补全能力", "多文件编辑", "Agent 模式", "定价", "生态整合"],
    "sources": [
        _src("src-c1", "url", "Cursor 官网",
             "Agent 模式自主完成编程任务，多文件同时编辑", "https://cursor.com", 0.9),
        _src("src-c2", "url", "GitHub Copilot 官网",
             "全球最大装机量（2000 万+ 开发者），深度 GitHub 生态集成", "https://github.com/features/copilot", 0.9),
        _src("src-c3", "url", "TRAE 官网",
             "完全免费使用（含 Agent 模式），中文编程体验深度优化", "https://trae.ai", 0.9),
        _src("src-c4", "url", "Windsurf 官网",
             "Cascade 多步骤 Agent，Flow 流畅编码体验", "https://windsurf.com", 0.9),
        _src("src-c5", "document", "AI 编程工具行业报告 2025",
             "Agent 模式成为核心竞争维度，能否自主完成编程任务决定产品天花板", reliability_score=0.7),
        _src("src-c6", "interview", "开发者访谈: AI 编程工具使用偏好",
             "高级开发者更偏好 Agent 模式的自主性，初级开发者更需要代码补全", reliability_score=0.6),
        _src("src-c7", "survey", "AI 编程工具满意度调研 N=800",
             "Cursor 满意度 4.5/5，Copilot 4.2/5，TRAE 3.9/5，Windsurf 4.0/5", reliability_score=0.55),
        _src("src-c8", "url", "技术博客: AI IDE 对比评测",
             "Cursor 在 Agent 模式成熟度上领先，Copilot 在生态集成上最强", "https://techcrunch.com", 0.75),
    ],
    "report": {
        "title": "AI 编程工具竞品分析报告",
        "executive_summary": (
            "AI 编程工具市场正经历从「代码补全」到「Agent 自主编程」的范式转移。"
            "Cursor 以 Agent 模式和多文件编辑能力领跑创新，GitHub Copilot 依托 GitHub 生态拥有最大装机量，"
            "TRAE 作为后来者以免费策略和中文优化快速切入，Windsurf 以 Flow 体验和轻量化设计吸引个人开发者。"
            "2025 年 Agent 模式成为核心竞争维度。"
        ),
        "sections": [
            _section("市场格局概览",
                     "AI 编程工具市场在 2024-2025 年经历了从辅助补全到自主编程的范式转移。"
                     "GitHub Copilot 凭借先发优势和 GitHub 生态拥有最大装机量，Cursor 以技术创新引领 Agent 模式，"
                     "TRAE 和 Windsurf 作为新进入者分别以免费策略和体验差异化争夺市场。",
                     [
                         _claim("cc1", "AI 编程工具正从代码补全向 Agent 自主编程范式转移", ["src-c5", "src-c6"], 0.9, "market_trend"),
                         _claim("cc2", "Agent 模式成为 2025 年核心竞争维度", ["src-c5"], 0.9, "market_trend"),
                     ]),
            _section("竞品详细分析", "", [], [
                _section("Cursor",
                         "Anysphere 公司推出的 AI-first 代码编辑器，基于 VS Code 深度改造，以 Agent 模式和多文件编辑领跑市场。"
                         "核心竞争力：Agent 模式自主完成编程任务；多文件同时编辑（Multi-file Edit）；"
                         "深度代码库理解（Codebase Indexing）；支持 Claude/GPT/自定义模型。",
                         [
                             _claim("cc3", "Cursor Agent 模式是当前最成熟的自主编程方案", ["src-c1", "src-c8"], 0.9, "feature"),
                         ]),
                _section("GitHub Copilot",
                         "GitHub/微软推出的 AI 编程助手，拥有最大的开发者装机量和最成熟的 GitHub 生态集成。"
                         "核心竞争力：全球最大装机量（2000 万+ 开发者）；深度 GitHub 生态集成；"
                         "多 IDE 支持（VS Code/JetBrains/Neovim）；Copilot Workspace 协作空间。",
                         [
                             _claim("cc4", "Copilot 拥有 2000 万+ 开发者装机量，生态最强", ["src-c2"], 0.95, "market_share"),
                         ]),
                _section("TRAE",
                         "字节跳动推出的 AI IDE，以免费策略和中文优化快速获客。"
                         "核心竞争力：完全免费使用（含 Agent 模式）；中文编程体验深度优化；"
                         "Builder 模式一句话生成项目；集成豆包大模型能力。",
                         [
                             _claim("cc5", "TRAE 完全免费使用含 Agent 模式，是唯一免费方案", ["src-c3"], 0.9, "pricing"),
                         ]),
                _section("Windsurf",
                         "原 Codeium 品牌升级，以 Flow 流畅体验和 Cascade Agent 为核心卖点。"
                         "核心竞争力：Cascade 多步骤 Agent；Flow 流畅编码体验；轻量级设计/启动快；代码补全速度快。",
                         [
                             _claim("cc6", "Windsurf 以 Flow 体验和轻量化设计吸引个人开发者", ["src-c4", "src-c8"], 0.85, "market_position"),
                         ]),
            ]),
            _section("功能对比矩阵",
                     "| 维度 | Cursor | Copilot | TRAE | Windsurf |\n"
                     "| --- | --- | --- | --- | --- |\n"
                     "| Agent 模式 | 最成熟 ★ | 2025 新增 | Builder 模式 | Cascade |\n"
                     "| 多文件编辑 | 原生支持 ★ | Workspace | 支持 | Cascade 支持 |\n"
                     "| 定价 | $20/月 | $10/月 | **免费** ★ | $15/月 |\n"
                     "| 生态集成 | VS Code 插件 | GitHub 深度集成 ★ | 豆包模型 | 多 LLM 后端 |\n"
                     "| 中文优化 | 一般 | 一般 | **深度优化** ★ | 一般 |",
                     [
                         _claim("cc7", "Cursor 在 Agent 模式成熟度上领先行业", ["src-c1", "src-c5", "src-c8"], 0.9, "feature"),
                     ]),
            _section("SWOT 分析", "", [], [
                _section("TRAE SWOT",
                         "**优势**: 完全免费策略降低门槛；中文编程体验深度优化；字节内部工程实践融入\n\n"
                         "**劣势**: 生态成熟度不足；第三方插件支持有限；海外市场认知度低\n\n"
                         "**机会**: 中国开发者市场巨大；免费策略快速获客；字节生态协同\n\n"
                         "**威胁**: Cursor 技术领先；Copilot 生态壁垒高；开源替代方案增多",
                         [
                             _claim("cc8", "TRAE 免费策略是获客利器但商业化路径待验证", ["src-c3", "src-c5"], 0.85, "strength"),
                         ]),
            ]),
            _section("战略建议",
                     "1. **TRAE 应强化 Agent 模式能力**：免费策略获客后，需在 Agent 自主性上追赶 Cursor\n"
                     "2. **深耕中文开发者生态**：中文优化是 TRAE 的差异化壁垒，应持续投入\n"
                     "3. **利用字节生态协同**：与豆包大模型、飞书、抖音开发者工具深度集成\n"
                     "4. **关注企业级需求**：免费策略吸引个人开发者后，需构建企业版变现路径",
                     [
                         _claim("cc9", "建议 TRAE 强化 Agent 模式能力以追赶 Cursor", ["src-c1", "src-c5"], 0.8, "recommendation"),
                     ]),
        ],
    },
    "traces": [
        {"agent_name": "collector", "events": [
            {"event_type": "start", "agent_name": "collector", "input_summary": "采集 Cursor/Copilot/TRAE/Windsurf 竞品信息"},
            {"event_type": "output", "agent_name": "collector", "output_summary": "采集 8 条来源，覆盖 4 个工具", "token_count": 2100, "duration": 2.8},
        ], "total_duration": 2.8, "total_tokens": 2100, "status": "completed"},
        {"agent_name": "survey", "events": [
            {"event_type": "start", "agent_name": "survey", "input_summary": "设计AI编程工具竞品分析问卷"},
            {"event_type": "output", "agent_name": "survey", "output_summary": "生成 10 道问卷题目，覆盖补全/Agent/定价维度", "token_count": 1500, "duration": 1.8},
        ], "total_duration": 1.8, "total_tokens": 1500, "status": "completed"},
        {"agent_name": "interview", "events": [
            {"event_type": "start", "agent_name": "interview", "input_summary": "设计开发者访谈提纲"},
            {"event_type": "output", "agent_name": "interview", "output_summary": "生成 6 道访谈问题，含追问策略", "token_count": 1200, "duration": 1.4},
        ], "total_duration": 1.4, "total_tokens": 1200, "status": "completed"},
        {"agent_name": "analyst", "events": [
            {"event_type": "start", "agent_name": "analyst", "input_summary": "分析采集数据，提取结构化洞察"},
            {"event_type": "output", "agent_name": "analyst", "output_summary": "生成功能对比、SWOT、定价分析", "token_count": 3500, "duration": 2.5},
        ], "total_duration": 2.5, "total_tokens": 3500, "status": "completed"},
        {"agent_name": "writer", "events": [
            {"event_type": "start", "agent_name": "writer", "input_summary": "基于分析结果撰写报告"},
            {"event_type": "output", "agent_name": "writer", "output_summary": "报告草稿完成，含 5 个章节", "token_count": 4800, "duration": 4.0},
        ], "total_duration": 4.0, "total_tokens": 4800, "status": "completed"},
        {"agent_name": "filter", "events": [
            {"event_type": "start", "agent_name": "filter", "input_summary": "过滤无证据支撑的声明"},
            {"event_type": "output", "agent_name": "filter", "output_summary": "移除 0 条声明，保留 9 条", "token_count": 90, "duration": 0.2},
        ], "total_duration": 0.2, "total_tokens": 90, "status": "completed"},
        {"agent_name": "qa", "events": [
            {"event_type": "start", "agent_name": "qa", "input_summary": "质检报告完整性和证据覆盖率"},
            {"event_type": "output", "agent_name": "qa", "output_summary": "质检通过，evidence_coverage_rate=1.0", "token_count": 1800, "duration": 1.5},
        ], "total_duration": 1.5, "total_tokens": 1800, "status": "completed"},
    ],
    "metrics": {
        "source_count": 8,
        "claim_count": 9,
        "evidence_coverage_rate": 1.0,
        "manual_correction_count": 0,
    },
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Structured analysis (feature trees / pricing / personas / SWOT) powering the
# comparison matrix and SWOT quadrants in the frontend. Kept alongside each
# scenario's narrative report so demo mode renders the matrix without a pipeline run.
AI_ASSISTANT["analysis"] = {
    "feature_trees": [
        {"product_name": "豆包 (Doubao)", "root_nodes": [
            {"name": "多模态能力", "description": "文/图/音/视频全模态", "status": "supported", "children": []},
            {"name": "超长上下文", "description": "128K tokens", "status": "partial", "children": []},
            {"name": "深度推理", "description": "推理模型能力", "status": "partial", "children": []},
            {"name": "生态整合", "description": "抖音+飞书+即梦", "status": "supported", "children": []},
            {"name": "开源模型", "description": "", "status": "missing", "children": []},
        ]},
        {"product_name": "Kimi", "root_nodes": [
            {"name": "多模态能力", "description": "文本+图片", "status": "partial", "children": []},
            {"name": "超长上下文", "description": "200 万字，业界最长", "status": "supported", "children": []},
            {"name": "深度推理", "description": "", "status": "partial", "children": []},
            {"name": "生态整合", "description": "独立应用为主", "status": "missing", "children": []},
            {"name": "开源模型", "description": "", "status": "missing", "children": []},
        ]},
        {"product_name": "DeepSeek", "root_nodes": [
            {"name": "多模态能力", "description": "文本+图片+代码", "status": "partial", "children": []},
            {"name": "超长上下文", "description": "128K tokens", "status": "partial", "children": []},
            {"name": "深度推理", "description": "R1 达 GPT-4 级别", "status": "supported", "children": []},
            {"name": "生态整合", "description": "开源社区驱动", "status": "partial", "children": []},
            {"name": "开源模型", "description": "全栈开源", "status": "supported", "children": []},
        ]},
        {"product_name": "通义千问", "root_nodes": [
            {"name": "多模态能力", "description": "文/图/音/视频", "status": "supported", "children": []},
            {"name": "超长上下文", "description": "128K tokens", "status": "partial", "children": []},
            {"name": "深度推理", "description": "", "status": "partial", "children": []},
            {"name": "生态整合", "description": "阿里云+淘宝+钉钉", "status": "supported", "children": []},
            {"name": "开源模型", "description": "部分开源", "status": "partial", "children": []},
        ]},
    ],
    "pricing_models": [],
    "personas": [],
    "swot_analyses": [],
}
SHORT_VIDEO["analysis"] = {
    "feature_trees": [
        {"product_name": "抖音", "root_nodes": [
            {"name": "用户规模", "description": "DAU 8 亿+", "status": "supported", "children": []},
            {"name": "电商能力", "description": "GMV 3 万亿+", "status": "supported", "children": []},
            {"name": "AI 推荐", "description": "推荐+AI特效+AI搜索", "status": "supported", "children": []},
            {"name": "本地生活", "description": "侵蚀美团份额", "status": "partial", "children": []},
            {"name": "内容生态", "description": "全品类覆盖", "status": "supported", "children": []},
        ]},
        {"product_name": "快手", "root_nodes": [
            {"name": "用户规模", "description": "DAU 4 亿+", "status": "supported", "children": []},
            {"name": "电商能力", "description": "GMV 1.2 万亿+", "status": "supported", "children": []},
            {"name": "AI 技术", "description": "AI直播+数字人+短剧", "status": "partial", "children": []},
            {"name": "社区信任", "description": "下沉市场/中老年", "status": "supported", "children": []},
            {"name": "内容生态", "description": "直播+短剧+电商", "status": "supported", "children": []},
        ]},
        {"product_name": "小红书", "root_nodes": [
            {"name": "用户规模", "description": "MAU 3 亿+", "status": "supported", "children": []},
            {"name": "电商能力", "description": "千亿级 GMV", "status": "partial", "children": []},
            {"name": "搜索心智", "description": "生活方式搜索", "status": "supported", "children": []},
            {"name": "用户画像", "description": "一二线/年轻女性★", "status": "supported", "children": []},
            {"name": "内容生态", "description": "种草+笔记+直播", "status": "supported", "children": []},
        ]},
        {"product_name": "B站", "root_nodes": [
            {"name": "用户规模", "description": "MAU 3.4 亿+", "status": "supported", "children": []},
            {"name": "电商能力", "description": "百亿级 GMV", "status": "partial", "children": []},
            {"name": "AI 技术", "description": "AI字幕+内容总结", "status": "partial", "children": []},
            {"name": "用户画像", "description": "Z世代/学生群体★", "status": "supported", "children": []},
            {"name": "内容生态", "description": "中长视频+弹幕文化", "status": "supported", "children": []},
        ]},
    ],
    "pricing_models": [],
    "personas": [],
    "swot_analyses": [],
}

AI_CODING["analysis"] = {
    "feature_trees": [
        {"product_name": "Cursor", "root_nodes": [
            {"name": "Agent 模式", "description": "最成熟 ★", "status": "supported", "children": []},
            {"name": "多文件编辑", "description": "原生支持 ★", "status": "supported", "children": []},
            {"name": "定价", "description": "$20/月", "status": "partial", "children": []},
            {"name": "生态集成", "description": "VS Code 插件", "status": "partial", "children": []},
            {"name": "中文优化", "description": "一般", "status": "missing", "children": []},
        ]},
        {"product_name": "GitHub Copilot", "root_nodes": [
            {"name": "Agent 模式", "description": "2025 新增", "status": "partial", "children": []},
            {"name": "多文件编辑", "description": "Workspace", "status": "partial", "children": []},
            {"name": "定价", "description": "$10/月", "status": "supported", "children": []},
            {"name": "生态集成", "description": "GitHub 深度集成 ★", "status": "supported", "children": []},
            {"name": "中文优化", "description": "一般", "status": "missing", "children": []},
        ]},
        {"product_name": "TRAE", "root_nodes": [
            {"name": "Agent 模式", "description": "Builder 模式", "status": "partial", "children": []},
            {"name": "多文件编辑", "description": "支持", "status": "supported", "children": []},
            {"name": "定价", "description": "**免费** ★", "status": "supported", "children": []},
            {"name": "生态集成", "description": "豆包模型", "status": "partial", "children": []},
            {"name": "中文优化", "description": "**深度优化** ★", "status": "supported", "children": []},
        ]},
        {"product_name": "Windsurf", "root_nodes": [
            {"name": "Agent 模式", "description": "Cascade", "status": "partial", "children": []},
            {"name": "多文件编辑", "description": "Cascade 支持", "status": "partial", "children": []},
            {"name": "定价", "description": "$15/月", "status": "partial", "children": []},
            {"name": "生态集成", "description": "多 LLM 后端", "status": "supported", "children": []},
            {"name": "中文优化", "description": "一般", "status": "missing", "children": []},
        ]},
    ],
    "pricing_models": [],
    "personas": [],
    "swot_analyses": [],
}
DEMO_SCENARIOS: list[dict[str, Any]] = [AI_ASSISTANT, SHORT_VIDEO, AI_CODING]


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    for s in DEMO_SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None
