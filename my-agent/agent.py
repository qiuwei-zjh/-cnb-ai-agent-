"""
第3章产出：Agent 主循环
========================

补全这个类，让 tests/test_agent.py 全部通过。

核心逻辑：Agent = LLM + Tools + Loop
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from llm import LLMClient
from tools import ToolRegistry
from typing import Generator, Callable, Optional


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

    def _execute_tool(self, tool_call: dict) -> dict:
        """执行单个工具调用，返回 {"id": ..., "content": ...} 格式的结果。"""
        name = tool_call["function"]["name"]
        raw_args = tool_call["function"]["arguments"]
        try:
            args = json.loads(raw_args)
        except Exception as e:
            result = f"[error] {e}"
        else:
            result = self.tools.invoke(name, args)
        return {"id": tool_call["id"], "content": str(result)}

    def run(self, user_message: str, max_iterations: int = 10) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

       
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
                pass 

        tool_schemas = self.tools.to_schemas()

        for i in range(max_iterations):
           
            if self.context_manager:
                try:
                    if self.context_manager.should_compress(messages):
                        messages = self.context_manager.compress(messages)
                except Exception:
                    pass  

            if tool_schemas:
                response = self.llm.chat_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                )
            else:
                content = self.llm.chat(messages=messages)
                response = {"role": "assistant", "content": content}

            tool_calls = response.get("tool_calls")

          
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
            # 执行工具调用（单个直接执行，多个并发）
            if len(tool_calls) == 1:
                results = [self._execute_tool(tool_calls[0])]
            else:
                max_workers = min(len(tool_calls), 5)
                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    results = list(pool.map(self._execute_tool, tool_calls))

            for result in results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result["id"],
                    "content": str(result["content"]),
                })

        # 达到最大迭代次数
        return f"[agent] 已达到最大迭代次数 ({max_iterations})，停止执行。"

    def run_stream(
        self, 
        user_message: str, 
        max_iterations: int = 10,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Generator[str, None, None]:
        """
        流式运行 Agent，支持进度回调。
        
        Args:
            user_message: 用户消息
            max_iterations: 最大迭代次数
            progress_callback: 进度回调函数，参数为 (status, progress)
                status: 状态描述，如 "thinking", "calling tool: read_file", "done"
                progress: 进度值 0.0-1.0
        
        Yields:
            流式输出的文本片段
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        # 添加记忆
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
                pass 

        tool_schemas = self.tools.to_schemas()

        for i in range(max_iterations):
            # 报告进度：正在思考
            if progress_callback:
                progress_callback("thinking", i / max_iterations)
            
            # 压缩上下文
            if self.context_manager:
                try:
                    if self.context_manager.should_compress(messages):
                        messages = self.context_manager.compress(messages)
                except Exception:
                    pass  

            if tool_schemas:
                # 流式调用带工具的LLM
                full_response = None
                for event in self.llm.chat_stream_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                ):
                    if event["type"] == "content":
                        # 流式输出内容
                        yield event["content"]
                    elif event["type"] == "result":
                        full_response = event["result"]
                        break
                
                if full_response is None:
                    # 如果没有收到结果，构建一个空响应
                    full_response = {"role": "assistant", "content": ""}
            else:
                # 流式调用普通LLM
                content_parts = []
                for chunk in self.llm.chat_stream(messages=messages):
                    content_parts.append(chunk)
                    yield chunk
                full_response = {"role": "assistant", "content": "".join(content_parts)}

            tool_calls = full_response.get("tool_calls")

            # 添加助手消息到对话历史
            assistant_msg: dict = {"role": full_response["role"]}
            if full_response.get("content"):
                assistant_msg["content"] = full_response["content"]
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            if not tool_calls:
                # 任务完成
                if progress_callback:
                    progress_callback("done", 1.0)
                
                # 将本轮对话存入记忆
                if self.memory and full_response.get("content"):
                    try:
                        self.memory.add(f"用户: {user_message}\nAgent: {full_response['content']}")
                    except Exception:
                        pass
                return

            # 执行工具调用
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = tool_call["function"]["arguments"]
                # 报告进度：正在调用工具
                if progress_callback:
                    progress_callback(f"calling tool: {tool_name}", (i + 0.5) / max_iterations)

                # 向用户展示正在调用的工具
                yield f"\n\n🔧 **调用工具**: `{tool_name}`\n```json\n{tool_args}\n```\n"

                # 执行工具
                result = self._execute_tool(tool_call)

                # 向用户展示工具执行结果（截断过长内容）
                result_str = str(result["content"])
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "\n... (结果过长，已截断)"
                yield f"\n📋 **执行结果**:\n```\n{result_str}\n```\n"

                # 添加工具结果到对话历史
                messages.append({
                    "role": "tool",
                    "tool_call_id": result["id"],
                    "content": str(result["content"]),
                })

        # 达到最大迭代次数
        if progress_callback:
            progress_callback("max iterations reached", 1.0)
        yield f"[agent] 已达到最大迭代次数 ({max_iterations})，停止执行。"

