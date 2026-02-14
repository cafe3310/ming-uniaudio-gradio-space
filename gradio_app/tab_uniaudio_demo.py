import base64
import gzip
import io
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import gradio as gr
import requests
from loguru import logger
from pypinyin import Style, pinyin

# --- 静态数据 ---
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
    "emotions": list(set(["愤怒", "高兴", "悲伤"])),
    "env_sounds": [],  # 原 Demo 未使用
}

IP_DICT = {
    "爱新觉罗·弘历": "雍正王朝_爱新觉罗·弘历",
    "爱新觉罗·弘时": "雍正王朝_爱新觉罗·弘时",
    "曹操": "三国演义_曹操",
    "刁光斗": "大宋提刑官_刁光斗",
    "丰兰息": "且试天下_丰兰息",
    "公孙胜": "水浒传_公孙胜",
    "关涛": "幸福到万家_关涛",
    "关雪": "哈尔滨一九四四_关雪",
    "郭启东": "风吹半夏_郭启东",
    "何幸福": "幸福到万家_何幸福",
    "灰太狼": "喜羊羊与灰太狼_灰太狼",
    "康熙": "康熙王朝_康熙",
    "李蔷": "法医秦明_李蔷",
    "李涯": "潜伏_李涯",
    "卢怀德": "大宋提刑官_卢怀德",
    "陆建勋": "老九门_陆建勋",
    "陆桥山": "潜伏_陆桥山",
    "穆晚秋": "潜伏_穆晚秋",
    "年羹尧": "雍正王朝_年羹尧",
    "潘金莲": "水浒传_潘金莲",
    "潘越": "哈尔滨一九四四_潘越",
    "佩奇": "小猪佩奇_佩奇",
    "齐铁嘴": "老九门_齐铁嘴",
    "秦明": "法医秦明_秦明",
    "青年康熙": "康熙王朝_青年康熙",
    "裘德考": "老九门_裘德考",
    "荣妃": "康熙王朝_荣妃",
    "四郎": "甄嬛传_四郎",
    "司徒末": "致我们暖暖的小时光_司徒末",
    "宋慈": "大宋提刑官_宋慈",
    "苏麻喇姑": "康熙王朝_苏麻喇姑",
    "苏培盛": "甄嬛传_苏培盛",
    "孙颖莎": "孙颖莎_孙颖莎",
    "唐僧": "西游记_唐僧",
    "铁铉": "山河月明_铁铉",
    "王翠平": "潜伏_王翠平",
    "吴三桂": "康熙王朝_吴三桂",
    "邬思道": "雍正王朝_邬思道",
    "武松": "水浒传_武松",
    "萧崇": "少年歌行_萧崇",
    "孝庄": "康熙王朝_孝庄",
    "许半夏": "风吹半夏_许半夏",
    "徐文昌": "安家_徐文昌",
    "野原美伢 (美伢)": "蜡笔小新_野原美伢 (美伢)",
    "野原新之助 (小新)": "蜡笔小新_野原新之助 (小新)",
    "雍正": "雍正王朝_雍正",
    "余则成": "潜伏_余则成",
    "张启山": "老九门_张启山",
    "朱标": "山河月明_朱标",
    "朱棣": "山河月明_朱棣",
    "朱颜": "玉骨遥_朱颜",
    "朱元璋": "山河月明_朱元璋",
    "左蓝": "潜伏_左蓝",
}


# 辅助函数
def load_and_merge_ips(original_dict: dict, filepath: str) -> dict:
    """
    从txt文件加载新的IP，按拼音排序后，追加到原始字典末尾。
    支持两种格式: 'Key:Value' 或仅 'Value' (此时Key和Value相同)。

    :param original_dict: 原始的IP_DICT。
    :param filepath: 包含新IP的txt文件路径。
    :return: 一个合并后的新字典。
    """
    new_ips = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 忽略空行或注释行
                if not line or line.startswith("#"):
                    continue

                # 判断行中是否包含冒号来决定解析方式
                if ":" in line:
                    # 格式为 'Key:Value'
                    try:
                        key, value = line.split(":", 1)
                        new_ips[key.strip()] = value.strip()
                    except ValueError:
                        logger.warning(f"无法解析行: {line}，格式应为 'Key:Value'")
                else:
                    # 格式仅为 'Value'，此时key和value相同
                    key = value = line
                    new_ips[key] = value

    # 仅对从文件读取的新IP按拼音进行排序
    sorted_new_ips = dict(
        sorted(new_ips.items(), key=lambda item: pinyin(item[0], style=Style.NORMAL))
    )

    # 合并字典：将排序后的新IP追加到原始字典后面
    merged_dict = original_dict.copy()
    merged_dict.update(sorted_new_ips)

    return merged_dict


IP_DICT = load_and_merge_ips(IP_DICT, "uniaudio_ip_list.txt")


class MingOmniTTSDemoTab:
    """
    独立实现了基于 Ming-Omni-TTS V4 MOE (WebGW) 的请求逻辑。
    """

    def __init__(
        self, webgw_url, webgw_api_key, webgw_app_id, api_project="260203-ming-uniaudio-v4-moe-lite", i18n=None
    ):
        self.webgw_url = webgw_url
        self.api_key = webgw_api_key
        self.app_id = webgw_app_id
        self.api_project = api_project
        self.i18n = i18n if i18n is not None else lambda x: x

    def create_tab(self):
        with gr.TabItem(self.i18n("tab_ming_omni")):
            gr.Markdown(self.i18n("ming_omni_title"))

            with gr.Tabs():
                # --- Tab 1: 指令TTS ---
                with gr.TabItem(self.i18n("instruct_tts_tab")):
                    with gr.Row():
                        with gr.Column(scale=2):
                            i_tts_type = gr.Dropdown(
                                [
                                    (self.i18n("instruct_type_dialect"), "dialect"),
                                    (self.i18n("instruct_type_emotion"), "emotion"),
                                    (self.i18n("instruct_type_ip"), "IP"),
                                    (self.i18n("instruct_type_style"), "style"),
                                    (self.i18n("instruct_type_basic"), "basic")
                                ],
                                label=self.i18n("instruct_type_label"),
                                value="emotion",
                            )
                            i_tts_text = gr.Textbox(label=self.i18n("instruct_text_label"), info=self.i18n("instruct_text_info"))
                            i_tts_prompt = gr.Audio(
                                type="filepath",
                                label=self.i18n("instruct_prompt_label"),
                                sources=["upload", "microphone"],
                            )

                            with gr.Accordion(self.i18n("instruct_details_accordion"), open=True):
                                i_tts_emotion = gr.Dropdown(
                                    DROPDOWN_CHOICES["emotions"], label=self.i18n("instruct_emotion_label"), value="高兴"
                                )
                                i_tts_dialect = gr.Dropdown(
                                    DROPDOWN_CHOICES["dialects"],
                                    label=self.i18n("instruct_dialect_label"),
                                    value="广粤话",
                                    visible=False,
                                )
                                i_tts_ip = gr.Dropdown(
                                    list(IP_DICT.keys()), label=self.i18n("instruct_ip_label"), visible=False
                                )
                                i_tts_style = gr.Textbox(
                                    label=self.i18n("instruct_style_label"),
                                    info=self.i18n("instruct_style_info"),
                                    visible=False,
                                )
                                i_tts_speed = gr.Dropdown(
                                    [(self.i18n("instruct_speed_slow"), "慢速"), (self.i18n("instruct_speed_medium"), "中速"), (self.i18n("instruct_speed_fast"), "快速")],
                                    label=self.i18n("instruct_speed_label"),
                                    value="中速",
                                    visible=False,
                                )
                                i_tts_pitch = gr.Dropdown(
                                    [(self.i18n("instruct_pitch_low"), "低"), (self.i18n("instruct_pitch_medium"), "中"), (self.i18n("instruct_pitch_high"), "高")], 
                                    label=self.i18n("instruct_pitch_label"), 
                                    value="中", 
                                    visible=False
                                )
                                i_tts_volume = gr.Dropdown(
                                    [(self.i18n("instruct_volume_low"), "低"), (self.i18n("instruct_volume_medium"), "中"), (self.i18n("instruct_volume_high"), "高")], 
                                    label=self.i18n("instruct_volume_label"), 
                                    value="中", 
                                    visible=False
                                )

                            i_tts_btn = gr.Button(self.i18n("instruct_generate_button"), variant="primary")

                        with gr.Column(scale=1):
                            i_tts_status = gr.Markdown(value=self.i18n("instruct_status_default"))
                            i_tts_output = gr.Audio(
                                label=self.i18n("instruct_output_label"), type="filepath", interactive=False
                            )

                    def update_details_visibility(instruct_type):
                        prompt_visible = instruct_type not in ["IP", "style"]
                        return {
                            i_tts_prompt: gr.update(visible=prompt_visible),
                            i_tts_emotion: gr.update(visible=instruct_type == "emotion"),
                            i_tts_dialect: gr.update(visible=instruct_type == "dialect"),
                            i_tts_ip: gr.update(visible=instruct_type == "IP"),
                            i_tts_style: gr.update(visible=instruct_type == "style"),
                            i_tts_speed: gr.update(visible=instruct_type == "basic"),
                            i_tts_pitch: gr.update(visible=instruct_type == "basic"),
                            i_tts_volume: gr.update(visible=instruct_type == "basic"),
                        }

                    i_tts_type.change(
                        fn=update_details_visibility,
                        inputs=i_tts_type,
                        outputs=[
                            i_tts_prompt,
                            i_tts_emotion,
                            i_tts_dialect,
                            i_tts_ip,
                            i_tts_style,
                            i_tts_speed,
                            i_tts_pitch,
                            i_tts_volume,
                        ],
                    )

                # --- Tab 2: 零样本TTS (音色克隆) ---
                with gr.TabItem(self.i18n("zeroshot_tts_tab")):
                    with gr.Row():
                        with gr.Column(scale=2):
                            zs_tts_text = gr.Textbox(
                                label=self.i18n("zeroshot_text_label"), info=self.i18n("zeroshot_text_info")
                            )
                            zs_tts_prompt = gr.Audio(
                                type="filepath",
                                label=self.i18n("zeroshot_prompt_label"),
                                sources=["upload", "microphone"],
                            )
                            zs_tts_btn = gr.Button(self.i18n("zeroshot_button"), variant="primary")
                        with gr.Column(scale=1):
                            zs_tts_status = gr.Markdown(value=self.i18n("zeroshot_status_default"))
                            zs_tts_output = gr.Audio(
                                label=self.i18n("zeroshot_output_label"), type="filepath", interactive=False
                            )

                # --- Tab 3: 多人播客 ---
                with gr.TabItem(self.i18n("podcast_tab")):
                    with gr.Row():
                        with gr.Column(scale=2):
                            pod_text = gr.Textbox(
                                lines=5,
                                label=self.i18n("podcast_script_label"),
                                info=self.i18n("podcast_script_info"),
                            )
                            pod_prompt1 = gr.Audio(
                                type="filepath",
                                label=self.i18n("podcast_prompt1_label"),
                                sources=["upload", "microphone"],
                            )
                            pod_prompt2 = gr.Audio(
                                type="filepath",
                                label=self.i18n("podcast_prompt2_label"),
                                sources=["upload", "microphone"],
                            )
                            pod_btn = gr.Button(self.i18n("podcast_button"), variant="primary")
                        with gr.Column(scale=1):
                            pod_status = gr.Markdown(
                                value=self.i18n("podcast_status_default")
                            )
                            pod_output = gr.Audio(
                                label=self.i18n("podcast_output_label"), type="filepath", interactive=False
                            )

                # --- Tab 4: 带背景音乐的语音 ---
                with gr.TabItem(self.i18n("swb_tab")):
                    with gr.Row():
                        with gr.Column(scale=2):
                            swb_text = gr.Textbox(label=self.i18n("swb_text_label"))
                            swb_prompt = gr.Audio(
                                type="filepath",
                                label=self.i18n("swb_prompt_label"),
                                sources=["upload", "microphone"],
                            )
                            gr.Markdown(self.i18n("swb_bgm_title"))
                            with gr.Row():
                                swb_genre = gr.Dropdown(
                                    DROPDOWN_CHOICES["swb_genres"],
                                    label=self.i18n("swb_genre_label"),
                                    value="流行摇滚",
                                )
                                swb_mood = gr.Dropdown(
                                    DROPDOWN_CHOICES["swb_moods"],
                                    label=self.i18n("swb_mood_label"),
                                    value="快乐",
                                )
                            with gr.Row():
                                swb_instrument = gr.Dropdown(
                                    DROPDOWN_CHOICES["swb_instruments"],
                                    label=self.i18n("swb_instrument_label"),
                                    value="合成铜管乐器",
                                )
                                swb_theme = gr.Dropdown(
                                    DROPDOWN_CHOICES["swb_themes"],
                                    label=self.i18n("swb_theme_label"),
                                    value="旅行",
                                )
                            with gr.Row():
                                swb_snr = gr.Slider(
                                    0,
                                    20,
                                    value=10.0,
                                    step=0.5,
                                    label="信噪比 (SNR)",
                                    info="值越小，背景音乐音量越大。",
                                )
                            swb_btn = gr.Button(self.i18n("swb_button"), variant="primary")
                        with gr.Column(scale=1):
                            swb_status = gr.Markdown(value=self.i18n("swb_status_default"))
                            swb_output = gr.Audio(
                                label=self.i18n("swb_output_label"), type="filepath", interactive=False
                            )

                # --- Tab 5: 纯背景音乐生成 ---
                with gr.TabItem(self.i18n("bgm_tab")):
                    with gr.Row():
                        with gr.Column(scale=2):
                            bgm_genre = gr.Dropdown(
                                DROPDOWN_CHOICES["bgm_genres"],
                                label=self.i18n("bgm_genre_label"),
                                value="迪斯科",
                            )
                            bgm_mood = gr.Dropdown(
                                DROPDOWN_CHOICES["bgm_moods"],
                                label=self.i18n("bgm_mood_label"),
                                value="快乐",
                            )
                            bgm_instrument = gr.Dropdown(
                                DROPDOWN_CHOICES["bgm_instruments"],
                                label=self.i18n("bgm_instrument_label"),
                                value="电吉他",
                            )
                            bgm_theme = gr.Dropdown(
                                DROPDOWN_CHOICES["bgm_themes"],
                                label=self.i18n("bgm_theme_label"),
                                value="庆典与喜悦",
                            )
                            bgm_duration = gr.Slider(30, 60, value=35, step=1, label=self.i18n("bgm_duration_label"))
                            bgm_btn = gr.Button(self.i18n("bgm_button"), variant="primary")
                        with gr.Column(scale=1):
                            bgm_status = gr.Markdown(value=self.i18n("bgm_status_default"))
                            bgm_output = gr.Audio(
                                label=self.i18n("bgm_output_label"), type="filepath", interactive=False
                            )

                # --- Tab 6: 音效生成 ---
                with gr.TabItem(self.i18n("tta_tab")):
                    with gr.Row():
                        with gr.Column(scale=2):
                            tta_text = gr.Textbox(
                                label=self.i18n("tta_text_label"),
                                info=self.i18n("tta_text_info"),
                            )
                            tta_btn = gr.Button(self.i18n("tta_button"), variant="primary")
                        with gr.Column(scale=1):
                            tta_status = gr.Markdown(value=self.i18n("tta_status_default"))
                            tta_output = gr.Audio(
                                label=self.i18n("tta_output_label"), type="filepath", interactive=False
                            )

            # --- 事件绑定 ---
            def i_tts_submit(
                instruct_type,
                text,
                prompt_audio,
                emotion,
                dialect,
                ip_choice,
                style,
                speed,
                pitch,
                volume,
            ):
                details = {}
                if instruct_type == "emotion":
                    details = {"情感": emotion}
                elif instruct_type == "dialect":
                    details = {"方言": dialect}
                elif instruct_type == "IP":
                    backend_ip = IP_DICT.get(ip_choice)
                    if not backend_ip:
                        raise gr.Error(f"未找到IP角色'{ip_choice}'的配置。")
                    details = {"IP": backend_ip}
                elif instruct_type == "style":
                    details = {"风格": style}
                elif instruct_type == "basic":
                    details = {"语速": speed, "基频": pitch, "音量": volume}
                yield from self._submit_and_poll("TTS", instruct_type, text, prompt_audio, details)

            i_tts_btn.click(
                fn=i_tts_submit,
                inputs=[
                    i_tts_type,
                    i_tts_text,
                    i_tts_prompt,
                    i_tts_emotion,
                    i_tts_dialect,
                    i_tts_ip,
                    i_tts_style,
                    i_tts_speed,
                    i_tts_pitch,
                    i_tts_volume,
                ],
                outputs=[i_tts_status, i_tts_btn, i_tts_output],
            )

            zs_tts_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("zero_shot_TTS", *args)),
                inputs=[zs_tts_text, zs_tts_prompt],
                outputs=[zs_tts_status, zs_tts_btn, zs_tts_output],
            )
            pod_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("podcast", *args)),
                inputs=[pod_text, pod_prompt1, pod_prompt2],
                outputs=[pod_status, pod_btn, pod_output],
            )
            swb_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("speech_with_bgm", *args)),
                inputs=[
                    swb_text,
                    swb_prompt,
                    swb_genre,
                    swb_mood,
                    swb_instrument,
                    swb_theme,
                    swb_snr,
                ],
                outputs=[swb_status, swb_btn, swb_output],
            )
            bgm_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("bgm", *args)),
                inputs=[bgm_genre, bgm_mood, bgm_instrument, bgm_theme, bgm_duration],
                outputs=[bgm_status, bgm_btn, bgm_output],
            )
            tta_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("TTA", *args)),
                inputs=[tta_text],
                outputs=[tta_status, tta_btn, tta_output],
            )

    # --- 辅助方法 ---
    def _file_to_b64(self, filepath: Optional[str]) -> Optional[str]:
        if not filepath or not os.path.exists(filepath):
            return None
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _cleanup_temp_files(self, output_dir: str, max_files: int = 10):
        """
        清理临时目录，仅保留最新的 max_files 个文件。
        """
        try:
            if not os.path.exists(output_dir):
                return

            files = [
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
            ]

            # 按修改时间排序（从旧到新）
            files.sort(key=os.path.getmtime)

            if len(files) >= max_files:
                num_to_delete = (
                    len(files) - max_files + 1
                )  # +1 是为了给即将新创建的文件腾位置，保持总数 <= 10
                for i in range(num_to_delete):
                    try:
                        os.remove(files[i])
                        logger.info(f"Deleted old temp file: {files[i]}")
                    except OSError as e:
                        logger.warning(f"Error deleting file {files[i]}: {e}")
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")

    def _submit_and_poll(self, task_type: str, *args):
        """
        核心的提交和轮询逻辑。
        独立实现，不依赖外部 SpeechService，适配 UniAudio V4 MOE 接口。
        """
        yield (
            gr.update(value="⏳ 正在准备任务..."),
            gr.update(interactive=False),
            gr.update(value=None),
        )

        payload = {}
        try:
            if task_type == "TTS":
                instruct_type, text, prompt_audio, caption_details = args
                prompt_b64 = self._file_to_b64(prompt_audio)

                if not text:
                    raise ValueError("合成文本不能为空。")
                if instruct_type not in ["IP", "style"] and not prompt_b64:
                    raise ValueError(f"指令类型 '{instruct_type}' 需要上传参考音频。")

                # V4 接口要求 caption 是 JSON 字符串
                # 构造 caption 对象
                caption_obj = {"audio_sequence": [caption_details]}

                payload = {
                    "task_type": "TTS",
                    "instruct_type": instruct_type,
                    "text": text,
                    "caption": json.dumps(caption_obj, ensure_ascii=False),  # 序列化
                    "prompt_wav_b64": prompt_b64,
                }
            elif task_type == "zero_shot_TTS":
                text, prompt_audio = args
                logger.info(
                    f"[Zero-shot TTS] Preparing task. Text: '{text[:20]}...', Audio: {prompt_audio}"
                )
                prompt_b64 = self._file_to_b64(prompt_audio)
                if not text or not prompt_b64:
                    logger.error("[Zero-shot TTS] Validation failed: Missing text or prompt audio.")
                    raise ValueError("文本和参考音频不能为空。")
                payload = {"task_type": "zero_shot_TTS", "text": text, "prompt_wav_b64": prompt_b64}
                logger.info("[Zero-shot TTS] Payload constructed successfully.")
            elif task_type == "podcast":
                text, prompt_audio_1, prompt_audio_2 = args
                prompt_b64_1, prompt_b64_2 = self._file_to_b64(prompt_audio_1), self._file_to_b64(
                    prompt_audio_2
                )
                if not text or not prompt_b64_1 or not prompt_b64_2:
                    raise ValueError("对话脚本和两个参考音频均不能为空。")
                payload = {
                    "task_type": "podcast",
                    "text": text,
                    "prompt_wavs_b64": [prompt_b64_1, prompt_b64_2],
                }
            elif task_type == "bgm":
                genre, mood, instrument, theme, duration = args
                prompt_text = f"Genre: {genre}. Mood: {mood}. Instrument: {instrument}. Theme: {theme}. Duration: {duration}s."
                payload = {"task_type": "bgm", "prompt_text": prompt_text}
            elif task_type == "TTA":
                (text,) = args
                if not text:
                    raise ValueError("音效描述不能为空。")
                payload = {"task_type": "TTA", "text": text}
            elif task_type == "speech_with_bgm":
                text, prompt_audio, genre, mood, instrument, theme, snr = args
                prompt_b64 = self._file_to_b64(prompt_audio)
                if not text or not prompt_b64:
                    raise ValueError("文本和参考音频不能为空。")
                bgm_data = {
                    "Genre": f"{genre}.",
                    "Mood": f"{mood}.",
                    "Instrument": f"{instrument}.",
                    "Theme": f"{theme}.",
                    "SNR": str(float(snr)),
                    "ENV": None,
                }
                payload = {
                    "task_type": "speech_with_bgm",
                    "text": text,
                    "prompt_wav_b64": prompt_b64,
                    "caption": json.dumps(bgm_data, ensure_ascii=False),  # 序列化
                }
            else:
                raise ValueError(f"未知的任务类型: {task_type}")

        except Exception as e:
            yield (
                gr.update(value=f"❌ 错误：输入参数组装失败 - {e}"),
                gr.update(interactive=True),
                gr.update(value=None),
            )
            return

        yield (
            gr.update(value="🚀 任务提交中..."),
            gr.update(interactive=False),
            gr.update(value=None),
        )

        # --- 发起 WebGW 请求 (Submit) ---
        call_token = str(uuid.uuid4())
        logger.info(f"[{task_type}] Submitting task to WebGW. Token: {call_token}")

        request_body = {
            "api_key": self.api_key,
            "api_project": self.api_project,
            "call_name": "submit_task",
            "call_token": call_token,
            "call_args": payload,
        }

        headers = {
            "Content-Type": "application/json",
            "x-webgw-appid": self.app_id,
            "x-webgw-version": "2.0",
        }

        try:
            logger.info(f"Submitting task to WebGW: {self.webgw_url}")
            r = requests.post(url=self.webgw_url, json=request_body, headers=headers, timeout=30)
            r.raise_for_status()
            res_data = r.json()

            if not res_data.get("success"):
                raise ConnectionError(f"WebGW 请求失败: {res_data.get('errorMessage', '未知错误')}")

            # 解析内部结果
            result_obj = res_data.get("resultObj", {})
            inner_result_str = result_obj.get("result")

            if not inner_result_str:
                # 可能是直接返回在 resultObj 里，视具体实现而定，但标准 WebGW 通常在 result 字段返回字符串
                # 这里的解析逻辑需要适配 Chair FaaS 的 AudioProxyController 返回
                # 回顾 AudioProxyController，它返回 { result: object }
                # 如果是 AudioProxyController.ts:
                # return { success: true, resultObj: { ..., result: res } }
                # 所以 res 就是 payload
                inner_result = result_obj.get("result")
                if not inner_result:
                    raise ValueError("服务返回中未找到 'result' 字段。")
            else:
                # 如果 result 是字符串（常见情况），则 parse
                if isinstance(inner_result_str, str):
                    inner_result = json.loads(inner_result_str)
                else:
                    inner_result = inner_result_str

            # 检查内部业务成功状态 (根据 V4 接口定义)
            # V4 MOE 接口通常直接返回 task_id
            task_id = inner_result.get("task_id")
            if not task_id:
                raise ValueError(f"未能从响应中获取 task_id: {inner_result}")

        except Exception as e:
            logger.error(f"Task submission failed: {e}")
            yield (
                gr.update(value=f"❌ 错误：任务提交失败 - {e}"),
                gr.update(interactive=True),
                gr.update(value=None),
            )
            return

        # --- 轮询逻辑 (Poll) ---
        max_polls = 60  # 2分钟超时
        poll_interval = 2

        for i in range(max_polls):
            yield (
                gr.update(value=f"🔄 生成中... ({i*poll_interval}s)"),
                gr.update(interactive=False),
                gr.update(value=None),
            )
            time.sleep(poll_interval)

            poll_body = {
                "api_key": self.api_key,
                "api_project": self.api_project,
                "call_name": "poll_task",
                "call_token": str(uuid.uuid4()),
                "call_args": {"task_id": task_id},
            }

            try:
                r = requests.post(url=self.webgw_url, json=poll_body, headers=headers, timeout=30)
                r.raise_for_status()
                res_data = r.json()

                if not res_data.get("success"):
                    logger.warning(f"Poll request failed: {res_data.get('errorMessage')}")
                    continue  # 轮询失败暂不中断，重试

                result_obj = res_data.get("resultObj", {})
                inner_result = result_obj.get("result")  # 对象或字符串

                if not inner_result:
                    continue

                if isinstance(inner_result, str):
                    poll_res = json.loads(inner_result)
                else:
                    poll_res = inner_result

                # status: pending / completed / failed
                status = poll_res.get("status")
                logger.info(f"[{task_type}] Poll status for task {task_id}: {status}")

                if status == "completed" or status == "success":
                    audio_url = poll_res.get("output_audio_url")
                    if not audio_url:
                        raise ValueError("任务完成但未返回音频 URL")

                    # 下载音频 (通过 FaaS Proxy 曲线救国，解决 OSS 403 问题)
                    try:
                        parsed_url = urlparse(audio_url)
                        query_params = parse_qs(parsed_url.query)

                        # 提取 OSS 签名参数
                        proxy_args = {
                            "filename": os.path.basename(parsed_url.path),
                            "oss_access_key_id": query_params.get("OSSAccessKeyId", [None])[0],
                            "expires": query_params.get("Expires", [None])[0],
                            "signature": query_params.get("Signature", [None])[0],
                        }

                        logger.info(f"Downloading audio via Proxy: {proxy_args['filename']}")

                        proxy_payload = {
                            "api_key": self.api_key,
                            "api_project": self.api_project,
                            "call_name": "get_audio",
                            "call_token": str(uuid.uuid4()),
                            "call_args": proxy_args,
                        }

                        # 发起代理下载请求 (POST)
                        audio_resp = requests.post(
                            url=self.webgw_url, json=proxy_payload, headers=headers, timeout=60
                        )
                        audio_resp.raise_for_status()

                        res_json = audio_resp.json()
                        if not res_json.get("success"):
                            raise RuntimeError(
                                f"Proxy download error: {res_json.get('errorMessage', 'Unknown error')}"
                            )

                        # 解析 Gzip+Base64 响应
                        result_obj = res_json.get("resultObj", {})
                        # result 可能是 JSON 对象也可能是字符串
                        inner_result = result_obj.get("result")
                        if isinstance(inner_result, str):
                            try:
                                inner_result = json.loads(inner_result)
                            except json.JSONDecodeError:
                                pass  # 应该不会发生，除非格式错乱

                        if not isinstance(inner_result, dict) or "gzippedRaw" not in inner_result:
                            raise ValueError("Invalid proxy response: missing 'gzippedRaw' field")

                        gzipped_b64 = inner_result["gzippedRaw"]
                        compressed_data = base64.b64decode(gzipped_b64)

                        # 解压 Gzip
                        try:
                            with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as f_gz:
                                content = f_gz.read()
                        except OSError as e:
                            # 兼容性尝试：如果不是 Gzip 格式（虽然服务端强制压缩了），尝试直接使用
                            logger.warning(f"Gzip decompression failed, trying raw: {e}")
                            content = compressed_data

                        os.makedirs("temp_audio", exist_ok=True)
                        self._cleanup_temp_files("temp_audio")  # 清理旧文件

                        audio_file = os.path.join("temp_audio", f"{task_id}.wav")
                        with open(audio_file, "wb") as f_out:
                            f_out.write(content)

                        yield (
                            gr.update(value="✅ 成功！"),
                            gr.update(interactive=True),
                            gr.update(value=audio_file),
                        )
                        return
                    except Exception as e:
                        logger.error(f"Audio download via proxy failed: {e}")
                        raise RuntimeError(f"音频下载失败: {e}")

                elif status == "failed":
                    raise RuntimeError(f"任务执行失败: {poll_res.get('error_message', '未知错误')}")

                # pending 继续循环

            except Exception as e:
                logger.error(f"Polling error: {e}")
                # 轮询出错通常不应直接中断，除非严重错误
                # 这里简单处理，继续
                pass

        yield (
            gr.update(value="⏰ 错误：任务超时。", color="red"),
            gr.update(interactive=True),
            gr.update(value=None),
        )
