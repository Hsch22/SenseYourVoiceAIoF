#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""
测试保存和读取功能的脚本
"""

import json
import datetime
from pathlib import Path

# 模拟保存目录
SAVE_DIR = Path("saved_transcriptions")
SAVE_DIR.mkdir(exist_ok=True)

def test_save_function():
    """测试保存功能"""
    print("=== 测试保存功能 ===")
    
    # 模拟数据
    test_data = {
        "title": "测试语音转文字记录",
        "timestamp": datetime.datetime.now().isoformat(),
        "audio_text": "这是一个测试的语音转文字内容，用于验证保存功能是否正常工作。",
        "chat_history": [
            ["用户: 这是什么内容？", "助手: 这是一个测试内容。"],
            ["用户: 能详细解释一下吗？", "助手: 当然可以，这是一个用于测试保存功能的示例内容。"]
        ],
        "filename": "test_transcription.json"
    }
    
    # 保存到文件
    filepath = SAVE_DIR / "test_transcription.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 测试数据已保存到: {filepath}")
    return filepath

def test_load_function(filepath):
    """测试加载功能"""
    print("\n=== 测试加载功能 ===")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ 成功加载文件: {filepath}")
        print(f"标题: {data.get('title', '无标题')}")
        print(f"时间: {data.get('timestamp', '无时间')}")
        print(f"音频文本: {data.get('audio_text', '无内容')}")
        print(f"对话历史: {len(data.get('chat_history', []))} 条记录")
        
        return True
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return False

def test_list_files():
    """测试列出所有保存的文件"""
    print("\n=== 测试列出保存的文件 ===")
    
    saved_files = []
    for filepath in SAVE_DIR.glob("*.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                saved_files.append({
                    "filename": data.get("filename", filepath.name),
                    "title": data.get("title", "未命名"),
                    "timestamp": data.get("timestamp", ""),
                    "filepath": str(filepath)
                })
        except Exception as e:
            print(f"⚠️ 读取文件 {filepath} 失败: {e}")
            continue
    
    # 按时间戳排序
    saved_files.sort(key=lambda x: x["timestamp"], reverse=True)
    
    print(f"✅ 找到 {len(saved_files)} 个保存的文件:")
    for i, file_info in enumerate(saved_files, 1):
        print(f"  {i}. {file_info['title']} ({file_info['timestamp'][:19]})")
    
    return saved_files

if __name__ == "__main__":
    print("开始测试保存和读取功能...\n")
    
    # 测试保存
    test_file = test_save_function()
    
    # 测试加载
    test_load_function(test_file)
    
    # 测试列出文件
    test_list_files()
    
    print("\n✅ 所有测试完成！")
    print(f"保存目录: {SAVE_DIR.absolute()}") 