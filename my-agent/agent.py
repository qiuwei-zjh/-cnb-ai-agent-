"""
第3章产出：Agent 主循环
========================

补全这个类，让 tests/test_agent.py 全部通过。

核心逻辑：Agent = LLM + Tools + Loop
"""

from __future__ import annotations

import json

from llm import LLMClient
from tools import ToolRegistry


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        system_prompt: str = "你是一个有用的助手。",
        context_manager=None,
        memory=None,
    ):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.context_manager = context_manager
        self.memory = memory

    def run(self, user_message: str, max_iterations: int = 10) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        # 第4章 接入：Memory — 检索相关历史记忆，注入上下文
        if self.memory:
            try:
                memories = self.memory.search(user_message, k=3)
                relevant = [(sim, text) for sim, text in memories if sim > 0.3]
                if relevant:
                    memory_text = "【相关历史记忆】\n" + "\n".join(
                        f"- {text}" for _, text in relevant
                    )
                    messages.insert(1, {"role": "system", "content": memory_text})
            except Exception:
                pass  # 记忆检索失败不影响主流程

        tool_schemas = self.tools.to_schemas()

        for i in range(max_iterations):
            # 第4章 接入：ContextManager — 上下文过长时自动压缩
            if self.context_manager:
                try:
                    if self.context_manager.should_compress(messages):
                        messages = self.context_manager.compress(messages)
                except Exception:
                    pass  # 压缩失败不影响主流程

            if tool_schemas:
                response = self.llm.chat_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                )
            else:
                content = self.llm.chat(messages=messages)
                response = {"role": "assistant", "content": content}

            tool_calls = response.get("tool_calls")

            # 构建 assistant 消息（有 tool_calls 时必须一起带上，DeepSeek 对此严格要求）
            assistant_msg: dict = {"role": response["role"]}
            if response.get("content"):
                assistant_msg["content"] = response["content"]
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            if not tool_calls:
                # 任务完成，将本轮对话存入记忆
                if self.memory and response.get("content"):
                    try:
                        self.memory.add(f"用户: {user_message}\nAgent: {response['content']}")
                    except Exception:
                        pass  # 记忆存储失败不影响主流程
                return response.get("content", "")

            # 执行工具调用
            for tool_call in tool_calls:
                name = tool_call["function"]["name"]
                raw_args = tool_call["function"]["arguments"]
                try:
                    args = json.loads(raw_args)
                except Exception as e:
                    result = f"[error] {e}"
                else:
                    result = self.tools.invoke(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(result),
                })

        # 达到最大迭代次数
        return f"[agent] 已达到最大迭代次数 ({max_iterations})，停止执行。"

