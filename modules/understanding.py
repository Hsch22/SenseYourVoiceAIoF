# -*- encoding: utf-8 -*-

import requests
import logging
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('UnderstandingModule')

class UnderstandingModule:
    def __init__(self, api_key=None, api_url=None, model="gpt-3.5-turbo"):
        """理解与分析模块，可以连接到外部LLM API"""
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        logger.info("理解模块初始化完成")

    def analyze(self, text, context="", llm_params=None):
        """分析文本内容并返回结果流，支持多轮对话和自定义LLM参数"""
        try:
            if not self.api_url or not self.api_key:
                logger.warning("未配置API，返回模拟响应流")
                yield {
                    "success": True,
                    "response_chunk": f"模拟分析结果: 已收到文本，长度为{len(text)}字符。请配置真实的LLM API以获取实际分析结果。",
                    "needs_specialized_task": False,
                    "is_final": True
                }
                return

            system_prompt = "你是一个专业的语音内容分析助手。你的任务是分析用户提供的语音转文字内容，并根据用户的指令提供相应的分析结果。请保持对话的连贯性，参考之前的对话历史进行回复。"
            messages = [{"role": "system", "content": system_prompt}]

            if context:
                logger.info("添加对话历史上下文")
                messages.append({"role": "user", "content": f"以下是之前的对话历史:\n{context}"})
                messages.append({"role": "assistant", "content": "我已了解之前的对话内容，请继续。"})

            messages.append({"role": "user", "content": text})

            logger.info(f"准备调用API分析文本，文本长度: {len(text)}字符")
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "Accept": "text/event-stream"}
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True  # 启用流式输出
            }

            if llm_params:
                valid_llm_params = {k: v for k, v in llm_params.items() if v is not None}
                if 'stop' in valid_llm_params and not valid_llm_params['stop']:
                    del valid_llm_params['stop']
                payload.update(valid_llm_params)
                logger.info(f"使用自定义LLM参数: {valid_llm_params}")
            else:
                 payload["temperature"] = 0.7
                 logger.info("使用默认LLM参数")

            logger.debug(f"API请求: {json.dumps(payload, ensure_ascii=False)}")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30, stream=True) # 设置 stream=True

            if response.status_code == 200:
                logger.info("API调用成功，开始接收流式响应")
                full_response_text = ""
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
                                full_response_text += content_chunk
                                yield {
                                    "success": True,
                                    "response_chunk": content_chunk,
                                    "needs_specialized_task": False, 
                                    "is_final": False
                                }
                        except json.JSONDecodeError as e:
                            logger.error(f"无法解析流式块: {chunk_str}, 错误: {e}")
                        except Exception as e:
                            logger.error(f"处理流式块时出错: {chunk_str}, 错误: {e}")

                # 流结束后，进行最终判断
                needs_specialized = self._check_if_needs_specialized_task(full_response_text)
                if needs_specialized:
                    logger.info("检测到需要专业任务处理")

                yield {
                    "success": True,
                    "response_chunk": None, # 标记流结束
                    "needs_specialized_task": needs_specialized,
                    "is_final": True,
                    "full_response": full_response_text 
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
            error_msg = f"分析过程发生错误: {str(e)}"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}

    def _check_if_needs_specialized_task(self, response):
        """检查是否需要专业任务处理"""
        keywords = [
            "代码", "编程", "程序", "算法", "函数", "变量", "类", "对象",
            "数学问题", "计算", "方程", "公式", "数值", "统计",
            "搜索", "查询", "检索", "查找", "数据库",
            "专业分析", "深度解析", "技术细节"
        ]
        for keyword in keywords:
            if keyword in response:
                logger.debug(f"检测到专业任务关键词: {keyword}")
                return True
        return False