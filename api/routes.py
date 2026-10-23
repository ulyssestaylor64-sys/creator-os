"""
Creator OS — REST API 路由
所有接口返回 JSON，统一挂载在 /api 前缀下。
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api import mock_data, ai_client

router = APIRouter(prefix="/api")


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


class RecommendationRequest(BaseModel):
    hitId: Optional[str] = None


# ---------- health ----------
@router.get("/health")
def health():
    return mock_data.health()


# ---------- topics ----------
@router.get("/topics")
def topics(
    source: str = Query("all", pattern="^(all|douyin|niche|search)$"),
    refresh: int = Query(0),
):
    # 把前端 source 参数映射到内部标签
    source_map = {"douyin": "抖音热榜", "niche": "同赛道爆款", "search": "搜索趋势", "all": "all"}
    internal_source = source_map.get(source, "all")
    return {
        "source": source,
        "refresh": bool(refresh),
        "sync_time": "刚刚更新 · 抖音热榜 / 创作灵感" if refresh else "12 分钟前更新 · 抖音热榜 / 创作灵感",
        "stats": {"new": 38, "matched": 12, "planned": 3, "avg_heat": 8.6},
        "topics": mock_data.generate_topics(internal_source, refresh=bool(refresh)),
    }


@router.get("/topics/{topic_id}")
def topic_detail(topic_id: str):
    detail = mock_data.generate_topic_detail(topic_id)
    if not detail:
        raise HTTPException(status_code=404, detail="topic not found")
    return detail


@router.post("/draft")
async def draft(req: DraftRequest):
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

    return {
        "topicId": req.topicId,
        "type": req.type,
        "model": ai_client.LAST["model"] if text else "mock",
        "ai": bool(text),
        "content": text or mock_data.generate_draft(req.topicId, req.type),
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
def niche_analyze(req: NicheRequest):
    return mock_data.analyze_niche(req.skills, req.interests, req.hours, req.shoot, req.goal)


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


@router.post("/comments/rules")
def add_rule(req: RuleRequest):
    rule = mock_data.add_comment_rule(req.keyword, req.category)
    return {"success": True, "rule": rule}


# ---------- hits ----------
@router.get("/hits")
def hits(kind: str = Query("all", pattern="^(all|saved|analyzed)$")):
    return {
        "kind": kind,
        "total": 126,
        "stats": {"saved": 86, "analyzed": 42},
        "hits": mock_data.generate_hits(kind),
    }


@router.get("/hits/{hit_id}")
def hit_detail(hit_id: str):
    detail = mock_data.generate_hit_detail(hit_id)
    if not detail:
        raise HTTPException(status_code=404, detail="hit not found")
    return detail


@router.post("/hits/analyze")
def hit_analyze(req: HitAnalyzeRequest):
    return {"success": True, "hit": mock_data.analyze_hit(req.url)}


@router.post("/hits/recommendations")
def hit_recommendations(req: RecommendationRequest):
    return {"success": True, "recommendation": mock_data.generate_hit_recommendations(req.hitId)}


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
