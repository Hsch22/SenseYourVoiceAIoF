# SenseYourVoice - 语音理解与处理应用

## 项目简介

SenseYourVoice是一个多功能语音理解与处理应用，基于SenseVoice-Small模型，支持多语言语音识别、语音内容理解和专业任务处理。本应用提供了友好的Web界面，支持音频上传、文本分析和多轮对话。

### 主要功能

- **多语言语音识别**：支持中文、英语和粤语的语音转文字
- **语音内容理解**：分析语音内容并提供智能回复
- **专业任务处理**：根据语音内容执行特定任务
- **多轮对话**：支持基于语音内容的多轮问答
- **Web界面**：基于Gradio的友好用户界面

## 安装指南

### 环境要求

- Python 3.8+
- CUDA支持（可选，用于GPU加速）

### 安装步骤

1. **克隆仓库**

```bash
git clone [仓库地址]
cd SenseYourVoice
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

> **注意**：如果安装过程中遇到问题，可以尝试使用国内镜像源：
> ```bash
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

3. **下载模型**

本项目使用SenseVoice-Small模型，请从以下位置下载模型文件：

- 模型下载地址：[SenseVoice-Small模型](https://modelscope.cn/models/iic/SenseVoiceSmall/summary)

下载后，将模型文件放置在项目根目录下的`iic/SenseVoiceSmall`文件夹中。如果使用其他位置，请在启动时指定模型路径。

## 使用方法

### 启动应用

```bash
python main.py
```

### 命令行参数

- `--model_dir`：模型目录路径，默认为`iic/SenseVoiceSmall`
- `--device`：运行设备，可选`cuda:0`或`cpu`，默认根据环境自动选择
- `--understanding_api_key`：理解模块API密钥
- `--understanding_api_url`：理解模块API地址
- `--specialized_api_key`：专业任务模块API密钥
- `--specialized_api_url`：专业任务模块API地址
- `--auto_init`：自动初始化应用
- `--share`：创建公共链接分享界面
- `--port`：服务端口，默认7800

示例：

```bash
python main.py --model_dir "./models/SenseVoiceSmall" --device "cpu" --port 8000
```

### Web界面使用

1. 启动应用后，在浏览器中访问`http://localhost:7800`（或您指定的端口）
2. 在"应用设置"标签页中配置参数并初始化应用
3. 在"语音处理"标签页中：
   - 上传音频文件并点击"处理音频"
   - 在文本框中输入问题，点击"继续对话"进行互动
4. 系统会记住音频内容，支持多轮问答