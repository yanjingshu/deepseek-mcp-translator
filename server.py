#!/usr/bin/env python3
"""
MCP Server: DeepSeek Role Translator
====================================
Android Studio 发来的消息里带有 "developer" 角色，但 DeepSeek API 只认 "system"。
这个 MCP 服务器在中间做翻译：developer → system，然后把请求转发给 DeepSeek。
"""

import os

from dotenv import load_dotenv
from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

# ── 加载 .env ──────────────────────────────────────────────────────────────
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ── DeepSeek 客户端（懒加载，避免无 key 时 import 就报错）───────────────────────
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    return _client

# ── MCP 服务器 ──────────────────────────────────────────────────────────────
mcp = MCPServer(
    name="deepseek_mcp",
    title="DeepSeek Role Translator",
    description="把 Android Studio 的 developer 角色翻译成 DeepSeek 认识的 system 角色",
)


# ── Pydantic 模型 ───────────────────────────────────────────────────────────
class Message(BaseModel):
    """一条对话消息"""

    role: str = Field(..., description="消息角色: system / user / assistant / developer")
    content: str = Field(..., description="消息内容")


# ── 核心翻译逻辑 ───────────────────────────────────────────────────────────
def translate_messages(messages: list[Message]) -> list[dict]:
    """把 developer 角色翻译成 system 角色，其余照原样传递。"""
    return [
        {"role": "system" if m.role == "developer" else m.role, "content": m.content}
        for m in messages
    ]


# ── 工具定义 ────────────────────────────────────────────────────────────────
@mcp.tool(
    name="deepseek_chat",
    title="DeepSeek Chat",
    description="调用 DeepSeek API 进行对话，自动将 developer 角色翻译为 system",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=True,
    ),
)
async def deepseek_chat(
    messages: list[Message],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """调用 DeepSeek API 进行对话。

    当 Android Studio 发来带 developer 角色的消息时，此工具会在转发给
    DeepSeek 之前自动将 developer 替换为 system，保证 DeepSeek 能正确识别。

    Args:
        messages: 对话消息列表。developer 角色会被自动翻译成 system。
        model: 模型名称，默认使用 DEEPSEEK_MODEL 环境变量指定的模型。
        temperature: 采样温度 (0-2)，默认 0.7。
        max_tokens: 最大输出 token 数，默认 4096。
    """
    translated = translate_messages(messages)
    actual_model = model or DEEPSEEK_MODEL

    response = await _get_client().chat.completions.create(
        model=actual_model,
        messages=translated,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content or ""


# ── 入口 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DeepSeek MCP Role Translator")
    parser.add_argument(
        "--http",
        action="store_true",
        help="使用 HTTP 模式（默认 stdio）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="HTTP 模式端口（默认 8765）",
    )
    args = parser.parse_args()

    if args.http:
        print(f"HTTP 模式启动: http://localhost:{args.port}/mcp")
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run()
