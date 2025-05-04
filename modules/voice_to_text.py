# -*- encoding: utf-8 -*-

import os
import sys
import torch
import logging
import numpy as np
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('VoiceToTextModule')

class VoiceToTextModule:
    def __init__(self, model_dir="iic/SenseVoiceSmall", device="cuda:0" if torch.cuda.is_available() else "cpu"):
        self.model_dir = model_dir
        self.device = device
        self.model = None
        self.init_error = None
        self.initialize_model()
        
    def initialize_model(self):
        try:
            self.model = AutoModel(
                model=self.model_dir,
                trust_remote_code=True,
                remote_code="./model.py",
                vad_model="fsmn-vad",
                vad_kwargs={"max_single_segment_time": 30000},
                device=self.device,
            )
            logger.info(f"语音转文字模块初始化成功，使用设备: {self.device}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"语音转文字模块初始化失败: {error_msg}")
            self.init_error = error_msg  # 保存错误信息
    
    emoji_dict = {
        "<|nospeech|><|Event_UNK|>": "❓",
        "<|zh|>": "",
        "<|en|>": "",
        "<|yue|>": "",
        "<|ja|>": "",
        "<|ko|>": "",
        "<|nospeech|>": "",
        "<|HAPPY|>": "😊",
        "<|SAD|>": "😔",
        "<|ANGRY|>": "😡",
        "<|NEUTRAL|>": "",
        "<|BGM|>": "🎼",
        "<|Speech|>": "",
        "<|Applause|>": "👏",
        "<|Laughter|>": "😀",
        "<|FEARFUL|>": "😰",
        "<|DISGUSTED|>": "🤢",
        "<|SURPRISED|>": "😮",
        "<|Cry|>": "😭",
        "<|EMO_UNKNOWN|>": "",
        "<|Sneeze|>": "🤧",
        "<|Breath|>": "",
        "<|Cough|>": "😷",
        "<|Sing|>": "",
        "<|Speech_Noise|>": "",
        "<|withitn|>": "",
        "<|woitn|>": "",
        "<|GBG|>": "",
        "<|Event_UNK|>": "",
    }
    
    emo_dict = {
        "<|HAPPY|>": "😊",
        "<|SAD|>": "😔",
        "<|ANGRY|>": "😡",
        "<|NEUTRAL|>": "",
        "<|FEARFUL|>": "😰",
        "<|DISGUSTED|>": "🤢",
        "<|SURPRISED|>": "😮",
    }
    
    event_dict = {
        "<|BGM|>": "🎼",
        "<|Speech|>": "",
        "<|Applause|>": "👏",
        "<|Laughter|>": "😀",
        "<|Cry|>": "😭",
        "<|Sneeze|>": "🤧",
        "<|Breath|>": "",
        "<|Cough|>": "🤧",
    }
    
    lang_dict = {
        "<|zh|>": "<|lang|>",
        "<|en|>": "<|lang|>",
        "<|yue|>": "<|lang|>",
        "<|ja|>": "<|lang|>",
        "<|ko|>": "<|lang|>",
        "<|nospeech|>": "<|lang|>",
    }
    
    emo_set = {"😊", "😔", "😡", "😰", "🤢", "😮"}
    event_set = {"🎼", "👏", "😀", "😭", "🤧", "😷"}
    
    def format_str(self, s):
        """基本格式化，替换特殊标记为表情符号"""
        for sptk in self.emoji_dict:
            s = s.replace(sptk, self.emoji_dict[sptk])
        return s
    
    def format_str_v2(self, s):
        """高级格式化，处理情感和事件标记"""
        sptk_dict = {}
        for sptk in self.emoji_dict:
            sptk_dict[sptk] = s.count(sptk)
            s = s.replace(sptk, "")
        emo = "<|NEUTRAL|>"
        for e in self.emo_dict:
            if sptk_dict[e] > sptk_dict[emo]:
                emo = e
        for e in self.event_dict:
            if sptk_dict[e] > 0:
                s = self.event_dict[e] + s
        s = s + self.emo_dict[emo]

        for emoji in self.emo_set.union(self.event_set):
            s = s.replace(" " + emoji, emoji)
            s = s.replace(emoji + " ", emoji)
        return s.strip()
    
    def format_str_v3(self, s):
        """完整格式化，处理多语言和标记"""
        def get_emo(s):
            return s[-1] if s[-1] in self.emo_set else None
        def get_event(s):
            return s[0] if s[0] in self.event_set else None

        s = s.replace("<|nospeech|><|Event_UNK|>", "❓")
        for lang in self.lang_dict:
            s = s.replace(lang, "<|lang|>")
        s_list = [self.format_str_v2(s_i).strip(" ") for s_i in s.split("<|lang|>")]
        new_s = " " + s_list[0]
        cur_ent_event = get_event(new_s)
        for i in range(1, len(s_list)):
            if len(s_list[i]) == 0:
                continue
            if get_event(s_list[i]) == cur_ent_event and get_event(s_list[i]) != None:
                s_list[i] = s_list[i][1:]
            cur_ent_event = get_event(s_list[i])
            if get_emo(s_list[i]) != None and get_emo(s_list[i]) == get_emo(new_s):
                new_s = new_s[:-1]
            new_s += s_list[i].strip().lstrip()
        new_s = new_s.replace("The.", " ")
        return new_s.strip()
    
    def transcribe(self, audio_path, language="auto"):
        """将音频转换为文本
        
        Args:
            audio_path: 音频文件路径或音频数据
            language: 语言代码，可选值："auto", "zh", "en", "yue", "ja", "ko", "nospeech"
            
        Returns:
            dict: 包含转录结果或错误信息的字典
        """
        try:
            # 检查模型是否已初始化
            if self.model is None:
                error_msg = getattr(self, 'init_error', '未知错误')
                return {"success": False, "error": f"模型未初始化: {error_msg}"}
            
            # 处理不同类型的输入，与webui.py保持一致
            if isinstance(audio_path, str):
                if not os.path.exists(audio_path):
                    return {"success": False, "error": f"音频文件不存在: {audio_path}"}
                input_data = audio_path
            elif isinstance(audio_path, tuple):
                # 处理来自麦克风的输入，格式为(采样率, 音频数据)
                fs, audio_data = audio_path
                audio_data = audio_data.astype(np.float32) / np.iinfo(np.int16).max
                if len(audio_data.shape) > 1:
                    audio_data = audio_data.mean(-1)  # 转为单声道
                if fs != 16000:
                    logger.info(f"重采样音频从 {fs}Hz 到 16000Hz")
                    try:
                        import torchaudio
                        resampler = torchaudio.transforms.Resample(fs, 16000)
                        audio_data_t = torch.from_numpy(audio_data).to(torch.float32)
                        audio_data = resampler(audio_data_t[None, :])[0, :].numpy()
                    except ImportError:
                        return {"success": False, "error": "需要安装torchaudio以支持音频重采样"}
                input_data = audio_data
            else:
                return {"success": False, "error": f"不支持的音频输入类型: {type(audio_path)}"}
                
            # 使用SenseVoice模型处理音频，与demo1.py和webui.py保持一致
            res = self.model.generate(
                input=input_data,
                cache={},
                language=language,  # "zh", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,
                merge_length_s=15,
            )
            
            if not res:
                return {"success": False, "error": "转录失败，未返回结果"}
            
            # 获取原始文本
            raw_text = res[0]["text"]
            
            # 使用rich_transcription_postprocess处理文本
            basic_text = rich_transcription_postprocess(raw_text)
            
            # 使用format_str_v3进一步格式化文本，添加表情符号和事件标记
            formatted_text = self.format_str_v3(raw_text)
            
            return {
                "success": True, 
                "text": formatted_text,
                "raw_text": raw_text,
                "basic_text": basic_text
            }
        except Exception as e:
            logger.error(f"转录过程发生错误: {str(e)}")
            return {"success": False, "error": f"转录过程发生错误: {str(e)}"}