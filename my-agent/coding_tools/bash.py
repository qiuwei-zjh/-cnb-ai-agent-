"""bash 工具 — 支持沙箱隔离执行。"""

import re
import platform
from sandbox import SandboxConfig, SandboxType, get_sandbox

# Linux/macOS 危险命令模式
DANGER_PATTERNS_UNIX = [
    r"rm\s+(-\w+\s+)*(/|~)",
    r"sudo\s+",
    r"curl\s+.*\|\s*(ba)?sh",
    r"wget\s+.*\|\s*(ba)?sh",
    r"chmod\s+(-R\s+)?777\s+/",
    r"mkfs\.",
    r"dd\s+if=.*of=/dev/",
]

# Windows 危险命令模式
DANGER_PATTERNS_WINDOWS = [
    r"rmdir\s+(/s|/q)\s+[a-zA-Z]:\\",
    r"del\s+(/f|/s|/q)\s+[a-zA-Z]:\\",
    r"format\s+[a-zA-Z]:",
    r"rd\s+/s\s+[a-zA-Z]:\\",
    r"takeown\s+/f\s+[a-zA-Z]:\\",
    r"icacls\s+[a-zA-Z]:\\\s+/grant\s+everyone:F",
    r"rmdir\s+(/s|/q)\s+\\\\",
    r"del\s+(/f|/s|/q)\s+\\\\",
    r"rd\s+/s\s+\\\\",
    r"format\s+[a-zA-Z]:\\",
    r"format\s+[a-zA-Z]:",
]


def bash(command: str, workdir: str = ".", timeout: int = 30, max_output: int = 50000,
         sandbox_type: str = "subprocess") -> str:
    """在工作目录下执行 shell 命令，带安全闸门和沙箱隔离。

    Args:
        command: 要执行的命令
        workdir: 工作目录
        timeout: 超时秒数
        max_output: 最大输出字符数
        sandbox_type: 沙箱类型 (subprocess/docker/filesystem)
    """
    # 根据操作系统选择危险命令模式
    is_windows = platform.system() == "Windows"
    danger_patterns = DANGER_PATTERNS_WINDOWS if is_windows else DANGER_PATTERNS_UNIX
    
    # 危险命令拦截
    for pattern in danger_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return f"❌ 拒绝执行危险命令: {command}"

    # 配置沙箱
    sandbox_type_enum = SandboxType(sandbox_type)
    config = SandboxConfig(
        sandbox_type=sandbox_type_enum,
        timeout=timeout,
        network_enabled=False,  # 默认禁用网络
    )
    
    # 创建沙箱并执行
    sandbox = get_sandbox(config)
    result = sandbox.execute(command, workdir, timeout)
    
    output = result["output"]
    
    if len(output) > max_output:
        output = output[:max_output] + f"\n... (截断，共 {len(output)} 字符)"

    return output if output else "(无输出)"
