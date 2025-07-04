# -*- encoding: utf-8 -*-

import os
import sys
import argparse
import torch
import logging
from pathlib import Path

# 导入配置和模块化组件
from config import load_config
from modules import VoiceToTextModule, UnderstandingModule, SpecializedTaskModule

# 设置日志
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SenseYourVoiceApp')


def validate_response_dict(response_dict, required_keys, context_msg="Stream"):
    """
    简单的校验函数，检查字典中是否存在所有必需的键。
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

    return None  # 表示校验通过，调用者应继续处理原始 response_dict


class SenseYourVoiceApp:
    def __init__(self, config=None):
        """主应用类，整合三个模块"""
        # 加载配置，合并用户配置和默认配置
        self.config = load_config(config)
        logger.info("加载应用配置完成")

        # 初始化语音转文字模块
        logger.info("初始化语音转文字模块...")
        self.voice_to_text = VoiceToTextModule(
            model_dir=self.config.get("model_dir"), device=self.config.get("device")
        )

        # 初始化理解模块
        logger.info("初始化理解模块...")
        self.understanding = UnderstandingModule(
            api_key=self.config.get("understanding_api_key"),
            api_url=self.config.get("understanding_api_url"),
            model=self.config.get("understanding_model"),
        )

        # 初始化专业任务模块
        logger.info("初始化专业任务模块...")
        self.specialized_task = SpecializedTaskModule(
            api_key=self.config.get("specialized_api_key"),
            api_url=self.config.get("specialized_api_url"),
            model=self.config.get("specialized_model"),
        )

        logger.info("SenseYourVoice应用初始化完成")

    def process(self, audio_path, instruction="", context=""):
        """处理音频文件的完整流程，支持多轮对话"""
        try:
            # 步骤1: 语音转文字
            logger.info(f"正在处理音频文件: {audio_path}")
            transcription_result = self.voice_to_text.transcribe(audio_path)

            # --- 校验 VoiceToTextModule 输出 ---
            vtt_required_keys = [
                "success",
                "text",
            ]  # "error" is conditional on success=False
            validation_error = validate_response_dict(
                transcription_result, vtt_required_keys, "VoiceToTextModule.transcribe"
            )
            if validation_error:
                return validation_error  # 校验失败，返回错误信息
            # --- 校验结束 ---

            if not transcription_result["success"]:
                error_msg = transcription_result.get(
                    "error", "语音转文字失败，但未提供明确错误信息。"
                )
                logger.error(f"语音转文字失败: {error_msg}")
                return {"success": False, "error": error_msg}

            text = transcription_result["text"]
            logger.info(f"语音转文字完成，文本长度: {len(text)}字符")

            # 步骤2: 理解与分析，处理流式输出
            logger.info("开始进行文本理解与分析")
            
            # 增强语音内容的上下文构建
            enhanced_context = ""
            if context:
                enhanced_context += f"历史上下文: {context}\n\n"
            
            # 添加语音内容强调指令
            enhanced_context += f"""
=== 用户语音输入 ===
{text}
=== 语音输入结束 ===

请基于以上语音内容进行分析和理解。这是用户的核心输入，请重点关注。

"""
            
            understanding_stream = self.understanding.analyze(
                text, context=enhanced_context
            )

            full_understanding_response = ""
            needs_specialized_task = False
            understanding_error = None
            # --- 定义理解模块流式输出期望的关键字段 ---
            understanding_chunk_required_keys = [
                "success",
                "is_final",
            ]

            for chunk_data in understanding_stream:
                # --- 校验 UnderstandingModule 流式块 ---
                validation_error = validate_response_dict(
                    chunk_data,
                    understanding_chunk_required_keys,
                    "UnderstandingModule.analyze stream",
                )
                if validation_error:
                    understanding_error = validation_error[
                        "error"
                    ]  # 获取校验产生的错误信息
                    logger.error(f"理解分析流中校验失败: {understanding_error}")
                    break  # 停止处理流
                # --- 校验结束 ---

                if not chunk_data["success"]:
                    understanding_error = chunk_data.get(
                        'error', "理解分析流中发生未知错误。"
                    )  # 使用get避免KeyError
                    logger.error(f"理解分析流中出错: {understanding_error}")
                    break  # 停止处理流

                if chunk_data.get("response_chunk"):
                    full_understanding_response += chunk_data["response_chunk"]

                if chunk_data["is_final"]:
                    needs_specialized_task = chunk_data.get(
                        "needs_specialized_task", False
                    )
                    # 如果没有累积到响应，尝试从 final chunk 获取
                    if not full_understanding_response:
                        full_understanding_response = chunk_data.get(
                            "full_response", ""
                        )
                    break  # 流结束

            if understanding_error:
                return {
                    "success": False,
                    "error": f"理解分析失败: {understanding_error}",
                }

            response = full_understanding_response

            # 步骤3: 如果需要，进行专业任务处理 (同样处理流式)
            if needs_specialized_task:
                logger.info("检测到需要专业任务处理")
                task_type = self._determine_task_type(response)
                logger.info(f"确定任务类型: {task_type}")

                specialized_task_stream = self.specialized_task.process_task(
                    task_type, response
                )

                full_specialized_result = ""
                specialized_error = None
                # --- 定义专业任务模块流式输出期望的关键字段 ---
                specialized_chunk_required_keys = [
                    "success",
                    "is_final",
                ]

                for specialized_chunk_data in specialized_task_stream:
                    # --- 校验 SpecializedTaskModule 流式块 ---
                    validation_error = validate_response_dict(
                        specialized_chunk_data,
                        specialized_chunk_required_keys,
                        "SpecializedTaskModule.process_task stream",
                    )
                    if validation_error:
                        specialized_error = validation_error[
                            "error"
                        ]  # 获取校验产生的错误信息
                        logger.error(f"专业任务处理流中校验失败: {specialized_error}")
                        break  # 停止处理流
                    # --- 校验结束 ---

                    if not specialized_chunk_data["success"]:
                        specialized_error = specialized_chunk_data.get(
                            'error', "专业任务处理流中发生未知错误。"
                        )  # 使用get避免KeyError
                        logger.error(f"专业任务处理流中出错: {specialized_error}")
                        break  # 停止处理流

                    if specialized_chunk_data.get("result_chunk"):
                        full_specialized_result += specialized_chunk_data[
                            "result_chunk"
                        ]

                    if specialized_chunk_data["is_final"]:
                        # 如果没有累积到结果，尝试从 final chunk 获取
                        if not full_specialized_result:
                            full_specialized_result = specialized_chunk_data.get(
                                "full_result", ""
                            )
                        break  # 流结束

                if specialized_error:
                    return {
                        "success": False,
                        "error": f"专业任务处理失败: {specialized_error}",
                    }

                final_result = {
                    "success": True,
                    "transcription": text,
                    "understanding": response,
                    "specialized_result": full_specialized_result,
                }
            else:
                logger.info("无需专业任务处理")
                final_result = {
                    "success": True,
                    "transcription": text,
                    "understanding": response,
                }

            logger.info("处理完成，返回结果")
            return final_result

        except Exception as e:
            error_msg = f"处理过程发生未预期错误: {str(e)}"
            logger.error(
                error_msg, exc_info=True
            )  # 添加 exc_info=True 获取更详细的traceback
            return {"success": False, "error": error_msg}

    def _determine_task_type(self, text):
        """根据文本内容确定专业任务类型"""
        # 代码相关关键词
        code_keywords = [
            "代码",
            "编程",
            "程序",
            "算法",
            "函数",
            "变量",
            "类",
            "对象",
            "接口",
            "API",
            "库",
            "框架",
            "编译",
            "调试",
            "bug",
            "错误",
            "异常",
            "开发",
        ]

        # 数学相关关键词
        math_keywords = [
            "数学",
            "计算",
            "方程",
            "公式",
            "数值",
            "统计",
            "概率",
            "微积分",
            "代数",
            "几何",
            "三角",
            "矩阵",
            "向量",
            "函数式",
            "导数",
            "积分",
        ]

        # 搜索相关关键词
        search_keywords = [
            "搜索",
            "查询",
            "检索",
            "查找",
            "数据库",
            "信息",
            "资料",
            "文献",
            "调研",
            "研究",
            "探索",
            "发现",
        ]

        # 计数各类关键词出现次数
        code_count = sum(1 for keyword in code_keywords if keyword in text)
        math_count = sum(1 for keyword in math_keywords if keyword in text)
        search_count = sum(1 for keyword in search_keywords if keyword in text)

        # 根据关键词出现频率确定任务类型
        if code_count > math_count and code_count > search_count:
            logger.info(f"检测到代码相关关键词 {code_count} 个")
            return "代码处理"
        elif math_count > code_count and math_count > search_count:
            logger.info(f"检测到数学相关关键词 {math_count} 个")
            return "数学问题"
        elif search_count > code_count and search_count > math_count:
            logger.info(f"检测到搜索相关关键词 {search_count} 个")
            return "网络搜索"
        else:
            logger.info("未明确检测到专业任务类型，使用通用任务处理")
            return "通用任务"


def parse_args():
    parser = argparse.ArgumentParser(description="SenseYourVoice - 语音理解与处理应用")
    parser.add_argument("--audio", type=str, required=True, help="音频文件路径")
    parser.add_argument("--instruction", type=str, default="", help="处理指令")
    parser.add_argument(
        "--model_dir", type=str, default="iic/SenseVoiceSmall", help="语音模型目录"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="设备",
    )
    parser.add_argument("--understanding_api_key", type=str, help="理解模块API密钥")
    parser.add_argument("--understanding_api_url", type=str, help="理解模块API地址")
    parser.add_argument("--specialized_api_key", type=str, help="专业任务模块API密钥")
    parser.add_argument("--specialized_api_url", type=str, help="专业任务模块API地址")
    return parser.parse_args()


def main():
    args = parse_args()

    config = {
        "model_dir": args.model_dir,
        "device": args.device,
        "understanding_api_key": args.understanding_api_key,
        "understanding_api_url": args.understanding_api_url,
        "specialized_api_key": args.specialized_api_key,
        "specialized_api_url": args.specialized_api_url,
    }

    app = SenseYourVoiceApp(config)
    result = app.process(args.audio, args.instruction)

    if result["success"]:
        print("\n===== 处理结果 =====")
        print(f"\n语音转文字结果:\n{result['transcription']}")
        print(f"\n理解分析结果:\n{result['understanding']}")
        if "specialized_result" in result:
            print(f"\n专业任务处理结果:\n{result['specialized_result']}")
    else:
        print(f"\n处理失败: {result['error']}")


if __name__ == "__main__":
    main()
