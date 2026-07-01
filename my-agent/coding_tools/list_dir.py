"""list_dir 工具 — 第5章实现。"""

import os


def list_dir(path: str = ".") -> str:
    """列出目录内容，返回格式化的文件列表。

    Args:
        path: 目录路径
    """
    if not os.path.isdir(path):
        return f"❌ 不是目录: {path}"

    try:
        entries = sorted(os.listdir(path))
    except Exception as e:
        return f"❌ 读取失败: {e}"

    lines = []
    for entry in entries:
        full = os.path.join(path, entry)
        tag = "[目录]" if os.path.isdir(full) else "[文件]"
        lines.append(f"  {tag} {entry}")

    return "\n".join(lines) if lines else "(空目录)"
