import base64
import gzip
import io
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import time
import uuid
import wave
from io import BytesIO
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import numpy as np
import requests
from loguru import logger
from PIL import Image

DROPDOWN_CHOICES = {
    "bgm_genres": list(
        set(
            [
                "独立民谣：吉他驱动",
                "当代古典音乐：钢琴驱动",
                "现代流行抒情曲：钢琴驱动的",
                "乡村音乐",
                "流行乐",
                "流行摇滚",
                "电子舞曲",
                "雷鬼顿",
                "迪斯科",
            ]
        )
    ),
    "swb_genres": list(set(["流行摇滚", "迪斯科", "电子舞曲"])),
    "bgm_moods": list(
        set(
            [
                "鼓舞人心/充满希望",
                "壮丽宏大",
                "快乐",
                "平静放松",
                "自信/坚定",
                "轻快无忧无虑",
                "活力四射/精力充沛",
                "悲伤哀愁",
                "温暖/友善",
                "兴奋",
            ]
        )
    ),
    "swb_moods": list(set(["快乐", "兴奋", "活力四射"])),
    "bgm_instruments": list(
        set(["低音鼓", "电吉他", "合成拨弦", "合成铜管乐器", "架子鼓", "定音鼓"])
    ),
    "swb_instruments": list(set(["电吉他", "合成铜管乐器", "架子鼓"])),
    "bgm_themes": list(
        set(
            [
                "励志",
                "生日",
                "分手",
                "旅行",
                "运动",
                "剧院音乐厅",
                "音乐现场",
                "节日",
                "好时光",
                "庆典与喜悦",
            ]
        )
    ),
    "swb_themes": list(set(["生日", "旅行", "运动"])),
    "dialects": list(set(["四川话", "广粤话"])),
    "emotions": list(set(["中性", "高兴", "惊讶", "愤怒", "悲伤", "厌恶", "恐惧"])),
    "env_sounds": [],  # 原 Demo 未使用
}

IP_LINES_DICT = {
    "何幸福": "凡事都要讲个理，我就想跟他们讲讲理！",
    "朱元璋": "咱告诉你，从今往后，中书省，废了！丞相，废了！",
    "朱标": "父皇，治国之道，当以仁爱为本，刑罚为辅。",
    "朱棣": "我朱棣，奉天靖难，入主金陵，此乃天命所归！",
    "潘金莲": "大郎，起来把这碗药喝了。",
    "公孙胜": "贫道乃云游之人，特来相助替天行道。",
    "齐铁嘴": "哎哟我的佛爷啊，此事非同小可，咱们可得从长计议啊！",
    "爱新觉罗·弘时": "皇阿玛，儿臣以为，八叔他们并无大错。",
    "邬思道": "四爷，这太子之位，争，还是不争，皆在一念之间。",
    "孝庄": "我告诉你，就是把它烧成灰，你也要给我吞下去！",
    "吴三桂": "大丈夫不可一日无权，人生不可一日无钱！",
    "司徒末": "顾未易，你是不是喜欢我啊？",
    "宋慈": "人命大如天，我等提刑官，须得明察秋毫，洗冤泽物。",
    "刁光斗": "在这官场之上，能屈能伸，方为大丈夫。",
    "萧崇": "这天启城，终究还是姓萧的。",
    "余则成": "有一种胜利，叫撤退；有一种失败，叫占领。",
    "左蓝": "你能保证，你刚才说的话，都是真的吗？",
    "曹操": "宁教我负天下人，休教天下人负我！",
    "四郎": "逆风如解意，容易莫摧残。",
    "李蔷": "作为一名法医，我的职责是让逝者开口说话。",
    "陆建勋": "我陆建勋，要的就是这长沙城，谁也别想挡我的路！",
    "野原美伢 (美伢)": "小新！你又在搞什么鬼！你这个孩子真是的！",
    "荣妃": "皇上，难道您就真的这么狠心，一点旧情都不念了吗？",
    "青年康熙": "朕现在是越来越看清你们这群所谓的大臣了！",
    "许半夏": "我就不信了，这天底下还有我们办不成的事！",
    "朱颜": "我此生，只为守护空桑，守护你。",
    "王翠平": "你这鸡脑袋里想什么呢？这点事都搞不明白！",
    "李涯": "为了党国，我什么都可以做，包括我自己的命！",
    "穆晚秋": "则成，我什么都不要，我只要跟你在一起。",
    "陆桥山": "马奎啊马奎，你太让我失望了。",
    "徐文昌": "房子是用来住的，不是用来炒的。",
    "关涛": "何幸福，你这种较真的精神，我很欣赏。",
    "铁铉": "我铁铉就算死，也绝不向燕贼投降！",
    "苏培盛": "皇上，熹贵妃娘娘她，是真心待您的。",
    "武松": "我武松，顶天立地，岂能受这般屈辱！",
    "秦明": "每一具尸体，都有他自己的故事。",
    "裘德考": "这些秘密，必须由我来揭开！",
    "张启山": "我张启山，一定要守护好这九门，守护好长沙！",
    "爱新觉罗·弘历": "皇阿玛，儿臣以为，当以宽仁治天下。",
    "年羹尧": "我年羹尧戎马一生，难道还怕这区区几句谗言吗？",
    "雍正": "朕就是这样的汉子！就是这样的秉性！就是这样的皇帝！",
    "野原新之助 (小新)": "大姐姐，你喜欢吃青椒吗？",
    "潘越": "在这儿，我说了算。",
    "关雪": "宋卓文，你最好别在我面前耍花样。",
    "佩奇": "我是佩奇，这是我的弟弟乔治。",
    "康熙": "朕宣布，削三藩！朕要让天下看看，到底谁才是这大清的皇帝！",
    "苏麻喇姑": "格格，您要保重凤体啊。",
    "郭启东": "商场如战场，没有永远的朋友，只有永远的利益。",
    "卢怀德": "来人，给我把这个刁民拖出去！",
    "丰兰息": "这天下，我要九十九。",
    "灰太狼": "我一定会回来的！",
    "唐僧": "悟空，休得无礼！",
    "郭德纲": "走着走着，哎，前边儿出一问号儿，后边儿出一感叹号儿。",
    "于谦": "您这说的，我可就不挨着了啊。",
    "孙颖莎": "就是一分一分去打，不管领先还是落后，都要去拼每一分球。",
}


# ============================================================
# 1. 生图功能的专属辅助类 (移植自源文件)
# ============================================================
class MLLMsResponseBase:
    def __init__(self, mllm_name, call_address, sk=None):
        self.mllm_name = mllm_name
        self.sk = sk if sk is not None else os.environ.get("API_SK", None)
        if self.sk is None:
            raise ValueError("API_SK is not set")
        self.call_adress = call_address
        container_info = self.get_container_info()
        self.headers = {
            "X-TraceInfo": container_info,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.sk}",
        }

    def get_container_info(self):
        workflow_id = os.environ.get("WORKFLOW_ID", "N/A")
        username = os.environ.get("USER_NAME", "N/A")
        usernumber = os.environ.get("USERNUMBER", "N/A")
        return f"{username}_{usernumber}_{workflow_id}"

    def get_response(self, params, retry=5, sleep_time=0.5):
        if "model" not in params:
            params["model"] = self.mllm_name
        for _ in range(retry):
            try:
                response = requests.post(self.call_adress, headers=self.headers, json=params)
                if response.status_code == 200:
                    return response
                logger.error(f"{self.mllm_name} response error code: {response.status_code}")
                if sleep_time > 0:
                    time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"error: {str(e)}")
                if sleep_time > 0:
                    time.sleep(sleep_time)
        return ""


class ImageText2ImageTextResponse(MLLMsResponseBase):
    def __init__(self, mllm_name, env, sk=None):
        self.mllm_name = mllm_name
        if self.mllm_name not in ["gemini-2.5-flash-image-preview", "gemini-2.5-flash-image"]:
            raise ValueError(f"mllm name {self.mllm_name} not supported")
        if env == "office":
            self.call_address = "https://matrixcube.alipay.com/v1/genericCall"
        elif env == "prod":
            self.call_address = "matrixcube-pool.global.alipay.com"
        else:
            raise ValueError(f"env {env} not in [office, prod]")
        super().__init__(self.mllm_name, self.call_address, sk)

    def get_text2image_response(self, prompt, retry=5, sleep_time=0.5):
        data = {
            "model": self.mllm_name,
            "method": f"/{self.mllm_name}:generateContent",
            "contents": {"role": "USER", "parts": [{"text": prompt}]},
            "generation_config": {"response_modalities": ["TEXT", "IMAGE"]},
        }
        response = self.get_response(data, retry, sleep_time)
        if not response:
            logger.warning(f"[生图失败] API请求失败。Prompt: {prompt[:50]}...")
            return ""
        try:
            resp_json = response.json()
            if "candidates" not in resp_json or not resp_json["candidates"]:
                logger.warning(
                    f"[生图失败] 响应中无candidates。响应: {json.dumps(resp_json, ensure_ascii=False)[:500]}"
                )
                return ""
            content = resp_json["candidates"][0]["content"]
            text, image = "", None
            for part in content["parts"]:
                if "text" in part:
                    text = part["text"].strip()
                if "inlineData" in part:
                    image = Image.open(BytesIO(base64.b64decode(part["inlineData"]["data"])))
            if image is None:
                logger.warning(f"[生图失败] 未生成图片。文本: {text[:200] if text else '(空)'}")
                return ""
            return (text, image)
        except Exception as e:
            logger.error(f"[生图失败] 未知异常: {e}。响应: {response.text[:500]}")
            return ""


# ============================================================
# 2. 综合播客生成器主类
# ============================================================
class CompositePodcastGenerator:
    def __init__(self, webgw_url, api_key, api_project, app_id, mllm_config, ip_dict):
        # 统一使用主框架的WebGW配置
        self.webgw_url = webgw_url
        self.api_key = api_key
        self.api_project = api_project
        self.app_id = app_id

        # 独立的功能配置
        self.mllm_config = mllm_config
        self.ip_dict = ip_dict
        self.ip_lines_dict = self._get_ip_lines()
        self.bgm_params_list = self._get_bgm_params()

    def _file_to_b64(self, filepath: Optional[str]) -> Optional[str]:
        if not filepath or not os.path.exists(filepath):
            return None
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _b64_to_file(
        self, b64_string: Optional[str], output_dir: str = "temp_audio"
    ) -> Optional[str]:
        if not b64_string:
            return None
        os.makedirs(output_dir, exist_ok=True)
        audio_bytes = base64.b64decode(b64_string)
        filepath = os.path.join(output_dir, f"{uuid.uuid4()}.wav")
        with open(filepath, "wb") as f:
            f.write(audio_bytes)
        return filepath

    def _get_ip_lines(self):
        return IP_LINES_DICT

    def _get_bgm_params(self):
        return [
            {
                "genre": random.choice(DROPDOWN_CHOICES["bgm_genres"]),
                "mood": random.choice(DROPDOWN_CHOICES["bgm_moods"]),
                "instrument": random.choice(DROPDOWN_CHOICES["bgm_instruments"]),
                "theme": random.choice(DROPDOWN_CHOICES["bgm_themes"]),
            }
        ]

    def _concat_wav_files(self, wav_files: List[str], output_path: str) -> str:
        """使用标准库 wave 模块拼接多个 WAV 文件"""
        if not wav_files:
            raise ValueError("wav_files 列表为空")

        with wave.open(wav_files[0], "rb") as first:
            params = first.getparams()

        with wave.open(output_path, "wb") as output:
            output.setparams(params)
            for filepath in wav_files:
                with wave.open(filepath, "rb") as wf:
                    # 校验格式一致性
                    if (
                        wf.getnchannels() != params.nchannels
                        or wf.getframerate() != params.framerate
                        or wf.getsampwidth() != params.sampwidth
                    ):
                        logger.warning(
                            f"[WAV拼接] 文件 {filepath} 的音频参数与第一个文件不一致，"
                            f"尝试继续拼接但可能产生异常音频。"
                        )
                    output.writeframes(wf.readframes(wf.getnframes()))

        logger.info(f"[WAV拼接] 成功拼接 {len(wav_files)} 个文件到: {output_path}")
        return output_path

    def _mix_audio_with_bgm(
        self, speech_path: str, bgm_path: str, output_path: str, bgm_volume: float
    ) -> str:
        """
        使用 numpy 将语音和背景音乐混合。
        bgm_volume: BGM 的音量系数 (0~1)，由 10**(-snr/20) 计算得到。
        输出与语音等长的混音 WAV 文件。
        """
        # 读取语音
        with wave.open(speech_path, "rb") as wf:
            speech_params = wf.getparams()
            speech_frames = wf.readframes(wf.getnframes())

        # 读取 BGM
        with wave.open(bgm_path, "rb") as wf:
            bgm_params = wf.getparams()
            bgm_frames = wf.readframes(wf.getnframes())

        # 转换为 numpy 数组
        dtype = np.int16 if speech_params.sampwidth == 2 else np.int32
        speech_data = np.frombuffer(speech_frames, dtype=dtype).astype(np.float64)
        bgm_data = np.frombuffer(bgm_frames, dtype=dtype).astype(np.float64)

        # 处理声道数不同的情况：统一为与语音相同的声道数
        speech_channels = speech_params.nchannels
        bgm_channels = bgm_params.nchannels
        if bgm_channels != speech_channels:
            if bgm_channels == 2 and speech_channels == 1:
                # 立体声转单声道：取平均
                bgm_data = bgm_data.reshape(-1, 2).mean(axis=1)
            elif bgm_channels == 1 and speech_channels == 2:
                # 单声道转立体声：复制
                bgm_data = np.repeat(bgm_data, 2)

        # 截断或填充 BGM 使其与语音等长
        speech_len = len(speech_data)
        if len(bgm_data) >= speech_len:
            bgm_data = bgm_data[:speech_len]
        else:
            # BGM 比语音短，循环填充
            repeats = (speech_len // len(bgm_data)) + 1
            bgm_data = np.tile(bgm_data, repeats)[:speech_len]

        # 混合
        mixed = speech_data + bgm_data * bgm_volume

        # 裁剪防止溢出
        if dtype == np.int16:
            mixed = np.clip(mixed, -32768, 32767)
        else:
            mixed = np.clip(mixed, -2147483648, 2147483647)

        mixed = mixed.astype(dtype)

        # 写出
        with wave.open(output_path, "wb") as wf:
            wf.setparams(speech_params)
            wf.writeframes(mixed.tobytes())

        logger.info(f"[混音] 成功混合语音和BGM，保存至: {output_path}")
        return output_path

    def _sync_call_service(self, payload: Dict, task_name: str, output_dir: str) -> str:
        """
        同步调用WebGW服务
        """
        # 1. 提交任务
        submit_body = {
            "api_key": self.api_key,
            "api_project": self.api_project,
            "call_name": "submit_task",
            "call_token": str(uuid.uuid4()),
            "call_args": payload,
        }
        headers = {
            "Content-Type": "application/json",
            "x-webgw-appid": self.app_id,
            "x-webgw-version": "2.0",
        }

        r = requests.post(self.webgw_url, json=submit_body, headers=headers, timeout=30)
        r.raise_for_status()
        res = r.json()
        if not res.get("success"):
            raise ConnectionError(f"WebGW 任务提交失败: {res.get('errorMessage', '未知错误')}")

        result_str = res.get("resultObj", {}).get("result", "{}")
        if isinstance(result_str, str):
            inner_result = json.loads(result_str)
        else:
            inner_result = result_str
        task_id = inner_result.get("task_id")
        if not task_id:
            raise ValueError(f"[{task_name}] 未能从响应中获取 task_id: {inner_result}")
        logger.info(f"[{task_name}] 任务提交成功, Task ID: {task_id}")

        # 2. 轮询等待
        start_time, timeout = time.time(), 600
        while time.time() - start_time < timeout:
            time.sleep(5)
            poll_body = {
                "api_key": self.api_key,
                "api_project": self.api_project,
                "call_name": "poll_task",
                "call_token": str(uuid.uuid4()),
                "call_args": {"task_id": task_id},
            }
            try:
                r_poll = requests.post(self.webgw_url, json=poll_body, headers=headers, timeout=30)
                if r_poll.status_code == 200:
                    poll_res = r_poll.json()
                    if poll_res.get("success"):
                        poll_data_str = poll_res.get("resultObj", {}).get("result", "{}")
                        if isinstance(poll_data_str, str):
                            poll_data = json.loads(poll_data_str)
                        else:
                            poll_data = poll_data_str
                        status = poll_data.get("status")
                        if status == "completed" or status == "success":
                            audio_url = poll_data.get("output_audio_url")
                            if not audio_url:
                                raise ValueError("任务完成但未返回音频URL")

                            # --- 完整下载逻辑开始 ---
                            try:
                                # a. 解析URL，为代理下载做准备
                                parsed_url = urlparse(audio_url)
                                query_params = parse_qs(parsed_url.query)
                                proxy_args = {
                                    "filename": os.path.basename(parsed_url.path),
                                    "oss_access_key_id": query_params.get("OSSAccessKeyId", [None])[
                                        0
                                    ],
                                    "expires": query_params.get("Expires", [None])[0],
                                    "signature": query_params.get("Signature", [None])[0],
                                }

                                # b. 通过WebGW代理下载音频
                                proxy_payload = {
                                    "api_key": self.api_key,
                                    "api_project": self.api_project,
                                    "call_name": "get_audio",
                                    "call_token": str(uuid.uuid4()),
                                    "call_args": proxy_args,
                                }
                                audio_resp = requests.post(
                                    self.webgw_url, json=proxy_payload, headers=headers, timeout=60
                                )
                                audio_resp.raise_for_status()
                                res_json = audio_resp.json()
                                if not res_json.get("success"):
                                    raise RuntimeError(
                                        f"代理下载失败: {res_json.get('errorMessage', '未知')}"
                                    )

                                # c. 解析Gzip+Base64响应
                                result_obj = res_json.get("resultObj", {})
                                inner_result = result_obj.get("result", {})
                                if isinstance(inner_result, str):
                                    inner_result = json.loads(inner_result)

                                if "gzippedRaw" not in inner_result:
                                    raise ValueError("代理响应中缺少 'gzippedRaw' 字段")

                                gzipped_b64 = inner_result["gzippedRaw"]
                                compressed_data = base64.b64decode(gzipped_b64)

                                # d. 解压Gzip数据
                                with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as f_gz:
                                    content = f_gz.read()

                                # e. 保存文件
                                output_path = os.path.join(
                                    output_dir, f"{task_name}-{uuid.uuid4()}.wav"
                                )
                                with open(output_path, "wb") as f_out:
                                    f_out.write(content)

                                logger.info(
                                    f"[{task_name}] 音频下载并解压成功，保存至: {output_path}"
                                )
                                return output_path
                            except Exception as e:
                                logger.error(f"音频下载或处理失败: {e}")
                                raise RuntimeError(f"音频下载失败: {e}")
                            # --- 完整下载逻辑结束 ---

                        elif status == "failed":
                            raise RuntimeError(
                                f"任务执行失败: {poll_data.get('error_message', '未知错误')}"
                            )
            except Exception as e:
                logger.warning(f"轮询请求时发生异常，将继续重试: {e}")
        raise TimeoutError(f"任务 {task_id} 轮询超时({timeout}秒)。")

    # --- 其他辅助函数保持不变 ---
    def _generate_cover_image(self, script_text: str, output_dir: str) -> str:
        prompt = (
            f"根据下面的播客对话台本的主题和内容，生成一张合适的图片作为播客的封面。"
            f"要求：风格简洁大方，色彩和谐，适合作为音频播客的封面配图。不要在图片中包含任何文字。"
            f"\n\n台本内容：\n{script_text}"
        )
        mllm_model = ImageText2ImageTextResponse(**self.mllm_config)
        response = mllm_model.get_text2image_response(prompt, retry=3)
        if not response:
            raise RuntimeError("生图模型调用失败。")
        _, image = response
        os.makedirs(output_dir, exist_ok=True)
        image_path = os.path.join(output_dir, f"cover_{uuid.uuid4()}.png")
        image.save(image_path)
        return image_path

    def _combine_video(self, image_path: str, audio_path: str, output_dir: str) -> str:
        video_path = os.path.join(output_dir, f"podcast_video_{uuid.uuid4()}.mp4")
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            image_path,
            "-i",
            audio_path,
            "-c:v",
            "libopenh264",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"视频合成失败: {result.stderr}")
        return video_path

    def _normalize_script(self, text: str) -> str:
        if not text or not text.strip():
            return ""

        lines = text.split("\n")
        normalized_lines = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            # 统一中文冒号为英文冒号
            stripped = stripped.replace("：", ":")
            match = re.match(r"^[Ss]peaker\s*[_\s]\s*(\d+)\s*:\s*(.*)", stripped)

            if match:
                speaker_num = match.group(1)
                content = match.group(2).strip()
                # 组装为标准格式：" speaker_X:文本内容\n"
                normalized_lines.append(f" speaker_{speaker_num}:{content}")
            else:
                # 非 speaker 行，可能是用户写的旁白或格式异常
                # 保留原内容但加上标准缩进，方便排查
                logger.warning(f"[台本格式化] 无法解析的行，原样保留: '{stripped}'")
                normalized_lines.append(f" {stripped}")

        # 每行以 \n 结尾，最后一行也要有
        result = "\n".join(normalized_lines) + "\n"

        logger.info(
            f"[台本格式化] 原始行数: {len(lines)}, "
            f"有效行数: {len(normalized_lines)}, "
            f"格式化后前100字: {result[:100]!r}"
        )

        return result

    def _split_chunks(self, text: str, max_chars: int = 280) -> List[str]:
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

        if not lines:
            return []
        if not lines[0].startswith("speaker_1"):
            raise ValueError("文本必须以'speaker_1'的发言开始。")

        # 步骤 1: 将连续的行按“轮次”分组
        # 每一轮都由一个 'speaker_1' 的发言和其后所有 'speaker_2' 的连续发言构成
        turns = []
        current_turn = []
        for line in lines:
            if line.startswith("speaker_1"):
                if current_turn:
                    turns.append("\n".join(current_turn))
                current_turn = [line]
            else:
                current_turn.append(line)
        if current_turn:
            turns.append("\n".join(current_turn))

        # 步骤 2: 将轮次组合成不超过最大字符数的文本块
        chunks = []
        current_chunk_lines = []
        for turn in turns:
            # 如果当前块不为空，并且加入新一轮会超长，则将当前块保存
            if (
                current_chunk_lines
                and (len("\n".join(current_chunk_lines)) + len(turn) + 1) > max_chars
            ):
                chunks.append("\n".join(current_chunk_lines))
                # 用当前轮次开始一个新的块
                current_chunk_lines = turn.split("\n")
            else:
                # 否则，将当前轮次添加到当前块中
                current_chunk_lines.extend(turn.split("\n"))

        # 步骤 3: 添加最后一个未满的文本块
        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        logger.info(f"文本已被切分为 {len(chunks)} 个块，并确保了对话的完整性和起始规则。")
        return chunks

    def _get_duration(self, file_path: str) -> float:
        with wave.open(file_path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())

    def generate(
        self,
        text,
        spk1_choice,
        spk1_ip,
        spk1_audio,
        spk2_choice,
        spk2_ip,
        spk2_audio,
        add_bgm,
        bgm_snr,
        generate_video,
    ):
        """
        核心生成逻辑，这是一个阻塞函数，由Gradio的后台线程调用。
        """
        logger.info("=" * 20 + " 开始执行综合播客生成任务 " + "=" * 20)
        try:
            if not text or not text.strip().startswith("speaker_1"):
                raise ValueError("播客台本不能为空或格式错误。")
            text = self._normalize_script(text)
            persistent_dir = "temp_audio"
            os.makedirs(persistent_dir, exist_ok=True)

            with tempfile.TemporaryDirectory() as temp_dir:
                # 步骤1 & 2: 准备说话人音色
                prompt_b64s = [None, None]
                choices = [
                    (spk1_choice, spk1_ip, spk1_audio, 1),
                    (spk2_choice, spk2_ip, spk2_audio, 2),
                ]
                for choice, ip_name, audio_file, spk_num in choices:
                    if choice == "IP音色":
                        if not ip_name:
                            raise ValueError(f"请为说话人{spk_num}选择一个IP角色。")
                        payload = {
                            "task_type": "TTS",
                            "instruct_type": "IP",
                            "text": self.ip_lines_dict[ip_name],
                            "caption": json.dumps(
                                {"audio_sequence": [{"IP": self.ip_dict[ip_name]}]}
                            ),
                        }
                        ip_audio_path = self._sync_call_service(
                            payload, f"ip-gen-spk{spk_num}", temp_dir
                        )
                        prompt_b64s[spk_num - 1] = self._file_to_b64(ip_audio_path)
                    else:
                        if not audio_file:
                            raise ValueError(f"请为说话人{spk_num}提供参考音频。")
                        prompt_b64s[spk_num - 1] = self._file_to_b64(audio_file)

                # 步骤3 & 4: 分片生成并拼接音频
                chunks = self._split_chunks(text)
                chunk_files = [
                    self._sync_call_service(
                        {"task_type": "podcast", "text": chunk, "prompt_wavs_b64": prompt_b64s},
                        f"podcast-chunk-{i}",
                        temp_dir,
                    )
                    for i, chunk in enumerate(chunks)
                ]
                concat_path = os.path.join(temp_dir, "concatenated.wav")
                if len(chunk_files) > 1:
                    self._concat_wav_files(chunk_files, concat_path)
                else:
                    shutil.copy2(chunk_files[0], concat_path)
                final_audio_path = concat_path

                # 步骤5: 可选BGM
                if add_bgm:
                    duration = self._get_duration(concat_path)
                    bgm_params = random.choice(self.bgm_params_list)
                    bgm_prompt = f"Genre: {bgm_params['genre']}. Mood: {bgm_params['mood']}. Instrument: {bgm_params['instrument']}. Theme: {bgm_params['theme']}. Duration: {int(duration) + 2}s."
                    bgm_path = self._sync_call_service(
                        {"task_type": "bgm", "prompt_text": bgm_prompt}, "bgm-gen", temp_dir
                    )
                    mixed_path = os.path.join(temp_dir, "mixed.wav")
                    volume = 10 ** (-bgm_snr / 20)
                    self._mix_audio_with_bgm(concat_path, bgm_path, mixed_path, volume)
                    final_audio_path = mixed_path

                # 步骤6 & 7: 复制结果并可选生成视频
                final_persistent_path = None
                video_path = None
                if generate_video:
                    try:
                        cover_path = self._generate_cover_image(text, temp_dir)
                        video_path = self._combine_video(
                            cover_path,
                            final_audio_path,
                            temp_dir,
                        )

                    except Exception as e:
                        logger.warning(f"视频生成失败，将仅返回音频: {e}")

                final_persistent_video = None
                if video_path:
                    final_persistent_video = os.path.join(
                        persistent_dir, f"podcast_video_{uuid.uuid4()}.mp4"
                    )
                    shutil.copy2(video_path, final_persistent_video)
                else:
                    final_persistent_path = os.path.join(
                        persistent_dir, f"podcast_{uuid.uuid4()}.wav"
                    )
                    shutil.copy2(final_audio_path, final_persistent_path)

                logger.info("=" * 20 + " 综合播客生成任务成功 " + "=" * 20)
                return "✅ 成功！", final_persistent_path, final_persistent_video
        except Exception as e:
            logger.error("综合播客任务失败！", exc_info=True)
            raise e
