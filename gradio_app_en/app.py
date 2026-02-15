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
        """Submit TTS task and return task_id"""
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
            return f"Error: {initial_response.get('errorMessage', 'Task submission failed')}"

        result_content_str = initial_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "Error: Missing 'result' field in submission response"

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"Error: {inner_response.get('errMsg', 'Internal API call failed')}"

        task_id = inner_response.get("data", {}).get("task_id")
        if not task_id:
            return "Error: Failed to get task_id from response"

        logger.info(f"TTS task started with ID: {task_id}")
        return task_id

    def tts_check_task(self, task_id: str) -> (str, tuple or None):
        """Check TTS task status and return result"""
        poll_response = self._poll_tts_result(task_id)

        if not poll_response.get("success"):
            return f"Error: {poll_response.get('errorMessage', 'Polling failed')}", None

        result_content_str = poll_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "pending", None  # Still pending, no result map yet

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"Error: {inner_response.get('errMsg', 'Task processing failed')}", None

        task_status = inner_response.get("data", {}).get("status")
        if task_status == "pending":
            return "pending", None

        # Task finished, process final audio
        output_audio_b64 = inner_response.get("data", {}).get("output_audio_b64")
        if not output_audio_b64:
            return "Error: Task succeeded but no audio data returned.", None

        try:
            decoded_audio_bytes = base64.b64decode(output_audio_b64)
            rate, audio_data = wavfile.read(io.BytesIO(decoded_audio_bytes))
            return "done", (rate, audio_data)
        except Exception as e:
            logger.error(f"Error decoding final audio for task {task_id}: {e}")
            return f"Error: Failed to decode audio - {e}", None

    def asr_start_task(self, audio_path: str) -> str:
        """Submit ASR task and return task_id"""
        processed_path = self._preprocess_audio(audio_path)
        if not processed_path:
            return "Error: Audio preprocessing failed"

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

        # Reuse common async submission logic
        initial_response = self._submit_tts_task(submit_payload)
        logger.info(f"ASR task submission response: {initial_response}")

        if not initial_response.get("success"):
            return f"Error: {initial_response.get('errorMessage', 'ASR task submission failed')}"

        result_content_str = initial_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "Error: Missing 'result' field in submission response"

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"Error: {inner_response.get('errMsg', 'Internal API call failed')}"

        task_id = inner_response.get("data", {}).get("task_id")
        if not task_id:
            return "Error: Failed to get task_id from response"

        logger.info(f"ASR task started with ID: {task_id}")
        return task_id

    def asr_check_task(self, task_id: str) -> (str, str or None):
        """Check ASR task status and return result"""
        # Reuse common async polling logic
        poll_response = self._poll_tts_result(task_id)

        if not poll_response.get("success"):
            return f"Error: {poll_response.get('errorMessage', 'Polling failed')}", None

        result_content_str = poll_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "pending", None  # Task still processing, no results yet

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"Error: {inner_response.get('errMsg', 'Task processing failed')}", None

        task_status = inner_response.get("data", {}).get("status")
        if task_status == "pending":
            return "pending", None

        # Task finished, process final text result
        transcribed_text = inner_response.get("data", {}).get("transcribed_text")
        if transcribed_text is None:  # Use `is None` to allow empty string results
            return "Error: Task succeeded but no transcription text returned.", None

        # API returns "Language\tText" format, we only take the text part
        final_text = transcribed_text.split("\t", 1)[-1]
        return "done", final_text

    def edit_start_task(self, audio_path: str, instruction_text: str) -> str:
        """Submit Edit task and return task_id"""
        processed_path = self._preprocess_audio(audio_path)
        if not processed_path:
            return "Error: Audio preprocessing failed"

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

        # Call dedicated Edit task submission logic
        initial_response = self._submit_edit_task(submit_payload)
        logger.info(f"Edit task submission response: {initial_response}")

        if not initial_response.get("success"):
            return f"Error: {initial_response.get('errorMessage', 'Edit task submission failed')}"

        result_content_str = initial_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "Error: Missing 'result' field in submission response"

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return f"Error: {inner_response.get('errMsg', 'Internal API call failed')}"

        task_id = inner_response.get("data", {}).get("task_id")
        if not task_id:
            return "Error: Failed to get task_id from response"

        logger.info(f"Edit task started with ID: {task_id}")
        return task_id

    def edit_check_task(self, task_id: str) -> (str, str or None, tuple or None):
        """Check Edit task status and return result (status, text_result, audio_result)"""
        # Call dedicated Edit task polling logic
        poll_response = self._poll_edit_result(task_id)

        if not poll_response.get("success"):
            return "Error", f"Polling failed: {poll_response.get('errorMessage', 'Unknown error')}", None

        result_content_str = poll_response.get("resultMap", {}).get("result")
        if not result_content_str:
            return "pending", "Processing...", None

        if isinstance(result_content_str, str):
            inner_response = json.loads(result_content_str)
        else:
            inner_response = result_content_str

        if inner_response.get("success") != "True":
            return "Error", f"Task processing failed: {inner_response.get('errMsg', 'Unknown error')}", None

        task_status = inner_response.get("data", {}).get("status")
        if task_status == "pending":
            return "pending", "Processing...", None

        # Task finished, parse results
        data = inner_response.get("data", {})
        edited_text = data.get("edited_text", "API call successful but no text returned.")
        output_audio_b64 = data.get("output_audio_b64")

        if not output_audio_b64:
            logger.warning(f"Edit task {task_id} did not return audio data.")
            # Return blank audio
            return "done", edited_text, (blank_rate, blank_audio_data)

        try:
            decoded_audio_bytes = base64.b64decode(output_audio_b64)
            rate, audio_data = wavfile.read(io.BytesIO(decoded_audio_bytes))
            return "done", edited_text, (rate, audio_data)
        except Exception as e:
            logger.error(f"Error decoding final audio for edit task {task_id}: {e}")
            return "Error", f"Failed to decode audio: {e}", None

    # Instruct Model Methods ===========================================
    def submit_instruct_task(self, payload: dict) -> str:
        """Submit controllable TTS task"""
        # Process reference audio (if exists and is file path)
        prompt_audio = payload.get("prompt_audio")
        prompt_wav_b64 = None

        if prompt_audio:
            # If it's already a Base64 string (though UI usually passes paths), keep it
            # Otherwise attempt to read as a file path
            if os.path.isfile(prompt_audio):
                processed_path = self._preprocess_audio(prompt_audio)
                if processed_path:
                    with open(processed_path, "rb") as f:
                        prompt_wav_b64 = base64.b64encode(f.read()).decode("utf-8")
                else:
                    return "Error: Audio file processing failed"
            else:
                # Assume it's Base64 or invalid path, don't process for now
                pass

        # Construct API parameters
        call_args = {
            "text": payload.get("text"),
            "caption": payload.get("caption"),
            "seed": payload.get("seed"),
            "prompt_wav_b64": prompt_wav_b64,
        }

        # Remove None values (prompt_wav_b64 optional in some modes)
        call_args = {k: v for k, v in call_args.items() if v is not None}

        response = self._call_webgw_api(
            call_name="submit_task",
            call_args=call_args,
            api_project="260113-ming-uniaudio-instruct",
        )

        if not response.get("success"):
            return f"Error: {response.get('errorMessage', 'Submission failed')}"

        result_content = response.get("resultMap", {}).get("result")

        # Logging
        logger.info(f"Instruct task submission response content: {response}")

        # Parse inner JSON (Maya returned structure)
        if isinstance(result_content, str):
            try:
                result_data = json.loads(result_content)
            except json.JSONDecodeError:
                return f"Error: Invalid response format - {result_content}"
        else:
            result_data = result_content

        # Note: Directly return task_id from data
        # Maya format: { "task_id": "...", "status": "pending" }
        task_id = result_data.get("task_id")
        if not task_id:
            return f"Error: Missing task_id in response - {result_data}"

        logger.info(f"Instruct task started with ID: {task_id}")

        return task_id

    def poll_instruct_task(self, task_id: str) -> (str, tuple or None):
        """Poll controllable TTS task result"""
        response = self._call_webgw_api(
            call_name="poll_task",
            call_args={"task_id": task_id},
            api_project="260113-ming-uniaudio-instruct",
        )

        if not response.get("success"):
            return f"Error: {response.get('errorMessage', 'Polling request failed')}", None

        result_content = response.get("resultMap", {}).get("result")

        if isinstance(result_content, str):
            try:
                result_data = json.loads(result_content)
            except json.JSONDecodeError:
                return f"Error: Invalid response format", None
        else:
            result_data = result_content or {}

        status = result_data.get("status")

        if status == "pending":
            return "pending", None
        elif status == "failed":
            return f"Error: {result_data.get('error_message', 'Task execution failed')}", None
        elif status == "success" or status == "completed":
            output_audio_b64 = result_data.get("output_audio_b64")
            if not output_audio_b64:
                return "Error: Task successful but no audio returned", None
            try:
                decoded_audio = base64.b64decode(output_audio_b64)
                rate, audio_data = wavfile.read(io.BytesIO(decoded_audio))
                return "done", (rate, audio_data)
            except Exception as e:
                logger.error(f"Failed to decode instruct audio: {e}")
                return f"Error: Audio decoding failed - {e}", None
        else:
            return f"Error: Unknown status '{status}'", None


# Gradio Interface Building =======================================================
class GradioInterface:
    def __init__(self, speech_service: SpeechService):
        self.service = speech_service

        # Initialize UniAudio V4 MOE Demo Tab
        self.uniaudio_demo_tab = MingOmniTTSDemoTab(
            webgw_url=self.service.WEB_GW_API_URL,
            webgw_api_key=self.service.WEB_GW_API_KEY,
            webgw_app_id=self.service.WEB_GW_APP_ID,
        )

        self.custom_css = """
            .equal-height-group {
                height: 100%;
                min-height: 400px;          /* Minimal height */
                border: 1px solid #e0e0e0;  /* Flat style border */
                border-radius: 4px;         /* Slightly rounded */
                padding: 16px;
                background-color: #ffffff;  /* Clean white background */
                box-shadow: none;           /* Remove shadow for flat style */
                display: flex;
                flex-direction: column;
                justify-content: space-between; /* Neat distribution */
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
        # Functional method: Play audio. Input gr.Audio
        logger.info(f"Playing audio from content: {content}")
        return gr.update(autoplay=True)

    def _create_interface(self) -> gr.Blocks:
        """Build Gradio Interface"""

        theme = gr.themes.Soft(
            primary_hue=gr.themes.colors.blue,
            secondary_hue=gr.themes.colors.blue,
            neutral_hue=gr.themes.colors.gray,
            font=["PingFang SC", "SF Pro", "Microsoft YaHei", "Segoe UI", "sans-serif"],
        )
        with gr.Blocks(
            title="Ming-omni-tts Demo",
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
                    f"""<div style="position: relative; width: 100%; display: flex; align-items: center; justify-content: center; padding: 10px 0;"><div style="position: absolute; left: 20px; top: 50%; transform: translateY(-50%);"><img src="{base64_src}" alt="Logo" style="height: 60px;"></div><div style="text-align: center;"><h1 style="margin: 0; font-size: 1.8em;">Bailing Series Ming-omni-tts Voice Model Demo</h1><p style="margin: 5px 0 0 0; font-size: 1.1em; color: #555;">One-stop Speech Recognition, Speech Editing, and Speech Synthesis. [Ming-v2 Series](https://huggingface.co/collections/inclusionAI/ming-v2)</p></div></div>"""
                )

            with gr.Tabs():
                # Introduce UniAudio V4 MOE Comprehensive Demo Tab
                self.uniaudio_demo_tab.create_tab()

                with gr.Tab("Core Capabilities (ASR/Edit/TTS)"):
                    with gr.Row(equal_height=True):
                        with gr.Column(scale=1, min_width="300px"):
                            with gr.Group(elem_classes="equal-height-group"):
                                gr.Markdown(
                                    "### 🎤 Speech-to-Text (ASR)\nAutomatically transcribe uploaded audio files into text.",
                                    elem_classes="audio-md",
                                )
                                asr_task_id_state = gr.State(None)
                                asr_polling_counter = gr.Number(value=0, visible=False)
                                input_audio = gr.Audio(
                                    sources=["upload", "microphone"],
                                    type="filepath",
                                    label="Original Audio",
                                    elem_id="input_audio_player",
                                )
                                btn_input = gr.Button(
                                    "Play Audio", elem_id="btn_input_play", variant="secondary"
                                )
                                btn_input.click(
                                    fn=self.play_audio,
                                    inputs=[],
                                    outputs=[],
                                    js="""() => { const playBtn = document.querySelector('#input_audio_player [aria-label=\"Play\"]'); if (playBtn) { playBtn.click(); } }""",
                                )
                                transcription_box = gr.Textbox(label="Transcription Result", interactive=False)

                        with gr.Column(scale=1, min_width="300px"):
                            with gr.Group(elem_classes="equal-height-group"):
                                gr.Markdown(
                                    "### ✏️ Smart Editing\nModify audio and text using simple natural language instructions.",
                                    elem_classes="audio-md",
                                )
                                edit_task_id_state = gr.State(None)
                                edit_polling_counter = gr.Number(value=0, visible=False)
                                continuous_edit = gr.Checkbox(label="Enable Continuous Editing")
                                instruction_box = gr.Textbox(
                                    label="Editing Instruction", placeholder="e.g.: 'Noise reduction for audio'"
                                )
                                submit_btn = gr.Button("Execute Edit", variant="primary")
                                output_text = gr.Textbox(label="Edited Text", interactive=False)
                                output_audio = gr.Audio(
                                    label="Edited Audio",
                                    autoplay=True,
                                    interactive=False,
                                    elem_id="output_audio_player",
                                )
                                btn_edit = gr.Button("Play Audio", variant="secondary")
                                btn_edit.click(
                                    fn=self.play_audio,
                                    inputs=[],
                                    outputs=[],
                                    js="""() => { const playBtn = document.querySelector('#output_audio_player [aria-label=\"Play\"]'); if (playBtn) { playBtn.click(); } }""",
                                )
                                continuous_btn = gr.Button("Continuous Edit", visible=False)

                        with gr.Column(scale=1, min_width="300px"):
                            with gr.Group(elem_classes="equal-height-group"):
                                gr.Markdown(
                                    "### 🔊 Voice Synthesis (TTS)\nUpload reference audio, clone its timbre, and synthesize any text into natural speech.",
                                    elem_classes="audio-md",
                                )
                                prompt_asr_task_id_state = gr.State(None)
                                prompt_asr_polling_counter = gr.Number(value=0, visible=False)
                                task_id_state = gr.State(None)
                                polling_counter = gr.Number(value=0, visible=False)
                                prompt_audio = gr.Audio(
                                    type="filepath", label="Reference Audio", elem_id="prompt_audio_player"
                                )
                                btn_prompt = gr.Button("Play Audio", variant="secondary")
                                btn_prompt.click(
                                    fn=self.play_audio,
                                    inputs=[],
                                    outputs=[],
                                    js="""() => { const playBtn = document.querySelector('#prompt_audio_player [aria-label=\"Play\"]'); if (playBtn) { playBtn.click(); } }""",
                                )
                                prompt_text = gr.Textbox(label="Reference Text", interactive=False)
                                tts_box = gr.Textbox(
                                    label="Synthesis Text", placeholder="Enter text for synthesis"
                                )
                                tts_btn = gr.Button("Synthesize Speech", variant="primary")
                                synthesized_audio = gr.Audio(
                                    label="Synthesized Audio", interactive=False, autoplay=True
                                )
                                btn_tts = gr.Button("Play Audio", variant="secondary")
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
                                label="Voice Editing Examples",
                                run_on_click=True,
                                cache_examples="lazy",
                            )
                        with gr.Column(scale=1, min_width="300px"):
                            gr.Examples(
                                examples=self._get_tts_examples(),
                                inputs=[prompt_audio, tts_box],
                                outputs=[prompt_audio, tts_box],
                                fn=self.fill_tts_example,
                                label="Voice Synthesis Examples",
                                run_on_click=False,
                                cache_examples="lazy",
                            )

            # Event Binding
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

            with gr.Accordion("Microphone permissions not working? Click for solutions", open=False):
                gr.Markdown(
                    """
                    If you are using Chrome and the microphone permissions are not working, and this application is deployed on a non-HTTPS site, please try the following steps:

                    1.  Enter `chrome://flags/#unsafely-treat-insecure-origin-as-secure` in the Chrome address bar.
                    2.  Change the status of this flag to **Enabled**.
                    3.  In the "Enabled domains" input box, enter the domain of this application.
                    4.  **Important:** Completely close and restart the Chrome browser.

                    After completing these steps, you should be able to successfully grant microphone permissions to this page.
                """
                )

        return demo

    def _get_tts_examples(self) -> list:
        """Get example data"""
        return [
            [
                "audio/日常女声.wav",
                "We found that about two-thirds of cats prefer to sleep on their left side, so that their left field of vision, which is the field of vision controlled by the right brain, can better observe approaching animals without being blocked by their own bodies.",
            ],
            [
                "audio/日常男声.wav",
                "Large language models have mastered the complex rules of human language by learning from massive amounts of text data. It can not only accurately understand your instructions, but also assist you in writing or programming as fluently as a real person.",
            ],
            ["audio/罗翔.wav", "True courage is not the absence of fear, but the choice to do the right thing even while knowing fear."],
            ["audio/阿洛娜.wav", "Sensei, let me tell you, the weather today is super~ good!"],
        ]

    def _get_examples(self) -> list:
        """Get example data"""
        return [
            ["audio/天气预报.wav", "substitute '需要做好防暑工作' with '大家躲在空调房里就好了。'"],
            ["audio/土豆能算主食吗.wav", "insert '还有各种菠萝汉堡等离谱食物。' at the end"],
            ["audio/高尔夫.wav", "insert '然后' before the character or word at index 12"],
            ["audio/可持续发展.wav", "delete the characters or words from index 3 to index 10"],
            ["audio/珠三角城市.wav", "delete '珠三角城市群'"],
            ["audio/小说朗读.wav", "substitute '提升' with '削弱自己的'"],
        ]

    # Wrapper Functions =======================================================

    def edit_start_wrapper(self, audio_path: str, instruction: str):
        """Async task start wrapper for Voice Editing"""
        logger.info(
            f"Edit start wrapper called with audio: {audio_path}, instruction: {instruction}"
        )
        if not audio_path or not instruction:
            # Correspond to UI outputs: task_id, polling_counter, output_text, output_audio
            return None, 0, "Error: Please provide audio and editing instructions", (blank_rate, blank_audio_data)

        task_id = self.service.edit_start_task(audio_path, instruction)
        if task_id.startswith("Error:"):
            return None, 0, task_id, (blank_rate, blank_audio_data)

        status_message = f"Edit task submitted (ID: ...{task_id[-6:]}), waiting for results..."
        # Return task_id, start polling counter, update status info, clear audio output
        return task_id, 1, status_message, gr.update(value=None)

    def edit_check_wrapper(self, task_id: str, polling_counter: int):
        """Async task status check wrapper for Voice Editing"""
        if not task_id or polling_counter == 0:
            # No task or polling not started, return directly
            return gr.update(), gr.update(), polling_counter

        logger.info(f"Polling Edit task {task_id}, counter: {polling_counter}")
        status, text_result, audio_result = self.service.edit_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2
            status_message = f"Editing... ({elapsed}s elapsed)"
            # Update status info, audio remains same, counter + 1
            return status_message, gr.update(), polling_counter + 1
        elif status == "done":
            # Return final result, stop polling
            return text_result, audio_result, 0
        else:  # Error occurred
            # Show error in textbox, return blank audio, stop polling
            return text_result, audio_result or (blank_rate, blank_audio_data), 0

    def tts_start_wrapper(self, text: str, prompt_wav_path: str, prompt_text: str):
        """Task start wrapper for Voice Synthesis"""
        logger.info(
            f"TTS start wrapper called with text length: {len(text)}, prompt_wav_path: {prompt_wav_path}, prompt_text length: {len(prompt_text)}"
        )
        if not all([text, prompt_wav_path, prompt_text]):
            # outputs: [task_id_state, synthesized_audio, polling_counter]
            return None, gr.update(label="Error: Missing synthesis text, reference audio, or reference text.", value=None), 0

        task_id = self.service.tts_start_task(text, prompt_wav_path, prompt_text)
        if task_id.startswith("Error:"):
            return None, gr.update(label=task_id, value=None), 0

        status_message = f"Task submitted (ID: ...{task_id[-6:]}), starting polling..."
        return task_id, gr.update(label=status_message, value=None), 1

    def tts_check_wrapper(self, task_id: str, polling_counter: int):
        """Task status check wrapper for Voice Synthesis"""
        if not task_id or polling_counter == 0:
            # outputs: [synthesized_audio, polling_counter]
            return gr.update(), 0

        logger.info(f"Polling TTS task {task_id}, counter: {polling_counter}")
        status, result = self.service.tts_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2  # Approx. 2s per check
            status_message = f"Synthesizing... ({elapsed}s)"
            return gr.update(label=status_message), polling_counter + 1
        elif status == "done":
            return gr.update(label="Synthesis successful!", value=result), 0
        else:  # Error case
            return gr.update(label=status, value=None), 0

    def asr_start_wrapper(self, audio_path: str):
        """Async task start wrapper for ASR"""
        logger.info(f"ASR start wrapper called with audio_path: {audio_path}")
        if not audio_path:
            return None, "Error: Please upload an audio file first.", 0

        task_id = self.service.asr_start_task(audio_path)
        if task_id.startswith("Error:"):
            return None, task_id, 0

        status_message = f"Recognition task submitted (ID: ...{task_id[-6:]}), waiting for results..."
        # Return task_id to state, update status, start polling
        return task_id, status_message, 1

    def asr_check_wrapper(self, task_id: str, polling_counter: int):
        """Async task status check wrapper for ASR"""
        if not task_id or polling_counter == 0:
            return gr.update(), 0

        logger.info(f"Polling ASR task {task_id}, counter: {polling_counter}")
        status, result = self.service.asr_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2
            status_message = f"Transcribing... ({elapsed}s elapsed)"
            return status_message, polling_counter + 1
        elif status == "done":
            status_message = "Recognition successful!"
            return result, 0
        else:  # Error occurred
            status_message = f"Recognition failed: {status}"
            return status_message, 0

    def prompt_asr_start_wrapper(self, audio_path: str):
        """Async task start wrapper for TTS reference audio ASR"""
        logger.info(f"Prompt ASR start wrapper called with audio_path: {audio_path}")
        if not audio_path:
            # outputs: [task_id_state, output_textbox, polling_counter]
            return None, "Error: Please upload reference audio first.", 0

        task_id = self.service.asr_start_task(audio_path)
        if task_id.startswith("Error:"):
            return None, task_id, 0

        status_message = f"Reference audio recognition task submitted, waiting for results..."
        return task_id, status_message, 1

    def prompt_asr_check_wrapper(self, task_id: str, polling_counter: int):
        """Async task status check wrapper for TTS reference audio ASR"""
        if not task_id or polling_counter == 0:
            return gr.update(), 0

        logger.info(f"Polling Prompt ASR task {task_id}, counter: {polling_counter}")
        status, result = self.service.asr_check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2
            status_message = f"Transcribing... ({elapsed}s elapsed)"
            return status_message, polling_counter + 1
        elif status == "done":
            return result, 0
        else:  # Error occurred
            return f"Recognition failed: {result}", 0

    # Interface Interaction Functions =====================================================
    @staticmethod
    def toggle_continuous(is_checked: bool) -> dict:
        """Toggle visibility of continuous editing button"""
        return gr.update(visible=is_checked)

    @staticmethod
    def chain_edit(current_audio):
        """Chain editing process"""
        if not current_audio:
            return gr.update(), gr.update(), gr.update(), gr.update()
        return (
            gr.update(value=current_audio),  # Update input_audio
            gr.update(value=""),  # Clear instruction
            gr.update(value=""),  # Clear output_text
            gr.update(value=None),  # Clear output_audio
        )

    def fill_tts_example(self, audio_path: str, text: str) -> tuple:
        """Fill TTS example data"""
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
        """Chain editing process"""
        if not current_audio:
            return gr.update(), gr.update(), gr.update(), gr.update()
        return (
            gr.update(value=current_audio),  # Update input_audio
            gr.update(value=""),  # Clear instruction
            gr.update(value=""),  # Clear output_text
            gr.update(value=None),  # Clear output_audio
        )

    def fill_example(self, audio_path: str, instruction: str) -> tuple:
        """Fill example data"""
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
        ), "Submitting recognition task...", gr.update(), gr.update()

        # --- ASR Task ---
        asr_task_id = self.service.asr_start_task(audio_path)
        if asr_task_id.startswith("Error:"):
            yield gr.update(), gr.update(), asr_task_id, gr.update(), gr.update()
            return

        yield gr.update(), gr.update(), "Recognition task submitted, waiting for results...", gr.update(), gr.update()

        transcription = ""
        for i in range(30):  # Timeout after 60s
            time.sleep(2)
            status, result = self.service.asr_check_task(asr_task_id)
            if status == "pending":
                yield gr.update(), gr.update(), f"Transcribing... ({(i+1)*2}s)", gr.update(), gr.update()
            elif status == "done":
                transcription = result
                yield gr.update(), gr.update(), transcription, gr.update(), gr.update()
                break
            else:  # Error
                yield gr.update(), gr.update(), f"Recognition failed: {result}", gr.update(), gr.update()
                return

        if not transcription:
            yield gr.update(), gr.update(), "Recognition timeout or no results returned", gr.update(), gr.update()
            return

        # --- Edit Task ---
        yield gr.update(), gr.update(), transcription, "Submitting edit task...", gr.update(value=None)

        edit_task_id = self.service.edit_start_task(audio_path, instruction)
        if edit_task_id.startswith("Error:"):
            yield gr.update(), gr.update(), transcription, f"Edit task submission failed: {edit_task_id}", (
                blank_rate,
                blank_audio_data,
            )
            return

        yield gr.update(), gr.update(), transcription, "Edit task submitted, waiting for results...", gr.update(
            value=None
        )

        for i in range(60):  # Timeout after 120s
            time.sleep(2)
            status, text_result, audio_result = self.service.edit_check_task(edit_task_id)
            if status == "pending":
                yield gr.update(), gr.update(), transcription, f"Editing... ({(i+1)*2}s)", gr.update()
            elif status == "done":
                yield gr.update(), gr.update(), transcription, text_result, audio_result
                return
            else:  # Error
                yield gr.update(), gr.update(), transcription, f"Edit failed: {text_result}", audio_result or (
                    blank_rate,
                    blank_audio_data,
                )
                return

        yield gr.update(), gr.update(), transcription, "Edit task timeout", (
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
