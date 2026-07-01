"""
第1章产出：LLMClient
=====================

补全这个类，让 tests/test_llm.py 全部通过。

依赖：
  - openai SDK
  - tiktoken
  - 环境变量：BASE_URL / API_KEY / MODEL_ID
"""

from __future__ import annotations

import os
from typing import Generator

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("BASE_URL"),
            api_key=os.getenv("API_KEY"),
        )
        self.model = os.getenv("MODEL_ID")
        self.enc = tiktoken.get_encoding("cl100k_base")

    def chat(self, messages: list[dict], **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message.content

    def chat_with_tools(self, messages: list[dict], tools: list[dict], **kwargs) -> dict:
        """带工具调用的 chat，返回包含 content 和 tool_calls 的 dict。"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            **kwargs,
        )
        msg = resp.choices[0].message
        result = {"role": msg.role, "content": msg.content}
        if msg.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return result

    def chat_stream(self, messages: list[dict], **kwargs) -> Generator[str, None, None]:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs,
        )
        for chunk in resp:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def count_tokens(self, text: str) -> int:
        return len(self.enc.encode(text))