"""第1章 测试：LLMClient"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from llm import LLMClient


def test_init():
    llm = LLMClient()
    assert llm.client is not None, "client 应该初始化"
    assert llm.model is not None, "model 不应该为空"


def test_chat():
    llm = LLMClient()
    reply = llm.chat([{"role": "user", "content": "回复一个字：好"}])
    assert isinstance(reply, str), "chat 应该返回字符串"
    assert len(reply) > 0, "回复不应该为空"


def test_chat_stream():
    llm = LLMClient()
    chunks = list(llm.chat_stream([{"role": "user", "content": "回复一个字：好"}]))
    assert len(chunks) > 0, "流式应该至少有一个 chunk"
    full = "".join(chunks)
    assert len(full) > 0, "拼接后不应该为空"


def test_count_tokens():
    llm = LLMClient()
    n = llm.count_tokens("Hello, world!")
    assert isinstance(n, int), "应该返回整数"
    assert 1 <= n <= 10, f"'Hello, world!' 应该是 4 token 左右，实际: {n}"

    assert llm.count_tokens("") == 0, "空字符串应该是 0"


def test_count_tokens_boundary():
    """边界测试：极短/极长/特殊字符"""
    llm = LLMClient()

    # 单字符
    assert llm.count_tokens("a") == 1, "单字符 'a' 应该是 1 token"
    assert llm.count_tokens("中") >= 1, "中文字符至少 1 token"

    # 仅空格
    assert llm.count_tokens("   ") >= 1, "空格字符串至少 1 token"
    assert llm.count_tokens(" ") == 1, "单个空格应该是 1 token"

    # 换行符
    assert llm.count_tokens("\n") == 1, "换行符应该是 1 token"

    # 数字
    assert llm.count_tokens("1234567890") >= 1, "数字字符串至少 1 token"

    # 特殊字符
    assert llm.count_tokens("!@#$%^&*()") >= 1, "特殊字符至少 1 token"


def test_count_tokens_consistency():
    """一致性测试：相同输入应返回相同结果"""
    llm = LLMClient()
    text = "The quick brown fox jumps over the lazy dog."
    n1 = llm.count_tokens(text)
    n2 = llm.count_tokens(text)
    assert n1 == n2, "相同输入应该返回相同 token 数"


def test_count_tokens_additivity():
    """可加性测试：拼接文本的 token 数 ≈ 各段 token 数之和（或相近）"""
    llm = LLMClient()
    a = "Hello"
    b = " world"
    n_combined = llm.count_tokens(a + b)
    n_separate = llm.count_tokens(a) + llm.count_tokens(b)
    # 拼接后 token 数 ≤ 分段之和（可能因为合并边界而更少）
    assert n_combined <= n_separate + 1, (
        f"拼接 token ({n_combined}) 不应远大于分段之和 ({n_separate})"
    )


def test_count_tokens_long_text():
    """长文本测试"""
    llm = LLMClient()
    # 1000 个单词的文本
    long_text = "hello " * 1000
    n = llm.count_tokens(long_text)
    assert isinstance(n, int), "长文本也应返回整数"
    assert n > 500, f"1000 个 'hello' 应该 > 500 token，实际: {n}"


if __name__ == "__main__":
    test_init()
    print("  ✓ test_init")
    test_chat()
    print("  ✓ test_chat")
    test_chat_stream()
    print("  ✓ test_chat_stream")
    test_count_tokens()
    print("  ✓ test_count_tokens")
    test_count_tokens_boundary()
    print("  ✓ test_count_tokens_boundary")
    test_count_tokens_consistency()
    print("  ✓ test_count_tokens_consistency")
    test_count_tokens_additivity()
    print("  ✓ test_count_tokens_additivity")
    test_count_tokens_long_text()
    print("  ✓ test_count_tokens_long_text")
    print("\n✅ 第1章 LLMClient 全部测试通过")
