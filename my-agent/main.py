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
from session import SessionManager
from coding_tools import build_coding_tools

SYSTEM_PROMPT = """\
你是一个 Coding Agent，能够读写文件、执行命令来帮用户完成编程任务。

工作规范：
- 先用 list_dir / read_file 了解现状
- 再用 write_file / edit_file 修改代码
- 最后用 bash 验证结果
- 每一步都要说清楚你在做什么
"""


def _print_session_summary(data: dict) -> None:
    """打印会话摘要信息。"""
    conversation = data.get("conversation", [])
    user_msgs = [m for m in conversation if m["role"] == "user"]
    assistant_msgs = [m for m in conversation if m["role"] == "assistant"]
    tool_msgs = [m for m in conversation if m["role"] == "tool"]

    print(f"📂 已恢复会话: {data.get('name', '未命名')}")
    print(f"   ID: {data['session_id']}")
    print(f"   消息: {len(user_msgs)} 问 / {len(assistant_msgs)} 答 / {len(tool_msgs)} 次工具调用")
    print(f"   创建: {data.get('created_at', '未知')[:19]}")
    print(f"   更新: {data.get('updated_at', '未知')[:19]}")

    summary = data.get("summary", "")
    if summary:
        print(f"   📝 摘要: {summary}")
    else:
        # 兜底：显示最近几条用户消息
        recent_users = [m["content"][:80] for m in user_msgs[-3:]]
        if recent_users:
            print(f"   📝 最近话题:")
            for msg in recent_users:
                print(f"      - {msg}")


def main():
    # 初始化各模块
    llm = LLMClient()
    tools = build_coding_tools()
    context = ContextManager(llm=llm, max_tokens=8000)
    mem = Memory(llm=llm)

    # 会话持久化管理（传入 LLM 以支持摘要生成）
    session_mgr = SessionManager(llm=llm)

    # 解析命令行参数
    new_session = "--new-session" in sys.argv or "-n" in sys.argv
    # 支持通过命令行指定会话 ID
    session_arg = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--session", "-s") and i + 1 < len(sys.argv):
            session_arg = sys.argv[i + 1]
            break

    session_id = None
    conversation = []
    memory_entries = []

    if new_session:
        # 强制新建会话
        session_id = session_mgr.create_session()
        print(f"🆕 已创建新会话: {session_id}")
    elif session_arg:
        # 命令行指定了会话 ID
        found_id = session_mgr.find_session(session_arg)
        if found_id:
            data = session_mgr.load_session(found_id)
            if data:
                session_id = found_id
                conversation = data.get("conversation", [])
                memory_entries = data.get("memory_entries", [])
                mem.load_entries(memory_entries)
                _print_session_summary(data)
        if session_id is None:
            print(f"⚠️  未找到会话: {session_arg}，将创建新会话")
    else:
        # 尝试恢复最近会话
        latest_id = session_mgr.get_latest_session()
        if latest_id:
            data = session_mgr.load_session(latest_id)
            if data:
                session_id = latest_id
                conversation = data.get("conversation", [])
                memory_entries = data.get("memory_entries", [])
                mem.load_entries(memory_entries)
                _print_session_summary(data)

    # 仍未确定会话则创建新的
    if session_id is None:
        session_id = session_mgr.create_session()
        print(f"🆕 已创建新会话: {session_id}")

    # 组装 Agent（传入历史对话）
    agent = Agent(
        llm=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        context_manager=context,
        memory=mem,
        conversation=conversation,
    )

    # 交互式 REPL
    print("🤖 My Coding Agent")
    print("   命令: exit 退出 | /new 新建 | /sessions 列表 | /session <id> 切换")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input or user_input.lower() in ("exit", "quit"):
            break

        # ── 内置命令 ──

        # 新建会话
        if user_input.lower() in ("/new", "/clear"):
            # 保存当前会话
            try:
                session_mgr.save_session(
                    session_id, agent.get_conversation(), mem.get_entries()
                )
            except Exception:
                pass
            agent.clear_conversation()
            mem = Memory(llm=llm)
            agent.memory = mem
            session_id = session_mgr.create_session()
            print(f"🆕 已创建新会话: {session_id}")
            continue

        # 列出所有会话
        if user_input.lower() in ("/sessions", "/list"):
            print(session_mgr.format_session_list())
            continue

        # 切换到指定会话
        if user_input.lower().startswith("/session "):
            query = user_input[len("/session "):].strip()
            if not query:
                print("⚠️  用法: /session <编号或ID>")
                continue

            # 保存当前会话
            try:
                session_mgr.save_session(
                    session_id, agent.get_conversation(), mem.get_entries()
                )
            except Exception:
                pass

            found_id = session_mgr.find_session(query)
            if found_id:
                data = session_mgr.load_session(found_id)
                if data:
                    session_id = found_id
                    conversation = data.get("conversation", [])
                    memory_entries = data.get("memory_entries", [])
                    mem = Memory(llm=llm)
                    mem.load_entries(memory_entries)
                    agent = Agent(
                        llm=llm,
                        tools=tools,
                        system_prompt=SYSTEM_PROMPT,
                        context_manager=context,
                        memory=mem,
                        conversation=conversation,
                    )
                    print(f"✅ 已切换到会话: {session_id}")
                    _print_session_summary(data)
                else:
                    print(f"⚠️  无法加载会话: {query}")
            else:
                print(f"⚠️  未找到会话: {query}（使用 /sessions 查看列表）")
            continue

        # ── 正常对话 ──

        # 进度状态
        last_status = ""

        def progress_callback(status: str, progress: float):
            """更新进度状态"""
            nonlocal last_status
            if status != last_status:
                if last_status:
                    print("\r" + " " * 60 + "\r", end="", flush=True)

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

        try:
            for chunk in agent.run_stream(
                user_input,
                progress_callback=progress_callback
            ):
                if last_status:
                    print("\r" + " " * 60 + "\r", end="", flush=True)
                    last_status = ""

                print(chunk, end="", flush=True)
        except KeyboardInterrupt:
            print("\n[中断]")

        if last_status:
            print("\r" + " " * 60 + "\r", end="", flush=True)

        print()  # 换行

        # 每次对话后自动保存会话
        try:
            session_mgr.save_session(
                session_id,
                agent.get_conversation(),
                mem.get_entries(),
            )
        except Exception:
            pass

    # 退出前保存会话
    try:
        session_mgr.save_session(
            session_id,
            agent.get_conversation(),
            mem.get_entries(),
        )
        print(f"\n💾 会话已保存: {session_id}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
