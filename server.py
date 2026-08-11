#!/usr/bin/env python3
"""
DeepSeek Role Translator
=========================
HTTP 代理 + MCP 服务器。Android Studio 发来的 developer 角色消息会被自动
翻译成 DeepSeek 认识的 system 角色。

用法：
    python server.py              # stdio 模式（MCP）
    python server.py --http       # HTTP 模式（代理 + MCP）
"""

import json
import os
import traceback

import httpx
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

# ── 加载配置 ──────────────────────────────────────────────────────────────────
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


# ── 角色翻译 ──────────────────────────────────────────────────────────────────
def translate_messages(messages: list[dict]) -> list[dict]:
    for msg in messages:
        if msg.get("role") == "developer":
            msg["role"] = "system"
    return messages


# ── 代理请求 ──────────────────────────────────────────────────────────────────
def _proxy_headers():
    return {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }


async def _proxy_chat(request: Request) -> Response:
    body = await request.body()
    data = json.loads(body)

    if "messages" in data:
        data["messages"] = translate_messages(data["messages"])
    if not data.get("model"):
        data["model"] = DEEPSEEK_MODEL

    is_stream = data.get("stream", False)

    if is_stream:
        async def streamer():
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers=_proxy_headers(), json=data,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk

        return StreamingResponse(streamer(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=_proxy_headers(), json=data,
        )
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type="application/json")


async def _proxy_other(request: Request) -> Response:
    body = await request.body()
    path = request.url.path
    query = str(request.url.query)
    url = f"{path}?{query}" if query else path

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.request(
            method=request.method, url=f"{DEEPSEEK_BASE_URL}{url}",
            headers=_proxy_headers(), content=body or None,
        )
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type=resp.headers.get("Content-Type", "application/json"))


# ── MCP 服务器 ────────────────────────────────────────────────────────────────
from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field

mcp = MCPServer(
    name="deepseek_mcp",
    title="DeepSeek Role Translator",
    description="把 developer 角色翻译成 system，透明代理 DeepSeek API",
)


class Message(BaseModel):
    role: str = Field(..., description="system / user / assistant / developer")
    content: str = Field(...)


@mcp.tool(
    name="deepseek_chat",
    annotations=ToolAnnotations(
        read_only_hint=True, destructive_hint=False,
        idempotent_hint=False, open_world_hint=True,
    ),
)
async def deepseek_chat(
    messages: list[Message],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    translated = translate_messages(
        [{"role": m.role, "content": m.content} for m in messages]
    )
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=_proxy_headers(),
            json={
                "model": model or DEEPSEEK_MODEL,
                "messages": translated,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


# ── ASGI 调度 ─────────────────────────────────────────────────────────────────
async def dispatch(scope, receive, send):
    if scope["type"] == "http":
        path = scope["path"]
        method = scope["method"]
        request = Request(scope, receive)

        if path == "/v1/chat/completions" and method == "POST":
            try:
                response = await _proxy_chat(request)
            except Exception:
                traceback.print_exc()
                response = Response(
                    content=json.dumps({"error": traceback.format_exc()}),
                    status_code=500, media_type="application/json",
                )
        elif path.startswith("/v1/"):
            response = await _proxy_other(request)
        else:
            # 其他请求交给 MCP 处理
            mcp_app = mcp.streamable_http_app()
            await mcp_app(scope, receive, send)
            return

        await response(scope, receive, send)


# ── 入口 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="DeepSeek Role Translator")
    parser.add_argument("--http", action="store_true", help="HTTP 模式")
    parser.add_argument("--port", type=int, default=8765, help="端口（默认 8765）")
    args = parser.parse_args()

    if args.http:
        print(f"代理 + MCP 已启动: http://localhost:{args.port}")
        print(f"  代理端点:     http://localhost:{args.port}/v1")
        print(f"  MCP 端点:     http://localhost:{args.port}/mcp")
        uvicorn.run(dispatch, host="127.0.0.1", port=args.port, log_level="info")
    else:
        mcp.run()
