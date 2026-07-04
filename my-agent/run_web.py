#!/usr/bin/env python3
"""
启动 Web UI 的便捷脚本
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import gradio
        print(f"✅ Gradio {gradio.__version__} 已安装")
        return True
    except ImportError:
        print("❌ Gradio 未安装")
        print("正在安装依赖...")
        subprocess.run([sys.executable, "-m", "pip", "install", "gradio>=4.0.0"])
        return True

def main():
    """主函数"""
    print("=" * 50)
    print("🤖 My Coding Agent - Web UI")
    print("=" * 50)
    
    # 检查依赖
    check_dependencies()
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 启动 Web UI
    print("\n🚀 启动 Web UI...")
    print("📍 地址: http://localhost:7860")
    print("🛑 按 Ctrl+C 停止服务\n")
    
    # 导入并运行
    sys.path.insert(0, current_dir)
    from web_ui import main as web_main
    
    # 设置参数
    sys.argv = [
        "run_web.py",
        "--host", "0.0.0.0",
        "--port", "7860",
        "--workspace", current_dir
    ]
    
    web_main()

if __name__ == "__main__":
    main()