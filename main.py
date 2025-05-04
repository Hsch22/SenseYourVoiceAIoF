# -*- encoding: utf-8 -*-

import os
import sys
import argparse
import torch
import gradio as gr
import gradio.themes as grt
import time

# 导入配置和主应用
from config import load_config
from app_new import SenseYourVoiceApp

# 全局应用实例
sense_app = None

def initialize_app(model_dir, device, understanding_api_key, understanding_api_url, specialized_api_key, specialized_api_url):
    """初始化应用实例"""
    global sense_app
    
    # 从用户输入创建配置字典
    user_config = {
        "model_dir": model_dir,
        "device": device,
        "understanding_api_key": understanding_api_key,
        "understanding_api_url": understanding_api_url,
        "specialized_api_key": specialized_api_key,
        "specialized_api_url": specialized_api_url
    }
    
    # 使用load_config函数加载配置，合并用户配置和默认配置
    config = load_config(user_config)
    
    try:
        sense_app = SenseYourVoiceApp(config)
        return "应用初始化成功！"
    except Exception as e:
        return f"应用初始化失败: {str(e)}"

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
        # 构建对话历史上下文
        context = ""
        if chat_history:
            for user_msg, bot_msg in chat_history:
                if user_msg and bot_msg:
                    context += f"用户: {user_msg}\n助手: {bot_msg}\n"
        
        # 处理音频文件
        result = sense_app.process(audio_file, context=context) # Removed instruction
        
        if not result["success"]:
            yield chat_history, None, result["error"], audio_text
            return
        
        # 获取音频转录内容
        transcription = result["transcription"]
        audio_text = transcription  # 存储音频文本内容
        
        # 系统反馈消息
        system_message = "我已成功理解音频文件，您想了解些什么？"
        new_chat_history = list(chat_history) if chat_history else []
        new_chat_history.append(("", system_message))
        
        for i in range(len(system_message) + 1):
            time.sleep(0.05) 
            new_chat_history[-1] = ("", system_message[:i])
            yield new_chat_history, None, None, audio_text
        
        # 确保完整输出
        yield new_chat_history, None, None, audio_text
    except Exception as e:
        yield chat_history, None, f"处理过程发生错误: {str(e)}", audio_text

def process_text(text_input, chat_history, audio_text, max_tokens, temperature, top_p, top_k):
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
        if audio_text:
            context += f"音频内容: {audio_text}\n"
        if chat_history:
            for user_msg, bot_msg in chat_history:
                if user_msg and bot_msg:
                    context += f"用户: {user_msg}\n助手: {bot_msg}\n"
        
        # 分析用户输入的文本 (流式)
        llm_params = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k
            # "stop": stop # Stop might be handled differently
        }
        
        new_chat_history = list(chat_history) if chat_history else []
        new_chat_history.append((text_input, ""))
        full_response = ""
        needs_specialized_task = False
        specialized_result_output = None # 用于存储专业任务的最终结果或流式块

        # 处理理解模块的流式输出
        understanding_stream = sense_app.understanding.analyze(text_input, context=context, llm_params=llm_params)
        for chunk_data in understanding_stream:
            if not chunk_data["success"]:
                yield new_chat_history, specialized_result_output, chunk_data["error"], audio_text
                return
            
            if chunk_data["is_final"]:
                needs_specialized_task = chunk_data.get("needs_specialized_task", False)
                full_response = chunk_data.get("full_response", full_response) # 获取完整响应
                break # 理解流结束
            
            response_chunk = chunk_data.get("response_chunk", "")
            if response_chunk:
                full_response += response_chunk
                new_chat_history[-1] = (text_input, full_response)
                yield new_chat_history, specialized_result_output, None, audio_text

        # 如果需要专业任务处理 (流式)
        if needs_specialized_task:
            task_type = sense_app._determine_task_type(full_response) # 使用完整响应判断任务类型
            specialized_task_stream = sense_app.specialized_task.process_task(task_type, full_response)
            
            full_specialized_result = "" # 用于累积专业任务的流式结果
            specialized_result_output = "" # 初始化专业任务输出为空字符串
            
            for specialized_chunk_data in specialized_task_stream:
                if not specialized_chunk_data["success"]:
                    # 专业任务出错，也需要更新聊天记录（显示之前的理解结果）
                    yield new_chat_history, specialized_result_output, specialized_chunk_data["error"], audio_text
                    return
                
                if specialized_chunk_data["is_final"]:
                    # 可选：获取完整的专业任务结果
                    # full_specialized_result = specialized_chunk_data.get("full_result", full_specialized_result)
                    break # 专业任务流结束
                
                result_chunk = specialized_chunk_data.get("result_chunk", "")
                if result_chunk:
                    full_specialized_result += result_chunk
                    specialized_result_output = full_specialized_result # 更新输出
                    # 在专业任务流式输出时，聊天记录通常保持不变（显示理解结果）
                    # 但专业任务结果区域会更新
                    yield new_chat_history, specialized_result_output, None, audio_text
            
            # 专业任务流结束后，确保最终的专业结果被传递
            specialized_result_output = full_specialized_result

        # 确保最终状态被传递
        yield new_chat_history, specialized_result_output, None, audio_text

    except Exception as e:
        yield chat_history, None, f"处理过程发生错误: {str(e)}", audio_text

def main():
    # 加载默认配置
    default_config = load_config()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="SenseYourVoice - Gradio WebUI")
    parser.add_argument("--model_dir", type=str, default=default_config["model_dir"], help="语音模型目录")
    parser.add_argument("--device", type=str, default=default_config["device"], help="设备")
    parser.add_argument("--understanding_api_key", type=str, default=default_config["understanding_api_key"], help="理解模块API密钥")
    parser.add_argument("--understanding_api_url", type=str, default=default_config["understanding_api_url"], help="理解模块API地址")
    parser.add_argument("--specialized_api_key", type=str, default=default_config["specialized_api_key"], help="专业任务模块API密钥")
    parser.add_argument("--specialized_api_url", type=str, default=default_config["specialized_api_url"], help="专业任务模块API地址")
    parser.add_argument("--auto_init", action="store_true", default=default_config["auto_init"], help="自动初始化应用")
    parser.add_argument("--share", action="store_true", default=default_config["share"], help="创建公共链接分享界面")
    parser.add_argument("--port", type=int, default=default_config["port"], help="服务端口")
    args = parser.parse_args()

    # 创建Gradio界面
    with gr.Blocks(title="SenseYourVoice - 语音理解与处理",theme=grt.Citrus()) as demo:
        gr.Markdown("""
        # SenseYourVoice - 语音理解与处理
        上传音频文件，系统将解读并记住内容，然后您可以进行多次问答互动。
        """)
        
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
            with gr.Row():
                with gr.Column(scale=1): # 左侧放模型和设备
                    model_dir = gr.Textbox(label="语音模型目录", value=args.model_dir)
                    device = gr.Dropdown(label="设备", choices=["cuda:0", "cpu"], value=args.device)
                with gr.Column(scale=2): # 右侧放API设置，并分组
                    with gr.Group():
                        gr.Markdown("### 理解模块 API") # 添加小标题
                        understanding_api_key = gr.Textbox(label="API密钥", value=args.understanding_api_key or "", type="password") # 使用密码类型
                        understanding_api_url = gr.Textbox(label="API地址", value=args.understanding_api_url or "")
                    with gr.Group():
                        gr.Markdown("### 专业任务模块 API") # 添加小标题
                        specialized_api_key = gr.Textbox(label="API密钥", value=args.specialized_api_key or "", type="password") # 使用密码类型
                        specialized_api_url = gr.Textbox(label="API地址", value=args.specialized_api_url or "")

            init_btn = gr.Button("初始化应用", variant="primary") # 使用 primary 变体突出按钮
            init_output = gr.Textbox(label="初始化状态", interactive=False) # 设置为不可编辑

            # ... click 事件不变 ...
            init_btn.click(
                fn=initialize_app,
                inputs=[model_dir, device, understanding_api_key, understanding_api_url, specialized_api_key, specialized_api_url],
                outputs=init_output
            )

        
        # 语音处理部分
        with gr.Tab("语音处理"):
            # 添加State组件存储对话历史和音频文本
            chat_history = gr.State([])
            audio_text = gr.State("")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 音频输入")
                    audio_input = gr.Audio(label="上传音频文件", type="filepath")
                    process_audio_btn = gr.Button("处理音频")
                
                with gr.Column():
                    gr.Markdown("### 提问与参数设置")
                    text_input = gr.Textbox(label="输入问题", placeholder="请根据音频内容提问")
                    with gr.Accordion("参数设置", open=False):
                        max_tokens = gr.Slider(minimum=1, maximum=2048, value=default_config["llm_max_tokens"], step=1, label="Max Tokens")
                        temperature = gr.Slider(minimum=0.0, maximum=2.0, value=default_config["llm_temperature"], step=0.1, label="Temperature")
                        top_p = gr.Slider(minimum=0.0, maximum=1.0, value=default_config["llm_top_p"], step=0.1, label="Top P")
                        top_k = gr.Slider(minimum=1, maximum=100, value=default_config["llm_top_k"], step=1, label="Top K")
                        # stop = gr.Textbox(label="Stop Sequences", value=default_config["llm_stop"] or "") # Stop sequences might be complex for UI
                    process_text_btn = gr.Button("继续对话")
            
            # 显示对话历史
            chatbot = gr.Chatbot(label="对话历史", height=400)
            
            clear_btn = gr.Button("清除对话历史")
            
            specialized_output = gr.Markdown(label="专业任务处理结果", visible=False)
            # specialized_output = gr.Textbox(label="专业任务处理结果", visible=False)
            error_output = gr.Textbox(label="错误信息", visible=False)
            
            def process_and_update(audio_file, history, audio_text):
                """处理音频并逐步更新界面"""
                for new_history, specialized, error, new_audio_text in process_audio(audio_file, history, audio_text):
                    if error:
                        yield history, history, gr.update(value="", visible=False), gr.update(value=error, visible=True), audio_text
                    else:
                        yield new_history, new_history, gr.update(value=specialized if specialized else "", visible=specialized is not None), gr.update(value="", visible=False), new_audio_text
            
            def process_text_and_update(text, history, audio_text, max_tokens, temperature, top_p, top_k):
                """处理文本并逐步更新界面"""
                for new_history, specialized, error, new_audio_text in process_text(text, history, audio_text, max_tokens, temperature, top_p, top_k):
                    if error:
                        yield history, history, gr.update(value="", visible=False), gr.update(value=error, visible=True), audio_text, gr.update(value=text)
                    else:
                        yield new_history, new_history, gr.update(value=specialized if specialized else "", visible=specialized is not None), gr.update(value="", visible=False), new_audio_text, gr.update(value=text)
                
                # 在处理完后清空输入框
                # 在process_text_and_update函数中，修改yield语句
                # yield new_history, new_history, gr.update(value=specialized if specialized else "", visible=specialized is not None), gr.update(value="", visible=False), new_audio_text, gr.update(value=text)
                yield new_history, new_history, gr.update(value=specialized if specialized else "", visible=specialized is not None), gr.update(value="", visible=False), new_audio_text, gr.update(value="")
            
            def clear_chat_history():
                """清除对话历史和音频文本"""
                return [], [], gr.update(value="", visible=False), gr.update(value="", visible=False), ""
            
            # 处理音频按钮事件
            process_audio_btn.click(
                fn=process_and_update,
                inputs=[audio_input, chat_history, audio_text],
                outputs=[chat_history, chatbot, specialized_output, error_output, audio_text]
            )
            
            # 处理文本按钮事件
            process_text_btn.click(
                fn=process_text_and_update,
                inputs=[text_input, chat_history, audio_text, max_tokens, temperature, top_p, top_k],
                outputs=[chat_history, chatbot, specialized_output, error_output, audio_text, text_input]
            )
            
            clear_btn.click(
                fn=clear_chat_history,
                inputs=[],
                outputs=[chat_history, chatbot, specialized_output, error_output, audio_text]
            )
        
        gr.Markdown("""
        ### 使用说明
        1. 在"应用设置"标签页中配置参数并初始化应用。
        2. 在"语音处理"标签页中：
           - **上传音频**：上传音频文件，点击"处理音频"，系统会解读并反馈。
           - **提问**：在文本框中输入问题，点击"继续对话"进行互动。
        3. 系统会记住音频内容，支持多轮问答。
        4. 使用"清除对话历史"按钮开始新的对话。
        """)
    
    # 如果设置了自动初始化，则在启动前初始化应用
    if args.auto_init:
        init_result = initialize_app(
            args.model_dir,
            args.device,
            args.understanding_api_key,
            args.understanding_api_url,
            args.specialized_api_key,
            args.specialized_api_url
        )
        print(f"自动初始化结果: {init_result}")
    
    # 启动Gradio界面
    demo.launch(share=args.share, server_port=args.port)

if __name__ == "__main__":
    main()