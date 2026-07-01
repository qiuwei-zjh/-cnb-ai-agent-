"""bash 工具 — 第5章实现。"""

import subprocess
import re

DANGER_PATTERNS = [
    r"rm\s+(-\w+\s+)*(/|~)",
    r"sudo\s+",
    r"curl\s+.*\|\s*(ba)?sh",
]


def bash(command: str, workdir: str = ".", timeout: int = 30, max_output: int = 50000) -> str:
    """在工作目录下执行 shell 命令，带安全闸门。

    Args:
        command: 要执行的命令
        workdir: 工作目录
        timeout: 超时秒数
        max_output: 最大输出字符数
    """
    # 危险命令拦截
    for pattern in DANGER_PATTERNS:
        if re.search(pattern, command):
            return f"❌ 拒绝执行危险命令: {command}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"❌ 命令超时 ({timeout}s): {command}"
    except Exception as e:
        return f"❌ 执行失败: {e}"

    output = result.stdout
    if result.stderr:
        output += result.stderr

    if len(output) > max_output:
        output = output[:max_output] + f"\n... (截断，共 {len(output)} 字符)"

    return output if output else "(无输出)"
