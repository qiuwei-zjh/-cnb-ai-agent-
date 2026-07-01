"""
第4章产出：ContextManager
==========================

补全这个类，让 tests/test_context.py 全部通过。
"""

from __future__ import annotations

from llm import LLMClient


class ContextManager:
    def __init__(self, llm: LLMClient, max_tokens: int = 4000, keep_last: int = 4):
        self.llm = llm
        self.max_tokens = max_tokens
        self.keep_last = keep_last

    def should_compress(self, messages: list[dict]) -> bool:
        """判断 messages 总 token 是否超过 max_tokens。"""
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.llm.count_tokens(content)
        return total > self.max_tokens

    def compress(self, messages: list[dict]) -> list[dict]:
        """压缩 messages：保留 system + 最近 keep_last 条，中间部分摘要。"""
        # 消息数不够多则无需压缩
        if len(messages) <= self.keep_last + 1:
            return messages

        system = messages[0]
        recent = messages[-self.keep_last:] if self.keep_last > 0 else []
        middle = messages[1:len(messages) - self.keep_last] if self.keep_last > 0 else messages[1:]

        if not middle:
            return messages

        # 让 LLM 对中间部分生成摘要
        summary_text = "\n".join(
            f"[{m['role']}]: {m.get('content', '')}" for m in middle
        )
        summary_prompt = f"请用一句话总结以下对话的要点：\n{summary_text}"
        summary = self.llm.chat([{"role": "user", "content": summary_prompt}])

        summary_msg = {"role": "system", "content": f"[对话摘要] {summary}"}
        return [system, summary_msg] + recent
