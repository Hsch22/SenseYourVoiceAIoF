# -*- encoding: utf-8 -*-

import requests
import logging
import json
import time

# 设置日志
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SpecializedTaskModule')

# --- 重试配置 ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
# --- 重试配置结束 ---


class SpecializedTaskModule:
    def __init__(self, api_key, api_url, model):
        """专业任务处理模块，用于处理代码、数学问题等"""
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.task_handlers = {
            "代码处理": self._handle_code_task,
            "数学问题": self._handle_math_task,
            "网络搜索": self._handle_search_task,
            "通用任务": self._handle_general_task,
        }
        logger.info("专业任务模块初始化完成")

    def process_task(self, task_type, content):
        """处理特定类型的任务，返回生成器"""
        logger.info(f"开始处理专业任务，类型: {task_type}")

        if not self.api_url or not self.api_key:
            logger.warning("未配置API，返回模拟响应流")
            yield {
                "success": True,
                "result_chunk": f"模拟专业任务处理结果: 已收到{task_type}任务，内容长度为{len(content)}字符。请配置真实的专业LLM API以获取实际处理结果。",
                "is_final": True,
            }
            return

        handler = self.task_handlers.get(task_type, self._handle_general_task)
        # 使用 yield from 将生成器委托出去
        yield from handler(task_type, content)

    def _handle_code_task(self, task_type, content):
        """处理代码相关任务"""
        logger.info("处理代码任务")
        system_prompt = """嗨！我是您的编程伙伴小码 👨‍💻，很开心能帮助您解决编程问题！

我可以为您提供：
✨ 代码问题的详细分析和解释
🔧 实用的修复建议和优化方案  
🚀 高效算法的思路和实现
📚 清晰易懂的代码示例

我会用通俗易懂的语言来解释技术概念，让复杂的编程问题变得简单明了。无论您是编程新手还是经验丰富的开发者，我都会根据您的需求调整解答的深度。

温馨提示：我专注于编程相关的帮助，如果您有其他类型的问题，我会温和地提醒您，并建议您寻找更合适的帮助渠道。让我们一起在代码的世界里探索吧！ 🎯"""
        yield from self._call_api(system_prompt, content)

    def _handle_math_task(self, task_type, content):
        """处理数学相关任务"""
        logger.info("处理数学任务")
        system_prompt = """您好！我是数学小助手阿尔法 📐，非常高兴能陪您一起探索数学的奥秘！

我擅长的领域包括：
🧮 详细的数学问题解题过程
📊 清晰的公式推导和计算步骤
🎯 准确的最终答案和验证
💡 多种解法的比较和推荐

我会像一位耐心的数学老师一样，用简单明了的语言为您讲解每一个步骤，确保您不仅能得到答案，更能理解解题的思路和方法。遇到复杂问题时，我会分步骤细致解释，让数学变得生动有趣！

小贴士：我专门负责数学问题的解答，如果您有其他学科的问题，我会友善地建议您寻找相应的专业帮助。让我们一起在数学的海洋中畅游吧！ 🌟"""
        yield from self._call_api(system_prompt, content)

    def _handle_search_task(self, task_type, content):
        """处理搜索相关任务"""
        logger.info("处理搜索任务")
        system_prompt = """您好！我是信息搜索小助手小搜 🔍，很高兴成为您的知识探索伙伴！

我可以为您做的事情：
🎯 理解您的查询需求并提供相关信息
📚 基于我的知识库为您答疑解惑
💡 提供实用的信息整理和总结
🗺️ 为您指明进一步搜索的方向

需要坦诚告诉您的是，我无法直接访问互联网进行实时搜索，但我会充分利用我的知识储备为您服务。如果您需要最新资讯或实时数据，我会诚实地告知限制，并贴心地建议您通过搜索引擎获取最新信息。

我始终秉承帮助您获取准确信息的原则，如果遇到超出我能力范围的问题，我会坦率地说明，并尽力为您提供替代方案。让我们一起在知识的海洋中寻找答案吧！ 🌐"""
        yield from self._call_api(system_prompt, content)

    def _handle_general_task(self, task_type, content):
        """处理通用专业任务"""
        logger.info(f"处理通用专业任务: {task_type}")
        system_prompt = f"""您好！我是{task_type}领域的专业助手小专 🎯，很荣幸能为您提供帮助！

我的服务宗旨：
✨ 用心分析您提供的内容
🔍 提供专业、准确、详细的解答
💖 以温暖友善的方式与您交流
🚀 尽我所能帮您解决问题

我会结合专业知识和人性化的服务态度，为您提供既权威又贴心的帮助。无论问题简单还是复杂，我都会耐心细致地为您解答，力求让您满意而归。

请放心，我会专注在{task_type}领域内为您服务。如果遇到超出我专业范围的问题，我会诚实告知，并尽力为您推荐更合适的帮助渠道。让我们开始愉快的协作吧！ 🌟"""
        yield from self._call_api(system_prompt, content)

    def _call_api(self, system_prompt, content):
        """调用API处理任务，返回生成器"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                "temperature": 0.3,  # 使用较低的温度以获得更确定性的回答
                "stream": True,  # 启用流式输出
            }

            logger.debug(f"API请求: {json.dumps(payload, ensure_ascii=False)}")

            response = None
            last_exception = None
            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=60,
                        stream=True,
                    )
                    if response.status_code >= 500 and response.status_code < 600:
                        logger.warning(
                            f"Specialized API调用收到服务器错误 {response.status_code}. 尝试次数 {attempt + 1}/{MAX_RETRIES}. 将在 {RETRY_DELAY_SECONDS} 秒后重试."
                        )
                        last_exception = requests.exceptions.HTTPError(
                            f"Server Error: {response.status_code}", response=response
                        )
                        time.sleep(RETRY_DELAY_SECONDS)  # 确保 time 已导入
                        continue

                    response.raise_for_status()  # 处理 4xx 等错误
                    break  # 成功或不可重试错误
                except requests.exceptions.Timeout as e:
                    logger.warning(
                        f"Specialized API请求超时. 尝试次数 {attempt + 1}/{MAX_RETRIES}. 将在 {RETRY_DELAY_SECONDS} 秒后重试."
                    )
                    last_exception = e
                    time.sleep(RETRY_DELAY_SECONDS)
                except requests.exceptions.ConnectionError as e:
                    logger.warning(
                        f"Specialized API连接错误. 尝试次数 {attempt + 1}/{MAX_RETRIES}. 将在 {RETRY_DELAY_SECONDS} 秒后重试."
                    )
                    last_exception = e
                    time.sleep(RETRY_DELAY_SECONDS)
                except requests.exceptions.RequestException as e:
                    logger.error(f"Specialized API请求发生无法重试的错误: {e}")
                    last_exception = e
                    break

            if response is None or not response.ok:
                error_msg = f"Specialized API调用在 {MAX_RETRIES} 次尝试后失败. 最后错误: {str(last_exception)}"
                logger.error(error_msg)
                if last_exception is None:
                    last_exception = Exception("未知Specialized API错误")
                if response is not None:
                    error_msg_detail = f"Specialized API调用失败: {response.status_code} - {response.text if response.text else str(last_exception)}"
                    yield {
                        "success": False,
                        "error": error_msg_detail,
                        "is_final": True,
                    }
                else:
                    yield {"success": False, "error": error_msg, "is_final": True}
                return

            # 原有的成功处理逻辑
            logger.info("API调用成功，开始接收流式响应")
            full_result_text = ""
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8').strip()
                    if chunk_str.startswith('data: '):
                        chunk_str = chunk_str[len('data: ') :]
                    if chunk_str == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(chunk_str)
                        delta = chunk_data['choices'][0].get('delta', {})
                        content_chunk = delta.get('content', '')
                        if content_chunk:
                            full_result_text += content_chunk
                            yield {
                                "success": True,
                                "result_chunk": content_chunk,
                                "is_final": False,
                            }
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"无法解析Specialized API响应流中的JSON块: '{chunk_str[:100]}...'. 错误: {e}"
                        )
                        logger.warning(
                            f"跳过无法解析的Specialized API响应块: {chunk_str[:100]}..."
                        )
                    except KeyError as e:
                        logger.error(
                            f"Specialized API响应JSON块结构错误: '{chunk_str[:100]}...'. 缺少键: {e}"
                        )
                        logger.warning(
                            f"跳过结构错误的Specialized API响应块: {chunk_str[:100]}..."
                        )
                    except Exception as e:
                        logger.error(
                            f"处理Specialized API响应流中的块时发生未知错误: '{chunk_str[:100]}...'. 错误: {e}",
                            exc_info=True,
                        )
                        logger.warning(
                            f"跳过处理时发生未知错误的Specialized API响应块: {chunk_str[:100]}..."
                        )

            # 流结束后标记
            yield {
                "success": True,
                "result_chunk": None,  # 标记流结束
                "is_final": True,
                "full_result": full_result_text,  # 可选：返回完整结果
            }
        except requests.exceptions.Timeout:
            # 外部捕获，理论上不应触发
            error_msg = f"Specialized API请求最终超时 (外部捕获)."
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}
        except requests.exceptions.RequestException as e:
            # 外部捕获，理论上不应触发
            error_msg = f"Specialized API请求最终异常 (外部捕获): {str(e)}"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}
        except Exception as e:
            error_msg = f"专业任务处理过程发生错误: {str(e)}"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}
