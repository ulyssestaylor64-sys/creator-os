"""
Creator OS — AI 调用封装
优先读取环境变量 GLM_API_KEY 调用智谱 GLM 服务；
未配置时返回 mock 结果，保证接口不报错。
"""
import os
import json
from typing import AsyncIterator

import httpx

GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
# 可通过环境变量 GLM_MODEL 覆盖；若模型名不可用会自动尝试备用模型
DEFAULT_MODEL = "glm-5.3-flash"
FALLBACK_MODELS = ["glm-4-flash", "glm-4.5-flash", "glm-4-plus", "glm-4-air"]

# 最近一次调用状态，供 /api/ai/status 排查
LAST = {"ok": False, "model": "", "error": "", "provider": "mock"}


def _key() -> str:
    key = (os.getenv("GLM_API_KEY") or "").strip()
    if not key or key.startswith("your"):
        return ""
    return key


def has_key() -> bool:
    return bool(_key())


def model_name() -> str:
    return (os.getenv("GLM_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _candidates() -> list[str]:
    models = [model_name()] + FALLBACK_MODELS
    seen, out = set(), []
    for m in models:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
    }


async def chat_completion(messages: list[dict], temperature: float = 0.7) -> str:
    """非流式 GLM 调用，返回文本内容；失败返回空字符串。"""
    if not has_key():
        LAST.update(ok=False, provider="mock", error="GLM_API_KEY 未配置")
        return ""

    payload_base = {
        "messages": messages,
        "temperature": temperature,
    }
    last_error = ""
    async with httpx.AsyncClient(timeout=60.0) as client:
        for model in _candidates():
            try:
                resp = await client.post(
                    f"{GLM_BASE_URL}/chat/completions",
                    headers=_headers(),
                    json={**payload_base, "model": model},
                )
                if resp.status_code == 404 or resp.status_code == 400:
                    # 模型名不可用，换下一个候选
                    last_error = f"{model}: {resp.status_code} {resp.text[:160]}"
                    continue
                if resp.status_code in (401, 403):
                    last_error = "鉴权失败（401/403）：请检查 GLM_API_KEY 是否正确或已过期"
                    break
                if resp.status_code == 429:
                    last_error = "调用频率超限或额度不足（429）：请稍后再试或检查账户余额"
                    break
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                LAST.update(ok=True, model=model, error="", provider="glm")
                return text
            except Exception as exc:
                last_error = f"{model}: {exc}"
                continue

    LAST.update(ok=False, model=model_name(), error=last_error, provider="mock")
    return ""


async def chat_completion_stream(messages: list[dict], temperature: float = 0.7) -> AsyncIterator[str]:
    """流式 GLM 调用，按 chunk 产出文本。"""
    if not has_key():
        return
    payload = {
        "model": model_name(),
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{GLM_BASE_URL}/chat/completions", headers=_headers(), json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        obj = json.loads(chunk)
                        delta = obj["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue
    except Exception as exc:
        LAST.update(ok=False, model=model_name(), error=str(exc), provider="mock")
        return


async def ping() -> dict:
    """用一条极短的请求验证 Key 是否可用。"""
    if not has_key():
        return {"ok": False, "provider": "mock", "model": "", "error": "GLM_API_KEY 未配置"}
    text = await chat_completion([{"role": "user", "content": "回复两个字：可用"}], temperature=0.1)
    return {
        "ok": bool(text),
        "provider": LAST["provider"],
        "model": LAST["model"],
        "error": LAST["error"],
        "sample": text[:40],
    }


def mock_ai_result(prompt_type: str, topic: str = "") -> str:
    """当未配置 API Key 或调用失败时返回 mock AI 文案。"""
    results = {
        "draft": """0–3s 钩子 · 结果前置
「我让 AI 替我开完了 30 场会，结果老板以为我偷偷加了班。」

3–15s 展开 · 身份代入
「如果你也是那种会议开不完、纪要写到手软的打工人，这条一定要看完。」

15–32s 转折 · 反常识
「真正省时间的不是某个工具，而是把会议拆成：会前、会中、会后三个动作。」

32–50s 方法 · 三步工作流
「会前让 AI 读背景材料，会中只记结论和待办，会后自动生成纪要并发到群里。」

50–58s 收束 · 低门槛 CTA
「整套模板我整理好了，评论区留『模板』，我发你。」""",
        "titles": """1. 我把 AI 当同事用了 30 天，效率真的翻了 3 倍
2. 别再手写会议纪要了，这套工作流 3 分钟搞定
3. 月薪 3 万的人，都在偷偷用这套 AI 工作流
4. 一个人做自媒体，我如何用 AI 替代一个团队
5. 为什么你越努力越焦虑？可能缺的不是自律""",
        "story": """0–3s 特写 · 桌面：手把会议录音拖进 AI 工具，屏幕出现「转写中」。字幕直接给出结果：3 分钟。
3–12s 中景 · 真人：对着镜头说「以前我最怕开会，现在我最怕会议纪要没人写」。
12–30s 录屏 · 全屏：三步工作流加速播放：转写、提炼、分发，每步停留 3 秒。
30–45s 近景 · 结果：展示整理后的纪要：结论、待办、负责人，一页看清。
45–58s 中景 · 收束：「模板我整理好了，评论区留『模板』。」画面停在账号名。""",
        "recommendation": """Hook：「{}这件事，我一开始也不信，直到它帮我省下了每天 2 小时。今天把完整流程拆给你。」
Structure：0–3s 结果前置；3–12s 真实场景；12–45s 三步方法；45–58s 评论区领模板。
Emotion：从「被琐事追着跑」的疲惫，过渡到「重新掌控时间」的轻松。""".format(topic or "AI 会议纪要工作流"),
        "default": "已根据你的账号规则生成内容，数据来自 mock 模式（未配置 GLM_API_KEY）。",
    }
    return results.get(prompt_type, results["default"])
