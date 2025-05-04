# -*- encoding: utf-8 -*-

import requests
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SpecializedTaskModule')

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
            "通用任务": self._handle_general_task
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
                "is_final": True
            }
            return

        handler = self.task_handlers.get(task_type, self._handle_general_task)
        # 使用 yield from 将生成器委托出去
        yield from handler(task_type, content)

    def _handle_code_task(self, task_type, content):
        """处理代码相关任务"""
        logger.info("处理代码任务")
        system_prompt = """你是一个专业的编程助手。请分析用户提供的代码或编程问题，并提供详细的解释、修复建议或实现方案。
        如果是代码问题，请提供清晰的代码示例和解释。
        如果是算法问题，请提供高效的算法思路和实现。
        请确保你的回答准确、专业且易于理解。"""
        yield from self._call_api(system_prompt, content)

    def _handle_math_task(self, task_type, content):
        """处理数学相关任务"""
        logger.info("处理数学任务")
        system_prompt = """你是一个专业的数学问题解答助手。请分析用户提供的数学问题，并提供详细的解题过程和答案。
        请确保你的解题步骤清晰，公式准确，并给出最终结果。
        如果问题有多种解法，请提供最优解法并简要说明其他可能的方法。"""
        yield from self._call_api(system_prompt, content)

    def _handle_search_task(self, task_type, content):
        """处理搜索相关任务"""
        logger.info("处理搜索任务")
        system_prompt = """你是一个专业的信息检索助手。请分析用户的查询需求，并提供相关的信息和解答。
        请注意，你无法直接访问互联网进行实时搜索，但可以基于你的知识库提供相关信息。
        如果用户询问的是最新信息或需要实时数据，请告知用户你的知识有限制，并建议他们通过搜索引擎获取最新信息。"""
        yield from self._call_api(system_prompt, content)

    def _handle_general_task(self, task_type, content):
        """处理通用专业任务"""
        logger.info(f"处理通用专业任务: {task_type}")
        system_prompt = f"你是一个专业的{task_type}处理助手。请分析用户提供的内容，并提供专业、准确、详细的解答。"
        yield from self._call_api(system_prompt, content)

    def _call_api(self, system_prompt, content):
        """调用API处理任务，返回生成器"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Accept": "text/event-stream"}
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                "temperature": 0.3, # 使用较低的温度以获得更确定性的回答
                "stream": True # 启用流式输出
            }

            logger.debug(f"API请求: {json.dumps(payload, ensure_ascii=False)}")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60, stream=True) # 设置 stream=True

            if response.status_code == 200:
                logger.info("API调用成功，开始接收流式响应")
                full_result_text = ""
                for chunk in response.iter_lines():
                    if chunk:
                        chunk_str = chunk.decode('utf-8').strip()
                        if chunk_str.startswith('data: '):
                            chunk_str = chunk_str[len('data: '):]
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
                                    "is_final": False
                                }
                        except json.JSONDecodeError as e:
                            logger.error(f"无法解析流式块: {chunk_str}, 错误: {e}")
                        except Exception as e:
                            logger.error(f"处理流式块时出错: {chunk_str}, 错误: {e}")

                # 流结束后标记
                yield {
                    "success": True,
                    "result_chunk": None, # 标记流结束
                    "is_final": True,
                    "full_result": full_result_text # 可选：返回完整结果
                }
            else:
                error_msg = f"API调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                yield {"success": False, "error": error_msg, "is_final": True}

        except requests.exceptions.Timeout:
            error_msg = "API请求超时"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求异常: {str(e)}"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}
        except Exception as e:
            error_msg = f"专业任务处理过程发生错误: {str(e)}"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}