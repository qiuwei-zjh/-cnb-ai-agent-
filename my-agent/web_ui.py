"""
Web UI 模块
===========

使用 Gradio 构建图形化界面，替代 CLI。
支持文件树浏览 + 对话交互 + 会话持久化 + 会话切换。
"""

import os
import sys
import random
import gradio as gr

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import LLMClient
from tools import ToolRegistry
from agent import Agent
from context import ContextManager
from memory import Memory
from session import SessionManager
from coding_tools import build_coding_tools


class WebUI:
    """Web UI 主类"""

    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = os.path.abspath(workspace_dir)

        # 会话持久化管理
        self.session_mgr = SessionManager()

        # 尝试恢复最近会话
        latest_id = self.session_mgr.get_latest_session()
        if latest_id:
            data = self.session_mgr.load_session(latest_id)
            if data:
                self.session_id = latest_id
                conversation = data.get("conversation", [])
                memory_entries = data.get("memory_entries", [])
                self.chat_history = [
                    {"role": m["role"], "content": m.get("content", "")}
                    for m in conversation
                    if m["role"] in ("user", "assistant")
                ]
                summary = data.get("summary", "")
                print(f"📂 已恢复会话: {self.session_id} ({len(self.chat_history)} 条消息)")
                if summary:
                    print(f"   📝 {summary}")
            else:
                self.session_id = self.session_mgr.create_session()
                self.chat_history = []
                conversation = []
                memory_entries = []
        else:
            self.session_id = self.session_mgr.create_session()
            self.chat_history = []
            conversation = []
            memory_entries = []

        self.agent = self._init_agent(conversation=conversation, memory_entries=memory_entries)

    def _init_agent(
        self,
        conversation: list[dict] | None = None,
        memory_entries: list | None = None,
    ) -> Agent:
        """初始化 Agent"""
        llm = LLMClient()
        tools = build_coding_tools()
        context = ContextManager(llm=llm, max_tokens=8000)
        mem = Memory(llm=llm)

        # 将 LLM 传给 SessionManager 以支持摘要生成
        self.session_mgr.set_llm(llm)

        if memory_entries:
            mem.load_entries(memory_entries)

        system_prompt = """\
你是一个 Coding Agent，能够读写文件、执行命令来帮用户完成编程任务。

工作规范：
- 先用 list_dir / read_file 了解现状
- 再用 write_file / edit_file 修改代码
- 最后用 bash 验证结果
- 每一步都要说清楚你在做什么
"""

        return Agent(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            context_manager=context,
            memory=mem,
            conversation=conversation or [],
        )

    def _save_current_session(self) -> None:
        """保存当前会话。"""
        try:
            self.session_mgr.save_session(
                self.session_id,
                self.agent.get_conversation(),
                self.agent.memory.get_entries() if self.agent.memory else [],
            )
        except Exception:
            pass  # 保存失败不影响主流程

    # ═══════════════════════════════════════════════════════════════
    # 会话管理方法
    # ═══════════════════════════════════════════════════════════════

    def _get_session_choices(self) -> list[str]:
        """获取会话下拉选项列表（格式: "编号. 名称 (消息数) 摘要"）。"""
        sessions = self.session_mgr.list_sessions()
        choices = []
        for i, s in enumerate(sessions):
            marker = "●" if s["session_id"] == self.session_id else "○"
            summary = s.get("summary", "")
            # 截断摘要
            if len(summary) > 40:
                summary = summary[:37] + "..."
            label = f"{marker} [{i+1}] {s['name']} ({s['message_count']}条)"
            if summary:
                label += f" — {summary}"
            choices.append(label)
        if not choices:
            choices = ["（无会话）"]
        return choices

    def _get_session_id_by_index(self, index: int) -> str | None:
        """根据下拉索引获取 session_id。"""
        sessions = self.session_mgr.list_sessions()
        if 0 <= index < len(sessions):
            return sessions[index]["session_id"]
        return None

    def get_session_info(self) -> str:
        """获取当前会话信息文本。"""
        sessions = self.session_mgr.list_sessions()
        current = None
        for s in sessions:
            if s["session_id"] == self.session_id:
                current = s
                break

        if current:
            summary = current.get("summary", "")
            lines = [
                f"📌 **{current['name']}**",
                f"ID: `{self.session_id}`",
                f"消息: {current['message_count']} 条",
            ]
            if summary:
                lines.append(f"📝 {summary}")
            return "  \n".join(lines)
        return f"📌 当前会话: `{self.session_id}`"

    def list_sessions(self) -> str:
        """列出所有历史会话（带摘要）。"""
        sessions = self.session_mgr.list_sessions()
        if not sessions:
            return "📭 暂无历史会话"

        lines = ["📋 **历史会话列表**:", ""]
        for i, s in enumerate(sessions):
            marker = "🟢" if s["session_id"] == self.session_id else "  "
            summary = s.get("summary", "")
            lines.append(
                f"{marker} **{i+1}. {s['name']}** — "
                f"{s['message_count']} 条消息"
            )
            if summary:
                lines.append(f"     📝 {summary}")
            lines.append(f"     `{s['session_id']}`  |  更新: {s['updated_at'][:19]}")
            lines.append("")
        return "\n".join(lines)

    def switch_to_session(self, choice: str) -> tuple[list, str, str]:
        """切换到选中的会话。返回 (chat_history, session_info, dropdown_value)。"""
        if not choice or choice == "（无会话）":
            return (
                self.chat_history,
                self.get_session_info(),
                choice,
            )

        # 从 choice 中提取编号
        import re
        match = re.search(r'\[(\d+)\]', choice)
        if not match:
            return (self.chat_history, self.get_session_info(), choice)

        idx = int(match.group(1)) - 1
        session_id = self._get_session_id_by_index(idx)
        if not session_id:
            return (self.chat_history, self.get_session_info(), choice)

        if session_id == self.session_id:
            return (self.chat_history, "✅ 已是当前会话", choice)

        # 保存当前会话
        self._save_current_session()

        # 加载目标会话
        data = self.session_mgr.load_session(session_id)
        if not data:
            return (self.chat_history, "⚠️ 加载失败", choice)

        self.session_id = session_id
        conversation = data.get("conversation", [])
        memory_entries = data.get("memory_entries", [])

        # 重建 Agent
        self.agent = self._init_agent(
            conversation=conversation,
            memory_entries=memory_entries,
        )

        # 重建聊天记录
        self.chat_history = [
            {"role": m["role"], "content": m.get("content", "")}
            for m in conversation
            if m["role"] in ("user", "assistant")
        ]

        summary = data.get("summary", "")
        info = f"✅ 已切换到: **{data.get('name', '未命名')}**"
        if summary:
            info += f"  \n📝 {summary}"

        # 更新下拉选项
        new_choices = self._get_session_choices()

        return (
            self.chat_history,
            info,
            gr.Dropdown(choices=new_choices, value=choice),
        )

    def refresh_session_dropdown(self) -> gr.Dropdown:
        """刷新会话下拉列表。"""
        choices = self._get_session_choices()
        return gr.Dropdown(choices=choices)

    # ═══════════════════════════════════════════════════════════════
    # 文件树方法
    # ═══════════════════════════════════════════════════════════════

    def get_file_tree(self, root_dir: str = None, max_depth: int = 3) -> str:
        """获取文件树结构"""
        if root_dir is None:
            root_dir = self.workspace_dir

        def build_tree(path: str, prefix: str = "", depth: int = 0) -> list[str]:
            if depth >= max_depth:
                return []

            items = []
            try:
                entries = sorted(os.listdir(path))
            except PermissionError:
                return []

            dirs = []
            files = []
            for entry in entries:
                if entry.startswith('.'):
                    continue
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    dirs.append(entry)
                else:
                    files.append(entry)

            for i, d in enumerate(dirs):
                is_last = (i == len(dirs) - 1) and len(files) == 0
                connector = "└── " if is_last else "├── "
                items.append(f"{prefix}{connector}📁 {d}/")
                extension = "    " if is_last else "│   "
                items.extend(build_tree(
                    os.path.join(path, d),
                    prefix + extension,
                    depth + 1
                ))

            for i, f in enumerate(files):
                is_last = (i == len(files) - 1)
                connector = "└── " if is_last else "├── "
                icon = self._get_file_icon(f)
                items.append(f"{prefix}{connector}{icon} {f}")

            return items

        tree_lines = [f"📂 {os.path.basename(root_dir)}/"]
        tree_lines.extend(build_tree(root_dir))
        return "\n".join(tree_lines)

    def _get_file_icon(self, filename: str) -> str:
        """根据文件扩展名返回图标"""
        ext = os.path.splitext(filename)[1].lower()
        icon_map = {
            '.py': '🐍', '.js': '📜', '.ts': '📘',
            '.html': '🌐', '.css': '🎨', '.json': '📋',
            '.md': '📝', '.txt': '📄',
            '.yml': '⚙️', '.yaml': '⚙️', '.toml': '⚙️', '.cfg': '⚙️',
            '.env': '🔒', '.gitignore': '🙈',
            '.dockerfile': '🐳', '.sh': '🐚', '.bat': '🐚',
        }
        return icon_map.get(ext, '📄')

    def read_file_content(self, filepath: str) -> str:
        """读取文件内容"""
        try:
            full_path = os.path.join(self.workspace_dir, filepath)
            if not os.path.exists(full_path):
                return f"文件不存在: {filepath}"
            if os.path.isdir(full_path):
                return f"这是一个目录: {filepath}"

            size = os.path.getsize(full_path)
            if size > 100 * 1024:
                return f"文件过大 ({size/1024:.1f}KB)，只显示前1000行"

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            lines = content.split('\n')
            if len(lines) > 1000:
                content = '\n'.join(lines[:1000]) + f"\n\n... (共 {len(lines)} 行，只显示前1000行)"

            return content
        except Exception as e:
            return f"读取文件失败: {str(e)}"

    # ═══════════════════════════════════════════════════════════════
    # 对话方法
    # ═══════════════════════════════════════════════════════════════

    def chat_with_agent(self, message: str, history: list):
        """与 Agent 对话（Gradio 生成器模式），实时反馈执行进度。"""
        if not message or not message.strip():
            yield "", history, "🟢 就绪"
            return

        import re

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": ""})

        # 进度状态映射
        def _detect_status(chunk: str) -> str:
            if "调用工具" in chunk:
                m = re.search(r"调用工具.*?`(\w+)`", chunk)
                if m:
                    return f"🔧 正在执行: `{m.group(1)}` ..."
                return "🔧 正在调用工具..."
            if "执行结果" in chunk:
                return "📋 正在分析结果..."
            if "思考" in chunk:
                return "🤔 正在思考..."
            return "💬 正在生成回复..."

        try:
            response = ""
            last_status = "🤔 正在思考..."
            yield "", history, last_status

            for chunk in self.agent.run_stream(message):
                response += chunk
                history[-1] = {"role": "assistant", "content": response}

                new_status = _detect_status(chunk)
                if new_status != last_status:
                    last_status = new_status
                yield "", history, last_status
        except Exception as e:
            error_msg = f"\n\n❌ **运行错误**: {str(e)}"
            response += error_msg
            history[-1] = {"role": "assistant", "content": response}
            yield "", history, "❌ 运行出错"
            return

        # 每次对话完成后保存会话
        self._save_current_session()
        yield "", history, "✅ 任务完成"

    def reset_agent(self) -> tuple[str, list, gr.Dropdown]:
        """重置 Agent 状态，创建全新会话。"""
        self._save_current_session()
        self.session_id = self.session_mgr.create_session()
        self.agent = self._init_agent()
        self.chat_history = []
        new_choices = self._get_session_choices()
        return (
            f"🆕 新会话已创建: `{self.session_id}`",
            [],
            gr.Dropdown(choices=new_choices),
        )

    # ═══════════════════════════════════════════════════════════════
    # UI 构建
    # ═══════════════════════════════════════════════════════════════

    def create_ui(self) -> gr.Blocks:
        """创建 Gradio 界面"""
        with gr.Blocks(title="My Coding Agent") as app:
            gr.Markdown("# 🤖 My Coding Agent")
            gr.Markdown("AI 驱动的编程助手，支持文件浏览和代码编辑")

            with gr.Row():
                # ── 左侧：文件树 + 会话管理 ──
                with gr.Column(scale=1):
                    gr.Markdown("## 📁 文件树")

                    refresh_btn = gr.Button("🔄 刷新文件树", size="sm")

                    file_tree = gr.Textbox(
                        label="项目结构",
                        value=self.get_file_tree(),
                        lines=18,
                        max_lines=25,
                        interactive=False,
                        elem_classes=["file-tree"]
                    )

                    file_path = gr.Textbox(
                        label="文件路径",
                        placeholder="输入文件路径查看内容...",
                        value=""
                    )

                    view_file_btn = gr.Button("👀 查看文件", size="sm")

                    file_content = gr.Textbox(
                        label="文件内容",
                        lines=12,
                        max_lines=18,
                        interactive=False
                    )

                    # ── 会话管理区域 ──
                    gr.Markdown("---")
                    gr.Markdown("## 💾 会话管理")

                    session_dropdown = gr.Dropdown(
                        label="历史会话",
                        choices=self._get_session_choices(),
                        interactive=True,
                        allow_custom_value=False,
                    )

                    with gr.Row():
                        switch_btn = gr.Button("🔀 切换会话", size="sm")
                        refresh_sessions_btn = gr.Button("🔄 刷新", size="sm")

                    with gr.Row():
                        clear_btn = gr.Button("🆕 新建会话", size="sm")
                        list_sessions_btn = gr.Button("📋 详细列表", size="sm")

                # ── 右侧：对话界面 ──
                with gr.Column(scale=2):
                    gr.Markdown("## 💬 对话")

                    chatbot = gr.Chatbot(
                        label="对话历史",
                        height=420,
                        value=self.chat_history,
                    )

                    with gr.Row():
                        msg_input = gr.Textbox(
                            label="输入消息",
                            placeholder="描述你想要完成的任务...",
                            lines=2,
                            scale=4
                        )
                        send_btn = gr.Button("发送", variant="primary", scale=1)

                    # 实时进度指示器
                    status_display = gr.Markdown(
                        "🟢 就绪",
                        elem_classes=["status-display"],
                    )

                    session_info = gr.Markdown(self.get_session_info())

                    with gr.Row():
                        example_btn = gr.Button("💡 示例任务", size="sm")

            # ═══════════════════════════════════════════════════
            # 事件绑定
            # ═══════════════════════════════════════════════════

            # 刷新文件树
            refresh_btn.click(
                fn=lambda: self.get_file_tree(),
                outputs=file_tree
            )

            # 查看文件
            view_file_btn.click(
                fn=self.read_file_content,
                inputs=file_path,
                outputs=file_content
            )

            # 发送消息（完成后刷新文件树和会话信息）
            send_btn.click(
                fn=self.chat_with_agent,
                inputs=[msg_input, chatbot],
                outputs=[msg_input, chatbot, status_display]
            ).then(
                fn=lambda: self.get_file_tree(),
                outputs=file_tree
            ).then(
                fn=self.get_session_info,
                outputs=session_info,
            ).then(
                fn=self.refresh_session_dropdown,
                outputs=session_dropdown,
            )

            msg_input.submit(
                fn=self.chat_with_agent,
                inputs=[msg_input, chatbot],
                outputs=[msg_input, chatbot, status_display]
            ).then(
                fn=lambda: self.get_file_tree(),
                outputs=file_tree
            ).then(
                fn=self.get_session_info,
                outputs=session_info,
            ).then(
                fn=self.refresh_session_dropdown,
                outputs=session_dropdown,
            )

            # 切换会话
            switch_btn.click(
                fn=self.switch_to_session,
                inputs=session_dropdown,
                outputs=[chatbot, session_info, session_dropdown],
            )

            # 刷新会话下拉列表
            refresh_sessions_btn.click(
                fn=self.refresh_session_dropdown,
                outputs=session_dropdown,
            )

            # 新建会话
            clear_btn.click(
                fn=self.reset_agent,
                outputs=[session_info, chatbot, session_dropdown],
            )

            # 列出会话详情
            list_sessions_btn.click(
                fn=self.list_sessions,
                outputs=session_info,
            )

            # 示例任务
            example_tasks = [
                "帮我查看当前目录有哪些文件",
                "读取 README.md 文件内容",
                "创建一个简单的 Python 脚本",
                "运行测试用例",
            ]

            def get_example():
                return random.choice(example_tasks)

            example_btn.click(
                fn=get_example,
                outputs=msg_input
            )

        return app


def main():
    """启动 Web UI"""
    import argparse

    parser = argparse.ArgumentParser(description="My Coding Agent Web UI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=7860, help="Port to bind")
    parser.add_argument("--share", action="store_true", help="Create public link")
    parser.add_argument("--workspace", default=".", help="Workspace directory")

    args = parser.parse_args()

    web_ui = WebUI(workspace_dir=args.workspace)
    app = web_ui.create_ui()

    print(f"🚀 启动 Web UI: http://{args.host}:{args.port}")
    print(f"📌 会话 ID: {web_ui.session_id}")
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        show_error=True,
        css="""
        .file-tree {
            font-family: monospace;
            font-size: 14px;
            line-height: 1.5;
        }
        .status-display {
            padding: 8px 12px;
            border-radius: 8px;
            background: linear-gradient(135deg, #1e293b, #334155);
            border-left: 4px solid #3b82f6;
            font-size: 14px;
            margin: 8px 0;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.85; }
        }
        """
    )


if __name__ == "__main__":
    main()
