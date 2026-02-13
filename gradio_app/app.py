# -*- coding: utf-8 -*-
import base64
import io
import json
import os
import random
import time
import uuid

import gradio as gr
import requests
from dotenv import load_dotenv
from loguru import logger
from pydub import AudioSegment
from scipy.io import wavfile
from tab_uniaudio_demo import MingOmniTTSDemoTab

# 加载 .secret 文件中的环境变量
load_dotenv(dotenv_path=".secret")

blank_rate, blank_audio_data = wavfile.read("./audio/blank.wav")


# 模型服务类 ===========================================================
class SpeechService:
    def __init__(self):
        # API Configuration
        self.use_intranet_api = os.environ.get("USE_INTRANET_API", "false").lower() == "true"

        # WebGW Internet API
        self.WEB_GW_API_URL = os.environ.get("WEB_GW_API_URL")
        self.WEB_GW_API_KEY = os.environ.get("WEB_GW_API_KEY")
        self.WEB_GW_APP_ID = os.environ.get("WEB_GW_APP_ID")

        # Other configs
        self.dump_reqs = os.environ.get("DUMP_REQS", "false").lower() == "true"
        self.sample_rate = 16000  # Gradio expects a sample rate for audio output

        logger.info(f"SpeechService initialized. Using Intranet API: {self.use_intranet_api}")
        if not self.use_intranet_api:
            logger.info(f"WebGW API URL: {self.WEB_GW_API_URL}")
            logger.info(f"WebGW APP ID: {self.WEB_GW_APP_ID}")

    def _call_webgw_api(
        self, call_name: str, call_args: dict, api_project: str = "251220-ming-uniaudio"
    ) -> dict:
        """
        Calls the central WebGW proxy API and transforms the response to match the intranet format.
        """
        if not self.WEB_GW_API_URL or not self.WEB_GW_API_KEY or not self.WEB_GW_APP_ID:
            error_msg = "WebGW API URL, Key, or App ID is not configured in .secret file."
            logger.error(error_msg)
            return {"success": False, "errorMessage": error_msg}

        api_url = self.WEB_GW_API_URL
        request_body = {
            "api_key": self.WEB_GW_API_KEY,
            "api_project": api_project,
            "call_name": call_name,
            "call_token": "token",  # Placeholder
            "call_args": call_args,
        }
        headers = {
            "Content-Type": "application/json",
            "x-webgw-appid": self.WEB_GW_APP_ID,
            "x-webgw-version": "2.0",
        }

        try:
            if self.dump_reqs:
                try:
                    payload_str = json.dumps(request_body, indent=2, ensure_ascii=False)
                    log_message = (
                        f"---- DUMP_REQS (WebGW): Start Request ----\n"
                        f"URL         : {api_url}\n"
                        f"Headers     : {json.dumps(headers, indent=2)}\n"
                        # payload_str may be large, consider truncating if necessary (4KB)
                        f"Payload     : {payload_str[:4096]}{'... [truncated]' if len(payload_str) > 4096 else ''}\n"
                        f"---- DUMP_REQS (WebGW): End Request ----"
                    )
                    logger.info(log_message)
                except Exception as e:
                    logger.warning(
                        f"DUMP_REQS: Failed to serialize WebGW request data for logging: {e}"
                    )

            response = requests.post(api_url, headers=headers, json=request_body, timeout=20)
            response.raise_for_status()

            response_data = response.json()

            # response_data may be large, consider truncating if necessary (4KB)
            logger.info(
                f"WebGW API response data: {json.dumps(response_data, indent=2)[:4096]}{'... [truncated]' if len(json.dumps(response_data)) > 4096 else ''}"
            )

            # response headers
            resp_headers = response.headers
            logger.info(f"WebGW API response headers: {resp_headers}")

            # Transform the WebGW response to mimic the intranet response structure.
            if response_data.get("success"):
                result_obj = response_data.get("resultObj", {})
                inner_result_str = result_obj.get("result", "{}")  # Default to empty JSON string
                return {
                    "success": True,
                    "resultMap": {"result": inner_result_str},
                    "errorMessage": result_obj.get("result_message", ""),
                }
            else:
                # Handle WebGW level errors or model errors proxied through WebGW
                trace_msg = response_data.get("traceMsg")
                error_msg = trace_msg or response_data.get(
                    "errorMessage", "Unknown WebGW API error"
                )
                logger.error(f"WebGW API call failed: {error_msg}")
                return {"success": False, "errorMessage": error_msg}

        except requests.exceptions.RequestException as e:
            logger.error(f"WebGW API request failed: {e}")
            return {"success": False, "errorMessage": f"API request failed: {e}"}
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode WebGW API response JSON: {e}, Response content: {response.text}"
            )
            return {"success": False, "errorMessage": f"Failed to decode API response JSON: {e}"}

    def _preprocess_audio(self, audio_path: str) -> str:
        """
        Conditionally converts an audio file to a 16kHz, single-channel WAV file using pydub.
        Only processes files identified as microphone recordings (e.g., 'audio.wav').
        Returns the path to the converted file, or original path if not processed, or None on failure.
        """
        if not audio_path or not os.path.exists(audio_path):
            logger.error(f"Audio file not found or path is empty: {audio_path}")
            return None

        # Heuristic: Only process if it's a generic recording filename.
        # Assuming 'audio.wav' is the default name for microphone recordings from Gradio.
        if os.path.basename(audio_path) == "audio.wav":
            try:
                logger.info(
                    f"Detected microphone recording: {audio_path}. Starting preprocessing..."
                )
                audio = AudioSegment.from_file(audio_path)

                audio = audio.set_frame_rate(16000).set_channels(1)

                # Export to a new file in the same directory (or a temp one if preferred)
                # Using a distinct name to avoid overwriting original if it's not a temp file
                output_path = f"{os.path.splitext(audio_path)[0]}_16k_mono.wav"
                audio.export(output_path, format="wav")

                logger.info(f"Successfully preprocessed microphone recording to: {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Failed to preprocess microphone recording '{audio_path}': {e}")
                return None
        else:
            logger.info(
                f"Detected uploaded file: {audio_path}. Skipping preprocessing as per user instruction."
            )
            return audio_path

    def _submit_tts_task(self, payload: dict) -> dict:
        """
        Submits the TTS task to the async endpoint.
        Returns the initial response which should contain the task_id.
        """
        return self._call_webgw_api(call_name="call-non-edit-model", call_args=payload)

    def _poll_tts_result(self, task_id: str) -> dict:
        """Polls the TTS task result."""
        payload = {"task_id": task_id}
        return self._call_webgw_api(call_name="call-non-edit-model", call_args=payload)

    def _submit_edit_task(self, payload: dict) -> dict:
        """
        Submits the Edit task to the async endpoint.
        Returns the initial response which should contain the task_id.
        """
        return self._call_webgw_api(call_name="call-edit-model", call_args=payload)

    def _poll_edit_result(self, task_id: str) -> dict:
        """Polls the Edit task result."""
        payload = {"task_id": task_id}
        return self._call_webgw_api(call_name="call-edit-model", call_args=payload)

    def tts_start_task(self, text: str, prompt_wav_path: str, prompt_text: str) -> str:
        """提交TTS任务并返回task_id"""
        with open(prompt_wav_path, "rb") as f:
            prompt_audio_bytes = f.read()
        prompt_audio_b64 = base64.b64encode(prompt_audio_bytes).decode("utf-8")

        submit_payload = {
            "task_name": "tts",
            "prompt_audio_b64": prompt_audio_b64,
            "text": text,
            "prompt_text": prompt_text,
        }

        # The response from the submission API is the *outer* MPS response
        initial_response = self._submit_tts_task(submit_payload)
        logger.info(f"TTS task submission response: {initial_response}")

        if not initial_response.get("success"):
            return f"错误: {initial_response.get('errorMessage', '任务提交失败')}"

        result_content_str = initial_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "错误: 提交响应中缺少 'result' 字段"

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"错误: {inner_response.get('errMsg', '内部API调用失败')}"

        task_id = inner_response.get("data", {}).get("task_id")
        if not task_id:
            return "错误: 未能从响应中获取 task_id"

        logger.info(f"TTS task started with ID: {task_id}")
        return task_id

    def tts_check_task(self, task_id: str) -> (str, tuple or None):
        """检查TTS任务状态并返回结果"""
        poll_response = self._poll_tts_result(task_id)

        if not poll_response.get("success"):
            return f"错误: {poll_response.get('errorMessage', '轮询失败')}", None

        result_content_str = poll_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "pending", None  # Still pending, no result map yet

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"错误: {inner_response.get('errMsg', '任务处理失败')}", None

        task_status = inner_response.get("data", {}).get("status")
        if task_status == "pending":
            return "pending", None

        # Task finished, process final audio
        output_audio_b64 = inner_response.get("data", {}).get("output_audio_b64")
        if not output_audio_b64:
            return "错误: 任务成功但未返回音频数据。", None

        try:
            decoded_audio_bytes = base64.b64decode(output_audio_b64)
            rate, audio_data = wavfile.read(io.BytesIO(decoded_audio_bytes))
            return "done", (rate, audio_data)
        except Exception as e:
            logger.error(f"Error decoding final audio for task {task_id}: {e}")
            return f"错误: 解码音频失败 - {e}", None

    def asr_start_task(self, audio_path: str) -> str:
        """提交ASR任务并返回task_id"""
        processed_path = self._preprocess_audio(audio_path)
        if not processed_path:
            return "错误: 音频预处理失败"

        with open(processed_path, "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        submit_payload = {
            "task_name": "asr",
            "audio_b64": audio_b64,
            "messages": [
                {
                    "role": "HUMAN",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please recognize the language of this speech and transcribe it. Format: oral, punctuated.",
                        },
                        {"type": "audio", "audio": "placeholder"},
                    ],
                }
            ],
        }

        # 复用通用的异步提交逻辑
        initial_response = self._submit_tts_task(submit_payload)
        logger.info(f"ASR task submission response: {initial_response}")

        if not initial_response.get("success"):
            return f"错误: {initial_response.get('errorMessage', 'ASR 任务提交失败')}"

        result_content_str = initial_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "错误: 提交响应中缺少 'result' 字段"

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"错误: {inner_response.get('errMsg', '内部API调用失败')}"

        task_id = inner_response.get("data", {}).get("task_id")
        if not task_id:
            return "错误: 未能从响应中获取 task_id"

        logger.info(f"ASR task started with ID: {task_id}")
        return task_id

    def asr_check_task(self, task_id: str) -> (str, str or None):
        """检查ASR任务状态并返回结果"""
        # 复用通用的异步轮询逻辑
        poll_response = self._poll_tts_result(task_id)

        if not poll_response.get("success"):
            return f"错误: {poll_response.get('errorMessage', '轮询失败')}", None

        result_content_str = poll_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "pending", None  # 任务仍在处理中，尚未返回结果

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"错误: {inner_response.get('errMsg', '任务处理失败')}", None

        task_status = inner_response.get("data", {}).get("status")
        if task_status == "pending":
            return "pending", None

        # 任务完成，处理最终文本结果
        transcribed_text = inner_response.get("data", {}).get("transcribed_text")
        if transcribed_text is None:  # Use `is None` to allow empty string results
            return "错误: 任务成功但未返回识别文本。", None

        # API返回 "Language\tText" 格式, 我们只取文本部分
        final_text = transcribed_text.split("\t", 1)[-1]
        return "done", final_text

    def edit_start_task(self, audio_path: str, instruction_text: str) -> str:
        """提交Edit任务并返回task_id"""
        processed_path = self._preprocess_audio(audio_path)
        if not processed_path:
            return "错误: 音频预处理失败"

        with open(processed_path, "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        messages = [
            {
                "role": "HUMAN",
                "content": [
                    {"type": "audio", "audio": "placeholder", "target_sample_rate": 16000},
                    {
                        "type": "text",
                        "text": f"<prompt>Please recognize the language of this speech and transcribe it. And {instruction_text}\\n</prompt>",
                    },
                ],
            }
        ]

        submit_payload = {"task_name": "edit", "audio_b64": audio_b64, "messages": messages}

        # 调用专用的 Edit 任务提交逻辑
        initial_response = self._submit_edit_task(submit_payload)
        logger.info(f"Edit task submission response: {initial_response}")

        if not initial_response.get("success"):
            return f"错误: {initial_response.get('errorMessage', 'Edit 任务提交失败')}"

        result_content_str = initial_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "错误: 提交响应中缺少 'result' 字段"

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"错误: {inner_response.get('errMsg', '内部API调用失败')}"

        task_id = inner_response.get("data", {}).get("task_id")
        if not task_id:
            return "错误: 未能从响应中获取 task_id"

        logger.info(f"Edit task started with ID: {task_id}")
        return task_id

    def edit_check_task(self, task_id: str) -> (str, str or None, tuple or None):
        """检查Edit任务状态并返回结果 (status, text_result, audio_result)"""
        # 调用专用的 Edit 任务轮询逻辑
        poll_response = self._poll_edit_result(task_id)

        if not poll_response.get("success"):
            return "错误", f"轮询失败: {poll_response.get('errorMessage', '未知错误')}", None

        result_content_str = poll_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "pending", "任务处理中...", None

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return "错误", f"任务处理失败: {inner_response.get('errMsg', '未知错误')}", None

        task_status = inner_response.get("data", {}).get("status")
        if task_status == "pending":
            return "pending", "任务处理中...", None

        # 任务完成，解析结果
        data = inner_response.get("data", {})
        edited_text = data.get("edited_text", "接口调用成功但未返回文本。")
        output_audio_b64 = data.get("output_audio_b64")

        if not output_audio_b64:
            logger.warning(f"Edit task {task_id} did not return audio data.")
            # 返回空白音频
            return "done", edited_text, (blank_rate, blank_audio_data)

        try:
            decoded_audio_bytes = base64.b64decode(output_audio_b64)
            rate, audio_data = wavfile.read(io.BytesIO(decoded_audio_bytes))
            return "done", edited_text, (rate, audio_data)
        except Exception as e:
            logger.error(f"Error decoding final audio for edit task {task_id}: {e}")
            return "错误", f"解码音频失败: {e}", None

    # Instruct Model Methods ===========================================
    def submit_instruct_task(self, payload: dict) -> str:
        """提交可控TTS任务"""
        # 处理参考音频 (如果存在且是文件路径)
        prompt_audio = payload.get("prompt_audio")
        prompt_wav_b64 = None

        if prompt_audio:
            # 如果已经是 Base64 字符串（虽然 UI 传递的通常是路径），则保留
            # 否则尝试作为文件路径读取
            if os.path.isfile(prompt_audio):
                processed_path = self._preprocess_audio(prompt_audio)
                if processed_path:
                    with open(processed_path, "rb") as f:
                        prompt_wav_b64 = base64.b64encode(f.read()).decode("utf-8")
                else:
                    return "错误: 音频文件处理失败"
            else:
                # 假设是 Base64 或无效路径，暂不处理
                pass

        # 构造 API 参数
        call_args = {
            "text": payload.get("text"),
            "caption": payload.get("caption"),
            "seed": payload.get("seed"),
            "prompt_wav_b64": prompt_wav_b64,
        }

        # 移除 None 值参数 (某些模式下 prompt_wav_b64 可选)
        call_args = {k: v for k, v in call_args.items() if v is not None}

        response = self._call_webgw_api(
            call_name="submit_task",
            call_args=call_args,
            api_project="260113-ming-uniaudio-instruct",
        )

        if not response.get("success"):
            return f"错误: {response.get('errorMessage', '提交失败')}"

        result_content = response.get("resultMap", {}).get("result")

        # 打印日志
        logger.info(f"Instruct task submission response content: {response}")

        # 解析内部 JSON (Maya 返回的结构)
        if isinstance(result_content, str):
            try:
                result_data = json.loads(result_content)
            except json.JSONDecodeError:
                return f"错误: 响应格式无效 - {result_content}"
        else:
            result_data = result_content

        # 注意：这里直接返回 data 中的 task_id
        # Maya 返回格式: { "task_id": "...", "status": "pending" }
        task_id = result_data.get("task_id")
        if not task_id:
            return f"错误: 响应中缺少 task_id - {result_data}"

        logger.info(f"Instruct task started with ID: {task_id}")

        return task_id

    def poll_instruct_task(self, task_id: str) -> (str, tuple or None):
        """轮询可控TTS任务结果"""
        response = self._call_webgw_api(
            call_name="poll_task",
            call_args={"task_id": task_id},
            api_project="260113-ming-uniaudio-instruct",
        )

        if not response.get("success"):
            return f"错误: {response.get('errorMessage', '轮询请求失败')}", None

        result_content = response.get("resultMap", {}).get("result")

        if isinstance(result_content, str):
            try:
                result_data = json.loads(result_content)
            except json.JSONDecodeError:
                return f"错误: 响应格式无效", None
        else:
            result_data = result_content or {}

        status = result_data.get("status")

        if status == "pending":
            return "pending", None
        elif status == "failed":
            return f"错误: {result_data.get('error_message', '任务执行失败')}", None
        elif status == "success" or status == "completed":
            output_audio_b64 = result_data.get("output_audio_b64")
            if not output_audio_b64:
                return "错误: 任务成功但未返回音频", None
            try:
                decoded_audio = base64.b64decode(output_audio_b64)
                rate, audio_data = wavfile.read(io.BytesIO(decoded_audio))
                return "done", (rate, audio_data)
            except Exception as e:
                logger.error(f"Failed to decode instruct audio: {e}")
                return f"错误: 音频解码失败 - {e}", None
        else:
            return f"错误: 未知状态 '{status}'", None


# Gradio界面构建 =======================================================
class GradioInterface:
    def __init__(self, speech_service: SpeechService):
        self.service = speech_service

        # 初始化 UniAudio V4 MOE 演示 Tab
        self.uniaudio_demo_tab = MingOmniTTSDemoTab(
            webgw_url=self.service.WEB_GW_API_URL,
            webgw_api_key=self.service.WEB_GW_API_KEY,
            webgw_app_id=self.service.WEB_GW_APP_ID,
        )

        self.custom_css = """
            .equal-height-group {
                height: 100%;
                min-height: 400px;          /* 最小高度 */
                border: 1px solid #e0e0e0;  /* 扁平风格边框 */
                border-radius: 4px;         /* 略微圆角 */
                padding: 16px;
                background-color: #ffffff;  /* 干净的白色背景 */
                box-shadow: none;           /* 移除阴影以符合扁平风格 */
                display: flex;
                flex-direction: column;
                justify-content: space-between; /* 内容上下分布更整齐 */
                gap: 10px;
            }
            .audio-md {
                background: white !important;
                border: unset !important;
                padding-bottom: 10px;
            }
            input, textarea {
                font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, Courier, monospace !important;
            }
            """
        self.demo = self._create_interface()

    def play_audio(self, content):
        # 功能方法：播放音频。输入 gr.Audio
        logger.info(f"Playing audio from content: {content}")
        return gr.update(autoplay=True)

    def _create_interface(self) -> gr.Blocks:
        """构建Gradio界面"""

        theme = gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.blue,
            neutral_hue=gr.themes.colors.gray,
            font=["PingFang SC", "SF Pro", "Microsoft YaHei", "Segoe UI", "sans-serif"],
        )
        with gr.Blocks(
            title="Ming-omni-tts 演示",
            analytics_enabled=False,
            css=self.custom_css,
            theme=theme,
            fill_width=True,
        ) as demo:
            image_path = "figures/ant_bailing2.png"
            try:
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                base64_src = f"data:image/png;base64,{encoded_string}"
            except Exception:
                base64_src = "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="

            with gr.Row(variant="panel", elem_id="header-row"):
                gr.HTML(
                    f"""<div style="position: relative; width: 100%; display: flex; align-items: center; justify-content: center; padding: 10px 0;"><div style="position: absolute; left: 20px; top: 50%; transform: translateY(-50%);"><img src="{base64_src}" alt="Logo" style="height: 60px;"></div><div style="text-align: center;"><h1 style="margin: 0; font-size: 1.8em;">百灵系列 Ming-omni-tts 语音模型演示</h1><p style="margin: 5px 0 0 0; font-size: 1.1em; color: #555;">提供一站式语音识别、语音编辑和语音合成能力。 [Ming-v2 系列](https://huggingface.co/collections/inclusionAI/ming-v2)</p></div></div>"""
                )

            with gr.Tabs():
                # 引入 UniAudio V4 MOE 综合演示标签页
                self.uniaudio_demo_tab.create_tab()

                with gr.Tab("基础能力 (ASR/Edit/TTS)"):
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1, min_width="300px"):
                            with gr.Group(elem_classes="equal-height-group"):
                                gr.Markdown(
                                    "### 🎤 语音转写（ASR）\n将您上传的音频文件自动转写为文字。",
                                    elem_classes="audio-md",
                                )
                                asr_task_id_state = gr.State(None)
                                asr_polling_counter = gr.Number(value=0, visible=False)
                                input_audio = gr.Audio(
                                    sources=["upload", "microphone"],
                                    type="filepath",
                                    label="原始音频",
                                    elem_id="input_audio_player",
                                )
                                btn_input = gr.Button(
                                    "播放音频", elem_id="btn_input_play", variant="secondary"
                                )
                                btn_input.click(
                                    fn=self.play_audio,
                                    inputs=[],
                                    outputs=[],
                                    js="""() => { const playBtn = document.querySelector('#input_audio_player [aria-label=\"Play\"]'); if (playBtn) { playBtn.click(); } }""",
                                )
                                transcription_box = gr.Textbox(label="识别结果", interactive=False)

                        with gr.Column(scale=1, min_width="300px"):
                            with gr.Group(elem_classes="equal-height-group"):
                                gr.Markdown(
                                    "### ✏️ 智能编辑（Editing）\n通过简单的自然语言指令，对音频和文本进行修改。",
                                    elem_classes="audio-md",
                                )
                                edit_task_id_state = gr.State(None)
                                edit_polling_counter = gr.Number(value=0, visible=False)
                                continuous_edit = gr.Checkbox(label="启用连续编辑")
                                instruction_box = gr.Textbox(
                                    label="编辑指令", placeholder="例如: '给音频降噪'"
                                )
                                submit_btn = gr.Button("执行编辑", variant="primary")
                                output_text = gr.Textbox(label="编辑后文本", interactive=False)
                                output_audio = gr.Audio(
                                    label="编辑后音频",
                                    autoplay=True,
                                    interactive=False,
                                    elem_id="output_audio_player",
                                )
                                btn_edit = gr.Button("播放音频", variant="secondary")
                                btn_edit.click(
                                    fn=self.play_audio,
                                    inputs=[],
                                    outputs=[],
                                    js="""() => { const playBtn = document.querySelector('#output_audio_player [aria-label=\"Play\"]'); if (playBtn) { playBtn.click(); } }""",
                                )
                                continuous_btn = gr.Button("连续编辑", visible=False)

                        with gr.Column(scale=1, min_width="300px"):
                            with gr.Group(elem_classes="equal-height-group"):
                                gr.Markdown(
                                    "### 🔊 语音合成（TTS）\n上传参考音频，克隆其音色，将任意文本合成为自然的语音。",
                                    elem_classes="audio-md",
                                )
                                prompt_asr_task_id_state = gr.State(None)
                                prompt_asr_polling_counter = gr.Number(value=0, visible=False)
                                task_id_state = gr.State(None)
                                polling_counter = gr.Number(value=0, visible=False)
                                prompt_audio = gr.Audio(
                                    type="filepath", label="参考音频", elem_id="prompt_audio_player"
                                )
                                btn_prompt = gr.Button("播放音频", variant="secondary")
                                btn_prompt.click(
                                    fn=self.play_audio,
                                    inputs=[],
                                    outputs=[],
                                    js="""() => { const playBtn = document.querySelector('#prompt_audio_player [aria-label=\"Play\"]'); if (playBtn) { playBtn.click(); } }""",
                                )
                                prompt_text = gr.Textbox(label="参考文本", interactive=False)
                                tts_box = gr.Textbox(
                                    label="合成文本", placeholder="输入需要合成的文本"
                                )
                                tts_btn = gr.Button("合成语音", variant="primary")
                                synthesized_audio = gr.Audio(
                                    label="合成音频", interactive=False, autoplay=True
                                )
                                btn_tts = gr.Button("播放音频", variant="secondary")
                                btn_tts.click(
                                    fn=self.play_audio,
                                    inputs=[],
                                    outputs=[],
                                    js="""() => { const playBtn = document.querySelector('#synthesized_audio [aria-label=\"Play\"]'); if (playBtn) { playBtn.click(); } }""",
                                )

                    with gr.Row():
                        with gr.Column(scale=2, min_width="600px"):
                            gr.Examples(
                                examples=self._get_examples(),
                                inputs=[input_audio, instruction_box],
                                outputs=[
                                    input_audio,
                                    instruction_box,
                                    transcription_box,
                                    output_text,
                                    output_audio,
                                ],
                                fn=self.process_edit_example,
                                label="语音编辑示例",
                                run_on_click=True,
                                cache_examples="lazy",
                            )
                        with gr.Column(scale=1, min_width="300px"):
                            gr.Examples(
                                examples=self._get_tts_examples(),
                                inputs=[prompt_audio, tts_box],
                                outputs=[prompt_audio, tts_box],
                                fn=self.fill_tts_example,
                                label="语音合成示例",
                                run_on_click=False,
                                cache_examples="lazy",
                            )

            # 事件绑定
            input_audio.change(
                self.asr_start_wrapper,
                inputs=[input_audio],
                outputs=[asr_task_id_state, transcription_box, asr_polling_counter],
            )
            asr_polling_counter.change(
                self.asr_check_wrapper,
                inputs=[asr_task_id_state, asr_polling_counter],
                outputs=[transcription_box, asr_polling_counter],
                every=2,
            )

            submit_btn.click(
                self.edit_start_wrapper,
                inputs=[input_audio, instruction_box],
                outputs=[edit_task_id_state, edit_polling_counter, output_text, output_audio],
            )
            edit_polling_counter.change(
                self.edit_check_wrapper,
                inputs=[edit_task_id_state, edit_polling_counter],
                outputs=[output_text, output_audio, edit_polling_counter],
                every=2,
            )

            continuous_edit.change(
                self.toggle_continuous, inputs=continuous_edit, outputs=continuous_btn
            )
            continuous_btn.click(
                self.chain_edit,
                inputs=[output_audio],
                outputs=[input_audio, instruction_box, output_text, output_audio],
            )

            prompt_audio.change(
                self.prompt_asr_start_wrapper,
                inputs=[prompt_audio],
                outputs=[prompt_asr_task_id_state, prompt_text, prompt_asr_polling_counter],
            )
            prompt_asr_polling_counter.change(
                self.prompt_asr_check_wrapper,
                inputs=[prompt_asr_task_id_state, prompt_asr_polling_counter],
                outputs=[prompt_text, prompt_asr_polling_counter],
                every=2,
            )

            tts_btn.click(
                self.tts_start_wrapper,
                inputs=[tts_box, prompt_audio, prompt_text],
                outputs=[task_id_state, synthesized_audio, polling_counter],
            )
            polling_counter.change(
                self.tts_check_wrapper,
                inputs=[task_id_state, polling_counter],
                outputs=[synthesized_audio, polling_counter],
                every=2,
            )

            with gr.Accordion("麦克风权限不工作？点我查看解决方案", open=False):
                gr.Markdown(
                    """
                    如果你在使用 Chrome 浏览器时，麦克风权限无法正常工作，且本应用部署在非 HTTPS 站点上，请尝试以下步骤：

                    1.  在 Chrome 地址栏中输入 `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
                    2.  将该标志的状态改为 **Enabled**。
                    3.  在出现的“Enabled domains”或“启用的域名”输入框中，输入本应用的域名。
                    4.  **重要：** 彻底关闭并重新启动 Chrome 浏览器。

                    完成这些步骤后，你应该就能成功授予该页面麦克风权限了。
                """
                )

        return demo

    def _get_tts_examples(self) -> list:
        """获取示例数据"""
        return [
            [
                "audio/日常女声.wav",
                "我们发现，大约三分之二的猫更偏好左侧睡眠姿势，这样它们的左侧视野、也就是右脑控制的视野，可以更好地观察接近的动物，不会被自己的身体遮挡。",
            ],
            [
                "audio/日常男声.wav",
                "大语言模型通过学习海量的文本数据，掌握了人类语言的复杂规律。它不仅能精准理解你的指令，还能像真人一样流畅地协助你写作或编程。",
            ],
            ["audio/罗翔.wav", "真正的勇敢，不是无所畏惧，而是明知恐惧仍选择做正确的事。"],
            ["audio/阿洛娜.wav", "老师，我跟你讲哦，今天天气超~好的！"],
        ]

    def _get_examples(self) -> list:
        """获取示例数据"""
        return [
            ["audio/天气预报.wav", "substitute '需要做好防暑工作' with '大家躲在空调房里就好了。'"],
            ["audio/土豆能算主食吗.wav", "insert '还有各种菠萝汉堡等离谱食物。' at the end"],
            ["audio/高尔夫.wav", "insert '然后' before the character or word at index 12"],
            ["audio/可持续发展.wav", "delete the characters or words from index 3 to index 10"],
            ["audio/珠三角城市.wav", "delete '珠三角城市群'"],
            ["audio/小说朗读.wav", "substitute '提升' with '削弱自己的'"],
        ]

    # 包装器函数 =======================================================

    def edit_start_wrapper(self, audio_path: str, instruction: str):
        """语音编辑异步任务启动包装器"""
        logger.info(
            f"Edit start wrapper called with audio: {audio_path}, instruction: {instruction}"
        )
        if not audio_path or not instruction:
            # 返回值需要对应 UI outputs: task_id, polling_counter, output_text, output_audio
            return None, 0, "错误: 请提供音频和编辑指令", (blank_rate, blank_audio_data)

        task_id = self.service.edit_start_task(audio_path, instruction)
        if task_id.startswith("错误:"):
            return None, 0, task_id, (blank_rate, blank_audio_data)

        status_message = f"编辑任务已提交 (ID: ...{task_id[-6:]})，等待结果..."
        # 返回 task_id, 启动轮询计数器, 更新文本输出框为状态信息, 清空音频输出
        return task_id, 1, status_message, gr.update(value=None)

    def edit_check_wrapper(self, task_id: str, polling_counter: int):
        """语音编辑异步任务状态检查包装器"""
        if not task_id or polling_counter == 0:
            # 没有任务或轮询未启动，直接返回，不更新任何内容
            return gr.update(), gr.update(), polling_counter

        logger.info(f"Polling Edit task {task_id}, counter: {polling_counter}")
        status, text_result, audio_result = self.service.edit_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2
            status_message = f"编辑中... (已用时 {elapsed}s)"
            # 更新文本输出框为状态信息, 音频不变, 轮询计数器+1
            return status_message, gr.update(), polling_counter + 1
        elif status == "done":
            # 返回最终结果, 停止轮询
            return text_result, audio_result, 0
        else:  # 发生错误
            # 在文本框显示错误信息, 返回空白音频, 停止轮询
            return text_result, audio_result or (blank_rate, blank_audio_data), 0

    def tts_start_wrapper(self, text: str, prompt_wav_path: str, prompt_text: str):
        """语音合成任务启动包装器"""
        logger.info(
            f"TTS start wrapper called with text length: {len(text)}, prompt_wav_path: {prompt_wav_path}, prompt_text length: {len(prompt_text)}"
        )
        if not all([text, prompt_wav_path, prompt_text]):
            # outputs: [task_id_state, synthesized_audio, polling_counter]
            return None, gr.update(label="错误：缺少合成文本、参考音频或参考文本。", value=None), 0

        task_id = self.service.tts_start_task(text, prompt_wav_path, prompt_text)
        if task_id.startswith("错误:"):
            return None, gr.update(label=task_id, value=None), 0

        status_message = f"任务已提交 (ID: ...{task_id[-6:]})，开始轮询..."
        return task_id, gr.update(label=status_message, value=None), 1

    def tts_check_wrapper(self, task_id: str, polling_counter: int):
        """语音合成任务状态检查包装器"""
        if not task_id or polling_counter == 0:
            # outputs: [synthesized_audio, polling_counter]
            return gr.update(), 0

        logger.info(f"Polling TTS task {task_id}, counter: {polling_counter}")
        status, result = self.service.tts_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2  # Approx. 2s per check
            status_message = f"合成中... ({elapsed}s)"
            return gr.update(label=status_message), polling_counter + 1
        elif status == "done":
            return gr.update(label="合成成功！", value=result), 0
        else:  # Error case
            return gr.update(label=status, value=None), 0

    def asr_start_wrapper(self, audio_path: str):
        """ASR 异步任务启动包装器"""
        logger.info(f"ASR start wrapper called with audio_path: {audio_path}")
        if not audio_path:
            return None, "错误：请先上传一个音频文件。", 0

        task_id = self.service.asr_start_task(audio_path)
        if task_id.startswith("错误:"):
            return None, task_id, 0

        status_message = f"识别任务已提交 (ID: ...{task_id[-6:]})，等待结果..."
        # 返回 task_id 到 state, 更新状态信息, 启动轮询计数器
        return task_id, status_message, 1

    def asr_check_wrapper(self, task_id: str, polling_counter: int):
        """ASR 异步任务状态检查包装器"""
        if not task_id or polling_counter == 0:
            # 没有任务或轮询未启动，直接返回
            return gr.update(), 0

        logger.info(f"Polling ASR task {task_id}, counter: {polling_counter}")
        status, result = self.service.asr_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2  # 假设轮询间隔为2秒
            status_message = f"识别中... (已用时 {elapsed}s)"
            # 更新状态信息，并递增轮询计数器以继续轮询
            return status_message, polling_counter + 1
        elif status == "done":
            status_message = "识别成功！"
            # 停止轮询 (polling_counter=0)，并返回最终识别文本
            # 注意：这里我们将最终结果（result）和状态信息（status_message）都更新到同一个文本框中。
            # Gradio 会将 result 设置为文本框的值。
            return result, 0
        else:  # 发生错误
            status_message = f"识别失败: {status}"
            # 停止轮询，并显示错误信息
            return status_message, 0

    def prompt_asr_start_wrapper(self, audio_path: str):
        """专门用于TTS参考音频的ASR异步任务启动包装器"""
        logger.info(f"Prompt ASR start wrapper called with audio_path: {audio_path}")
        if not audio_path:
            # outputs: [task_id_state, output_textbox, polling_counter]
            return None, "错误：请先上传参考音频。", 0

        task_id = self.service.asr_start_task(audio_path)
        if task_id.startswith("错误:"):
            return None, task_id, 0

        status_message = f"参考音频识别任务已提交，等待结果..."
        return task_id, status_message, 1

    def prompt_asr_check_wrapper(self, task_id: str, polling_counter: int):
        """专门用于TTS参考音频的ASR异步任务状态检查包装器"""
        if not task_id or polling_counter == 0:
            return gr.update(), 0

        logger.info(f"Polling Prompt ASR task {task_id}, counter: {polling_counter}")
        status, result = self.service.asr_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2
            status_message = f"识别中... (已用时 {elapsed}s)"
            return status_message, polling_counter + 1
        elif status == "done":
            return result, 0
        else:  # 发生错误
            return f"识别失败: {result}", 0

    # 界面交互函数 =====================================================
    @staticmethod
    def toggle_continuous(is_checked: bool) -> dict:
        """切换连续编辑按钮可见性"""
        return gr.update(visible=is_checked)

    @staticmethod
    def chain_edit(current_audio):
        """链式编辑处理"""
        if not current_audio:
            return gr.update(), gr.update(), gr.update(), gr.update()
        return (
            gr.update(value=current_audio),  # 更新input_audio
            gr.update(value=""),  # 清空instruction
            gr.update(value=""),  # 清空output_text
            gr.update(value=None),  # 清空output_audio
        )

    def fill_tts_example(self, audio_path: str, text: str) -> tuple:
        """填充TTS示例数据"""
        # This is for run_on_click=False, it just populates the fields
        return audio_path, text

    def process_edit_example(self, audio_path: str, instruction: str) -> tuple:
        # Populate input fields
        updated_input_audio = gr.update(value=audio_path)
        updated_instruction_box = gr.update(value=instruction)

        # ASR
        transcription = self.service.asr_start_task(audio_path)
        updated_transcription_box = gr.update(value=transcription)

        # Editing
        edited_text, (rate, audio_data) = self.service.edit_voice(
            audio_path, instruction, transcription
        )
        updated_output_text = gr.update(value=edited_text)
        updated_output_audio = gr.update(value=(rate, audio_data))

        return (
            updated_input_audio,
            updated_instruction_box,
            updated_transcription_box,
            updated_output_text,
            updated_output_audio,
        )

    @staticmethod
    def chain_edit(current_audio):
        """链式编辑处理"""
        if not current_audio:
            return gr.update(), gr.update(), gr.update(), gr.update()
        return (
            gr.update(value=current_audio),  # 更新input_audio
            gr.update(value=""),  # 清空instruction
            gr.update(value=""),  # 清空output_text
            gr.update(value=None),  # 清空output_audio
        )

    def fill_example(self, audio_path: str, instruction: str) -> tuple:
        """填充示例数据"""
        return (
            audio_path,
            instruction,
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=None),
        )

    def process_edit_example(self, audio_path: str, instruction: str):
        # Populate input fields
        yield gr.update(value=audio_path), gr.update(
            value=instruction
        ), "正在提交识别任务...", gr.update(), gr.update()

        # --- ASR Task ---
        asr_task_id = self.service.asr_start_task(audio_path)
        if asr_task_id.startswith("错误:"):
            yield gr.update(), gr.update(), asr_task_id, gr.update(), gr.update()
            return

        yield gr.update(), gr.update(), "识别任务已提交，等待结果...", gr.update(), gr.update()

        transcription = ""
        for i in range(30):  # Timeout after 60s
            time.sleep(2)
            status, result = self.service.asr_check_task(asr_task_id)
            if status == "pending":
                yield gr.update(), gr.update(), f"识别中... ({(i+1)*2}s)", gr.update(), gr.update()
            elif status == "done":
                transcription = result
                yield gr.update(), gr.update(), transcription, gr.update(), gr.update()
                break
            else:  # Error
                yield gr.update(), gr.update(), f"识别失败: {result}", gr.update(), gr.update()
                return

        if not transcription:
            yield gr.update(), gr.update(), "识别超时或未返回结果", gr.update(), gr.update()
            return

        # --- Edit Task ---
        yield gr.update(), gr.update(), transcription, "正在提交编辑任务...", gr.update(value=None)

        edit_task_id = self.service.edit_start_task(audio_path, instruction)
        if edit_task_id.startswith("错误:"):
            yield gr.update(), gr.update(), transcription, f"编辑任务提交失败: {edit_task_id}", (
                blank_rate,
                blank_audio_data,
            )
            return

        yield gr.update(), gr.update(), transcription, "编辑任务已提交，等待结果...", gr.update(
            value=None
        )

        for i in range(60):  # Timeout after 120s
            time.sleep(2)
            status, text_result, audio_result = self.service.edit_check_task(edit_task_id)
            if status == "pending":
                yield gr.update(), gr.update(), transcription, f"编辑中... ({(i+1)*2}s)", gr.update()
            elif status == "done":
                yield gr.update(), gr.update(), transcription, text_result, audio_result
                return
            else:  # Error
                yield gr.update(), gr.update(), transcription, f"编辑失败: {text_result}", audio_result or (
                    blank_rate,
                    blank_audio_data,
                )
                return

        yield gr.update(), gr.update(), transcription, "编辑任务超时", (
            blank_rate,
            blank_audio_data,
        )

    def launch(self):
        """启动Gradio应用"""
        server_name = os.getenv("GRADIO_APP_HOST", "127.0.0.1")
        server_port = int(os.getenv("GRADIO_APP_PORT", "7860"))
        self.demo.launch(share=False, server_name=server_name, server_port=server_port)


# 主程序 ==============================================================
if __name__ == "__main__":
    # 初始化服务
    speech_service = SpeechService()

    # 创建并启动Gradio界面
    gradio_interface = GradioInterface(speech_service)
    gradio_interface.demo.queue(default_concurrency_limit=10).launch()
