"""
Web UI 模块
===========

使用 Gradio 构建图形化界面，替代 CLI。
支持文件树浏览 + 对话交互。
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Tuple, Optional
import gradio as gr

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import LLMClient
from tools import ToolRegistry
from agent import Agent
from context import ContextManager
from memory import Memory
from coding_tools import build_coding_tools


class WebUI:
    """Web UI 主类"""
    
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.agent = self._init_agent()
        self.chat_history = []
        
    def _init_agent(self) -> Agent:
        """初始化 Agent"""
        llm = LLMClient()
        tools = build_coding_tools()
        context = ContextManager(llm=llm, max_tokens=8000)
        mem = Memory(llm=llm)
        
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
        )
    
    def get_file_tree(self, root_dir: str = None, max_depth: int = 3) -> str:
        """获取文件树结构"""
        if root_dir is None:
            root_dir = self.workspace_dir
        
        def build_tree(path: str, prefix: str = "", depth: int = 0) -> List[str]:
            if depth >= max_depth:
                return []
            
            items = []
            try:
                entries = sorted(os.listdir(path))
            except PermissionError:
                return []
            
            # 分离目录和文件
            dirs = []
            files = []
            for entry in entries:
                if entry.startswith('.'):
                    continue  # 跳过隐藏文件
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    dirs.append(entry)
                else:
                    files.append(entry)
            
            # 添加目录
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
            
            # 添加文件
            for i, f in enumerate(files):
                is_last = (i == len(files) - 1)
                connector = "└── " if is_last else "├── "
                # 根据文件类型选择图标
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
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.html': '🌐',
            '.css': '🎨',
            '.json': '📋',
            '.md': '📝',
            '.txt': '📄',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.toml': '⚙️',
            '.cfg': '⚙️',
            '.env': '🔒',
            '.gitignore': '🙈',
            '.dockerfile': '🐳',
            '.sh': '🐚',
            '.bat': '🐚',
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
            
            # 检查文件大小
            size = os.path.getsize(full_path)
            if size > 100 * 1024:  # 100KB
                return f"文件过大 ({size/1024:.1f}KB)，只显示前1000行"
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 限制显示行数
            lines = content.split('\n')
            if len(lines) > 1000:
                content = '\n'.join(lines[:1000]) + f"\n\n... (共 {len(lines)} 行，只显示前1000行)"
            
            return content
        except Exception as e:
            return f"读取文件失败: {str(e)}"
    
    def chat_with_agent(self, message: str, history: List[Tuple[str, str]]) -> Tuple[str, List[Tuple[str, str]]]:
        """与 Agent 对话"""
        # 添加用户消息到历史
        history.append((message, ""))
        
        try:
            # 运行 Agent
            response = ""
            for chunk in self.agent.run_stream(message):
                response += chunk
                # 更新最后一轮的回复
                history[-1] = (message, response)
                yield "", history
        except Exception as e:
            response = f"错误: {str(e)}"
            history[-1] = (message, response)
        
        return "", history
    
    def create_ui(self) -> gr.Blocks:
        """创建 Gradio 界面"""
        with gr.Blocks(
            title="My Coding Agent",
            theme=gr.themes.Soft(),
            css="""
            .file-tree {
                font-family: monospace;
                font-size: 14px;
                line-height: 1.5;
            }
            """
        ) as app:
            gr.Markdown("# 🤖 My Coding Agent")
            gr.Markdown("AI 驱动的编程助手，支持文件浏览和代码编辑")
            
            with gr.Row():
                # 左侧：文件树
                with gr.Column(scale=1):
                    gr.Markdown("## 📁 文件树")
                    
                    # 刷新按钮
                    refresh_btn = gr.Button("🔄 刷新文件树", size="sm")
                    
                    # 文件树显示
                    file_tree = gr.Textbox(
                        label="项目结构",
                        value=self.get_file_tree(),
                        lines=20,
                        max_lines=30,
                        interactive=False,
                        elem_classes=["file-tree"]
                    )
                    
                    # 文件选择
                    file_path = gr.Textbox(
                        label="文件路径",
                        placeholder="输入文件路径查看内容...",
                        value=""
                    )
                    
                    view_file_btn = gr.Button("👀 查看文件", size="sm")
                    
                    # 文件内容预览
                    file_content = gr.Textbox(
                        label="文件内容",
                        lines=15,
                        max_lines=20,
                        interactive=False
                    )
                
                # 右侧：对话界面
                with gr.Column(scale=2):
                    gr.Markdown("## 💬 对话")
                    
                    # 对话历史
                    chatbot = gr.Chatbot(
                        label="对话历史",
                        height=400,
                        show_copy_button=True
                    )
                    
                    # 输入框
                    with gr.Row():
                        msg_input = gr.Textbox(
                            label="输入消息",
                            placeholder="描述你想要完成的任务...",
                            lines=2,
                            scale=4
                        )
                        send_btn = gr.Button("发送", variant="primary", scale=1)
                    
                    # 快捷操作
                    with gr.Row():
                        clear_btn = gr.Button("🗑️ 清空对话", size="sm")
                        example_btn = gr.Button("💡 示例任务", size="sm")
            
            # 事件绑定
            
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
            
            # 发送消息
            send_btn.click(
                fn=self.chat_with_agent,
                inputs=[msg_input, chatbot],
                outputs=[msg_input, chatbot]
            )
            
            # 回车发送
            msg_input.submit(
                fn=self.chat_with_agent,
                inputs=[msg_input, chatbot],
                outputs=[msg_input, chatbot]
            )
            
            # 清空对话
            clear_btn.click(
                fn=lambda: ([], []),
                outputs=chatbot
            )
            
            # 示例任务
            example_tasks = [
                "帮我查看当前目录有哪些文件",
                "读取 README.md 文件内容",
                "创建一个简单的 Python 脚本",
                "运行测试用例",
            ]
            
            def get_example():
                import random
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
    
    # 创建 Web UI
    web_ui = WebUI(workspace_dir=args.workspace)
    app = web_ui.create_ui()
    
    # 启动服务
    print(f"🚀 启动 Web UI: http://{args.host}:{args.port}")
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        show_error=True
    )


if __name__ == "__main__":
    main()