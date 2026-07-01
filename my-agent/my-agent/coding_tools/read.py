"""read_file 工具 — 第5章实现。"""

import os


def read_file(file_path: str, offset: int = 1, limit: int | None = None) -> str:
    """读取文件内容，返回带行号的字符串。

    Args:
        file_path: 文件路径
        offset: 起始行号（1-based）
        limit: 最多读几行
    """
    if not os.path.exists(file_path):
        return f"❌ 文件不存在: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return f"❌ 读取失败: {e}"

    # offset 是 1-based，转为 0-based index
    start = offset - 1
    if start >= len(lines):
        return ""

    end = len(lines)
    if limit is not None:
        end = min(start + limit, len(lines))

    result_lines = []
    for i in range(start, end):
        result_lines.append(f"{i + 1}:{lines[i].rstrip()}")

    return "\n".join(result_lines)
