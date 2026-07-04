"""
Web UI 测试脚本
"""

import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

def test_import():
    """测试导入"""
    try:
        from web_ui import WebUI
        print("✅ WebUI 导入成功")
        return True
    except Exception as e:
        print(f"❌ WebUI 导入失败: {e}")
        return False

def test_file_tree():
    """测试文件树功能"""
    try:
        from web_ui import WebUI
        ui = WebUI(workspace_dir=".")
        tree = ui.get_file_tree()
        print("✅ 文件树生成成功")
        print("预览:")
        print(tree[:500])
        return True
    except Exception as e:
        print(f"❌ 文件树测试失败: {e}")
        return False

def test_file_read():
    """测试文件读取"""
    try:
        from web_ui import WebUI
        ui = WebUI(workspace_dir=".")
        content = ui.read_file_content("README.md")
        print("✅ 文件读取成功")
        print(f"内容长度: {len(content)} 字符")
        return True
    except Exception as e:
        print(f"❌ 文件读取测试失败: {e}")
        return False

def test_ui_creation():
    """测试 UI 创建"""
    try:
        from web_ui import WebUI
        ui = WebUI(workspace_dir=".")
        app = ui.create_ui()
        print("✅ UI 创建成功")
        return True
    except Exception as e:
        print(f"❌ UI 创建测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("Web UI 测试")
    print("=" * 50)
    
    tests = [
        ("导入测试", test_import),
        ("文件树测试", test_file_tree),
        ("文件读取测试", test_file_read),
        ("UI 创建测试", test_ui_creation),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        result = test_func()
        results.append((name, result))
    
    print("\n" + "=" * 50)
    print("测试结果:")
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(result for _, result in results)
    print(f"\n总体结果: {'✅ 全部通过' if all_passed else '❌ 有失败'}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)