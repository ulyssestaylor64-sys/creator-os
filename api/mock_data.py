"""
Creator OS — 业务假数据生成器
所有返回数据均为中文、贴近真实场景。
"""
import hashlib
import random
from datetime import datetime, timedelta
from typing import Any

random.seed(42)

TOPIC_TITLES = [
    "我把 ChatGPT 当同事用了 30 天，效率提升了 3 倍",
    "月薪 8000 和月薪 3 万的人，差在这一份周报",
    "别再手动整理会议纪要了，这套 AI 工作流 3 分钟搞定",
    "一个人做自媒体，我用 5 个 AI 员工替代了一个团队",
    "2026 年最值得学的 3 个 AI 工具，普通人也能上手",
    "为什么越努力越焦虑？可能你缺的是系统而不是自律",
    "我用这套提示词，把周报从 2 小时压缩到 15 分钟",
    "普通人学 AI 的最佳顺序，我踩过的 3 个坑",
    "自由职业第 200 天：我靠这 4 个习惯稳定月入 3 万",
    "桌面效率改造：这 5 个小东西让我每天多 1 小时",
    "我把工作流交给 AI 之后，终于有时间做内容了",
    "从 0 到 1 万粉，我只做对了 3 件事",
    "为什么你的内容没人看？先检查这 3 个细节",
    "每天 30 分钟，我用 AI 维持日更",
]

TOPIC_SOURCES = ["抖音热榜", "同赛道爆款", "搜索趋势", "创作灵感"]

TOPIC_AUDIENCES = [
    "25–35 职场人",
    "22–32 职场新人",
    "25–40 职场人 / 管理者",
    "24–35 个人创作者",
    "20–35 AI 初学者",
    "25–35 高压职场人",
]

FRAMEWORK_TEMPLATES = [
    [
        ["0–3s", "钩子 · 结果前置 + 身份代入", "「我让 AI 替我开完了 30 场会，结果老板以为我偷偷加了班。」"],
        ["3–25s", "展开 · 三个真实场景", "会议记录、周报汇总、跨部门同步，每个场景保留一个反常识转折。"],
        ["25–58s", "收束 · 可复用工作流", "给出 3 步工作流与模板，结尾引导评论区领取，不硬广。"],
    ],
    [
        ["0–3s", "钩子 · 身份对比 + 数字冲突", "「同样写周报，为什么他 10 分钟，你要 2 小时？」"],
        ["3–30s", "展开 · 两种周报结构对比", "展示真实截图：一个记流水账，一个用结果和下一步说话。"],
        ["30–55s", "收束 · AI 周报模板", "给出 3 段式模板与提示词，评论区领取。"],
    ],
    [
        ["0–3s", "钩子 · 结果前置", "「3 分钟开完一场会，纪要自动发到群里。」"],
        ["3–35s", "展开 · 录屏演示三步工作流", "录音转写、结构化提炼、自动分发，每一步都给替代方案。"],
        ["35–55s", "收束 · 工具组合 + 模板", "结尾只引导评论区领取模板，不做硬广。"],
    ],
]

HIT_TITLES = [
    "我把 ChatGPT 当同事用了 30 天，效率提升了 3 倍",
    "月薪 8000 和月薪 3 万的人，差在这一份周报",
    "一个人做自媒体的第 180 天：我留下了这 5 条经验",
    "别再手动写周报了，这套模板救了我 100 次",
    "我拒绝了月薪 5 万的 offer，因为算清了这笔账",
    "AI 工具清单：用了 60 个之后，我只留下了这 5 个",
]

# 固定爆款池：id 与内容一一对应，避免列表与拉片详情错位
HIT_POOL = [
    {
        "id": f"h_{2001 + i}",
        "idx": f"{i + 1:02d}",
        "title": title,
        "kind": "analyzed" if i < 4 else "saved",
        "plays": ["328.4w", "612.8w", "186.2w", "241.6w", "98.4w", "154.2w"][i],
        "likes": ["12.4w", "28.6w", "9.1w", "11.8w", "4.2w", "6.7w"][i],
        "tags": [
            ["钩子 · 结果前置", "情绪 · 掌控感"],
            ["钩子 · 身份对比", "结构 · 对比体"],
            ["情绪 · 真实共鸣", "结构 · 清单体"],
            ["钩子 · 痛点直击", "CTA · 领模板"],
            ["钩子 · 反常识", "情绪 · 身份认同"],
            ["结构 · 减法清单", "视觉 · 实拍"],
        ][i],
    }
    for i, title in enumerate(HIT_TITLES)
]

# 用户导入的爆款，进程内保存，便于导入后立即查看拉片详情
_IMPORTED_HITS: dict[str, dict] = {}
_IMPORT_SEQ = {"n": 0}

BRAND_NAMES = [
    "MOKA 咖啡",
    "Notion 中国",
    "飞书",
    "讯飞听见",
    "戴森",
    "新榜内容服务",
    "无忧传媒",
    "石墨文档",
    "语雀",
    "即刻",
]

BRAND_INDUSTRY = [
    "办公 / 效率场景",
    "知识管理 / SaaS",
    "企业协作 / 云文档",
    "AI 工具 / 会议场景",
    "生活方式 / 数码",
    "MCN / 内容服务",
    "MCN / 知识类账号商业化",
]

PIPELINE_STAGES = ["沟通中", "已报价", "待签约", "执行中", "已完成", "已暂停"]

SKILL_OPTIONS = [
    "职场经验", "AI 工具", "文案写作", "数据分析",
    "镜头表现", "剪辑制作", "教学讲解", "选题策划",
]

INTEREST_OPTIONS = [
    "AI 与效率", "职场成长", "个人成长", "消费测评",
    "生活方式", "知识科普", "自由职业", "副业赚钱",
]


def _today_str(days: int = 0) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%m.%d")


def _random_id(prefix: str = "id") -> str:
    return f"{prefix}_{random.randint(100000, 999999)}"


def _seed_rand(key: str) -> random.Random:
    """按固定 key 生成可复现的随机数，保证同一资源多次请求结果一致。"""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
    return random.Random(int(digest, 16))


# 固定选题池：同一 id 的列表与详情必须一致
_TOPIC_SEED = [
    ("t_1001", 0, "抖音热榜", "25–35 职场人", "竞争 中", "预估 25–60w 播放", 95, 9.4, "+124%",
     "结果前置 + 30 天实验体，适合直接复刻你的「亲测」系列结构。"),
    ("t_1002", 1, "同赛道爆款", "25–40 职场人 / 管理者", "竞争 高", "预估 35–70w 播放", 88, 8.9, "+41%",
     "身份对比制造强冲突，前 3 秒留存高，但同质化严重，需要新角度。"),
    ("t_1003", 2, "搜索趋势", "22–32 职场新人", "竞争 低", "预估 20–50w 播放", 92, 9.1, "+26%",
     "搜索需求持续上升，你的会议纪要系列可以直接承接，转化基础最好。"),
    ("t_1004", 3, "创作灵感", "24–35 个人创作者", "竞争 中", "预估 15–40w 播放", 90, 8.6, "+18%",
     "人设 + 清单体，适合强化「一人公司」标签，评论区易产生工具追问。"),
    ("t_1005", 4, "抖音热榜", "20–35 AI 初学者", "竞争 高", "预估 45–90w 播放", 86, 9.6, "+9%",
     "流量稳定但广告感强，建议用「真实使用 30 天」降低推广感。"),
    ("t_1006", 5, "同赛道爆款", "25–35 高压职场人", "竞争 低", "预估 20–50w 播放", 83, 8.4, "+12%",
     "情绪共鸣型内容互动率高但涨粉慢，适合每周一条调节节奏。"),
    ("t_1007", 6, "搜索趋势", "25–35 职场人", "竞争 低", "预估 15–40w 播放", 89, 8.8, "新",
     "提示词类内容收藏率高，可承接模板领取，形成私域入口。"),
    ("t_1008", 7, "创作灵感", "20–35 AI 初学者", "竞争 中", "预估 25–60w 播放", 85, 8.2, "新",
     "踩坑复盘天然带信任感，适合做成系列第二条，承接上一条流量。"),
    ("t_1009", 10, "创作灵感", "24–35 个人创作者", "竞争 低", "预估 20–50w 播放", 91, 8.7, "+31%",
     "「终于有时间」是强共鸣点，适合用真实日程表做证据，承接自由职业人群。"),
    ("t_1010", 11, "同赛道爆款", "22–32 职场新人", "竞争 高", "预估 35–70w 播放", 87, 9.0, "+22%",
     "涨粉复盘类内容收藏率高，建议只讲 3 件事，避免变成流水账。"),
    ("t_1011", 12, "抖音热榜", "25–35 职场人", "竞争 中", "预估 15–40w 播放", 84, 8.5, "+14%",
     "问题诊断型开头留人强，适合做成系列合集，提升主页停留。"),
    ("t_1012", 13, "搜索趋势", "20–35 AI 初学者", "竞争 低", "预估 15–40w 播放", 93, 8.3, "新",
     "「每天 30 分钟」降低行动门槛，搜索需求稳定，适合长期更新。"),
]

TOPIC_POOL = [
    {
        "id": row[0],
        "title": TOPIC_TITLES[row[1]],
        "source": row[2],
        "audience": row[3],
        "competition": row[4],
        "estimate": row[5],
        "match": row[6],
        "heat": row[7],
        "rise": row[8],
        "peak": round(row[7] * 1.06, 1),
        "desc": row[9],
    }
    for row in _TOPIC_SEED
]


def health() -> dict:
    return {
        "status": "ok",
        "service": "Creator OS API",
        "version": "2.4.0",
        "time": datetime.now().isoformat(),
    }


def generate_topics(source: str = "all", refresh: bool = False) -> list[dict]:
    """返回固定选题池；refresh 会多返回新选题，但 id 与内容保持稳定。"""
    limit = 8 if refresh else 6
    if source in ("all", "", None):
        # 按来源轮转取数，保证每个标签页都有足够内容
        buckets: dict[str, list[dict]] = {}
        for t in TOPIC_POOL:
            buckets.setdefault(t["source"], []).append(t)
        ordered = [buckets.get(s, []) for s in TOPIC_SOURCES]
        pool: list[dict] = []
        depth = 0
        while len(pool) < limit and any(depth < len(b) for b in ordered):
            for bucket in ordered:
                if depth < len(bucket):
                    pool.append(bucket[depth])
                    if len(pool) >= limit:
                        break
            depth += 1
    else:
        pool = [t for t in TOPIC_POOL if t["source"] == source]
        if not pool:
            pool = TOPIC_POOL

    topics = []
    for i, base in enumerate(pool[:limit]):
        item = dict(base)
        item["rank"] = f"{i + 1:02d}" if i < 6 else "NEW"
        if refresh and i < 2:
            # 刷新时只轻微上调热度，id / 标题 / 详情不变
            item["heat"] = round(min(9.9, base["heat"] + 0.1), 1)
            item["rise"] = "+8%"
        topics.append(item)
    return topics


def _find_topic(topic_id: str) -> dict | None:
    for t in TOPIC_POOL:
        if t["id"] == topic_id:
            return t
    return None


def generate_topic_detail(topic_id: str) -> dict | None:
    base = _find_topic(topic_id)
    if not base:
        return None

    idx = TOPIC_POOL.index(base)
    rnd = _seed_rand(topic_id)
    labels = [_today_str(d) for d in range(-6, 1)]
    start = base["heat"] - 1.6
    trend = [round(start + k * 0.32 + rnd.uniform(-0.15, 0.15), 1) for k in range(7)]
    trend[-1] = base["heat"]
    framework = FRAMEWORK_TEMPLATES[idx % len(FRAMEWORK_TEMPLATES)]
    refs = [
        {"title": "我把 ChatGPT 当同事用了 30 天", "plays": "328.4w", "thumb": "hc1"},
        {"title": "一个人做自媒体的第 180 天", "plays": "186.2w", "thumb": "hc3"},
        {"title": "月薪 3 万的人都在用的工作流", "plays": "612.8w", "thumb": "hc2"},
    ]
    return {
        "id": base["id"],
        "title": base["title"],
        "audience": base["audience"],
        "competition": base["competition"],
        "estimate": base["estimate"],
        "match": base["match"],
        "peak": max(trend),
        "rise": base["rise"],
        "reason": base["desc"],
        "trend": {"labels": labels, "values": trend},
        "framework": framework,
        "refs": refs,
    }


def generate_draft(topic_id: str, draft_type: str = "script") -> dict:
    base = _find_topic(topic_id)
    title = base["title"] if base else TOPIC_TITLES[0]
    if draft_type == "story":
        return {
            "type": "story",
            "topicId": topic_id,
            "title": title,
            "content": [
                {"time": "0–3s", "shot": "特写 · 桌面", "note": "手把会议录音拖进 AI 工具，屏幕出现「转写中」。字幕直接给出结果：3 分钟。"},
                {"time": "3–12s", "shot": "中景 · 真人", "note": "对着镜头说「以前我最怕开会，现在我最怕会议纪要没人写」。"},
                {"time": "12–30s", "shot": "录屏 · 全屏", "note": "三步工作流加速播放：转写、提炼、分发，每步停留 3 秒。"},
                {"time": "30–45s", "shot": "近景 · 结果", "note": "展示整理后的纪要：结论、待办、负责人，一页看清。"},
                {"time": "45–58s", "shot": "中景 · 收束", "note": "「模板我整理好了，评论区留『模板』。」画面停在账号名。"},
            ],
        }
    if draft_type == "titles":
        return {
            "type": "titles",
            "topicId": topic_id,
            "title": title,
            "content": [
                "我把 AI 当同事用了 30 天，效率真的翻了 3 倍",
                "别再手写会议纪要了，这套工作流 3 分钟搞定",
                "月薪 3 万的人，都在偷偷用这套 AI 工作流",
                "一个人做自媒体，我如何用 AI 替代一个团队",
                "为什么你越努力越焦虑？可能缺的不是自律",
            ],
        }
    return {
        "type": "script",
        "topicId": topic_id,
        "title": title,
        "content": [
            {"time": "0–3s", "section": "钩子 · 结果前置", "text": "「我让 AI 替我开完了 30 场会，结果老板以为我偷偷加了班。」"},
            {"time": "3–15s", "section": "展开 · 身份代入", "text": "「如果你也是那种会议开不完、纪要写到手软的打工人，这条一定要看完。」"},
            {"time": "15–32s", "section": "转折 · 反常识", "text": "「真正省时间的不是某个工具，而是把会议拆成：会前、会中、会后三个动作。」"},
            {"time": "32–50s", "section": "方法 · 三步工作流", "text": "「会前让 AI 读背景材料，会中只记结论和待办，会后自动生成纪要并发到群里。」"},
            {"time": "50–58s", "section": "收束 · 低门槛 CTA", "text": "「整套模板我整理好了，评论区留『模板』，我发你。」"},
        ],
    }


def analyze_niche(skills: list[str], interests: list[str], hours: int, shoot: str, goal: str) -> dict:
    score = min(96, max(72, len(skills) * 6 + len(interests) * 5 + hours // 2 + random.randint(4, 12)))
    rate = "2 条 / 周" if hours <= 6 else "3 条 / 周" if hours <= 12 else "4 条 / 周" if hours <= 20 else "5 条 / 周"
    primary = "AI 效率 × 职场成长"
    radar = {
        "indicator": ["能力匹配", "兴趣匹配", "变现潜力", "持续输出", "竞争空间", "内容差异"],
        "you": [94, 88, 86, 79, 72, 90],
        "avg": [72, 70, 68, 74, 60, 64],
    }
    if skills:
        radar["you"] = [
            min(100, 75 + len(skills) * 4 + random.randint(-5, 5)),
            min(100, 70 + len(interests) * 6 + random.randint(-5, 5)),
            min(100, 65 + (1 if "稳定变现" in goal else 0) * 15 + random.randint(-5, 5)),
            min(100, 60 + hours * 1.5 + random.randint(-5, 5)),
            min(100, 55 + (1 if "快速涨粉" in goal else 0) * 15 + random.randint(-5, 5)),
            min(100, 80 + random.randint(-5, 5)),
        ]
    opportunity = [
        {"name": "AI 效率 × 职场成长", "competition": 62, "monetize": 86, "match": score, "color": "#1f6b4e"},
        {"name": "AI 工具测评", "competition": 84, "monetize": 81, "match": random.randint(70, 86), "color": "rgba(31,107,78,.5)"},
        {"name": "个人成长记录", "competition": 48, "monetize": 60, "match": random.randint(60, 80), "color": "#c3ed5a"},
        {"name": "职场干货口播", "competition": 76, "monetize": 64, "match": random.randint(60, 78), "color": "rgba(58,99,146,.55)"},
        {"name": "数码效率", "competition": 88, "monetize": 72, "match": random.randint(55, 75), "color": "rgba(226,89,47,.45)"},
        {"name": "知识科普", "competition": 42, "monetize": 66, "match": random.randint(50, 72), "color": "rgba(115,120,111,.35)"},
    ]
    plan = [
        {"day": 1, "weekday": "周四", "task": "用一条视频讲清：我是谁、帮谁、解决什么", "form": "口播", "duration": "45s"},
        {"day": 2, "weekday": "周五", "task": "拆解 5 条同赛道爆款的前 3 秒", "form": "拆解", "duration": "60min"},
        {"day": 3, "weekday": "周六", "task": "发布 AI 会议纪要工作流（结果前置版）", "form": "口播", "duration": "58s"},
        {"day": 4, "weekday": "周日", "task": "把评论区问题做成 15 秒快答", "form": "快答", "duration": "15s"},
        {"day": 5, "weekday": "周一", "task": "一个人公司的 5 个 AI 员工", "form": "清单", "duration": "65s"},
        {"day": 6, "weekday": "周二", "task": "对比完播率与 3 秒留存，找变量", "form": "复盘", "duration": "30min"},
        {"day": 7, "weekday": "周三", "task": "锁定下周 3 个可持续选题", "form": "规划", "duration": "40min"},
    ]
    return {
        "primary": primary,
        "score": score,
        "rate": rate,
        "hours": hours,
        "shoot": shoot,
        "goal": goal,
        "desc": "你的职场经验、AI 工具熟练度与文案能力形成了稀缺组合：既能讲清方法，也能用真实场景证明结果。当前供给不足，适合以「一人公司 / AI 提效」建立差异化记忆点。",
        "radar": radar,
        "opportunity": opportunity,
        "tracks": [
            {"rank": "01 / PRIMARY", "name": primary, "score": score, "tags": ["推荐主赛道", "供需缺口明显"],
             "competition": 62, "monetize": 86, "sustain": 78,
             "reason": "内容方向示例：3 分钟 AI 工作流、一个人公司的工具箱、打工人提效实录。"},
            {"rank": "02 / GROWTH", "name": "AI 工具测评", "score": random.randint(80, 88), "tags": ["高增长", "竞争激烈"],
             "competition": 84, "monetize": 81, "sustain": 90,
             "reason": "内容方向示例：每周工具红黑榜、真实工作场景实测、工具组合工作流。"},
            {"rank": "03 / NICHE", "name": "个人成长记录", "score": random.randint(72, 82), "tags": ["低竞争", "变现较慢"],
             "competition": 48, "monetize": 60, "sustain": 72,
             "reason": "内容方向示例：自由职业日记、一个人公司复盘、成长方法论长文。"},
        ],
        "plan": plan,
    }


def generate_comments(filter_cat: str = "all") -> dict:
    total = 1284
    cats = {
        "good": {"label": "好评", "pct": 46, "count": 590, "color": "#1f6b4e"},
        "need": {"label": "需求建议", "pct": 28, "count": 360, "color": "#c3ed5a"},
        "emotion": {"label": "情绪共鸣", "pct": 17, "count": 218, "color": "#e2592f"},
        "bad": {"label": "负面反馈", "pct": 9, "count": 116, "color": "#c9c5bb"},
    }
    rows = [
        {"id": _random_id("c"), "cat": "need", "name": "小满不加糖", "avatar": "满", "time": "2 小时前",
         "text": "这套会议纪要模板真的救了每周一的我，能不能出一期完整版？最好带提示词。",
         "work": "《别再手动整理会议纪要了》", "likes": 86, "tag": "高意向"},
        {"id": _random_id("c"), "cat": "emotion", "name": "阿哲在成长", "avatar": "哲", "time": "3 小时前",
         "text": "看完立刻把 ChatGPT 拉进群了，笑死，但真的有用。那种“终于有人懂我”的感觉。",
         "work": "《我把 ChatGPT 当同事用了 30 天》", "likes": 124, "tag": "情绪共鸣"},
        {"id": _random_id("c"), "cat": "need", "name": "凯文 K", "avatar": "K", "time": "5 小时前",
         "text": "讲得太快了，第三步没跟上，求慢一点或者图文版。可以出个步骤清单吗？",
         "work": "《别再手动整理会议纪要了》", "likes": 42, "tag": "体验问题"},
        {"id": _random_id("c"), "cat": "good", "name": "林子的日常", "avatar": "林", "time": "昨天",
         "text": "30 天实验太真实了，我也是从怀疑到离不开。这种亲测内容比工具测评好看多了。",
         "work": "《我把 ChatGPT 当同事用了 30 天》", "likes": 67, "tag": "好评"},
        {"id": _random_id("c"), "cat": "bad", "name": "一颗小石头", "avatar": "石", "time": "昨天",
         "text": "广告有点多，但内容确实有帮助。希望以后少一点口播植入。",
         "work": "《2026 年最值得学的 3 个 AI 工具》", "likes": 12, "tag": "负面"},
        {"id": _random_id("c"), "cat": "need", "name": "Momo", "avatar": "M", "time": "2 天前",
         "text": "月薪那期能不能讲讲具体怎么跟老板汇报？最好是话术模板。",
         "work": "《月薪 8000 和月薪 3 万的人差在哪》", "likes": 31, "tag": "需求建议"},
    ]
    if filter_cat != "all":
        rows = [r for r in rows if r["cat"] == filter_cat]
    emotion_points = [
        {"name": "模板完整版", "mentions": 186, "intensity": 82, "priority": 34},
        {"name": "汇报话术", "mentions": 150, "intensity": 74, "priority": 28},
        {"name": "新手教程", "mentions": 132, "intensity": 62, "priority": 24},
        {"name": "工具对比", "mentions": 98, "intensity": 58, "priority": 20},
        {"name": "价格敏感", "mentions": 76, "intensity": 66, "priority": 17},
        {"name": "真实案例", "mentions": 64, "intensity": 80, "priority": 16},
        {"name": "时间管理", "mentions": 54, "intensity": 48, "priority": 13},
        {"name": "直播带货", "mentions": 42, "intensity": 38, "priority": 11},
    ]
    return {
        "total": total,
        "stats": cats,
        "emotion_points": emotion_points,
        "comments": rows,
        "filters": {k: v["count"] for k, v in cats.items()},
    }


def add_comment_rule(keyword: str, category: str) -> dict:
    return {
        "id": _random_id("rule"),
        "keyword": keyword,
        "category": category,
        "status": "active",
        "backfill_count": random.randint(8, 35),
        "applied_at": datetime.now().isoformat(),
    }


def generate_hits(kind: str = "all") -> list[dict]:
    hits = []
    for base in HIT_POOL:
        if kind != "all" and base["kind"] != kind:
            continue
        hits.append(dict(base))
    for base in _IMPORTED_HITS.values():
        if kind == "saved":
            continue
        hits.append({"id": base["id"], "idx": "NEW", "title": base["title"],
                     "kind": "analyzed", "plays": "待验证", "likes": "待验证",
                     "tags": ["新导入", "待拉片"]})
    return hits


_DIM_PRESETS = [
    {
        "hook": "结果前置 + 身份代入",
        "hook_note": "第一句先给结果，第二句绑定「打工人」身份。",
        "emotion": "职场焦虑 → 掌控感",
        "emotion_note": "先承认被工作追着跑，再给出可控的小胜利。",
        "structure": "痛点 → 反常识 → 方法 → 结果",
        "structure_note": "每个段落只承担一个叙事任务，信息密度高。",
        "visual": "大字幕 + 桌面实拍",
        "visual_note": "关键结果用全屏大字卡停顿 0.8 秒，强化记忆。",
        "cta": "评论区领模板",
        "cta_note": "用「整理好了」替代「点赞关注」，降低反感。",
        "formula": "可复用公式：<b>结果前置</b> → 真实实验 → 反常识转折 → 可复用清单 → 低门槛 CTA。",
    },
    {
        "hook": "身份对比 + 数字锚点",
        "hook_note": "「8000」和「3 万」同时出现，制造即时落差。",
        "emotion": "不公平感 → 希望",
        "emotion_note": "先让观众代入委屈，再给出可复制的路径。",
        "structure": "对比 → 归因 → 方法 → 结果",
        "structure_note": "用两份真实周报做视觉证据。",
        "visual": "双屏对比 + 工资条",
        "visual_note": "左右分屏，关键差异用红框圈出。",
        "cta": "评论区领模板",
        "cta_note": "把「你怎么看」换成「要不要模板」，转化更直接。",
        "formula": "可复用公式：<b>身份对比</b> → 数据落差 → 结构拆解 → 模板交付。",
    },
]

_STRUCTURE_PRESETS = [
    [
        {"label": "钩子 18%", "w": 18, "bg": "#c3ed5a", "fg": "#1a2414", "legend": "0–3s 钩子"},
        {"label": "痛点 27%", "w": 27, "bg": "#1f6b4e", "fg": "#fff", "legend": "3–12s 痛点"},
        {"label": "方法 38%", "w": 38, "bg": "#9cc7b3", "fg": "", "legend": "12–45s 方法"},
        {"label": "CTA 17%", "w": 17, "bg": "#e2592f", "fg": "#fff", "legend": "45–58s CTA"},
    ],
    [
        {"label": "钩子 15%", "w": 15, "bg": "#c3ed5a", "fg": "#1a2414", "legend": "0–3s 对比"},
        {"label": "落差 25%", "w": 25, "bg": "#1f6b4e", "fg": "#fff", "legend": "3–12s 落差"},
        {"label": "拆解 42%", "w": 42, "bg": "#9cc7b3", "fg": "", "legend": "12–45s 拆解"},
        {"label": "CTA 18%", "w": 18, "bg": "#e2592f", "fg": "#fff", "legend": "45–58s CTA"},
    ],
]

_GRAPH_PRESETS = [
    {"topic": "30 天实验", "identity": "一人公司", "hook": "结果前置", "emotion": "焦虑→释然",
     "visual": "大字幕", "rhythm": "3 秒反转", "structure": "痛点→方法", "cta": "领模板", "core": "328.4w"},
    {"topic": "周报对比", "identity": "打工人", "hook": "身份对比", "emotion": "落差→希望",
     "visual": "双屏对比", "rhythm": "5 秒反转", "structure": "对比→拆解", "cta": "领模板", "core": "612.8w"},
    {"topic": "180 天记录", "identity": "个人 IP", "hook": "时间节点", "emotion": "迷茫→笃定",
     "visual": "日记实拍", "rhythm": "慢节奏", "structure": "时间线→清单", "cta": "关注追更", "core": "186.2w"},
    {"topic": "模板清单", "identity": "职场人", "hook": "痛点直击", "emotion": "疲惫→解救",
     "visual": "录屏大字卡", "rhythm": "3 秒切入", "structure": "痛点→方案", "cta": "领模板", "core": "241.6w"},
    {"topic": "拒绝 offer", "identity": "高薪职场人", "hook": "反常识", "emotion": "羡慕→认同",
     "visual": "真人白板", "rhythm": "算账节奏", "structure": "悬念→观点", "cta": "开放提问", "core": "98.4w"},
    {"topic": "减法清单", "identity": "工具控", "hook": "减法数字", "emotion": "焦虑→清晰",
     "visual": "桌面俯拍", "rhythm": "清单节奏", "structure": "总→分→总", "cta": "收藏", "core": "154.2w"},
]


def generate_hit_detail(hit_id: str) -> dict | None:
    base = None
    for h in HIT_POOL:
        if h["id"] == hit_id:
            base = h
            break
    if base is None:
        base = _IMPORTED_HITS.get(hit_id)
        if base is None:
            return None
        return dict(base)

    idx = HIT_POOL.index(base)
    rnd = _seed_rand(hit_id)
    plays_pct = rnd.choice(["38.2%", "42.6%", "35.8%", "40.1%", "44.3%", "37.4%"])
    retention = rnd.choice(["62.4%", "71.3%", "58.9%", "66.7%", "74.8%", "63.1%"])
    share = rnd.choice(["4.8%", "6.2%", "9.4%", "5.3%", "3.9%", "11.2%"])
    dims = _DIM_PRESETS[idx % len(_DIM_PRESETS)]
    return {
        "id": base["id"],
        "title": base["title"],
        "meta": [
            {"type": "green", "text": f"完播率 {plays_pct}"},
            {"type": "", "text": f"3 秒留存 {retention}"},
            {"type": "", "text": f"分享率 {share}"},
        ],
        "dims": dims,
        "formula": dims["formula"],
        "structure": _STRUCTURE_PRESETS[idx % len(_STRUCTURE_PRESETS)],
        "graph": dict(_GRAPH_PRESETS[idx % len(_GRAPH_PRESETS)]),
    }


def analyze_hit(url: str) -> dict:
    title = (url.split("/")[-1][:16] if url else "") or "AI 效率工具盘点 · 新导入爆款"
    _IMPORT_SEQ["n"] += 1
    result = {
        "id": f"h_{9000 + _IMPORT_SEQ['n']}",
        "title": title,
        "status": "analyzed",
        "progress": 100,
        "meta": [
            {"type": "green", "text": "完播率 36.5%"},
            {"type": "", "text": "3 秒留存 59.2%"},
            {"type": "", "text": "收藏率 7.8%"},
        ],
        "dims": {
            "hook": "痛点提问 + 数字",
            "hook_note": "先用一个高频问题抓住注意力。",
            "emotion": "焦虑 → 清晰",
            "emotion_note": "让观众从信息过载中感到被解救。",
            "structure": "问题 → 答案 → 清单",
            "structure_note": "结构简单，降低理解成本。",
            "visual": "桌面实拍 + 大字卡",
            "visual_note": "关键工具用大字卡停留 1 秒。",
            "cta": "收藏 + 关注",
            "cta_note": "引导收藏，符合工具类内容行为。",
            "formula": "可复用公式：<b>痛点提问</b> → 数字锚点 → 3 个答案 → 收藏关注。",
        },
        "structure": [
            {"label": "钩子 18%", "w": 18, "bg": "#c3ed5a", "fg": "#1a2414", "legend": "0–3s 提问"},
            {"label": "答案 22%", "w": 22, "bg": "#1f6b4e", "fg": "#fff", "legend": "3–12s 答案"},
            {"label": "清单 48%", "w": 48, "bg": "#9cc7b3", "fg": "", "legend": "12–50s 清单"},
            {"label": "CTA 12%", "w": 12, "bg": "#e2592f", "fg": "#fff", "legend": "50–58s 收藏"},
        ],
        "graph": {
            "topic": "新导入", "identity": "创作者", "hook": "痛点提问",
            "emotion": "焦虑→清晰", "visual": "桌面实拍", "rhythm": "清单节奏",
            "structure": "问题→清单", "cta": "收藏关注", "core": "待验证",
        },
    }
    _IMPORTED_HITS[result["id"]] = result
    return result


def generate_hit_recommendations(hit_id: str | None = None) -> dict:
    topic = "AI 会议纪要工作流"
    return {
        "hitId": hit_id,
        "topic": topic,
        "hook": f"「{topic}」这件事，我一开始也不信，直到它帮我省下了每天 2 小时。今天把完整流程拆给你。",
        "structure": "0–3s 结果前置；3–12s 真实场景；12–45s 三步方法；45–58s 评论区领模板。",
        "emotion": "从「被琐事追着跑」的疲惫，过渡到「重新掌控时间」的轻松。",
    }


def generate_brands(refresh: bool = False) -> list[dict]:
    brands = []
    for i, name in enumerate(BRAND_NAMES):
        brands.append({
            "id": _random_id("b"),
            "name": name,
            "industry": BRAND_INDUSTRY[i % len(BRAND_INDUSTRY)],
            "budget": random.choice(["¥8,000–15,000", "¥15,000–30,000", "¥30,000–60,000", "年度框架"]),
            "status": random.choice(["可对接", "沟通中", "高意向", "合作过 1 次"]),
            "match": random.randint(72, 96),
            "tags": random.sample(["职场场景", "效率工具", "口播植入", "图文授权", "长期合作"], k=2),
            "updated": "刚刚" if refresh else random.choice(["10 分钟前", "1 小时前", "昨天"]),
        })
    return brands


def generate_pipeline() -> list[dict]:
    return [
        {
            "stage": "沟通中",
            "count": 2,
            "cards": [
                {"brand": "MOKA 咖啡", "logo": "M", "status": "待回复", "project": "春季办公场景植入 · 1 条口播 + 1 条图文", "price": "¥12,000", "deadline": "10.28 前"},
                {"brand": "Notion 中国", "logo": "N", "status": "沟通中", "project": "效率模板联名 · 长期内容合作", "price": "¥25,000", "deadline": "11.02 前"},
            ],
        },
        {
            "stage": "已报价",
            "count": 1,
            "cards": [
                {"brand": "飞书", "logo": "飞", "status": "已发", "project": "AI 工作流专题 · 2 条短视频 + 直播连麦", "price": "¥18,500", "deadline": "10.30 前"},
            ],
        },
        {
            "stage": "待签约",
            "count": 1,
            "cards": [
                {"brand": "讯飞听见", "logo": "讯", "status": "高意向", "project": "会议纪要年度框架 · 每月 2 条内容", "price": "¥48,000", "deadline": "11.05 前"},
            ],
        },
        {
            "stage": "已完成",
            "count": 1,
            "cards": [
                {"brand": "戴森", "logo": "戴", "status": "已结款", "project": "桌面效率场景 · 1 条创意口播", "price": "¥22,000", "deadline": "10.18 完成"},
            ],
        },
    ]


def generate_scripts(path: str = "first") -> dict:
    scripts = {
        "first": {
            "title": "初次接洽",
            "content": "你好，感谢关注。我的账号主要面向 25–35 岁的职场效率人群，近 30 天平均播放 46 万、互动率 6.8%。<b>方便先同步一下品牌目标、预算区间和期望上线时间吗？</b>我会据此给出一版内容方案和报价。",
        },
        "quote": {
            "title": "报价谈判",
            "content": "理解预算差异。我的单条口播报价是 ¥18,500，包含脚本、拍摄、剪辑与一次修改；图文 + 授权套餐价 ¥26,000。这个价格基于近 30 天平均 46 万播放与 6.8% 互动率，<b>如果预算区间不同，我们可以调整内容形式，而不是压低价。</b>",
        },
        "follow": {
            "title": "催款跟进",
            "content": "你好，同步一下本期合作的尾款节点是 11 月 5 日，发票已在上周寄出。方便的话今天同步一下流程进度？<b>如果都已走完，麻烦回我一个确认，我好安排下一条排期。</b>",
        },
    }
    return scripts.get(path, scripts["first"])


def overview_data(range_days: str = "30") -> dict:
    mapping = {
        "7": {
            "labels": [_today_str(d) for d in range(-6, 1)],
            "plays": [22.1, 24.6, 21.8, 28.4, 25.2, 30.6, 32.8],
            "fans": [0.24, 0.31, 0.27, 0.38, 0.33, 0.41, 0.37],
        },
        "30": {
            "labels": ["9.23", "9.26", "9.29", "10.02", "10.05", "10.08", "10.11", "10.14", "10.17", "10.20", _today_str()],
            "plays": [12.4, 15.1, 13.8, 18.6, 21.2, 19.4, 25.8, 27.2, 24.6, 31.4, 32.8],
            "fans": [0.14, 0.18, 0.15, 0.23, 0.26, 0.21, 0.31, 0.34, 0.29, 0.39, 0.41],
        },
        "90": {
            "labels": ["8.01", "8.08", "8.15", "8.22", "8.29", "9.05", "9.12", "9.19", "9.26", "10.03", "10.10", "10.17", _today_str()],
            "plays": [9.8, 11.2, 10.6, 13.4, 12.1, 15.8, 14.2, 18.6, 17.4, 21.2, 23.8, 26.4, 32.8],
            "fans": [0.09, 0.11, 0.10, 0.14, 0.12, 0.16, 0.15, 0.19, 0.18, 0.22, 0.24, 0.27, 0.32],
        },
    }
    return mapping.get(range_days, mapping["30"])
