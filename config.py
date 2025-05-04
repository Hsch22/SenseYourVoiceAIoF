# -*- encoding: utf-8 -*-

import os
import torch

# 默认配置
DEFAULT_CONFIG = {
    "model_dir": "iic/SenseVoiceSmall",
    "device": "cuda:0" if torch.cuda.is_available() else "cpu",
    
    # 理解模块配置
    "understanding_api_key": os.environ.get("UNDERSTANDING_API_KEY", "sk-qseennfhdprismchczwnkzpohyjmuwgpiaywuclsisgugfvo"),
    "understanding_api_url": os.environ.get("UNDERSTANDING_API_URL", "https://api.siliconflow.cn/v1/chat/completions"),
    "understanding_model": "Qwen/Qwen2.5-72B-Instruct-128K",  # 默认使用的模型
    
    # 专业任务模块配置
    "specialized_api_key": os.environ.get("SPECIALIZED_API_KEY", "sk-qseennfhdprismchczwnkzpohyjmuwgpiaywuclsisgugfvo"),
    "specialized_api_url": os.environ.get("SPECIALIZED_API_URL", "https://api.siliconflow.cn/v1/chat/completions"),
    "specialized_model": "Qwen/Qwen2.5-72B-Instruct-128K",  # 默认使用的模型
    
    # 应用配置
    "auto_init": False,  # 是否自动初始化应用
    "share": False,     # 是否创建公共链接分享界面
    "port": 7800,       # 服务端口
    
    # LLM 调用参数
    "llm_max_tokens": 512,
    "llm_stop": None,
    "llm_temperature": 0.7,
    "llm_top_p": 0.7,
    "llm_top_k": 50
}


def load_config(user_config=None):
    """
    加载配置，合并用户配置和默认配置
    
    Args:
        user_config (dict, optional): 用户提供的配置
        
    Returns:
        dict: 合并后的配置
    """
    config = DEFAULT_CONFIG.copy()
    
    if user_config:
        # 更新配置
        for key, value in user_config.items():
            if value is not None:  # 只更新非None值
                config[key] = value
    
    return config