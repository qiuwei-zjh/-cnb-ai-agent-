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

    def chat_stream_with_tools(self, messages: list[dict], tools: list[dict], **kwargs) -> Generator[dict, None, None]:
        """带工具调用的流式 chat，返回包含 content 和 tool_calls 的 dict。"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=True,
            **kwargs,
        )
        
        # 用于累积工具调用信息
        tool_calls_data = {}
        content = ""
        
        for chunk in resp:
            if not chunk.choices:
                continue
            
            choice = chunk.choices[0]
            delta = choice.delta
            
            # 处理内容
            if delta.content:
                content += delta.content
                yield {"type": "content", "content": delta.content}
            
            # 处理工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls_data:
                        tool_calls_data[tc.index] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        }
                    
                    # 更新工具调用信息
                    if tc.id:
                        tool_calls_data[tc.index]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[tc.index]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_data[tc.index]["function"]["arguments"] += tc.function.arguments
            
            # 如果流结束（stop / tool_calls / length / content_filter），返回完整结果
            if choice.finish_reason is not None:
                # 返回最终结果
                result = {"role": "assistant", "content": content}
                if tool_calls_data:
                    result["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": tc["type"],
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            },
                        }
                        for tc in tool_calls_data.values()
                    ]
                yield {"type": "result", "result": result}
                break

    def count_tokens(self, text: str) -> int:
        return len(self.enc.encode(text))