"""
Creator OS — REST API 路由
所有接口返回 JSON，统一挂载在 /api 前缀下。
"""
import asyncio
import hashlib
import html
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from api import ai_client, auth, mock_data, store

router = APIRouter(prefix="/api")


def _secure_cookie(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").startswith("https")


def current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get(auth.SESSION_COOKIE)
    if not token:
        return None
    return store.get_session_user(auth.token_hash(token))


def owner_of(request: Request, response: Response) -> str:
    """登录用户按账号隔离；未登录时按设备 Cookie 隔离，避免不同访客互相看到数据。"""
    user = current_user(request)
    if user:
        return user["id"]
    device = request.cookies.get(auth.DEVICE_COOKIE)
    if not device:
        device = auth.new_device_id()
        response.set_cookie(
            auth.DEVICE_COOKIE, device, max_age=365 * 24 * 3600,
            httponly=True, samesite="lax", secure=_secure_cookie(request), path="/",
        )
    return device


def _start_session(user_id: str, request: Request, response: Response) -> None:
    token = auth.new_token()
    store.create_session(auth.token_hash(token), user_id, auth.SESSION_DAYS)
    response.set_cookie(
        auth.SESSION_COOKIE, token, max_age=auth.SESSION_DAYS * 24 * 3600,
        httponly=True, samesite="lax", secure=_secure_cookie(request), path="/",
    )


# 简单的登录频率限制（内存计数，实例重启即清空）
_LOGIN_WINDOW = 600
_LOGIN_LIMIT = 10
_login_hits: dict[str, list[float]] = {}


def _check_login_rate(key: str) -> None:
    now = time.time()
    hits = [t for t in _login_hits.get(key, []) if now - t < _LOGIN_WINDOW]
    if len(hits) >= _LOGIN_LIMIT:
        _login_hits[key] = hits
        raise HTTPException(status_code=429, detail="尝试过于频繁，请 10 分钟后再试")
    hits.append(now)
    _login_hits[key] = hits


class AuthRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class DraftRequest(BaseModel):
    topicId: str = Field(..., description="选题 ID")
    type: str = Field(default="script", description="script | story | titles")


class NicheRequest(BaseModel):
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    hours: int = Field(default=10, ge=1, le=80)
    shoot: str = Field(default="偶尔出镜")
    goal: str = Field(default="稳定变现")


class RuleRequest(BaseModel):
    keyword: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)


class HitAnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1)


class HotImportRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = Field(default="手动导入")


async def _ai_json(prompt: str, system: str) -> Optional[dict]:
    """调用 AI 并尽量解析出 JSON；解析失败返回 None。"""
    if not ai_client.has_key():
        return None
    text = await ai_client.chat_completion([
        {"role": "system", "content": system + " 只输出 JSON，不要输出解释或代码块标记。"},
        {"role": "user", "content": prompt},
    ], temperature=0.3)
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (ValueError, TypeError):
        return None



class RecommendationRequest(BaseModel):
    hitId: Optional[str] = None


# ---------- health ----------
@router.get("/health")
def health():
    return mock_data.health()


# ---------- auth ----------
@router.post("/auth/register")
def auth_register(req: AuthRequest, request: Request, response: Response):
    email = auth.normalize_email(req.email)
    if not auth.valid_email(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if not auth.valid_password(req.password):
        raise HTTPException(status_code=400, detail="密码至少 8 位")
    _check_login_rate("reg:" + email)
    if store.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")
    user = store.create_user(auth.new_user_id(), email, auth.hash_password(req.password))
    _start_session(user["id"], request, response)
    return {"success": True, "user": user}


@router.post("/auth/login")
def auth_login(req: AuthRequest, request: Request, response: Response):
    email = auth.normalize_email(req.email)
    _check_login_rate("login:" + email)
    user = store.get_user_by_email(email)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    store.purge_expired_sessions()
    _start_session(user["id"], request, response)
    return {"success": True, "user": {"id": user["id"], "email": user["email"]}}


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response):
    token = request.cookies.get(auth.SESSION_COOKIE)
    if token:
        store.delete_session(auth.token_hash(token))
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"success": True}


@router.get("/auth/me")
def auth_me(request: Request):
    user = current_user(request)
    return {"user": user, "anonymous": user is None}


# ---------- topics ----------
_HOT_ITEMS: dict[str, dict] = {}


def _hot_topic_from_title(title: str, origin: str) -> dict:
    clean = re.sub(r"\s+", " ", html.unescape(title)).strip()[:60]
    tid = "hot_" + hashlib.md5(clean.encode("utf-8")).hexdigest()[:8]
    seed = int(hashlib.md5(clean.encode("utf-8")).hexdigest()[8:14], 16)
    heat = round(8.0 + (seed % 18) / 10, 1)
    return {
        "id": tid,
        "rank": "HOT",
        "title": clean,
        "source": "抖音热榜" if origin in _RSS_ORIGINS else "热点导入",
        "origin": origin,
        "audience": "关注热点的泛内容人群",
        "competition": "竞争 中",
        "estimate": "预估 20–50w 播放",
        "match": 75 + seed % 20,
        "heat": min(heat, 9.6),
        "rise": "+" + str(10 + seed % 60) + "%",
        "peak": round(min(heat + 0.3, 9.9), 1),
        "desc": f"来自 {origin} 的实时热榜条目，可直接结合你的账号角度做二次解读。",
    }


def _hot_detail(base: dict) -> dict:
    seed = int(hashlib.md5(base["id"].encode()).hexdigest()[:8], 16)
    start = base["heat"] - 1.4
    trend = [round(start + k * 0.26 + ((seed >> (k * 2)) % 7) / 20, 1) for k in range(7)]
    trend[-1] = base["heat"]
    labels = [mock_data._today_str(d) for d in range(-6, 1)]
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
        "framework": mock_data.FRAMEWORK_TEMPLATES[0],
        "refs": [
            {"title": "同话题近期爆款 · 结果前置版", "plays": "128.6w", "thumb": "hc1"},
            {"title": "同话题近期爆款 · 情绪共鸣版", "plays": "96.2w", "thumb": "hc3"},
            {"title": "同话题近期爆款 · 清单拆解版", "plays": "84.7w", "thumb": "hc2"},
        ],
        "origin": base.get("origin", ""),
    }


def _fetch_rss(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 CreatorOS/2.4"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        raw = resp.read(400_000)
    root = ET.fromstring(raw)
    titles = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag in ("title",) and node.text and len(node.text.strip()) > 6:
            titles.append(node.text.strip())
    return titles[1:6]  # 跳过频道标题本身


RSS_FEEDS = [
    ("36氪", "https://36kr.com/feed"),
    ("少数派", "https://sspai.com/feed"),
    ("虎嗅", "https://www.huxiu.com/rss/0.xml"),
]
_RSS_ORIGINS = {name for name, _ in RSS_FEEDS}


@router.post("/hot/refresh")
async def hot_refresh():
    def collect() -> tuple[list[str], list[str]]:
        got, errors = [], []
        for name, url in RSS_FEEDS:
            try:
                for t in _fetch_rss(url):
                    got.append(f"{name}|{t}")
            except Exception as exc:  # 单个源失败不影响其他源
                errors.append(f"{name}: {type(exc).__name__}")
        return got, errors

    got, errors = await asyncio.to_thread(collect)
    added = []
    for line in got:
        origin, _, title = line.partition("|")
        item = _hot_topic_from_title(title, origin)
        _HOT_ITEMS[item["id"]] = item
        added.append(item)
    return {
        "success": bool(added),
        "count": len(added),
        "errors": errors,
        "sync_time": datetime.now().strftime("%H:%M") + " 实时同步",
        "topics": added,
    }


@router.post("/hot/import")
def hot_import(req: HotImportRequest):
    lines = [l.strip() for l in req.text.splitlines() if len(l.strip()) >= 6]
    added = []
    for line in lines[:20]:
        item = _hot_topic_from_title(line, req.source)
        _HOT_ITEMS[item["id"]] = item
        added.append(item)
    return {"success": bool(added), "count": len(added), "topics": added}


@router.get("/topics/saved")
def saved_topics(owner: str = Depends(owner_of)):
    rows = [{k: v for k, v in r.items() if k != "user_id"} for r in store.list_saved_topics(owner)]
    return {"total": len(rows), "topics": rows}


@router.post("/topics/{topic_id}/save")
def save_topic(topic_id: str, owner: str = Depends(owner_of)):
    detail = mock_data.generate_topic_detail(topic_id) or _HOT_ITEMS.get(topic_id)
    if not detail:
        raise HTTPException(status_code=404, detail="topic not found")
    row = store.save_topic(owner, topic_id, detail["title"])
    return {"success": True, "saved": row}


@router.delete("/topics/{topic_id}/save")
def unsave_topic(topic_id: str, owner: str = Depends(owner_of)):
    removed = store.delete_saved_topic(owner, topic_id)
    return {"success": removed}


@router.get("/topics")
def topics(
    source: str = Query("all", pattern="^(all|douyin|niche|search)$"),
    refresh: int = Query(0),
):
    # 把前端 source 参数映射到内部标签
    source_map = {"douyin": "抖音热榜", "niche": "同赛道爆款", "search": "搜索趋势", "all": "all"}
    internal_source = source_map.get(source, "all")
    rows = mock_data.generate_topics(internal_source, refresh=bool(refresh))
    if source in ("all", "douyin"):
        rows = rows[:6] + list(_HOT_ITEMS.values())[-3:]
    return {
        "source": source,
        "refresh": bool(refresh),
        "sync_time": "刚刚更新 · 抖音热榜 / 创作灵感" if refresh else "12 分钟前更新 · 抖音热榜 / 创作灵感",
        "stats": {"new": 38 + len(_HOT_ITEMS), "matched": 12, "planned": 3, "avg_heat": 8.6},
        "topics": rows,
    }


@router.get("/topics/{topic_id}")
def topic_detail(topic_id: str):
    detail = mock_data.generate_topic_detail(topic_id)
    if not detail and topic_id in _HOT_ITEMS:
        detail = _hot_detail(_HOT_ITEMS[topic_id])
    if not detail:
        raise HTTPException(status_code=404, detail="topic not found")
    return detail


@router.post("/draft")
async def draft(req: DraftRequest, owner: str = Depends(owner_of)):
    topic = mock_data.generate_topic_detail(req.topicId) or {}
    title = topic.get("title", "")
    audience = topic.get("audience", "个人创作者")
    framework = topic.get("framework") or []
    framework_text = "\n".join(
        "{} {}：{}".format(step[0], step[1], step[2]) for step in framework if len(step) >= 3
    )

    hints = {
        "script": "输出可直接开拍的口播脚本，按时间段分层，每段标注时间与作用。",
        "story": "输出分镜脚本，逐镜标注景别、画面内容与字幕，控制在 60 秒内。",
        "titles": "输出 5 条备选标题，风格各不相同，每条不超过 30 字。",
    }
    user_prompt = (
        f"选题：{title}\n目标人群：{audience}\n参考结构：\n{framework_text}\n\n"
        f"{hints.get(req.type, hints['script'])}\n只输出正文，不要解释。"
    )

    text = await ai_client.chat_completion([
        {"role": "system", "content": "你是资深抖音内容策略师，擅长把选题写成高完播率的口播与分镜脚本。语言口语化，不说废话。"},
        {"role": "user", "content": user_prompt},
    ])

    content = text or mock_data.generate_draft(req.topicId, req.type)
    model = ai_client.LAST["model"] if text else "mock"
    try:
        store.save_draft(owner, req.topicId, req.type, model, content)
    except Exception:
        pass  # 草稿保存失败不影响返回

    return {
        "topicId": req.topicId,
        "type": req.type,
        "model": model,
        "ai": bool(text),
        "content": content,
    }


# ---------- ai ----------
@router.get("/ai/status")
async def ai_status(ping: int = Query(0)):
    info = {
        "has_key": ai_client.has_key(),
        "model": ai_client.model_name(),
        "provider": ai_client.LAST["provider"],
        "last_ok": ai_client.LAST["ok"],
        "last_error": ai_client.LAST["error"],
    }
    if ping:
        info["ping"] = await ai_client.ping()
    return info


# ---------- niche ----------
@router.post("/niche/analyze")
async def niche_analyze(req: NicheRequest):
    base = mock_data.analyze_niche(req.skills, req.interests, req.hours, req.shoot, req.goal)
    prompt = (
        f"创作者条件：技能 {req.skills}，兴趣 {req.interests}，每周可投入 {req.hours} 小时，"
        f"出镜意愿 {req.shoot}，目标 {req.goal}。\n"
        "请给出赛道诊断，返回 JSON："
        '{"primary": "主赛道名称", "desc": "80 字以内诊断说明", '
        '"tracks": [{"name": "赛道名", "reason": "30 字内容方向示例"}], '
        '"plan": [{"task": "每天的具体任务"}]}。'
        "tracks 给 3 个，plan 给 7 天。"
    )
    payload = await _ai_json(prompt, "你是抖音赛道定位顾问，回答要具体、可执行。")
    if payload:
        if payload.get("primary"):
            base["primary"] = payload["primary"]
            base["tracks"][0]["name"] = payload["primary"]
        if payload.get("desc"):
            base["desc"] = payload["desc"][:180]
        for i, track in enumerate(payload.get("tracks") or []):
            if i < len(base["tracks"]):
                if track.get("name"):
                    base["tracks"][i]["name"] = track["name"][:20]
                if track.get("reason"):
                    base["tracks"][i]["reason"] = track["reason"][:80]
        for i, day in enumerate(payload.get("plan") or []):
            if i < len(base["plan"]) and day.get("task"):
                base["plan"][i]["task"] = day["task"][:60]
    base["ai"] = bool(payload)
    return base


# ---------- comments ----------
@router.get("/comments")
def comments(filter: str = Query("all", pattern="^(all|good|need|emotion|bad)$")):
    data = mock_data.generate_comments(filter)
    return {
        "filter": filter,
        "total": data["total"],
        "stats": data["stats"],
        "emotion_points": data["emotion_points"],
        "comments": data["comments"],
    }


@router.get("/comments/rules")
def list_rules(owner: str = Depends(owner_of)):
    rows = [{k: v for k, v in r.items() if k != "user_id"} for r in store.list_rules(owner)]
    return {"rules": rows}


@router.post("/comments/rules")
def add_rule(req: RuleRequest, owner: str = Depends(owner_of)):
    rule = mock_data.add_comment_rule(req.keyword, req.category)
    saved = store.add_rule(owner, rule)
    return {"success": True, "rule": saved}


@router.post("/comments/insights")
async def comment_insights():
    data = mock_data.generate_comments("all")
    samples = "\n".join(f"[{c['cat']}] {c['text']}" for c in data["comments"][:10])
    prompt = (
        "以下是抖音账号的评论样本：\n" + samples + "\n"
        "请提炼 3 条最有价值的洞察，返回 JSON："
        '{"signals": [{"label": "标签", "pill": "高意向|体验问题|内容资产|需求建议", '
        '"quote": "代表性评论原句", "advice": "具体可执行建议"}]}'
    )
    payload = await _ai_json(prompt, "你是内容运营分析师，只基于给定评论提炼，不编造数据。")
    signals = (payload or {}).get("signals") or []
    if not signals:
        signals = [
            {"label": "SIGNAL 01 · 47 条相似", "pill": "高意向",
             "quote": "这套会议纪要模板真的救了每周一的我，能不能出一期完整版？",
             "advice": "建议：把模板整理成 3 分钟教程，挂载评论置顶。"},
            {"label": "SIGNAL 02 · 23 条相似", "pill": "体验问题",
             "quote": "讲得太快了，第三步没跟上，求慢一点或者图文版。",
             "advice": "建议：下条视频插入 5 秒图解卡，并在评论区补步骤清单。"},
            {"label": "SIGNAL 03 · 61 条相似", "pill": "内容资产",
             "quote": "30 天实验太真实了，我也是从怀疑到离不开。",
             "advice": "建议：保留「亲测 + 真实结果」叙事，沉淀为账号方法论。"},
        ]
    return {"success": True, "ai": bool(payload), "signals": signals[:3]}


# ---------- hits ----------
@router.get("/hits")
def hits(kind: str = Query("all", pattern="^(all|saved|analyzed)$"), owner: str = Depends(owner_of)):
    rows = mock_data.generate_hits(kind)
    known = {h["id"] for h in rows}
    imported = store.list_imported_hits(owner)
    for item in imported:
        if item["id"] in known or kind == "saved":
            continue
        rows.append({"id": item["id"], "idx": "NEW", "title": item["title"],
                     "kind": "analyzed", "plays": "待验证", "likes": "待验证",
                     "tags": ["新导入", "待拉片"]})
    return {
        "kind": kind,
        "total": 126,
        "stats": {"saved": 86, "analyzed": 42 + len(imported)},
        "hits": rows,
    }


@router.get("/hits/{hit_id}")
def hit_detail(hit_id: str, owner: str = Depends(owner_of)):
    detail = mock_data.generate_hit_detail(hit_id)
    if not detail:
        for item in store.list_imported_hits(owner):
            if item["id"] == hit_id:
                detail = item
                break
    if not detail:
        raise HTTPException(status_code=404, detail="hit not found")
    return detail


@router.post("/hits/analyze")
def hit_analyze(req: HitAnalyzeRequest, owner: str = Depends(owner_of)):
    hit = mock_data.analyze_hit(req.url)
    try:
        store.save_imported_hit(owner, hit)
    except Exception:
        pass
    return {"success": True, "hit": hit}


@router.post("/hits/recommendations")
async def hit_recommendations(req: RecommendationRequest):
    base = mock_data.generate_hit_recommendations(req.hitId)
    prompt = (
        f"参考爆款：{req.hitId or '未指定'}。请给出一个可复用的新选题方案，返回 JSON："
        '{"topic": "新选题", "hook": "前 3 秒钩子文案", "structure": "结构建议", "emotion": "情绪路径"}'
    )
    payload = await _ai_json(prompt, "你是爆款拆解师，输出要能直接开拍，避免空话。")
    if payload:
        for key in ("topic", "hook", "structure", "emotion"):
            if payload.get(key):
                base[key] = payload[key][:200]
    base["ai"] = bool(payload)
    return {"success": True, "recommendation": base}


# ---------- monetize ----------
@router.get("/monetize/brands")
def brands(refresh: int = Query(0)):
    return {
        "refresh": bool(refresh),
        "updated": "刚刚" if refresh else "12 分钟前",
        "brands": mock_data.generate_brands(refresh=bool(refresh)),
    }


@router.get("/monetize/pipeline")
def pipeline():
    return {"pipeline": mock_data.generate_pipeline()}


@router.get("/monetize/scripts")
def scripts(path: str = Query("first", pattern="^(first|quote|follow)$")):
    return mock_data.generate_scripts(path)
