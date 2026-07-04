"""
第6章：组装完整 Agent
=====================

把 第1章-第5章 的零件拼起来，跑通一个真任务。
"""

import sys

# Windows 终端默认 GBK 编码无法输出 emoji，强制使用 UTF-8
sys.stdout.reconfigure(encoding="utf-8")

from llm import LLMClient
from tools import ToolRegistry
from agent import Agent
from context import ContextManager
from memory import Memory
from coding_tools import build_coding_tools

SYSTEM_PROMPT = """\
你是一个 Coding Agent，能够读写文件、执行命令来帮用户完成编程任务。

工作规范：
- 先用 list_dir / read_file 了解现状
- 再用 write_file / edit_file 修改代码
- 最后用 bash 验证结果
- 每一步都要说清楚你在做什么
"""


def main():
    # 初始化各模块
    llm = LLMClient()
    tools = build_coding_tools()
    context = ContextManager(llm=llm, max_tokens=8000)
    mem = Memory(llm=llm)

    # 组装 Agent
    agent = Agent(
        llm=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        context_manager=context,
        memory=mem,
    )

    # 交互式 REPL
    print("🤖 My Coding Agent (输入 exit 退出)")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input or user_input.lower() in ("exit", "quit"):
            break

        # 进度状态
        last_status = ""
        
        def progress_callback(status: str, progress: float):
            """更新进度状态"""
            nonlocal last_status
            if status != last_status:
                # 清除上一行状态
                if last_status:
                    print("\r" + " " * 60 + "\r", end="", flush=True)
                
                # 显示新状态
                if status == "done":
                    print("\r[完成]", end="", flush=True)
                elif status == "thinking":
                    print("\r[思考中...]", end="", flush=True)
                elif status.startswith("calling tool:"):
                    tool_name = status.split(": ")[1]
                    print(f"\r[调用工具: {tool_name}]", end="", flush=True)
                else:
                    print(f"\r[{status}]", end="", flush=True)
                
                last_status = status

        print("\nAgent: ", end="", flush=True)
        
        # 使用流式输出
        try:
            for chunk in agent.run_stream(
                user_input, 
                progress_callback=progress_callback
            ):
                # 清除进度状态行
                if last_status:
                    print("\r" + " " * 60 + "\r", end="", flush=True)
                    last_status = ""
                
                print(chunk, end="", flush=True)
        except KeyboardInterrupt:
            print("\n[中断]")
        
        # 清除进度状态
        if last_status:
            print("\r" + " " * 60 + "\r", end="", flush=True)
        
        print()  # 换行


if __name__ == "__main__":
    main()
