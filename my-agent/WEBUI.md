# Web UI 使用指南

## 概述

Web UI 提供了图形化界面，替代命令行操作，支持文件树浏览和对话交互。

## 快速启动

### 方法 1: 使用启动脚本（推荐）

```bash
python run_web.py
```

### 方法 2: 直接运行

```bash
python web_ui.py --host 0.0.0.0 --port 7860
```

### 方法 3: 使用 Gradio 命令

```bash
gradio web_ui.py
```

## 界面说明

### 布局

```
┌─────────────────┬─────────────────────────────┐
│   文件树 (左)    │        对话界面 (右)         │
│                 │                             │
│  📁 project/    │  💬 对话历史                │
│  ├── 🐍 main.py │                             │
│  ├── 📄 README  │  用户: 帮我查看文件         │
│  └── 📁 src/    │  Agent: 我来帮你...         │
│                 │                             │
│  [刷新文件树]    │  [输入消息] [发送]          │
│  [文件路径输入]  │                             │
│  [查看文件]      │  [清空对话] [示例任务]      │
│  [文件内容预览]  │                             │
└─────────────────┴─────────────────────────────┘
```

### 功能区域

#### 1. 文件树（左侧）
- **刷新文件树**: 重新扫描项目目录
- **文件路径输入**: 输入文件路径查看内容
- **查看文件**: 显示文件内容预览
- **文件内容预览**: 显示选中文件的内容

#### 2. 对话界面（右侧）
- **对话历史**: 显示与 Agent 的交互记录
- **输入消息**: 输入你想要完成的任务
- **发送按钮**: 发送消息给 Agent
- **清空对话**: 清空对话历史
- **示例任务**: 显示一些示例任务

## 使用示例

### 示例 1: 查看项目结构

1. 点击「刷新文件树」按钮
2. 在文件树中查看项目结构
3. 在对话框输入: "帮我查看当前目录有哪些文件"

### 示例 2: 查看文件内容

1. 在「文件路径」输入框输入: `README.md`
2. 点击「查看文件」按钮
3. 在下方预览区查看文件内容

### 示例 3: 代码编辑

1. 在对话框输入: "帮我创建一个简单的 Python 脚本，计算斐波那契数列"
2. 点击「发送」按钮
3. Agent 会自动创建文件并显示结果

## 命令行参数

```bash
python web_ui.py [OPTIONS]

选项:
  --host HOST       绑定地址 (默认: 0.0.0.0)
  --port PORT       端口号 (默认: 7860)
  --share           创建公共链接（可从外网访问）
  --workspace DIR   工作目录 (默认: 当前目录)
```

### 示例

```bash
# 使用默认配置
python web_ui.py

# 指定端口
python web_ui.py --port 8080

# 创建公共链接
python web_ui.py --share

# 指定工作目录
python web_ui.py --workspace /path/to/project
```

## 技术架构

### 组件

- **Gradio**: Web 框架，提供 UI 组件
- **Agent**: AI 代理，处理对话和任务
- **LLM**: 大语言模型客户端
- **Tools**: 工具集，执行文件操作和命令

### 数据流

```
用户输入 → Gradio UI → Agent → LLM → 工具调用 → 结果返回 → UI 显示
```

## 常见问题

### Q: 启动失败怎么办？

A: 检查以下几点：
1. 确保已安装 Gradio: `pip install gradio>=4.0.0`
2. 检查端口是否被占用
3. 检查 `.env` 文件中的 API 配置

### Q: 如何从外网访问？

A: 使用 `--share` 参数创建公共链接：
```bash
python web_ui.py --share
```

### Q: 文件树不显示隐藏文件？

A: 这是默认行为，隐藏文件（以 `.` 开头）默认不显示。如需显示，可以修改 `web_ui.py` 中的 `get_file_tree` 方法。

### Q: 对话响应很慢？

A: 可能原因：
1. LLM API 响应慢
2. 网络连接问题
3. 模型加载时间

## 开发说明

### 添加新功能

1. 在 `WebUI` 类中添加新方法
2. 在 `create_ui` 方法中添加 UI 组件
3. 绑定事件处理函数

### 自定义主题

修改 `create_ui` 方法中的 `theme` 参数：

```python
# 使用内置主题
app = gr.Blocks(theme=gr.themes.Soft())

# 自定义主题
custom_theme = gr.themes.Default(
    primary_hue="blue",
    secondary_hue="gray",
)
app = gr.Blocks(theme=custom_theme)
```

## 部署

### 本地部署

```bash
python web_ui.py --host 0.0.0.0 --port 7860
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 7860
CMD ["python", "web_ui.py", "--host", "0.0.0.0", "--port", "7860"]
```

### 云平台部署

- **Hugging Face Spaces**: 直接上传代码，自动部署
- **Streamlit Cloud**: 类似部署方式
- **Railway/Render**: 使用 Docker 部署