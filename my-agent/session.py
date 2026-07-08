"""
会话持久化管理模块
==================

管理会话的创建、保存、加载和删除。
会话数据存储在 ~/.my-agent/sessions/ 目录下。
支持自动生成会话摘要。
"""

from __future__ import annotations

import json
import os
from datetime import datetime


class SessionManager:
    """管理 Agent 会话的持久化存储。"""

    def __init__(self, session_dir: str | None = None, llm=None):
        if session_dir is None:
            session_dir = os.path.expanduser("~/.my-agent/sessions")
        self.session_dir = session_dir
        self.llm = llm  # 可选的 LLM 客户端，用于生成摘要
        os.makedirs(self.session_dir, exist_ok=True)

    def set_llm(self, llm) -> None:
        """设置 LLM 客户端（用于生成摘要）。"""
        self.llm = llm

    def _session_path(self, session_id: str) -> str:
        """获取会话文件的完整路径。"""
        safe_id = os.path.basename(session_id)
        return os.path.join(self.session_dir, f"{safe_id}.json")

    def _generate_id(self) -> str:
        """生成基于时间戳的会话 ID。"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _heuristic_summary(self, conversation: list[dict]) -> str:
        """基于启发式规则生成会话摘要（无需 LLM）。"""
        if not conversation:
            return "空会话"

        user_messages = [
            m.get("content", "") for m in conversation
            if m["role"] == "user" and m.get("content")
        ]

        if not user_messages:
            return f"{len(conversation)} 条系统消息"

        msg_count = len([
            m for m in conversation
            if m["role"] in ("user", "assistant")
        ])
        tool_count = len([
            m for m in conversation if m["role"] == "tool"
        ])

        parts = [f"共 {msg_count} 条对话"]
        if tool_count:
            parts.append(f"{tool_count} 次工具调用")

        topics = []
        for msg in user_messages[:3]:
            text = msg.strip()
            if len(text) > 60:
                text = text[:57] + "..."
            if text:
                topics.append(text)

        if topics:
            parts.append("话题: " + " | ".join(topics))

        return "；".join(parts)

    def _llm_summary(self, conversation: list[dict]) -> str | None:
        """使用 LLM 生成会话摘要。失败时返回 None。"""
        if not self.llm or not conversation:
            return None

        dialogs = []
        for m in conversation:
            if m["role"] in ("user", "assistant") and m.get("content"):
                dialogs.append(f"[{m['role']}]: {m['content']}")
            if len(dialogs) >= 20:
                break

        if not dialogs:
            return None

        prompt = (
            "请用一句话（不超过50个字）总结以下编程对话的核心内容：\n\n"
            + "\n".join(dialogs)
        )

        try:
            result = self.llm.chat([{"role": "user", "content": prompt}])
            if result and len(result) > 100:
                result = result[:97] + "..."
            return result
        except Exception:
            return None

    def generate_summary(self, conversation: list[dict]) -> str:
        """生成会话摘要。优先使用 LLM，失败时降级为启发式方法。"""
        llm_result = self._llm_summary(conversation)
        if llm_result:
            return llm_result
        return self._heuristic_summary(conversation)

    def list_sessions(self) -> list[dict]:
        """列出所有会话，按更新时间倒序。每个会话包含摘要信息。"""
        sessions = []
        for fname in os.listdir(self.session_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.session_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                conversation = data.get("conversation", [])
                sessions.append({
                    "session_id": data.get("session_id", fname[:-5]),
                    "name": data.get("name", "未命名"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len([
                        m for m in conversation
                        if m["role"] in ("user", "assistant")
                    ]),
                    "summary": data.get("summary", self._heuristic_summary(conversation)),
                })
            except (json.JSONDecodeError, OSError):
                continue
        sessions.sort(key=lambda s: s["updated_at"], reverse=True)
        return sessions

    def create_session(self, name: str = "默认会话") -> str:
        """创建新会话，返回 session_id。"""
        session_id = self._generate_id()
        data = {
            "session_id": session_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "conversation": [],
            "memory_entries": [],
            "summary": "",
        }
        with open(self._session_path(session_id), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return session_id

    def save_session(
        self,
        session_id: str,
        conversation: list[dict],
        memory_entries: list,
        name: str | None = None,
    ) -> None:
        """保存会话数据，自动更新摘要。"""
        path = self._session_path(session_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {
                "session_id": session_id,
                "name": name or "默认会话",
                "created_at": datetime.now().isoformat(),
            }

        data["updated_at"] = datetime.now().isoformat()
        data["conversation"] = conversation
        data["memory_entries"] = memory_entries
        data["summary"] = self.generate_summary(conversation)
        if name:
            data["name"] = name

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_session(self, session_id: str) -> dict | None:
        """加载会话数据，返回完整 data dict；不存在则返回 None。"""
        path = self._session_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "summary" not in data:
            data["summary"] = self._heuristic_summary(data.get("conversation", []))
        return data

    def delete_session(self, session_id: str) -> bool:
        """删除会话文件。返回是否成功。"""
        path = self._session_path(session_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def get_latest_session(self) -> str | None:
        """获取最近更新的会话 ID，无会话时返回 None。"""
        sessions = self.list_sessions()
        if sessions:
            return sessions[0]["session_id"]
        return None

    def format_session_list(self) -> str:
        """格式化会话列表为可读文本（供 CLI 使用）。"""
        sessions = self.list_sessions()
        if not sessions:
            return "📭 暂无历史会话"

        lines = ["📋 历史会话列表:", "=" * 50]
        for i, s in enumerate(sessions):
            created = s["created_at"][:19] if s["created_at"] else "未知"
            updated = s["updated_at"][:19] if s["updated_at"] else "未知"
            lines.append(f"\n  [{i+1}] {s['name']}")
            lines.append(f"      ID: {s['session_id']}")
            lines.append(f"      消息: {s['message_count']} 条")
            lines.append(f"      创建: {created}")
            lines.append(f"      更新: {updated}")
            if s.get("summary"):
                lines.append(f"      摘要: {s['summary']}")
        lines.append("\n" + "=" * 50)
        lines.append("使用 /session <编号或ID> 切换会话")
        return "\n".join(lines)

    def find_session(self, query: str) -> str | None:
        """根据编号或 ID 查找会话。返回 session_id 或 None。"""
        sessions = self.list_sessions()
        if not sessions:
            return None

        # 尝试精确匹配 ID
        for s in sessions:
            if s["session_id"] == query:
                return s["session_id"]

        # 尝试按编号匹配
        try:
            idx = int(query) - 1
            if 0 <= idx < len(sessions):
                return sessions[idx]["session_id"]
        except ValueError:
            pass

        # 尝试模糊匹配 ID（前缀）
        for s in sessions:
            if s["session_id"].startswith(query):
                return s["session_id"]

        return None
