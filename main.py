# -*- encoding: utf-8 -*-

import os
import sys
import argparse
import torch
import gradio as gr
import gradio.themes as grt
import time
import logging  # 需要导入 logging 以便校验函数使用
import json
import datetime
from pathlib import Path

# 导入配置和主应用
from config import load_config
from app_new import SenseYourVoiceApp

# 全局应用实例
sense_app = None

# 保存目录配置
SAVE_DIR = Path("saved_transcriptions")
SAVE_DIR.mkdir(exist_ok=True)

def save_transcription(audio_text, chat_history, title=""):
    """保存语音转文字内容和完整的对话历史"""
    try:
        if not audio_text.strip():
            return "没有可保存的内容，请先处理音频文件。"
        
        # 生成文件名（使用时间戳）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcription_{timestamp}.json"
        filepath = SAVE_DIR / filename
        
        # 准备保存的数据
        save_data = {
            "title": title if title else f"语音转文字记录_{timestamp}",
            "timestamp": datetime.datetime.now().isoformat(),
            "audio_text": audio_text,
            "chat_history": chat_history,
            "filename": filename,
            "total_messages": len(chat_history) if chat_history else 0,
            "audio_text_length": len(audio_text),
            "metadata": {
                "created_at": datetime.datetime.now().isoformat(),
                "version": "2.0",
                "app_name": "SenseYourVoice",
                "features": ["collapsible_sidebar", "init_status_update"]
            }
        }
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        return f"内容已保存到: {filename} (包含 {len(chat_history)} 条对话记录)"
    except Exception as e:
        return f"保存失败: {str(e)}"

def load_saved_transcriptions():
    """加载所有保存的转文字记录"""
    try:
        saved_files = []
        for filepath in SAVE_DIR.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    saved_files.append({
                        "filename": data.get("filename", filepath.name),
                        "title": data.get("title", "未命名"),
                        "timestamp": data.get("timestamp", ""),
                        "audio_text_preview": data.get("audio_text", "")[:100] + "..." if len(data.get("audio_text", "")) > 100 else data.get("audio_text", ""),
                        "filepath": str(filepath)
                    })
            except Exception as e:
                logger.warning(f"读取文件 {filepath} 失败: {e}")
                continue
        
        # 按时间戳排序（最新的在前）
        saved_files.sort(key=lambda x: x["timestamp"], reverse=True)
        return saved_files
    except Exception as e:
        logger.error(f"加载保存的记录失败: {e}")
        return []

def load_transcription_content(filepath):
    """加载指定文件的完整内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        audio_text = data.get("audio_text", "")
        chat_history = data.get("chat_history", [])
        title = data.get("title", "")
        metadata = data.get("metadata", {})
        
        # 验证数据完整性
        if not audio_text and not chat_history:
            return "", [], f"文件内容为空: {title}", {}
        
        return audio_text, chat_history, title, metadata
    except Exception as e:
        return "", [], f"加载失败: {str(e)}", {}

logger = logging.getLogger('main_gradio_app')
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
#background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab, #f093fb, #f5576c, #4facfe, #00f2fe);
# 自定义CSS样式 - 动态渐变背景和微光加载效果
CUSTOM_CSS = """
/* 动态渐变背景 */
.gradio-container {
    background: linear-gradient(-45deg, #dd8866, #d75588, #3399cc, #44ccaa, #e0aaff, #e06677, #66aaff, #33dddd);
    background-size: 400% 400%;
    animation: gradient-shift 15s ease infinite;
    min-height: 100vh;
}

@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* 微光加载效果 */
.shimmer-loading {
    position: relative;
    overflow: hidden;
    background: linear-gradient(90deg, rgba(255,255,255,0.1) 25%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0.1) 75%);
    background-size: 200% 100%;
    animation: shimmer 2s infinite;
    border-radius: 8px;
    padding: 16px;
    margin: 16px 0;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

/* 微光加载指示器 */
.loading-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px 24px;
    background: rgba(255,255,255,0.15);
    border-radius: 25px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    margin: 16px auto;
    width: fit-content;
}

.loading-dots {
    display: inline-flex;
    gap: 4px;
}

.loading-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
    animation: loading-pulse 1.4s infinite ease-in-out both;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }
.loading-dot:nth-child(3) { animation-delay: 0s; }

@keyframes loading-pulse {
    0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
    40% { transform: scale(1.0); opacity: 1; }
}

/* 增强按钮效果 */
.primary-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    color: white;
    font-weight: 600;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.primary-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.primary-button:hover::before {
    left: 100%;
}

/* 卡片容器美化 */
.card-container {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.2);
    padding: 20px;
    margin: 16px 0;
}

/* 自定义 Tab 标签悬停效果*/
.tabs .tab-button,
.tab-nav .tab-item {
    transition: all 0.3s ease !important;
    background: linear-gradient(135deg, #ffffff10, #ffffff20) !important;
    border-radius: 12px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    backdrop-filter: none !important; 
    font-size: 16px !important;
}

.tabs .tab-button:hover,
.tab-nav .tab-item:hover {
    transform: scale(1.03) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2) !important;
    background: linear-gradient(135deg, #ffffff20, #ffffff30) !important;
}

/* 系统状态指示灯样式 */
.status-indicator {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background-color: gray;
    margin-right: 10px;
    vertical-align: middle;
    transition: background-color 0.3s ease;
}

.status-indicator.green {
    background-color: #4caf50;
    box-shadow: 0 0 6px rgba(76, 175, 80, 0.6);
}

.status-indicator.red {
    background-color: #f44336;
    animation: blink 1.2s infinite;
    box-shadow: 0 0 8px rgba(244, 67, 54, 0.7);
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* 麦克风录音脉冲动画 */
.mic-pulse {
    position: relative;
    display: inline-block;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #4caf50;
    margin: 10px;
}

.mic-pulse::before {
    content: '';
    position: absolute;
    top: -6px;
    left: -6px;
    border-radius: 50%;
    width: 36px;
    height: 36px;
    background: rgba(76, 175, 80, 0.5);
    opacity: 0;
    animation: pulse 1.5s infinite ease-in-out;
}

@keyframes pulse {
    0% {
        transform: scale(0.8);
        opacity: 0.8;
    }
    100% {
        transform: scale(1.4);
        opacity: 0;
    }
}

/* 自定义标题样式 */
.custom-header {
    background-color: #bac0c3;
    color: #1f2328;
    padding: 8px 10px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 18px; 
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; 
    text-transform: uppercase; 
    letter-spacing: 0.5px; 
    margin-bottom: 0px; 
}

/* 添加背景遮罩 */
.gradio-container::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(255, 255, 255, 0.20); /* 柔和遮罩 */
    z-index: 1;
    pointer-events: none;
}

/* 聊天机器人美化 */
.chatbot-container {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.1);
}

/* 页边栏样式 */
.sidebar-container {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.2);
    padding: 20px;
    margin: 16px 0;
    transition: all 0.3s ease;
    position: relative;
}

.sidebar-toggle {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    color: white;
    font-weight: 600;
    transition: all 0.3s ease;
    cursor: pointer;
    margin-bottom: 16px;
    width: 100%;
}

.sidebar-toggle:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.sidebar-content {
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.3s ease;
    opacity: 0;
}

.sidebar-content.expanded {
    max-height: 800px;
    opacity: 1;
}

.sidebar-collapsed {
    max-height: 60px;
    overflow: hidden;
}

.sidebar-collapsed .sidebar-content {
    max-height: 0;
    opacity: 0;
}

.sidebar-expanded {
    max-height: none;
}

.sidebar-expanded .sidebar-content {
    max-height: 800px;
    opacity: 1;
}

/* 保存记录项样式 */
.saved-item {
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 1px solid rgba(255,255,255,0.1);
}

.saved-item:hover {
    background: rgba(255,255,255,0.1);
    transform: translateX(4px);
}

.saved-item.selected {
    background: rgba(102, 126, 234, 0.2);
    border-color: rgba(102, 126, 234, 0.5);
}

/* 加载动画 */
.loading-refresh {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255,255,255,0.3);
    border-radius: 50%;
    border-top-color: #fff;
    animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* 折叠指示器 */
.collapse-indicator {
    position: absolute;
    top: 20px;
    right: 20px;
    background: rgba(255,255,255,0.2);
    border: none;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.3s ease;
    color: white;
    font-size: 16px;
}

.collapse-indicator:hover {
    background: rgba(255,255,255,0.3);
    transform: scale(1.1);
}

.collapse-indicator.collapsed::after {
    content: "▼";
}

.collapse-indicator.expanded::after {
    content: "▲";
}
"""

# 页边栏折叠JavaScript代码
SIDEBAR_JS = """
<script>
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar-container');
    const collapseBtn = document.querySelector('.collapse-indicator');
    const sidebarContents = document.querySelectorAll('.sidebar-content');
    
    if (sidebar.classList.contains('sidebar-expanded')) {
        // 折叠页边栏
        sidebar.classList.remove('sidebar-expanded');
        sidebar.classList.add('sidebar-collapsed');
        collapseBtn.classList.remove('expanded');
        collapseBtn.classList.add('collapsed');
        collapseBtn.textContent = '▼';
        
        sidebarContents.forEach(content => {
            content.classList.remove('expanded');
        });
    } else {
        // 展开页边栏
        sidebar.classList.remove('sidebar-collapsed');
        sidebar.classList.add('sidebar-expanded');
        collapseBtn.classList.remove('collapsed');
        collapseBtn.classList.add('expanded');
        collapseBtn.textContent = '▲';
        
        sidebarContents.forEach(content => {
            content.classList.add('expanded');
        });
    }
}

// 添加事件监听器
document.addEventListener('DOMContentLoaded', function() {
    const collapseBtn = document.querySelector('.collapse-indicator');
    if (collapseBtn) {
        collapseBtn.addEventListener('click', toggleSidebar);
    }
});

// 添加键盘快捷键支持 (Ctrl+B)
document.addEventListener('keydown', function(event) {
    if (event.ctrlKey && event.key === 'b') {
        event.preventDefault();
        toggleSidebar();
    }
});
</script>
"""

def validate_response_dict(
    response_dict, required_keys, context_msg="Stream"
):  # Modified context_msg default
    """
    校验函数，检查字典中是否存在所有必需的键。
    如果校验失败，记录错误并返回一个标准的错误字典。
    """
    if not isinstance(response_dict, dict):
        error_msg = f"{context_msg} - 响应不是一个字典: {type(response_dict)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "is_final": True}

    missing_keys = [key for key in required_keys if key not in response_dict]
    if missing_keys:
        error_msg = f"{context_msg} - 响应中缺少关键字段: {', '.join(missing_keys)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "is_final": True}

    if (
        "success" in response_dict
        and not response_dict["success"]
        and "error" not in response_dict
    ):
        logger.warning(
            f"{context_msg} - 响应标记为失败但未提供错误信息。原始响应: {response_dict}"
        )
    return None  # 表示校验通过


def initialize_app(
    model_dir,
    device,
    understanding_api_key,
    understanding_api_url,
    specialized_api_key,
    specialized_api_url,
):
    """初始化应用实例"""
    global sense_app

    # 从用户输入创建配置字典
    user_config = {
        "model_dir": model_dir,
        "device": device,
        "understanding_api_key": understanding_api_key,
        "understanding_api_url": understanding_api_url,
        "specialized_api_key": specialized_api_key,
        "specialized_api_url": specialized_api_url,
    }

    # 使用load_config函数加载配置，合并用户配置和默认配置
    config = load_config(user_config)

    try:
        sense_app = SenseYourVoiceApp(config)
        return (
            "应用初始化成功！",
            gr.update(visible=False),
            gr.update(value="""<span class='status-indicator green'></span> 已就绪"""),
        )
    except Exception as e:
        return (
            f"应用初始化失败: {str(e)}",
            gr.update(visible=False),
            gr.update(value="""<span class='status-indicator red'></span> 初始化失败"""),
        )

def process_audio(audio_file, chat_history, audio_text):
    """处理上传的音频文件并逐步更新对话历史"""
    global sense_app

    if sense_app is None:
        yield chat_history, None, "应用尚未初始化，请先初始化应用。", audio_text
        return

    if audio_file is None:
        yield chat_history, None, "请上传音频文件。", audio_text
        return

    try:
        # 显示麦克风脉冲动画
        yield chat_history, None, None, audio_text, gr.update(visible=True)
        # 构建对话历史上下文
        context = ""
        if chat_history:
            for user_msg, bot_msg in chat_history:
                if user_msg and bot_msg:
                    context += f"用户: {user_msg}\n助手: {bot_msg}\n"

        # 处理音频文件
        result = sense_app.process(audio_file, context=context)  # Removed instruction

        # 关闭麦克风动画
        yield chat_history, None, None, audio_text, gr.update(visible=False)

        if not result["success"]:
            yield chat_history, None, result["error"], audio_text, gr.update(visible=False)
            return

        # 获取音频转录内容
        transcription = result["transcription"]
        audio_text = transcription  # 存储音频文本内容

        # 系统反馈消息
        system_message = "太好了！我已经成功理解了您的音频内容～ 🎉 有什么想要了解或分析的吗？我很乐意为您解答！"
        new_chat_history = list(chat_history) if chat_history else []
        new_chat_history.append(("", system_message))

        for i in range(len(system_message) + 1):
            time.sleep(0.05)
            new_chat_history[-1] = ("", system_message[:i])
            yield new_chat_history, None, None, audio_text, gr.update(visible=False)

        # 确保完整输出
        
        yield new_chat_history, None, None, audio_text, gr.update(visible=False)
    except Exception as e:
        yield chat_history, None, f"处理过程发生错误: {str(e)}", audio_text, gr.update(visible=False)


def process_text(
    text_input, chat_history, audio_text, max_tokens, temperature, top_p, top_k, audio_weight
):
    """处理用户输入的文本并逐步更新对话历史"""
    global sense_app

    if sense_app is None:
        yield chat_history, None, "应用尚未初始化，请先初始化应用。", audio_text
        return

    if not text_input or text_input.strip() == "":
        yield chat_history, None, "请输入文本内容。", audio_text
        return

    try:
        # 构建完整的对话上下文，包括音频内容
        context = ""
        
        # 增强语音内容的权重和可见性
        if audio_text and audio_text.strip():
            # 根据权重调整强调程度
            emphasis_level = "=" * (audio_weight + 2)  # 权重越高，等号越多
            repeat_count = audio_weight  # 权重越高，重复次数越多
            
            # 使用特殊标记和格式来强调语音内容
            context += f"""
{emphasis_level} 核心语音内容 (用户原始输入) - 权重级别: {audio_weight}/5 {emphasis_level}
{audio_text}
{emphasis_level} 语音内容结束 {emphasis_level}

"""
            
            # 根据权重重复强调语音内容
            for i in range(repeat_count):
                context += f"重要提醒 {i+1}: 请重点关注上述语音内容！\n"
            
            # 添加语音内容摘要和关键信息
            audio_length = len(audio_text)
            context += f"语音内容长度: {audio_length} 字符\n"
            context += f"语音内容关键词: {', '.join(audio_text.split()[:10])}...\n\n"
        
        # 添加对话历史，但降低其权重
        if chat_history:
            context += "=== 对话历史 (参考信息) ===\n"
            for i, (user_msg, bot_msg) in enumerate(chat_history):
                if user_msg and bot_msg:
                    context += f"第{i+1}轮对话:\n用户: {user_msg}\n助手: {bot_msg}\n\n"
            context += "=== 对话历史结束 ===\n\n"
        
        # 根据权重调整指令强度
        instruction_strength = {
            1: "温和提示",
            2: "一般提示", 
            3: "重要提示",
            4: "强烈提示",
            5: "最高优先级提示"
        }
        
        context += f"""
{emphasis_level} {instruction_strength.get(audio_weight, "重要提示")} {emphasis_level}
1. 请始终以用户的语音内容为核心进行回答
2. 语音内容是用户最原始的输入，具有最高优先级
3. 对话历史仅供参考，不应覆盖语音内容的信息
4. 如果用户的问题与语音内容相关，请重点基于语音内容回答
5. 如果语音内容与当前问题不直接相关，请明确说明
6. 权重级别: {audio_weight}/5 - 请相应调整对语音内容的重视程度

"""

        # 分析用户输入的文本 (流式)
        llm_params = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            # "stop": stop # Stop might be handled differently
        }

        new_chat_history = list(chat_history) if chat_history else []
        new_chat_history.append((text_input, ""))
        full_response = ""
        needs_specialized_task = False
        specialized_result_output = None  # 用于存储专业任务的最终结果或流式块

        # 处理理解模块的流式输出
        understanding_stream = sense_app.understanding.analyze(
            text_input, context=context, llm_params=llm_params
        )
        # --- 定义理解模块流式输出期望的关键字段 ---
        understanding_chunk_required_keys = ["success", "is_final"]

        for chunk_data in understanding_stream:
            # --- 校验 UnderstandingModule 流式块 ---
            validation_error = validate_response_dict(
                chunk_data,
                understanding_chunk_required_keys,
                "UnderstandingModule.analyze stream (main.py)",
            )
            if validation_error:
                # 如果校验失败，也需要更新聊天记录（显示之前的完整响应或部分响应）
                # 同时显示校验错误
                yield new_chat_history, specialized_result_output, validation_error[
                    "error"
                ], audio_text
                return  # 结束生成器
            # --- 校验结束 ---

            if not chunk_data["success"]:
                # 如果原始响应就是 error, 且通过了校验 (意味着 success 和 is_final 字段存在)
                yield new_chat_history, specialized_result_output, chunk_data.get(
                    "error", "理解模块处理出错但未返回具体错误信息"
                ), audio_text
                return

            if chunk_data["is_final"]:
                needs_specialized_task = chunk_data.get("needs_specialized_task", False)
                full_response = chunk_data.get(
                    "full_response", full_response
                )  # 获取完整响应
                break  # 理解流结束

            response_chunk = chunk_data.get("response_chunk", "")
            if response_chunk:
                full_response += response_chunk
                new_chat_history[-1] = (text_input, full_response)
                yield new_chat_history, specialized_result_output, None, audio_text

        # 如果需要专业任务处理 (流式)
        if needs_specialized_task:
            task_type = sense_app._determine_task_type(
                full_response
            )  # 使用完整响应判断任务类型
            specialized_task_stream = sense_app.specialized_task.process_task(
                task_type, full_response
            )

            full_specialized_result = ""  # 用于累积专业任务的流式结果
            specialized_result_output = ""  # 初始化专业任务输出为空字符串
            # --- 定义专业任务模块流式输出期望的关键字段 ---
            specialized_chunk_required_keys = ["success", "is_final"]

            for specialized_chunk_data in specialized_task_stream:
                # --- 校验 SpecializedTaskModule 流式块 ---
                validation_error = validate_response_dict(
                    specialized_chunk_data,
                    specialized_chunk_required_keys,
                    "SpecializedTaskModule.process_task stream (main.py)",
                )
                if validation_error:
                    # 专业任务校验出错，聊天记录（显示理解结果）不变，但专业任务结果区显示错误
                    yield new_chat_history, specialized_result_output, validation_error[
                        "error"
                    ], audio_text
                    return  # 结束生成器
                # --- 校验结束 ---

                if not specialized_chunk_data["success"]:
                    # 专业任务出错，也需要更新聊天记录（显示之前的理解结果）
                    yield new_chat_history, specialized_result_output, specialized_chunk_data.get(
                        "error", "专业任务模块处理出错但未返回具体错误信息"
                    ), audio_text
                    return

                if specialized_chunk_data["is_final"]:
                    break  # 专业任务流结束

                result_chunk = specialized_chunk_data.get("result_chunk", "")
                if result_chunk:
                    full_specialized_result += result_chunk
                    specialized_result_output = full_specialized_result  # 更新输出
                    # 在专业任务流式输出时，聊天记录通常保持不变（显示理解结果）
                    # 但专业任务结果区域会更新
                    yield new_chat_history, specialized_result_output, None, audio_text

            # 专业任务流结束后，确保最终的专业结果被传递
            specialized_result_output = full_specialized_result

        # 确保最终状态被传递
        yield new_chat_history, specialized_result_output, None, audio_text

    except Exception as e:
        yield chat_history, None, f"处理过程发生错误: {str(e)}", audio_text

def update_header_style(bg_color):
    style_html = f"""
    <style>
    .custom-header {{
        background-color: {bg_color};
        color: #8b8b8b;
        padding: 8px 15px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 16px; 
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif; 
        text-transform: uppercase; 
        letter-spacing: 0.5px; 
        margin-bottom: 0px; 
    }}
    </style>
    """
    return style_html
def main():
    # 加载默认配置
    default_config = load_config()

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="SenseYourVoice - Gradio WebUI")
    parser.add_argument(
        "--model_dir",
        type=str,
        default=default_config["model_dir"],
        help="语音模型目录",
    )
    parser.add_argument(
        "--device", type=str, default=default_config["device"], help="设备"
    )
    parser.add_argument(
        "--understanding_api_key",
        type=str,
        default=default_config["understanding_api_key"],
        help="理解模块API密钥",
    )
    parser.add_argument(
        "--understanding_api_url",
        type=str,
        default=default_config["understanding_api_url"],
        help="理解模块API地址",
    )
    parser.add_argument(
        "--specialized_api_key",
        type=str,
        default=default_config["specialized_api_key"],
        help="专业任务模块API密钥",
    )
    parser.add_argument(
        "--specialized_api_url",
        type=str,
        default=default_config["specialized_api_url"],
        help="专业任务模块API地址",
    )
    parser.add_argument(
        "--auto_init",
        action="store_true",
        default=default_config["auto_init"],
        help="自动初始化应用",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        default=default_config["share"],
        help="创建公共链接分享界面",
    )
    parser.add_argument(
        "--port", type=int, default=default_config["port"], help="服务端口"
    )
    args = parser.parse_args()

    # 创建Gradio界面
    with gr.Blocks(
        title="SenseYourVoice - 语音理解与处理", theme=grt.Citrus(), css=CUSTOM_CSS
    ) as demo:
        # 添加JavaScript代码到页面
        gr.HTML(SIDEBAR_JS)
        
        status_indicator = gr.HTML("""
            <div style="margin-bottom: 10px;">
            <span class="status-indicator" id="status-light"></span>
            <strong>系统状态：</strong><span id="status-text">未初始化</span>
            </div>
        """, visible=True)
        gr.Markdown(
            """
        # SenseYourVoice - 语音理解与处理
        上传音频文件，系统将解读并记住内容，然后您可以进行多次问答互动。
        """
        )

        # 微光加载指示器
        loading_indicator = gr.HTML(
            """
            <div class="loading-indicator" style="display: none;">
                <span style="color: white; font-weight: 500;">处理中</span>
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
            """,
            visible=False,
        )

        # 应用设置部分
        # with gr.Tab("应用设置"):
        #     model_dir = gr.Textbox(label="语音模型目录", value=args.model_dir)
        #     device = gr.Dropdown(label="设备", choices=["cuda:0", "cpu"], value=args.device)
        #     understanding_api_key = gr.Textbox(label="理解模块API密钥", value=args.understanding_api_key or "")
        #     understanding_api_url = gr.Textbox(label="理解模块API地址", value=args.understanding_api_url or "")
        #     specialized_api_key = gr.Textbox(label="专业任务模块API密钥", value=args.specialized_api_key or "")
        #     specialized_api_url = gr.Textbox(label="专业任务模块API地址", value=args.specialized_api_url or "")

        #     init_btn = gr.Button("初始化应用")
        #     init_output = gr.Textbox(label="初始化状态")

        #     init_btn.click(
        #         fn=initialize_app,
        #         inputs=[model_dir, device, understanding_api_key, understanding_api_url, specialized_api_key, specialized_api_url],
        #         outputs=init_output
        #     )

        with gr.Tab("应用设置"):
            #header_bg_color = gr.ColorPicker(label="选择小标题背景颜色", value="#e6e7e8")
            #dynamic_style = gr.HTML("", visible=False)
            #header_bg_color = gr.ColorPicker(...)
            #dynamic_style = gr.HTML(...)
            with gr.Row():
                with gr.Column(scale=1):  # 左侧放模型和设备
                    with gr.Group():
                        gr.HTML('<div class="custom-header">设备基础设置</div>', elem_classes=["custom-header"])
                        model_dir = gr.Textbox(label="语音模型目录", value=args.model_dir)
                        device = gr.Dropdown(
                        label="设备", choices=["cuda:0", "cpu"], value=args.device
                        )
                with gr.Column(scale=2):  # 右侧放API设置，并分组
                    with gr.Group():
                        gr.HTML('<div class="custom-header">理解模块 API</div>', elem_classes=["custom-header"])  # 添加小标题
                        understanding_api_key = gr.Textbox(
                            label="API密钥",
                            value=args.understanding_api_key or "",
                            type="password",
                        )  # 使用密码类型
                        understanding_api_url = gr.Textbox(
                            label="API地址", value=args.understanding_api_url or ""
                        )
                    with gr.Group():
                        gr.HTML('<div class="custom-header">专业任务模块 API</div>', elem_classes=["custom-header"])  # 添加小标题
                        specialized_api_key = gr.Textbox(
                            label="API密钥",
                            value=args.specialized_api_key or "",
                            type="password",
                        )  # 使用密码类型
                        specialized_api_url = gr.Textbox(
                            label="API地址", value=args.specialized_api_url or ""
                        )

            init_btn = gr.Button("初始化应用", elem_classes="primary_button")
            init_output = gr.Textbox(
                label="初始化状态", interactive=False
            )  # 设置为不可编辑

            # ... click 事件不变 ...
            init_btn.click(
                fn=initialize_app,
                inputs=[
                    model_dir,
                    device,
                    understanding_api_key,
                    understanding_api_url,
                    specialized_api_key,
                    specialized_api_url,
                ],
                outputs=[
                    init_output, 
                    loading_indicator,
                    status_indicator
                ],
            )
            #header_bg_color.change(
            #   fn=update_header_style,
            #   inputs=header_bg_color,
            #    outputs=dynamic_style
            #)
        # 语音处理部分
        with gr.Tab("语音处理"):
            mic_indicator = gr.HTML("""
            <div style="text-align: center; display: none;" id="mic-indicator">
            <div class="mic-pulse"></div>
            <div style="color: white; font-size: 14px;">录音中...</div>
            </div>
            """, visible=False)

            # 添加State组件存储对话历史和音频文本
            chat_history = gr.State([])
            audio_text = gr.State("")

            # 主界面布局
            with gr.Row():
                # 左侧：主要功能区域
                with gr.Column(scale=3):
                    with gr.Group():
                        gr.HTML('<div class="custom-header">音频处理</div>', elem_classes=["custom-header"])
                        audio_input = gr.Audio(label="上传音频文件", type="filepath")
                        process_audio_btn = gr.Button("处理音频")

                    with gr.Group():
                        gr.HTML('<div class="custom-header">提问与参数设置</div>', elem_classes=["custom-header"])
                        
                        # 语音内容状态指示器
                        audio_status = gr.HTML(
                            """
                            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 8px 0;">
                                <h4 style="margin: 0 0 8px 0; color: #fff;">🎤 语音内容状态</h4>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    📝 状态: <span id="audio-status">未加载</span>
                                </p>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    📊 长度: <span id="audio-length">0</span> 字符
                                </p>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    ⚖️ 权重: <span id="audio-weight">3</span>/5
                                </p>
                            </div>
                            """,
                            visible=False
                        )
                        
                        text_input = gr.Textbox(
                            label="输入问题", placeholder="请根据音频内容提问"
                        )
                        with gr.Accordion("参数设置", open=False):
                            max_tokens = gr.Slider(
                                minimum=1,
                                maximum=4096,
                                value=default_config["llm_max_tokens"],
                                step=1,
                                label="Max Tokens",
                            )
                            temperature = gr.Slider(
                                minimum=0.0,
                                maximum=2.0,
                                value=default_config["llm_temperature"],
                                step=0.1,
                                label="Temperature",
                            )
                            top_p = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                value=default_config["llm_top_p"],
                                step=0.1,
                                label="Top P",
                            )
                            top_k = gr.Slider(
                                minimum=1,
                                maximum=100,
                                value=default_config["llm_top_k"],
                                step=1,
                                label="Top K",
                            )
                            # 添加语音内容权重设置
                            audio_weight = gr.Slider(
                                minimum=1,
                                maximum=5,
                                value=3,
                                step=1,
                                label="语音内容权重 (1-5)",
                                info="数值越高，AI越重视语音内容"
                            )
                        process_text_btn = gr.Button("继续对话")

                    # 显示对话历史
                    chatbot = gr.Chatbot(label="对话历史", height=400)
                    clear_btn = gr.Button("清除对话历史")

                # 右侧：可缩回的页边栏
                with gr.Column(scale=1):
                    with gr.Group(elem_classes=["sidebar-container", "sidebar-expanded"]) as sidebar:
                        # 折叠指示器
                        collapse_btn = gr.Button(
                            "▲", 
                            elem_classes="collapse-indicator expanded",
                            size="sm"
                        )
                        
                        gr.HTML('<div class="custom-header">存储管理</div>', elem_classes=["custom-header"])
                        
                        # 保存功能
                        with gr.Group(elem_classes=["sidebar-content", "expanded"]):
                            save_title = gr.Textbox(
                                label="保存标题（可选）", 
                                placeholder="为这次记录起个名字",
                                max_lines=1
                            )
                            save_btn = gr.Button("💾 保存当前内容", elem_classes="primary_button")
                            save_status = gr.Textbox(label="保存状态", interactive=False, visible=False)
                        
                        # 分隔线
                        gr.HTML('<hr style="border: 1px solid rgba(255,255,255,0.2); margin: 16px 0;">', elem_classes=["sidebar-content", "expanded"])
                        
                        # 读取功能
                        with gr.Group(elem_classes=["sidebar-content", "expanded"]):
                            refresh_btn = gr.Button("🔄 刷新列表", size="sm")
                            saved_files_dropdown = gr.Dropdown(
                                label="选择要读取的记录",
                                choices=[],
                                interactive=True
                            )
                            load_btn = gr.Button("📂 加载选中内容", elem_classes="primary_button")
                            load_status = gr.Textbox(label="加载状态", interactive=False, visible=False)
                        
                        # 文件信息显示
                        file_info = gr.HTML(label="文件信息", visible=False, elem_classes=["sidebar-content", "expanded"])

            specialized_output = gr.Markdown(label="专业任务处理结果", visible=False)
            error_output = gr.Textbox(label="错误信息", visible=False)

            def process_and_update(audio_file, history, audio_text):
                """处理音频并逐步更新界面"""
                # 显示加载指示器 + 麦克风动画
                yield (
                history,
                history,
                gr.update(value="", visible=False),
                gr.update(value="", visible=False),
                audio_text,
                gr.update(visible=True),   # loading_indicator
                gr.update(visible=True),   # mic_indicator
                gr.update(visible=False)   # audio_status
                )

                specialized_result_output = None  # 初始化变量
                new_audio_text = audio_text  # 初始化变量
                
                for new_history, specialized, error, new_audio_text, mic_update in process_audio(
                audio_file, history, audio_text
                ):
                    specialized_result_output = specialized  # 更新变量
                    if error:
                        yield (
                        history,
                        history,
                        gr.update(value="", visible=False),
                        gr.update(value=error, visible=True),
                        audio_text,
                        gr.update(visible=False),
                        mic_update,
                        gr.update(visible=False)
                        )
                    else:
                        # 更新语音内容状态
                        if new_audio_text and new_audio_text.strip():
                            status_html = f"""
                            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 8px 0;">
                                <h4 style="margin: 0 0 8px 0; color: #fff;">🎤 语音内容状态</h4>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    📝 状态: <span style="color: #4caf50;">已加载</span>
                                </p>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    📊 长度: <span>{len(new_audio_text)}</span> 字符
                                </p>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    ⚖️ 权重: <span>3</span>/5
                                </p>
                            </div>
                            """
                            yield (
                            new_history,
                            new_history,
                            gr.update(value=specialized_result_output if specialized_result_output else "", visible=specialized_result_output is not None),
                            gr.update(value="", visible=False),
                            new_audio_text,
                            gr.update(visible=False),
                            mic_update,
                            gr.update(value=status_html, visible=True)
                            )
                        else:
                            yield (
                            new_history,
                            new_history,
                            gr.update(value=specialized_result_output if specialized_result_output else "", visible=specialized_result_output is not None),
                            gr.update(value="", visible=False),
                            new_audio_text,
                            gr.update(visible=False),
                            mic_update,
                            gr.update(visible=False)
                            )

                # 最终关闭加载和麦克风动画
                yield (
                new_history,
                new_history,
                gr.update(value=specialized_result_output if specialized_result_output else "", visible=specialized_result_output is not None),
                gr.update(value="", visible=False),
                new_audio_text,
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True)  # 保持语音状态显示
                )

            def process_text_and_update(
                text, history, audio_text, max_tokens, temperature, top_p, top_k, audio_weight
            ):
                """处理文本并逐步更新界面"""
                # 显示加载指示器
                yield history, history, gr.update(value="", visible=False), gr.update(
                    value="", visible=False
                ), audio_text, gr.update(value=text), gr.update(visible=True), gr.update(visible=False)

                specialized_result_output = None  # 初始化变量
                new_audio_text = audio_text  # 初始化变量
                
                for new_history, specialized_result_output, error, new_audio_text in process_text(
                    text, history, audio_text, max_tokens, temperature, top_p, top_k, audio_weight
                ):
                    if error:
                        yield history, history, gr.update(
                            value="", visible=False
                        ), gr.update(value=error, visible=True), audio_text, gr.update(
                            value=text
                        ), gr.update(
                            visible=False
                        ), gr.update(visible=False)
                    else:
                        # 更新语音内容状态
                        if new_audio_text and new_audio_text.strip():
                            status_html = f"""
                            <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 8px 0;">
                                <h4 style="margin: 0 0 8px 0; color: #fff;">🎤 语音内容状态</h4>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    📝 状态: <span style="color: #4caf50;">已加载</span>
                                </p>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    📊 长度: <span>{len(new_audio_text)}</span> 字符
                                </p>
                                <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                    ⚖️ 权重: <span>3</span>/5
                                </p>
                            </div>
                            """
                            yield new_history, new_history, gr.update(
                                value=specialized_result_output if specialized_result_output else "",
                                visible=specialized_result_output is not None,
                            ), gr.update(
                                value="", visible=False
                            ), new_audio_text, gr.update(
                                value=text
                            ), gr.update(
                                visible=False
                            ), gr.update(value=status_html, visible=True)
                        else:
                            yield new_history, new_history, gr.update(
                                value=specialized_result_output if specialized_result_output else "",
                                visible=specialized_result_output is not None,
                            ), gr.update(
                                value="", visible=False
                            ), new_audio_text, gr.update(
                                value=text
                            ), gr.update(
                                visible=False
                            ), gr.update(visible=False)

                # 最终状态
                if new_audio_text and new_audio_text.strip():
                    status_html = f"""
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 8px 0;">
                        <h4 style="margin: 0 0 8px 0; color: #fff;">🎤 语音内容状态</h4>
                        <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                            📝 状态: <span style="color: #4caf50;">已加载</span>
                        </p>
                        <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                            📊 长度: <span>{len(new_audio_text)}</span> 字符
                        </p>
                        <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                            ⚖️ 权重: <span>3</span>/5
                        </p>
                    </div>
                    """
                    yield new_history, new_history, gr.update(
                        value=specialized_result_output if specialized_result_output else "",
                        visible=specialized_result_output is not None,
                    ), gr.update(value="", visible=False), new_audio_text, gr.update(
                        value=""
                    ), gr.update(
                        visible=False
                    ), gr.update(value=status_html, visible=True)
                else:
                    yield new_history, new_history, gr.update(
                        value=specialized_result_output if specialized_result_output else "",
                        visible=specialized_result_output is not None,
                    ), gr.update(value="", visible=False), new_audio_text, gr.update(
                        value=""
                    ), gr.update(
                        visible=False
                    ), gr.update(visible=False)

            def save_current_content(audio_text, chat_history, title):
                """保存当前内容"""
                result = save_transcription(audio_text, chat_history, title)
                return gr.update(value=result, visible=True)

            def refresh_saved_files():
                """刷新保存的文件列表"""
                saved_files = load_saved_transcriptions()
                choices = []
                for file_info in saved_files:
                    # 格式化显示：标题 + 时间 + 消息数量
                    display_name = f"{file_info['title']} ({file_info['timestamp'][:19]}) - {file_info.get('total_messages', 0)}条消息"
                    choices.append((display_name, file_info['filepath']))
                return gr.update(choices=choices)

            def load_selected_content(selected_file):
                """加载选中的内容并刷新界面"""
                if not selected_file:
                    return "", [], [], gr.update(value="请先选择一个文件", visible=True), gr.update(visible=False), gr.update(value=""), gr.update(visible=False)
                
                audio_text, chat_history, title, metadata = load_transcription_content(selected_file)
                if audio_text or chat_history:
                    # 生成文件信息HTML
                    info_html = f"""
                    <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 8px 0;">
                        <h4 style="margin: 0 0 8px 0; color: #fff;">📄 {title}</h4>
                        <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                            📅 创建时间: {metadata.get('created_at', '未知')[:19]}
                        </p>
                        <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                            💬 对话记录: {len(chat_history)} 条
                        </p>
                        <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                            📝 音频文本: {len(audio_text)} 字符
                        </p>
                    </div>
                    """
                    
                    # 生成语音状态HTML
                    if audio_text and audio_text.strip():
                        audio_status_html = f"""
                        <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin: 8px 0;">
                            <h4 style="margin: 0 0 8px 0; color: #fff;">🎤 语音内容状态</h4>
                            <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                📝 状态: <span style="color: #4caf50;">已加载</span>
                            </p>
                            <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                📊 长度: <span>{len(audio_text)}</span> 字符
                            </p>
                            <p style="margin: 4px 0; font-size: 12px; color: rgba(255,255,255,0.8);">
                                ⚖️ 权重: <span>3</span>/5
                            </p>
                        </div>
                        """
                    else:
                        audio_status_html = ""
                    
                    # 更新模型初始化提示
                    init_message = f"✅ 已加载保存的内容：{title} (包含 {len(chat_history)} 条对话记录)"
                    
                    return (
                        audio_text, 
                        chat_history, 
                        chat_history, 
                        gr.update(value=f"✅ 已加载: {title}", visible=True),
                        gr.update(value=info_html, visible=True),
                        gr.update(value=init_message),  # 更新初始化提示
                        gr.update(value=audio_status_html, visible=bool(audio_status_html))
                    )
                else:
                    return "", [], [], gr.update(value=f"❌ 加载失败: {title}", visible=True), gr.update(visible=False), gr.update(value="❌ 加载失败"), gr.update(visible=False)

            def clear_chat_history():
                """清除对话历史和音频文本"""
                return (
                    [],
                    [],
                    gr.update(value="", visible=False),
                    gr.update(value="", visible=False),
                    "",
                    gr.update(visible=False),  # 清除文件信息
                    gr.update(visible=False),  # 清除语音状态
                )

            def toggle_sidebar():
                """切换页边栏折叠状态"""
                # 这个函数主要用于触发界面更新
                # 实际的折叠逻辑通过JavaScript实现
                return gr.update()

            def update_init_status(message):
                """更新初始化状态"""
                return gr.update(value=message)

            # 处理音频按钮事件
            process_audio_btn.click(
                fn=process_and_update,
                inputs=[audio_input, chat_history, audio_text],
                outputs=[
                    chat_history,
                    chatbot,
                    specialized_output,
                    error_output,
                    audio_text,
                    loading_indicator,
                    mic_indicator,
                    audio_status
                ],
            )

            # 处理文本按钮事件
            process_text_btn.click(
                fn=process_text_and_update,
                inputs=[
                    text_input,
                    chat_history,
                    audio_text,
                    max_tokens,
                    temperature,
                    top_p,
                    top_k,
                    audio_weight,
                ],
                outputs=[
                    chat_history,
                    chatbot,
                    specialized_output,
                    error_output,
                    audio_text,
                    text_input,
                    loading_indicator,
                    audio_status,
                ],
            )

            clear_btn.click(
                fn=clear_chat_history,
                inputs=[],
                outputs=[
                    chat_history,
                    chatbot,
                    specialized_output,
                    error_output,
                    audio_text,
                    file_info,
                    audio_status,
                ],
            )

            save_btn.click(
                fn=save_current_content,
                inputs=[
                    audio_text,
                    chat_history,
                    save_title,
                ],
                outputs=[
                    save_status,
                ],
            )

            refresh_btn.click(
                fn=refresh_saved_files,
                inputs=[],
                outputs=[
                    saved_files_dropdown,
                ],
            )

            saved_files_dropdown.change(
                fn=load_selected_content,
                inputs=[saved_files_dropdown],
                outputs=[
                    audio_text,
                    chat_history,
                    chatbot,
                    load_status,
                    file_info,
                    status_indicator,  # 更新初始化状态
                    audio_status,      # 更新语音状态
                ],
            )

            # 折叠按钮事件（可选，主要用于触发界面更新）
            collapse_btn.click(
                fn=toggle_sidebar,
                inputs=[],
                outputs=[sidebar],
            )

        gr.Markdown(
            """
        ### 使用说明
        1. 在"应用设置"标签页中配置参数并初始化应用。
        2. 在"语音处理"标签页中：
           - **上传音频**：上传音频文件，点击"处理音频"，系统会解读并反馈。
           - **提问**：在文本框中输入问题，点击"继续对话"进行互动。
           - **语音内容权重**：调整"语音内容权重"滑块(1-5)，数值越高AI越重视语音内容：
           - **语音状态指示器**：实时显示当前语音内容的状态、长度和权重设置。
           - **保存内容**：处理音频后，可以为记录添加标题并点击"💾 保存当前内容"。
           - **读取内容**：点击"🔄 刷新列表"查看已保存的记录，选择后自动加载内容。
           - **文件信息**：加载内容后会显示详细的文件信息，包括创建时间、对话记录数量等。
          o - **页边栏折叠**：点击右上角的▲/▼按钮可以折叠/展开存储管理页边栏。
        3. 系统会记住音频内容，支持多轮问答。
        4. 使用"清除对话历史"按钮开始新的对话。
        """
        )

    # 如果设置了自动初始化，则在启动前初始化应用
    if args.auto_init:
        init_result = initialize_app(
            args.model_dir,
            args.device,
            args.understanding_api_key,
            args.understanding_api_url,
            args.specialized_api_key,
            args.specialized_api_url,
        )
        print(f"自动初始化结果: {init_result}")

    # 启动Gradio界面
    demo.launch(share=args.share, server_port=args.port)


if __name__ == "__main__":
    main()
