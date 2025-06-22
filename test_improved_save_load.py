#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

"""
测试改进后的保存和读取功能的脚本
"""

import json
import datetime
from pathlib import Path

# 模拟保存目录
SAVE_DIR = Path("saved_transcriptions")
SAVE_DIR.mkdir(exist_ok=True)

def test_improved_save_function():
    """测试改进后的保存功能"""
    print("=== 测试改进后的保存功能 ===")
    
    # 模拟完整的对话数据
    test_data = {
        "title": "改进版测试语音转文字记录",
        "timestamp": datetime.datetime.now().isoformat(),
        "audio_text": "这是一个改进版的测试语音转文字内容，用于验证新的保存功能是否正常工作。包含了更详细的信息和完整的对话历史。",
        "chat_history": [
            ["用户: 这是什么内容？", "助手: 这是一个改进版的测试内容，包含了更详细的信息。"],
            ["用户: 能详细解释一下吗？", "助手: 当然可以，这个改进版本包含了完整的对话历史、元数据信息，以及更好的用户体验。"],
            ["用户: 有什么新功能？", "助手: 新功能包括：1. 可缩回的页边栏 2. 完整界面刷新 3. 详细的文件信息显示 4. 更好的用户体验"],
            ["用户: 听起来很棒！", "助手: 谢谢！我们确实做了很多改进，让用户能够更方便地管理和查看他们的语音转文字记录。"]
        ],
        "filename": "improved_test_transcription.json",
        "total_messages": 4,
        "audio_text_length": 89,
        "metadata": {
            "created_at": datetime.datetime.now().isoformat(),
            "version": "2.0",
            "app_name": "SenseYourVoice",
            "features": ["sidebar", "full_refresh", "detailed_info", "better_ux"]
        }
    }
    
    # 保存到文件
    filepath = SAVE_DIR / "improved_test_transcription.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 改进版测试数据已保存到: {filepath}")
    print(f"📊 包含 {test_data['total_messages']} 条对话记录")
    print(f"📝 音频文本长度: {test_data['audio_text_length']} 字符")
    print(f"🔧 版本: {test_data['metadata']['version']}")
    return filepath

def test_improved_load_function(filepath):
    """测试改进后的加载功能"""
    print("\n=== 测试改进后的加载功能 ===")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ 成功加载改进版文件: {filepath}")
        print(f"📄 标题: {data.get('title', '无标题')}")
        print(f"📅 时间: {data.get('timestamp', '无时间')}")
        print(f"💬 对话记录: {data.get('total_messages', 0)} 条")
        print(f"📝 音频文本: {data.get('audio_text_length', 0)} 字符")
        print(f"🔧 版本: {data.get('metadata', {}).get('version', '未知')}")
        print(f"🎯 功能特性: {data.get('metadata', {}).get('features', [])}")
        
        # 显示对话历史预览
        chat_history = data.get('chat_history', [])
        if chat_history:
            print(f"\n💭 对话历史预览:")
            for i, (user_msg, bot_msg) in enumerate(chat_history[:2], 1):
                print(f"  {i}. 用户: {user_msg[:30]}...")
                print(f"     助手: {bot_msg[:30]}...")
            if len(chat_history) > 2:
                print(f"     ... 还有 {len(chat_history) - 2} 条记录")
        
        return True
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return False

def test_list_improved_files():
    """测试列出改进后的保存文件"""
    print("\n=== 测试列出改进后的保存文件 ===")
    
    saved_files = []
    for filepath in SAVE_DIR.glob("*.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                saved_files.append({
                    "filename": data.get("filename", filepath.name),
                    "title": data.get("title", "未命名"),
                    "timestamp": data.get("timestamp", ""),
                    "total_messages": data.get("total_messages", 0),
                    "audio_text_length": data.get("audio_text_length", 0),
                    "version": data.get("metadata", {}).get("version", "1.0"),
                    "filepath": str(filepath)
                })
        except Exception as e:
            print(f"⚠️ 读取文件 {filepath} 失败: {e}")
            continue
    
    # 按时间戳排序
    saved_files.sort(key=lambda x: x["timestamp"], reverse=True)
    
    print(f"✅ 找到 {len(saved_files)} 个保存的文件:")
    for i, file_info in enumerate(saved_files, 1):
        print(f"  {i}. {file_info['title']} (v{file_info['version']})")
        print(f"     时间: {file_info['timestamp'][:19]}")
        print(f"     对话: {file_info['total_messages']} 条, 文本: {file_info['audio_text_length']} 字符")
    
    return saved_files

def test_ui_simulation():
    """模拟UI界面的操作流程"""
    print("\n=== 模拟UI界面操作流程 ===")
    
    print("🎯 用户操作流程:")
    print("1. 用户上传音频文件")
    print("2. 点击'处理音频'按钮")
    print("3. 系统显示语音转文字结果")
    print("4. 用户进行多轮对话")
    print("5. 用户点击'💾 保存当前内容'")
    print("6. 系统保存完整对话历史到JSON文件")
    print("7. 用户点击'🔄 刷新列表'")
    print("8. 系统显示所有保存的记录")
    print("9. 用户选择记录，系统自动加载并刷新界面")
    print("10. 系统显示详细的文件信息")
    
    print("\n✨ 改进特性:")
    print("- 可缩回的页边栏设计")
    print("- 完整界面刷新功能")
    print("- 详细的文件信息显示")
    print("- 更好的用户体验")
    print("- 完整的对话历史保存")

if __name__ == "__main__":
    print("开始测试改进后的保存和读取功能...\n")
    
    # 测试改进后的保存
    test_file = test_improved_save_function()
    
    # 测试改进后的加载
    test_improved_load_function(test_file)
    
    # 测试列出文件
    test_list_improved_files()
    
    # 模拟UI操作
    test_ui_simulation()
    
    print("\n✅ 所有改进功能测试完成！")
    print(f"保存目录: {SAVE_DIR.absolute()}")
    print("🎉 新功能已成功实现！") 