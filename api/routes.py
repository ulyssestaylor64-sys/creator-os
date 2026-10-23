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
def draft(req: DraftRequest):
    content = mock_data.generate_draft(req.topicId, req.type)
    return {
        "topicId": req.topicId,
        "type": req.type,
        "model": "GLM-5.3-Flash",
        "content": content,
    }


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
