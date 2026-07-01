"""edit_file 工具 — 第5章实现。"""


def edit_file(file_path: str, old_content: str, new_content: str) -> str:
    """精确替换文件中的一段内容。要求 old_content 在文件中唯一匹配。

    Args:
        file_path: 文件路径
        old_content: 要被替换的原文（必须唯一）
        new_content: 替换后的新内容
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return f"❌ 文件不存在: {file_path}"
    except Exception as e:
        return f"❌ 读取失败: {e}"

    count = content.count(old_content)
    if count == 0:
        return f"❌ 未找到匹配内容"
    if count > 1:
        return f"❌ 匹配到 {count} 处，请提供更精确的上下文"

    new_content_full = content.replace(old_content, new_content, 1)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content_full)
        return f"✅ 编辑成功: {file_path}"
    except Exception as e:
        return f"❌ 写入失败: {e}"
