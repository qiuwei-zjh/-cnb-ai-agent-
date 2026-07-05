# 基于第一代个人agent的2.0版本

## 基本功能
### 实现了流式输出；
### 新增了webUI访问的方式；
### 支持docker沙箱隔离模式；

# 具体使用

## 1.环境部署

### 进入项目目录
```bash
cd my-agent
```
### 创建python虚拟环境（建议）
```bash
python -m venv .venv
```
### 激活
```bash
.venv\Scripts\activate
```
### 激活后终端前面会显示（.venv），此时安装依赖
```bash
pip install -r requirements.txt -q

如果安装太慢,尝试访问国内镜像

pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 2.运行
### 方式一:便捷脚本(推荐)
```bash
python run_web.py
```
### 方式二:直接运行(自定义参数)
```bash 
python web_ui.py --host 0.0.0.0 --port 7860
```
启动浏览器访问**http://localhost:7860**即可