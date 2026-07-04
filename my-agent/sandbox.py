"""
沙箱隔离模块
============

提供多种沙箱隔离方式，确保bash命令在安全环境中执行。

支持的隔离方式：
1. Docker容器隔离（推荐）
2. subprocess隔离（轻量级）
3. 文件系统隔离（限制访问范围）
"""

import os
import subprocess
import tempfile
import shutil
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class SandboxType(Enum):
    """沙箱类型"""
    DOCKER = "docker"
    SUBPROCESS = "subprocess"
    FILESYSTEM = "filesystem"


@dataclass
class SandboxConfig:
    """沙箱配置"""
    sandbox_type: SandboxType = SandboxType.SUBPROCESS
    timeout: int = 30
    max_output: int = 50000
    network_enabled: bool = False
    working_dir: Optional[str] = None
    allowed_paths: Optional[list] = None
    env_vars: Optional[Dict[str, str]] = None
    memory_limit: str = "256m"
    cpu_limit: float = 1.0


class DockerSandbox:
    """Docker沙箱实现"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.image_name = "sandbox-base:latest"
        self._ensure_image()
    
    def _ensure_image(self):
        """确保基础镜像存在"""
        # 检查镜像是否存在
        result = subprocess.run(
            ["docker", "images", "-q", self.image_name],
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            # 创建基础镜像
            self._create_base_image()
    
    def _create_base_image(self):
        """创建基础Docker镜像"""
        dockerfile_content = """
FROM python:3.11-slim

# 安装基本工具
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    vim \\
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 sandbox
USER sandbox
WORKDIR /home/sandbox

# 设置环境变量
ENV PYTHONUNBUFFERED=1
"""
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = os.path.join(tmpdir, "Dockerfile")
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)
            
            # 构建镜像
            subprocess.run(
                ["docker", "build", "-t", self.image_name, tmpdir],
                check=True,
                capture_output=True
            )
    
    def execute(self, command: str, workdir: str = ".", timeout: int = None) -> Dict[str, Any]:
        """在Docker容器中执行命令"""
        timeout = timeout or self.config.timeout
        
        # 构建Docker命令
        docker_cmd = [
            "docker", "run",
            "--rm",  # 执行后删除容器
            "--network", "none" if not self.config.network_enabled else "bridge",
            "--memory", self.config.memory_limit,
            "--cpus", str(self.config.cpu_limit),
            "--read-only",  # 只读文件系统
            "--tmpfs", "/tmp:size=100m",  # 临时文件系统
        ]
        
        # 挂载工作目录
        abs_workdir = os.path.abspath(workdir)
        if os.path.exists(abs_workdir):
            docker_cmd.extend(["-v", f"{abs_workdir}:/workspace:rw"])
            docker_cmd.extend(["-w", "/workspace"])
        
        # 添加环境变量
        if self.config.env_vars:
            for key, value in self.config.env_vars.items():
                docker_cmd.extend(["-e", f"{key}={value}"])
        
        # 设置镜像和命令
        docker_cmd.extend([
            self.image_name,
            "bash", "-c", command
        ])
        
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += result.stderr
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": f"命令超时 ({timeout}s)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"执行失败: {str(e)}",
                "returncode": -1
            }


class SubprocessSandbox:
    """subprocess沙箱实现（轻量级隔离）"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.temp_dir = None
    
    def _setup_isolated_env(self, workdir: str) -> str:
        """设置隔离的执行环境"""
        # 创建临时目录作为隔离环境
        self.temp_dir = tempfile.mkdtemp(prefix="sandbox_")
        
        # 复制工作目录到隔离环境
        if os.path.exists(workdir):
            isolated_workdir = os.path.join(self.temp_dir, "workspace")
            shutil.copytree(workdir, isolated_workdir, dirs_exist_ok=True)
        else:
            isolated_workdir = self.temp_dir
        
        return isolated_workdir
    
    def _cleanup(self):
        """清理临时目录"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def execute(self, command: str, workdir: str = ".", timeout: int = None) -> Dict[str, Any]:
        """在隔离的subprocess中执行命令"""
        timeout = timeout or self.config.timeout
        
        try:
            # 设置隔离环境
            isolated_workdir = self._setup_isolated_env(workdir)
            
            # 设置环境变量
            env = os.environ.copy()
            env.update({
                "PYTHONPATH": isolated_workdir,
                "HOME": self.temp_dir,
                "TMPDIR": self.temp_dir,
            })
            
            if self.config.env_vars:
                env.update(self.config.env_vars)
            
            # 在Windows上使用不同的shell
            import platform
            shell = True
            if platform.system() == "Windows":
                # Windows上使用cmd.exe
                shell = True
            
            # 执行命令
            result = subprocess.run(
                command,
                shell=shell,
                cwd=isolated_workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            output = result.stdout
            if result.stderr:
                output += result.stderr
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": f"命令超时 ({timeout}s)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"执行失败: {str(e)}",
                "returncode": -1
            }
        finally:
            self._cleanup()


class FilesystemSandbox:
    """文件系统沙箱实现（限制访问范围）"""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
        self.allowed_paths = config.allowed_paths or []
    
    def _check_path_access(self, path: str) -> bool:
        """检查路径访问权限"""
        abs_path = os.path.abspath(path)
        
        # 如果没有设置允许的路径，默认允许当前目录
        if not self.allowed_paths:
            return True
        
        # 检查是否在允许的路径列表中
        for allowed in self.allowed_paths:
            allowed_abs = os.path.abspath(allowed)
            # 在Windows上使用normcase处理大小写
            import platform
            if platform.system() == "Windows":
                abs_path = os.path.normcase(abs_path)
                allowed_abs = os.path.normcase(allowed_abs)
            
            if abs_path.startswith(allowed_abs):
                return True
        
        return False
    
    def execute(self, command: str, workdir: str = ".", timeout: int = None) -> Dict[str, Any]:
        """在文件系统沙箱中执行命令"""
        timeout = timeout or self.config.timeout
        
        # 检查工作目录访问权限
        if not self._check_path_access(workdir):
            return {
                "success": False,
                "output": f"访问被拒绝: 工作目录 {workdir} 不在允许范围内",
                "returncode": -1
            }
        
        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += result.stderr
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": f"命令超时 ({timeout}s)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"执行失败: {str(e)}",
                "returncode": -1
            }


class SandboxManager:
    """沙箱管理器 - 统一接口"""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.sandbox = self._create_sandbox()
    
    def _create_sandbox(self):
        """根据配置创建对应的沙箱实现"""
        if self.config.sandbox_type == SandboxType.DOCKER:
            # 检查Docker是否可用
            try:
                subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    check=True
                )
                return DockerSandbox(self.config)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Docker不可用，降级到subprocess沙箱")
                return SubprocessSandbox(self.config)
        
        elif self.config.sandbox_type == SandboxType.SUBPROCESS:
            return SubprocessSandbox(self.config)
        
        elif self.config.sandbox_type == SandboxType.FILESYSTEM:
            return FilesystemSandbox(self.config)
        
        else:
            raise ValueError(f"不支持的沙箱类型: {self.config.sandbox_type}")
    
    def execute(self, command: str, workdir: str = ".", timeout: int = None) -> Dict[str, Any]:
        """执行命令"""
        return self.sandbox.execute(command, workdir, timeout)


# 默认沙箱实例
_default_sandbox = None


def get_sandbox(config: Optional[SandboxConfig] = None) -> SandboxManager:
    """获取沙箱实例"""
    global _default_sandbox
    if _default_sandbox is None or config is not None:
        _default_sandbox = SandboxManager(config)
    return _default_sandbox


def execute_in_sandbox(command: str, workdir: str = ".", timeout: int = 30, 
                      sandbox_type: SandboxType = SandboxType.SUBPROCESS) -> str:
    """在沙箱中执行命令的便捷函数"""
    config = SandboxConfig(
        sandbox_type=sandbox_type,
        timeout=timeout
    )
    sandbox = get_sandbox(config)
    result = sandbox.execute(command, workdir, timeout)
    
    if result["success"]:
        return result["output"]
    else:
        return f"❌ 执行失败: {result['output']}"