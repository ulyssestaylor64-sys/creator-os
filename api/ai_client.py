"""
Creator OS — AI 调用封装
优先读取环境变量 GLM_API_KEY 调用智谱 GLM 服务；
未配置时返回 mock 结果，保证接口不报错。
"""
import os
import json
from typing import AsyncIterator

import httpx

GLM_API_KEY = os.getenv("GLM_API_KEY")
GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
GLM_MODEL = "glm-5.3-flash"


def _has_key() -> bool:
    return bool(GLM_API_KEY and GLM_API_KEY.strip() and not GLM_API_KEY.startswith("your"))


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
    }


async def chat_completion(messages: list[dict], temperature: float = 0.7) -> str:
    """非流式 GLM 调用，返回文本内容。"""
    if not _has_key():
        return ""
    payload = {
        "model": GLM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{GLM_BASE_URL}/chat/completions", headers=_headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return ""


async def chat_completion_stream(messages: list[dict], temperature: float = 0.7) -> AsyncIterator[str]:
    """流式 GLM 调用，按 chunk 产出文本。"""
    if not _has_key():
        return
    payload = {
        "model": GLM_MODEL,
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
    except Exception:
        return


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
