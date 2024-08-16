# Poe Documentation: https://creator.poe.com/docs/server-bots-functional-guides
# OpenAI Documentation: https://platform.openai.com/docs/api-reference/chat/create
import asyncio
import json
# Get Environment Variables
import os
import time
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from fastapi import Request, Header
from fastapi.responses import StreamingResponse
from fastapi_poe.client import get_bot_response
from fastapi_poe.types import ProtocolMessage

from app.config import configure_logging

logger = configure_logging()

router = APIRouter()

DEFAULT_MODEL = os.getenv("BOT", default="GPT-4o")
LISTEN_PORT = int(os.getenv("PORT", default=10000))
BASE_URL = os.getenv("BASE", default="https://api.poe.com/bot/")


def openai_format_messages_to_poe_format(openai_format_messages: list) -> list:
    """Convert OpenAI formatted messages to POE formatted messages."""
    poe_format_messages = [
        # Convert 'assistant' to 'bot' or we get an error
        ProtocolMessage(
            role=msg["role"].lower().replace("assistant", "bot"),
            content=msg["content"],
            temperature=msg.get("temperature", 0.5),
        )
        for msg in openai_format_messages
    ]
    return poe_format_messages


async def get_poe_bot_stream_partials(
        api_key: str, poe_format_messages: list, bot_name: str
) -> AsyncGenerator[str, None]:
    async for partial in get_bot_response(
            messages=poe_format_messages,
            bot_name=bot_name,
            api_key=api_key,
            base_url=BASE_URL,
            skip_system_prompt=False,
    ):
        yield partial.text


async def adaptive_streamer(
        poe_bot_stream_partials_generator, is_sse_enabled=False
) -> AsyncGenerator[str, Any]:
    timestamp = int(time.time())
    id = f"chatcmpl-{timestamp}"

    STREAM_PREFIX = f'data: {{"id":"{id}","object":"chat.completion.chunk","created":{timestamp},"model":"gpt-4","choices":[{{"index":0,"delta":{{"content":'
    STREAM_SUFFIX = '},\"finish_reason\":null}]}\n\n'
    ENDING_CHUNK = f'data: {{"id":"{id}","object":"chat.completion.chunk","created":{timestamp},"model":"gpt-4","choices":[{{"index":0,"delta":{{}},"finish_reason":"stop"}}]}}\n\ndata: [DONE]\n\n'
    NON_STREAM_PREFIX = f'{{"id":"{id}","object":"chat.completion","created":{timestamp},"model":"gpt-4","choices":[{{"index":0,"message":{{"role":"assistant","content":"'
    NON_STREAM_SUFFIX = '"},"logprobs":null,"finish_reason":"stop"}],"usage":{"prompt_tokens":0,"completion_tokens":0,"total_tokens":0},"system_fingerprint":"abc"}\n\n'

    # 创建锁以避免共享状态问题
    lock = asyncio.Lock()

    try:
        if is_sse_enabled:
            chat_prefix, chat_suffix = STREAM_PREFIX, STREAM_SUFFIX
        else:
            chat_prefix, chat_suffix = "", ""
            yield NON_STREAM_PREFIX

        async for partial in poe_bot_stream_partials_generator:
            try:
                json_partial = json.dumps(partial)

                async with lock:
                    if is_sse_enabled:
                        yield chat_prefix
                        yield json_partial
                        yield chat_suffix
                    else:
                        yield json_partial[1:-1]  # 去掉首尾的引号
            except asyncio.CancelledError:
                # 处理任务取消
                if is_sse_enabled:
                    async with lock:
                        yield ENDING_CHUNK
                return
            except Exception as e:
                # 记录异常
                print(f"Error while processing partial data: {e}")  # 使用合适的日志库代替 print
                continue

        if not is_sse_enabled:
            async with lock:
                yield NON_STREAM_SUFFIX

    except asyncio.CancelledError:
        # 处理任务取消
        print("adaptive_streamer was cancelled, likely due to client disconnect.")  # 使用合适的日志库代替 print
    except Exception as e:
        # 记录异常
        print(f"Unhandled error in adaptive_streamer: {e}")  # 使用合适的日志库代替 print
    finally:
        # 执行清理工作
        print("adaptive_streamer has completed execution.")  # 使用合适的日志库代替 print

    return


@router.get("/")
def read_root():
    return {"message": "Hello, World!"}


@router.post("/v1/chat/completions")
async def chat_completions(
        request: Request, authorization: str = Header(None)
) -> StreamingResponse:
    # Assuming the header follows the standard format: "Bearer $API_KEY"
    api_key = authorization.split(" ")[1]
    body = await request.json()

    # Extract bot_name (model) and messages from the request body
    bot_name = body.get("model", DEFAULT_MODEL)
    openai_format_messages = body.get("messages", [])
    is_stream = body.get("stream", False)

    # Convert OpenAI formatted messages to POE formatted messages
    poe_format_messages = openai_format_messages_to_poe_format(openai_format_messages)

    # Get poe bot response
    poe_bot_stream_partials_generator = get_poe_bot_stream_partials(
        api_key, poe_format_messages, bot_name
    )

    return StreamingResponse(
        adaptive_streamer(poe_bot_stream_partials_generator, is_stream),
        media_type=(
                ("text/event-stream" if is_stream else "application/json")
                + ";charset=UTF-8"
        ),
    )