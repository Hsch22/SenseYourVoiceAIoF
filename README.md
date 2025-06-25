# SenseYourVoice - 语音理解与处理应用

> 🎙️ 基于 SenseVoice-Small 模型的多功能语音理解与处理应用，提供 Web 界面交互支持。

---

## 📌 项目简介

SenseYourVoice 是一个多功能语音理解与处理应用，基于 **SenseVoice-Small 模型**，支持多语言语音识别、语音内容理解和专业任务处理。本应用提供了友好的 Web 界面，支持音频上传、文本分析和多轮对话。

### ✅ 主要功能

- **多语言语音识别**：支持中文、英语、粤语等语言的语音转文字  
- **语音内容理解**：分析语音内容并提供智能回复  
- **专业任务处理**：根据语音内容执行特定任务  
- **多轮对话**：支持基于语音内容的多轮问答  
- **Web界面**：基于 [Gradio](https://www.gradio.app/) 的友好用户界面  

---

## ⚙️ 安装指南

### 🔧 环境要求

- Python 3.10+ （作者测试环境：Python 3.10.16）
- CUDA 支持（可选，用于 GPU 加速）

### 📥 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/Hsch22/SenseYourVoiceAIoF.git
cd SenseYourVoiceAIoF
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> 💡 **提示**：如果安装过程中遇到问题，可以尝试使用国内镜像源：
>
> ```bash
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

#### 3. 模型下载说明

> ⚠️ **重要提示**：本应用使用 **SenseVoice-Small** 模型，首次运行时会自动下载模型文件。

**模型下载信息**：
- 📦 **模型大小**：约 **2-3 GB**
- 🌐 **网络要求**：首次运行**必须联网**，用于自动下载模型
- ⏱️ **下载时间**：根据网络速度，通常需要 **10分钟**左右

**首次启动注意事项**：
- 🔌 确保网络连接稳定
- 💿 确保有足够的磁盘空间
- ⏳ 首次启动会显示模型下载进度，请耐心等待
- 🚫 下载期间请勿关闭应用程序

> 📌 **说明**：模型下载完成后，后续启动将直接使用本地缓存，无需重新下载。

---

## ▶️ 使用方法

### 🚀 启动应用

> ⚠️ **首次使用提醒**：如果是第一次运行，请确保网络连接正常，应用会自动下载 SenseVoice-Small 模型。

假设您的项目克隆或解压到了 `C:\\Path\\To\\Your\\SenseYourVoiceProject` 目录，先通过命令行进入该目录：

```bash
cd C:\\Path\\To\\Your\\SenseYourVoiceProject
```

然后根据需要选择以下任意一种方式运行应用：

#### 使用默认模型路径（模型在 `项目根目录/iic/SenseVoiceSmall` 下）：

```bash
python main.py
```

#### 指定自定义模型路径：

```bash
python main.py --model_dir "C:\\Path\\To\\Your\\Model\\Cache\\iic\\SenseVoiceSmall"
```

#### 自动初始化（配合模型路径参数）：

```bash
python main.py --model_dir "C:\\Path\\To\\Your\\Model\\Cache\\iic\\SenseVoiceSmall" --auto_init
```

或者，如果模型在默认位置：

```bash
python main.py --auto_init
```

> ❗ 您也可以不带任何参数直接运行 `python main.py`，然后在 Web 界面的“应用设置”中手动填入模型路径和其他配置，并点击“初始化应用”。

---

### 🛠️ 命令行参数说明

| 参数名                  | 说明 |
|-------------------------|------|
| `--model_dir`           | 模型所在目录路径。若模型不在默认路径，则**必须**提供此参数。 |
| `--device`              | 运行设备，可选 `cuda:0` 或 `cpu`。默认根据环境自动选择。 |
| `--understanding_api_key` | 理解模块 API 密钥。可省略，默认取自 `config.py` 或环境变量。 |
| `--understanding_api_url` | 理解模块 API 地址。可省略，默认取自 `config.py` 或环境变量。 |
| `--specialized_api_key`   | 专业任务模块 API 密钥。可省略，默认取自 `config.py` 或环境变量。 |
| `--specialized_api_url`   | 专业任务模块 API 地址。可省略，默认取自 `config.py` 或环境变量。 |
| `--auto_init`             | 若提供，启动时自动初始化应用。 |
| `--share`                 | 创建 Gradio 公共链接分享界面。 |
| `--port`                  | 服务端口，默认为 `7800`。 |

---

### 🖥️ Web 界面使用说明

1. 启动应用后，在浏览器中访问 `http://localhost:7800`（或您通过 `--port` 指定的端口）。
2. 在 **“应用设置”** 标签页中配置参数并点击 **“初始化应用”**。
3. 切换到 **“语音处理”** 标签页：
   - 上传音频文件并点击 **“处理音频”**
   - 在文本框中输入问题，点击 **“继续对话”** 进行互动
4. 系统会记住音频内容，支持多轮问答！

---