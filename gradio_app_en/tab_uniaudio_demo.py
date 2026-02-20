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

# --- Static Data ---
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


# Helper Function
def load_and_merge_ips(original_dict: dict, filepath: str) -> dict:
    """
    Load new IPs from a txt file, sort by Pinyin, and append to original dict.
    Supports: 'Key:Value' or 'Value' (where Key=Value).
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
                        logger.warning(f"Unable to parse line: {line}, format should be 'Key:Value'")
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

REFERENCE_AUDIO_WARNING = "**⚠️ Note: Reference audio works best at approximately 3-7 seconds. Longer audio may produce unexpected output. You can trim the audio using the Audio block below.**"


class MingOmniTTSDemoTab:
    """
    Implements request logic based on Ming-Omni-TTS V4 MOE (WebGW).
    """

    def __init__(
        self, webgw_url, webgw_api_key, webgw_app_id, api_project="260203-ming-uniaudio-v4-moe-lite"
    ):
        self.webgw_url = webgw_url
        self.api_key = webgw_api_key
        self.app_id = webgw_app_id
        self.api_project = api_project

    def create_tab(self):
        with gr.TabItem("Ming-omni-tts"):
            gr.Markdown("## Ming-omni-tts Comprehensive Demo")

            with gr.Tabs():
                # --- Tab 1: Instruct TTS ---
                with gr.TabItem("Instruct TTS"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            i_tts_type = gr.Dropdown(
                                [
                                    ("Dialect", "dialect"),
                                    ("Emotion", "emotion"),
                                    ("IP", "IP"),
                                    ("Style", "style"),
                                    ("Basic", "basic")
                                ],
                                label="Instruction Type",
                                value="emotion",
                            )
                            i_tts_text = gr.Textbox(label="Synthesis Text", info="Enter the text for speech synthesis.")
                            gr.Markdown(REFERENCE_AUDIO_WARNING)
                            i_tts_prompt = gr.Audio(
                                type="filepath",
                                label="Reference Audio (3-7s) - Upload clear speech to clone timbre.",
                                sources=["upload", "microphone"],
                            )

                            with gr.Accordion("Instruction Details", open=True):
                                i_tts_emotion = gr.Dropdown(
                                    [("Angry", "愤怒"), ("Happy", "高兴"), ("Sad", "悲伤")],
                                    label="Emotion",
                                    value="高兴",
                                )
                                i_tts_dialect = gr.Dropdown(
                                    [("Sichuanese", "四川话"), ("Cantonese", "广粤话")],
                                    label="Dialect",
                                    value="广粤话",
                                    visible=False,
                                )
                                i_tts_ip = gr.Dropdown(
                                    list(IP_DICT.keys()), label="IP Character", visible=False
                                )
                                i_tts_style = gr.Textbox(
                                    label="Style Description",
                                    info="e.g. Speak with a loud and powerful volume, showing male toughness and majesty. Fast pace, smooth tone, slow down at the end to enhance authority.",
                                    visible=False,
                                )
                                i_tts_speed = gr.Dropdown(
                                    [("Slow", "慢速"), ("Medium", "中速"), ("Fast", "快速")],
                                    label="Speed",
                                    value="中速",
                                    visible=False,
                                )
                                i_tts_pitch = gr.Dropdown(
                                    [("Low", "低"), ("Medium", "中"), ("High", "高")],
                                    label="Pitch",
                                    value="中",
                                    visible=False,
                                )
                                i_tts_volume = gr.Dropdown(
                                    [("Low", "低"), ("Medium", "中"), ("High", "高")],
                                    label="Volume",
                                    value="中",
                                    visible=False,
                                )

                            i_tts_btn = gr.Button("Generate Instruct Speech", variant="primary")

                        with gr.Column(scale=1):
                            i_tts_status = gr.Markdown(value="💡 Please select an instruction type and fill in the parameters.")
                            i_tts_output = gr.Audio(
                                label="Generated Result", type="filepath", interactive=False
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

                # --- Tab 2: Zero-shot TTS (Timbre Cloning) ---
                with gr.TabItem("Zero-shot TTS"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            zs_tts_text = gr.Textbox(
                                label="Target Text", info="Enter the text for speech synthesis."
                            )
                            gr.Markdown(REFERENCE_AUDIO_WARNING)
                            zs_tts_prompt = gr.Audio(
                                type="filepath",
                                label="Reference Audio (3-7s) - Upload clear speech to clone timbre.",
                                sources=["upload", "microphone"],
                            )
                            zs_tts_btn = gr.Button("Clone and Generate Speech", variant="primary")
                        with gr.Column(scale=1):
                            zs_tts_status = gr.Markdown(value="💡 Please enter text and upload reference audio.")
                            zs_tts_output = gr.Audio(
                                label="Generated Result", type="filepath", interactive=False
                            )

                # --- Tab 3: Podcast ---
                with gr.TabItem("Podcast"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            pod_text = gr.Textbox(
                                lines=5,
                                label="Dialogue Script",
                                info="Use 'speaker_1:', 'speaker_2:' to distinguish speakers. e.g. speaker_1: Hello!\n speaker_2: Hi there!",
                            )
                            gr.Markdown(REFERENCE_AUDIO_WARNING)
                            pod_prompt1 = gr.Audio(
                                type="filepath",
                                label="Speaker 1 Reference Audio",
                                sources=["upload", "microphone"],
                            )
                            gr.Markdown(REFERENCE_AUDIO_WARNING)
                            pod_prompt2 = gr.Audio(
                                type="filepath",
                                label="Speaker 2 Reference Audio",
                                sources=["upload", "microphone"],
                            )
                            pod_btn = gr.Button("Generate Podcast", variant="primary")
                        with gr.Column(scale=1):
                            pod_status = gr.Markdown(
                                value="💡 Please fill in the script and upload reference audio for both speakers."
                            )
                            pod_output = gr.Audio(
                                label="Generated Result", type="filepath", interactive=False
                            )

                # --- Tab 4: Speech with BGM ---
                with gr.TabItem("Speech with BGM"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            swb_text = gr.Textbox(label="Speech Text")
                            gr.Markdown(REFERENCE_AUDIO_WARNING)
                            swb_prompt = gr.Audio(
                                type="filepath",
                                label="Speaker Reference Audio",
                                sources=["upload", "microphone"],
                            )
                            gr.Markdown("##### BGM Description")
                            with gr.Row():
                                swb_genre = gr.Dropdown(
                                    [("Pop Rock", "流行摇滚"), ("Disco", "迪斯科"), ("EDM", "电子舞曲")],
                                    label="Genre",
                                    value="流行摇滚",
                                )
                                swb_mood = gr.Dropdown(
                                    [("Happy", "快乐"), ("Exciting", "兴奋"), ("Energetic", "活力四射")],
                                    label="Mood",
                                    value="快乐",
                                )
                            with gr.Row():
                                swb_instrument = gr.Dropdown(
                                    [("Electric Guitar", "电吉他"), ("Synth Brass", "合成铜管乐器"), ("Drum Kit", "架子鼓")],
                                    label="Instrument",
                                    value="合成铜管乐器",
                                )
                                swb_theme = gr.Dropdown(
                                    [("Birthday", "生日"), ("Travel", "旅行"), ("Sports", "运动")],
                                    label="Theme",
                                    value="旅行",
                                )
                            with gr.Row():
                                swb_snr = gr.Slider(
                                    0,
                                    20,
                                    value=10.0,
                                    step=0.5,
                                    label="SNR",
                                    info="Lower value means louder BGM.",
                                )
                            swb_btn = gr.Button("Generate Speech with BGM", variant="primary")
                        with gr.Column(scale=1):
                            swb_status = gr.Markdown(value="💡 Please fill in all fields and upload reference audio.")
                            swb_output = gr.Audio(
                                label="Generated Result", type="filepath", interactive=False
                            )

                # --- Tab 5: BGM Generation ---
                with gr.TabItem("BGM Generation"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            bgm_genre = gr.Dropdown(
                                [
                                    ("Indie Folk: Guitar-driven", "独立民谣：吉他驱动"),
                                    ("Contemporary Classical: Piano-driven", "当代古典音乐：钢琴驱动"),
                                    ("Modern Pop Ballad: Piano-driven", "现代流行抒情曲：钢琴驱动的"),
                                    ("Country Music", "乡村音乐"),
                                    ("Pop Music", "流行乐"),
                                    ("Pop Rock", "流行摇滚"),
                                    ("EDM", "电子舞曲"),
                                    ("Reggaeton", "雷鬼顿"),
                                    ("Disco", "迪斯科"),
                                ],
                                label="Genre",
                                value="迪斯科",
                            )
                            bgm_mood = gr.Dropdown(
                                [
                                    ("Inspirational/Hopeful", "鼓舞人心/充满希望"),
                                    ("Epic/Grand", "壮丽宏大"),
                                    ("Happy", "快乐"),
                                    ("Calm/Relaxing", "平静放松"),
                                    ("Confident/Determined", "自信/坚定"),
                                    ("Lighthearted/Carefree", "轻快无忧无虑"),
                                    ("Energetic/Vibrant", "活力四射/精力充沛"),
                                    ("Sad/Melancholy", "悲伤哀愁"),
                                    ("Warm/Friendly", "温暖/友善"),
                                    ("Exciting", "兴奋"),
                                ],
                                label="Mood",
                                value="快乐",
                            )
                            bgm_instrument = gr.Dropdown(
                                [
                                    ("Bass Drum", "低音鼓"),
                                    ("Electric Guitar", "电吉他"),
                                    ("Synth Pluck", "合成拨弦"),
                                    ("Synth Brass", "合成铜管乐器"),
                                    ("Drum Kit", "架子鼓"),
                                    ("Timpani", "定音鼓"),
                                ],
                                label="Instrument",
                                value="电吉他",
                            )
                            bgm_theme = gr.Dropdown(
                                [
                                    ("Inspirational", "励志"),
                                    ("Birthday", "生日"),
                                    ("Breakup", "分手"),
                                    ("Travel", "旅行"),
                                    ("Sports", "运动"),
                                    ("Concert Hall", "剧院音乐厅"),
                                    ("Live Music", "音乐现场"),
                                    ("Festival", "节日"),
                                    ("Good Times", "好时光"),
                                    ("Celebration & Joy", "庆典与喜悦"),
                                ],
                                label="Theme",
                                value="庆典与喜悦",
                            )
                            bgm_duration = gr.Slider(30, 60, value=35, step=1, label="Duration (s)")
                            bgm_btn = gr.Button("Generate BGM", variant="primary")
                        with gr.Column(scale=1):
                            bgm_status = gr.Markdown(value="💡 Please describe the music you want.")
                            bgm_output = gr.Audio(
                                label="Generated Result", type="filepath", interactive=False
                            )

                # --- Tab 6: Sound Effects (TTA) ---
                with gr.TabItem("Sound Effects (TTA)"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            tta_text = gr.Textbox(
                                label="Sound Description",
                                info="English descriptions are recommended. e.g.: 'Rain is falling continuously'.",
                            )
                            tta_btn = gr.Button("Generate Sound Effect", variant="primary")
                        with gr.Column(scale=1):
                            tta_status = gr.Markdown(value="💡 Please enter a text description of the sound effect.")
                            tta_output = gr.Audio(
                                label="Generated Result", type="filepath", interactive=False
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
                        raise gr.Error(f"IP configuration for '{ip_choice}' not found.")
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
        Core submission and polling logic.
        """
        yield (
            gr.update(value="⏳ Preparing task..."),
            gr.update(interactive=False),
            gr.update(value=None),
        )

        payload = {}
        try:
            if task_type == "TTS":
                instruct_type, text, prompt_audio, caption_details = args
                prompt_b64 = self._file_to_b64(prompt_audio)

                if not text:
                    raise ValueError("Synthesis text cannot be empty.")
                if instruct_type not in ["IP", "style"] and not prompt_b64:
                    raise ValueError(f"Instruction type '{instruct_type}' requires reference audio.")

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
                    raise ValueError("Text and reference audio cannot be empty.")
                payload = {"task_type": "zero_shot_TTS", "text": text, "prompt_wav_b64": prompt_b64}
                logger.info("[Zero-shot TTS] Payload constructed successfully.")
            elif task_type == "podcast":
                text, prompt_audio_1, prompt_audio_2 = args
                prompt_b64_1, prompt_b64_2 = self._file_to_b64(prompt_audio_1), self._file_to_b64(
                    prompt_audio_2
                )
                if not text or not prompt_b64_1 or not prompt_b64_2:
                    raise ValueError("Dialogue script and both reference audios cannot be empty.")
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
                    raise ValueError("Sound description cannot be empty.")
                payload = {"task_type": "TTA", "text": text}
            elif task_type == "speech_with_bgm":
                text, prompt_audio, genre, mood, instrument, theme, snr = args
                prompt_b64 = self._file_to_b64(prompt_audio)
                if not text or not prompt_b64:
                    raise ValueError("Text and reference audio cannot be empty.")
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
                raise ValueError(f"Unknown task type: {task_type}")

        except Exception as e:
            yield (
                gr.update(value=f"❌ Error: Input assembly failed - {e}"),
                gr.update(interactive=True),
                gr.update(value=None),
            )
            return

        yield (
            gr.update(value="🚀 Submitting task..."),
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
                raise ConnectionError(f"WebGW request failed: {res_data.get('errorMessage', 'Unknown error')}")

            # 解析内部结果
            result_obj = res_data.get("resultObj", {})
            inner_result_str = result_obj.get("result")

            if not inner_result_str:
                inner_result = result_obj.get("result")
                if not inner_result:
                    raise ValueError("'result' field not found in response.")
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
                raise ValueError(f"Could not obtain task_id from response: {inner_result}")

        except Exception as e:
            logger.error(f"Task submission failed: {e}")
            yield (
                gr.update(value=f"❌ Error: Task submission failed - {e}"),
                gr.update(interactive=True),
                gr.update(value=None),
            )
            return

        # --- 轮询逻辑 (Poll) ---
        max_polls = 60  # 2分钟超时
        poll_interval = 2

        for i in range(max_polls):
            yield (
                gr.update(value=f"🔄 Generating... ({i*poll_interval}s)"),
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
                        raise ValueError("Task completed but no audio URL returned")

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
                            gr.update(value="✅ Success!"),
                            gr.update(interactive=True),
                            gr.update(value=audio_file),
                        )
                        return
                    except Exception as e:
                        logger.error(f"Audio download via proxy failed: {e}")
                        raise RuntimeError(f"Audio download failed: {e}")

                elif status == "failed":
                    raise RuntimeError(f"Task execution failed: {poll_res.get('error_message', 'Unknown error')}")

                # pending 继续循环

            except Exception as e:
                logger.error(f"Polling error: {e}")
                # 轮询出错通常不应直接中断，除非严重错误
                # 这里简单处理，继续
                pass

        yield (
            gr.update(value="⏰ Error: Task timeout.", color="red"),
            gr.update(interactive=True),
            gr.update(value=None),
        )
