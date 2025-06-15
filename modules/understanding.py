# -*- encoding: utf-8 -*-

import requests
import logging
import json
import time

# 设置日志
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('UnderstandingModule')

# --- 重试配置 ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
# --- 重试配置结束 ---


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
                    "is_final": True,
                }
                return

            system_prompt = """你是一个友善、耐心的语音内容分析助手！我叫小智，很高兴为您服务。✨

我的主要任务是：
🎯 仔细分析您提供的语音转文字内容
💬 根据您的问题提供贴心、详细的分析和解答
🔗 保持对话的自然连贯，就像朋友间的交流一样

我会用亲切、易懂的语言与您对话，并尽量让我的回答既专业又温暖。如果有什么不清楚的地方，请随时告诉我，我会很乐意为您详细解释！

请注意：虽然我很乐意帮助您，但我只能专注于分析语音内容相关的问题。如果您想聊其他话题，我会礼貌地引导您回到语音分析的主题上来，希望您能理解～ 🥰"""
            messages = [{"role": "system", "content": system_prompt}]

            if context:
                logger.info("添加对话历史上下文")
                messages.append(
                    {"role": "user", "content": f"以下是之前的对话历史:\n{context}"}
                )
                messages.append(
                    {
                        "role": "assistant",
                        "content": "好的，我已经了解了我们之前的对话内容，有什么新的问题需要我帮助您分析吗？😊",
                    }
                )

            messages.append({"role": "user", "content": text})

            logger.info(f"准备调用API分析文本，文本长度: {len(text)}字符")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,  # 启用流式输出
            }

            if llm_params:
                valid_llm_params = {
                    k: v for k, v in llm_params.items() if v is not None
                }
                if 'stop' in valid_llm_params and not valid_llm_params['stop']:
                    del valid_llm_params['stop']
                payload.update(valid_llm_params)
                logger.info(f"使用自定义LLM参数: {valid_llm_params}")
            else:
                payload["temperature"] = 0.7
                logger.info("使用默认LLM参数")

            logger.debug(f"API请求: {json.dumps(payload, ensure_ascii=False)}")

            response = None
            last_exception = None
            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=30,
                        stream=True,
                    )
                    # 检查是否是可重试的服务器错误
                    if response.status_code >= 500 and response.status_code < 600:
                        logger.warning(
                            f"API调用收到服务器错误 {response.status_code}. 尝试次数 {attempt + 1}/{MAX_RETRIES}. 将在 {RETRY_DELAY_SECONDS} 秒后重试."
                        )
                        last_exception = requests.exceptions.HTTPError(
                            f"Server Error: {response.status_code}", response=response
                        )
                        time.sleep(RETRY_DELAY_SECONDS)  # 导入 time 模块
                        continue  # 继续下一次尝试

                    response.raise_for_status()  # 对于4xx等客户端错误，会直接抛出异常，不会重试
                    break  # 如果成功 (2xx) 或遇到不可重试的错误 (如4xx)，则跳出循环
                except requests.exceptions.Timeout as e:
                    logger.warning(
                        f"API请求超时. 尝试次数 {attempt + 1}/{MAX_RETRIES}. 将在 {RETRY_DELAY_SECONDS} 秒后重试."
                    )
                    last_exception = e
                    time.sleep(RETRY_DELAY_SECONDS)
                except requests.exceptions.ConnectionError as e:
                    logger.warning(
                        f"API连接错误. 尝试次数 {attempt + 1}/{MAX_RETRIES}. 将在 {RETRY_DELAY_SECONDS} 秒后重试."
                    )
                    last_exception = e
                    time.sleep(RETRY_DELAY_SECONDS)
                except requests.exceptions.RequestException as e:  # 更通用的请求异常
                    logger.error(f"API请求发生无法重试的错误: {e}")
                    last_exception = e  # 记录异常，但可能不重试，除非它是HTTPError且被上面的5xx逻辑捕获
                    # 如果不是 HTTPError 导致的 5xx (由 raise_for_status 抛出其他 RequestException)，则不应无限重试
                    # 此处假设非 Timeout/ConnectionError/5xx 的 RequestException 不可重试
                    break  # 跳出循环，后续会处理 last_exception

            if (
                response is None or not response.ok
            ):  # 如果所有尝试都失败了，或者最后一次尝试失败
                error_msg = f"API调用在 {MAX_RETRIES} 次尝试后失败. 最后错误: {str(last_exception)}"
                logger.error(error_msg)
                # 确保 last_exception 不是 None，如果循环从未成功进入过 try 块的 response 部分
                if last_exception is None:
                    last_exception = Exception("未知API错误")
                # 尝试从 response 获取更多信息（如果 response 对象存在）
                if response is not None:
                    error_msg_detail = f"API调用失败: {response.status_code} - {response.text if response.text else str(last_exception)}"
                    yield {
                        "success": False,
                        "error": error_msg_detail,
                        "is_final": True,
                    }
                else:
                    yield {"success": False, "error": error_msg, "is_final": True}
                return

            # 原有的成功处理逻辑 (response.status_code == 200)
            logger.info("API调用成功，开始接收流式响应")
            full_response_text = ""
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
                            full_response_text += content_chunk
                            yield {
                                "success": True,
                                "response_chunk": content_chunk,
                                "needs_specialized_task": False,
                                "is_final": False,
                            }
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"无法解析API响应流中的JSON块: '{chunk_str[:100]}...'. 错误: {e}"
                        )  # 记录部分块内容
                        # 决定是否要因为单个块解析失败而终止整个流，或者只是跳过这个坏块
                        # 当前选择: 跳过这个损坏的块，并记录警告，而不是完全失败。
                        # 如果一个损坏的块意味着整个响应不可信，则应该 yield 一个错误并 return/break。
                        logger.warning(f"跳过无法解析的API响应块: {chunk_str[:100]}...")
                        # continue # 如果选择跳过并继续处理流中其他块
                    except (
                        KeyError
                    ) as e:  # 如果 chunk_data 结构不符合预期 (例如缺少 'choices')
                        logger.error(
                            f"API响应JSON块结构错误: '{chunk_str[:100]}...'. 缺少键: {e}"
                        )
                        logger.warning(f"跳过结构错误的API响应块: {chunk_str[:100]}...")
                        # continue
                    except Exception as e:  # 捕获其他在块处理中可能发生的未知错误
                        logger.error(
                            f"处理API响应流中的块时发生未知错误: '{chunk_str[:100]}...'. 错误: {e}",
                            exc_info=True,
                        )
                        logger.warning(
                            f"跳过处理时发生未知错误的API响应块: {chunk_str[:100]}..."
                        )
                        # continue

            # 流结束后，进行最终判断
            needs_specialized = self._check_if_needs_specialized_task(
                full_response_text
            )
            if needs_specialized:
                logger.info("检测到需要专业任务处理")

            yield {
                "success": True,
                "response_chunk": None,  # 标记流结束
                "needs_specialized_task": needs_specialized,
                "is_final": True,
                "full_response": full_response_text,
            }

        except requests.exceptions.Timeout:
            # 这个顶层 Timeout 捕获理论上不应该被触发，因为内部循环会处理
            # 但保留它作为最后防线
            error_msg = f"API请求最终超时 (外部捕获)."
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}
        except requests.exceptions.RequestException as e:
            # 同上，理论上内部处理，但保留
            error_msg = f"API请求最终异常 (外部捕获): {str(e)}"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}
        except Exception as e:
            error_msg = f"分析过程发生错误: {str(e)}"
            logger.error(error_msg)
            yield {"success": False, "error": error_msg, "is_final": True}

    def _check_if_needs_specialized_task(self, response):
        """检查是否需要专业任务处理"""
        keywords = [
            "代码",
            "编程",
            "程序",
            "算法",
            "函数",
            "变量",
            "类",
            "对象",
            "数学问题",
            "计算",
            "方程",
            "公式",
            "数值",
            "统计",
            "搜索",
            "查询",
            "检索",
            "查找",
            "数据库",
            "专业分析",
            "深度解析",
            "技术细节",
        ]
        for keyword in keywords:
            if keyword in response:
                logger.debug(f"检测到专业任务关键词: {keyword}")
                return True
        return False
