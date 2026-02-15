import gradio as gr
import json
import os
from loguru import logger

class AudioInstructTab:
    def __init__(self, speech_service):
        self.service = speech_service
        self.prompt_audio_path_example = "audio/00000309-00000300.wav"

    def create_tab(self):
        with gr.TabItem("Controllable TTS (Audio Instruct)"):
            gr.Markdown("## Controllable Speech Synthesis Demo")

            with gr.Tabs() as sub_tabs:
                # --- Tab 1: Structured Mode ---
                with gr.TabItem("Structured Mode"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            instruct_type = gr.Radio(
                                [
                                    ("Basic", "basic"),
                                    ("Dialect", "dialect"),
                                    ("Emotion", "emotion"),
                                    ("IP", "IP"),
                                    ("Style", "style")
                                ],
                                label="Instruction Type",
                                value="emotion"
                            )
                            text_input = gr.Textbox(label="Input Text")
                            prompt_audio = gr.Audio(type="filepath", label="Reference Audio")
                            speaker_id = gr.Textbox(label="Speaker ID", value="speaker_1")

                            # Dynamic UI Groups
                            with gr.Group(visible=False) as basic_controls:
                                pitch_radio = gr.Radio([("Low", "低"), ("Medium", "中"), ("High", "高")], label="Pitch", value="中")
                                volume_radio = gr.Radio([("Low", "低"), ("Medium", "中"), ("High", "高")], label="Volume", value="中")
                                speed_radio = gr.Radio([("Slow", "慢速"), ("Medium", "中速"), ("Fast", "快速")], label="Speed", value="中速")

                            with gr.Group(visible=False) as dialect_controls:
                                dialect_input = gr.Textbox(label="Dialect")
                            with gr.Group(visible=True) as emotion_controls:
                                emotion_input = gr.Textbox(label="Emotion")
                            with gr.Group(visible=False) as ip_controls:
                                ip_character_input = gr.Textbox(label="IP Character")
                                album_input = gr.Textbox(label="Album/Show Title", placeholder="Optional")
                            with gr.Group(visible=False) as style_controls:
                                style_input = gr.Textbox(label="Style")
    
                            seed = gr.Number(value=1234, label="Random Seed", precision=0)
    
                            # Examples list
                            examples_data = [
                                ["basic", "This is a fast speech example with high pitch and high volume.", self.prompt_audio_path_example, "speaker_1", "高", "高", "快速", None, None, None, None, None, 1234],
                                ["basic", "This is a slow speech example with low pitch and low volume.", self.prompt_audio_path_example, "speaker_1", "低", "低", "慢速", None, None, None, None, None, 5678],
                                ["dialect", "Actually many Guangzhou primary school and kindergartens are like this.", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", "广粤话", None, None, None, None, 1234],
                                ["dialect", "So do you guys have any TV shows you like to watch?", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", "川渝话", None, None, None, None, 5678],
                                ["emotion", "I'm so happy today, the sun is shining!", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", None, "高兴", None, None, None, 1234],
                                ["emotion", "This news is so sad.", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", None, "悲伤", None, None, None, 5678],
                                ["IP", "The four brothers discussed among themselves and said, 'Our chance has come, let's show our skills.'", None, "speaker_1", "中", "中", "中速", None, None, "四郎", "甄嬛传", None, 1234],
                                ["IP", "Only the little animals who have been to the village entrance know that there is a Great Bear Ramen shop there.", None, "speaker_1", "中", "中", "中速", None, None, "野原新之助 (小新)", "蜡笔小新", None, 5678],
                                ["style", "Calling for more young people eager to break through themselves to join the ranks of those who dare to cross boundaries.", None, "speaker_1", "中", "中", "中速", None, None, None, "A woman tells a deep and sad story in a soft, slow, and emotional way, creating a contemplative and slightly melancholic atmosphere.", None, 1234],
                                ["style", "Now you go and make a full copy of the set and give it to my driver Wu Da.", None, "speaker_1", "中", "中", "中速", None, None, None, "A young boy tells a story in a slow, clear but slightly blurred tone, very expressive, with a singing-like rhythm.", None, 5678],
                                ["basic", "", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", '', '', '', '', '', 0],
                                ]
    
                            structured_param_inputs = [
                                speaker_id, pitch_radio, volume_radio, speed_radio,
                                dialect_input, emotion_input, ip_character_input,
                                style_input, album_input
                            ]

                            # Save reference for event binding
                            self.examples_component = gr.Examples(
                                examples=examples_data,
                                inputs=[instruct_type, text_input, prompt_audio] + structured_param_inputs + [seed],
                                label="Click an example to fill inputs",
                                cache_examples="lazy"
                            )

                            generate_btn = gr.Button("Generate Audio", variant="primary")

                        with gr.Column(scale=1):
                            audio_output = gr.Audio(label="Result", interactive=False)
                            # Status and polling components
                            task_id_state = gr.State(None)
                            polling_counter = gr.Number(value=0, visible=False)
                            status_msg = gr.Markdown("")

                # --- Tab 2: Expert Mode ---
                with gr.TabItem("Expert Mode"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("In this mode, you can combine all parameters for synthesis.")
                            expert_text = gr.Textbox(label="Input Text")
                            expert_prompt_audio = gr.Audio(type="filepath", label="Reference Audio (Optional for IP/Style mode)")
                            expert_speaker_id = gr.Textbox(label="Speaker ID", value="speaker_1")
                            expert_pitch = gr.Radio([("Low", "低"), ("Medium", "中"), ("High", "高")], label="Pitch", value="中")
                            expert_volume = gr.Radio([("Low", "低"), ("Medium", "中"), ("High", "高")], label="Volume", value="中")
                            expert_speed = gr.Radio([("Slow", "慢速"), ("Medium", "中速"), ("Fast", "快速")], label="Speed", value="中速")
                            expert_dialect = gr.Textbox(label="Dialect")
                            expert_emotion = gr.Textbox(label="Emotion")
                            expert_ip_character = gr.Textbox(label="IP Character")
                            expert_album = gr.Textbox(label="Album/Show Title", placeholder="Optional")
                            expert_style = gr.Textbox(label="Style")
                            expert_seed = gr.Number(value=1234, label="Random Seed", precision=0)
                            expert_generate_btn = gr.Button("Generate Audio", variant="primary")
                        with gr.Column(scale=1):
                            expert_audio_output = gr.Audio(label="Result", interactive=False)
                            expert_task_id_state = gr.State(None)
                            expert_polling_counter = gr.Number(value=0, visible=False)
                            expert_status_msg = gr.Markdown("")

                # --- Tab 3: JSON Input Mode ---
                with gr.TabItem("JSON Mode"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            json_input = gr.Textbox(lines=15, label="JSON Input", placeholder='Enter JSON here...')
                            free_prompt_audio = gr.Audio(type="filepath", label="Reference Audio")
                            free_seed = gr.Number(value=1234, label="Random Seed", precision=0)
                            free_generate_btn = gr.Button("Generate Audio", variant="primary")
                        with gr.Column(scale=1):
                            free_audio_output = gr.Audio(label="Result", interactive=False)
                            free_task_id_state = gr.State(None)
                            free_polling_counter = gr.Number(value=0, visible=False)
                            free_status_msg = gr.Markdown("")

            # --- 事件绑定 ---

            logger.info("Binding events for AudioInstructTab")

            # 1. UI 动态可见性逻辑
            instruct_type.change(
                fn=self.update_ui_visibility,
                inputs=instruct_type,
                outputs=[basic_controls, dialect_controls, emotion_controls, ip_controls, style_controls, prompt_audio]
            )

            # # 1.5. 示例点击事件绑定
            # self.examples_component.load_input_event.then(
            #     fn=self.update_ui_visibility,
            #     inputs=[instruct_type, text_input, prompt_audio] + structured_param_inputs + [seed],
            #     outputs=[basic_controls, dialect_controls, emotion_controls, ip_controls, style_controls, prompt_audio]
            # )

            logger.info("Examples component event bound.")

            # 2. 结构化模式生成
            generate_btn.click(
                fn=self.submit_structured_task,
                inputs=[instruct_type, text_input, prompt_audio] + structured_param_inputs + [seed],
                outputs=[task_id_state, polling_counter, status_msg, audio_output]
            )
            polling_counter.change(
                fn=self.check_task_status,
                inputs=[task_id_state, polling_counter],
                outputs=[audio_output, polling_counter, status_msg],
                every=2
            )

            logger.info("Structured mode events bound.")

            # 3. 自由/专家模式生成
            expert_param_inputs = [
                expert_speaker_id, expert_pitch, expert_volume, expert_speed,
                expert_dialect, expert_emotion, expert_ip_character,
                expert_style, expert_album
            ]
            expert_generate_btn.click(
                fn=self.submit_expert_task,
                inputs=[expert_text, expert_prompt_audio] + expert_param_inputs + [expert_seed],
                outputs=[expert_task_id_state, expert_polling_counter, expert_status_msg, expert_audio_output]
            )
            expert_polling_counter.change(
                fn=self.check_task_status,
                inputs=[expert_task_id_state, expert_polling_counter],
                outputs=[expert_audio_output, expert_polling_counter, expert_status_msg],
                every=2
            )

            logger.info("Expert mode events bound.")

            # 4. JSON 模式生成
            free_generate_btn.click(
                fn=self.submit_json_task,
                inputs=[json_input, free_prompt_audio, free_seed],
                outputs=[free_task_id_state, free_polling_counter, free_status_msg, free_audio_output]
            )
            free_polling_counter.change(
                fn=self.check_task_status,
                inputs=[free_task_id_state, free_polling_counter],
                outputs=[free_audio_output, free_polling_counter, free_status_msg],
                every=2
            )

    def update_ui_visibility(self, instruct_type):
        """Update visibility of UI controls based on instruction type"""
        # Gradio Radio with tuples passes the 'value' to the function
        if instruct_type in ["IP", "style"]:
            new_audio_label = "Reference Audio (Optional/Disabled in this mode)"
        else:
            new_audio_label = "Reference Audio (Prompt Audio)"

        # 打个日志
        logger.info(f"Updating UI visibility for instruct_type: {instruct_type}")

        # 必须按 outputs=[basic_controls, dialect_controls, emotion_controls, ip_controls, style_controls, prompt_audio] 的顺序返回
        return (
            gr.update(visible=instruct_type == "basic"),
            gr.update(visible=instruct_type == "dialect"),
            gr.update(visible=instruct_type == "emotion"),
            gr.update(visible=instruct_type == "IP"),
            gr.update(visible=instruct_type == "style"),
            gr.update(label=new_audio_label)
        )

    def _construct_caption(self, instruct_type, speaker_id, pitch, volume, speed,
                         dialect, emotion, ip_character, style, album):
        """Construct caption dictionary"""

        logger.info(f"Constructing caption for instruct_type: {instruct_type}")

        base_caption = {'序号': 1, '说话人': speaker_id or 'speaker_1'}

        # 统一处理逻辑，参考 004-in.py
        if instruct_type == "expert":
             return {
                "audio_sequence": [{
                    '序号': 1,
                    '说话人': speaker_id or 'speaker_1',
                    '方言': dialect if dialect else None,
                    '风格': style if style else None,
                    '语速': speed if speed and speed != "中" else None,
                    '基频': pitch if pitch and pitch != "中" else None,
                    '音量': volume if volume and volume != "中" else None,
                    '情感': emotion if emotion else None,
                    '影视IP': f"{album}_{ip_character}" if album and ip_character else ip_character
                }]
            }

        # Structured mode
        if instruct_type == "basic":
            base_caption.update({"基频": pitch, "音量": volume, "语速": speed})
        elif instruct_type == "dialect":
            base_caption["方言"] = dialect
        elif instruct_type == "emotion":
            base_caption["情感"] = emotion
        elif instruct_type == "IP":
            base_caption["影视IP"] = f"{album}_{ip_character}" if album and ip_character else ip_character
        elif instruct_type == "style":
            base_caption["风格"] = style

        return {"audio_sequence": [base_caption]}

    def _submit_task(self, payload):
        """Internal task submission method"""
        logger.info(f"AudioInstructTab submitting task with payload: {payload}")

        # 调用 SpeechService 的新接口
        # payload 已经包含了 text, prompt_audio, caption, seed
        return self.service.submit_instruct_task(payload)

    def _check_task(self, task_id):
        """Internal task status check method"""
        logger.info(f"AudioInstructTab checking task status for task_id: {task_id}")

        return self.service.poll_instruct_task(task_id)

    def submit_structured_task(self, instruct_type, text, prompt_audio,
                             speaker_id, pitch, volume, speed, dialect, emotion,
                             ip_character, style, album, seed):
        """Submit structured task"""
        logger.info(f"Submitting structured task: type={instruct_type}, text={text}")
        if not text:
            return None, 0, "Error: Please enter text", None

        # Validation: Non IP/Style modes must provide reference audio
        if not prompt_audio and instruct_type not in ["IP", "style"]:
            return None, 0, "Error: This mode requires reference audio for timbre cloning", None

        caption = self._construct_caption(instruct_type, speaker_id, pitch, volume, speed,
                                        dialect, emotion, ip_character, style, album)

        payload = {
            "text": text,
            "prompt_audio": prompt_audio,
            "caption": json.dumps(caption, ensure_ascii=False),
            "seed": seed,
        }

        # 调用内部提交方法
        task_id = self._submit_task(payload)

        if task_id.startswith("错误") or task_id.startswith("Error"):
            return None, 0, task_id, None

        return task_id, 1, f"Task submitted (ID: ...{task_id[-6:]})", None

    def submit_expert_task(self, text, prompt_audio,
                         speaker_id, pitch, volume, speed, dialect, emotion,
                         ip_character, style, album, seed):
        """Submit expert mode task"""

        logger.info(f"Submitting expert task with text: {text}")

        return self.submit_structured_task("expert", text, prompt_audio,
                                         speaker_id, pitch, volume, speed, dialect, emotion,
                                         ip_character, style, album, seed)

    def submit_json_task(self, json_str, prompt_audio, seed):
        """Submit JSON mode task"""

        logger.info(f"Submitting JSON task with input: {json_str}")

        if not json_str or not json_str.strip():
            return None, 0, "Error: Please enter JSON", None

        try:
            data = json.loads(json_str)

            # 参考 inbox/004-in.py 的逻辑处理 caption
            if "caption" in data and isinstance(data["caption"], str):
                caption_str = data["caption"]
                corrected_caption_str = caption_str.replace('"null"', 'null')
                data["caption"] = json.loads(corrected_caption_str)

            text = data.get("text")
            caption_dict = data.get("caption")

            if text is None or caption_dict is None:
                 return None, 0, "Error: JSON must contain 'text' and 'caption' fields", None

            # 检查是否包含 IP 或 风格，如果包含则无需 prompt_audio
            is_ip_or_style = False
            if isinstance(caption_dict, dict) and "audio_sequence" in caption_dict and caption_dict["audio_sequence"]:
                first_item = caption_dict["audio_sequence"][0]
                # 注意：key 可能是中文 "影视IP"/"风格"
                if first_item.get("影视IP") or first_item.get("风格"):
                    is_ip_or_style = True

            if not prompt_audio and not is_ip_or_style:
                return None, 0, "Error: This mode requires reference audio (unless IP or style is specified)", None

        except (json.JSONDecodeError, TypeError) as e:
            return None, 0, f"Error: Invalid JSON format or processing failed: {e}", None

        payload = {
            "text": text,
            "prompt_audio": prompt_audio,
            "caption": json.dumps(caption_dict, ensure_ascii=False),
            "seed": seed,
        }

        task_id = self._submit_task(payload)

        if task_id.startswith("错误") or task_id.startswith("Error"):
            return None, 0, task_id, None

        return task_id, 1, f"Task submitted (ID: ...{task_id[-6:]})", None

    def check_task_status(self, task_id, polling_counter):
        """Check task status"""

        # 如果没有任务ID或者轮询计数器归零（任务已结束），则停止轮询逻辑
        if not task_id or polling_counter == 0:
             return gr.update(), 0, gr.update()

        logger.info(f"Checking task status for task_id: {task_id}, polling_counter: {polling_counter}")

        # 调用内部检查方法
        status, result = self._check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2
            return gr.update(), polling_counter + 1, f"Synthesizing... ({elapsed}s)"
        elif status == "done" or status == "completed":
            return gr.update(value=result), 0, "Success!"
        else:
            return gr.update(), 0, f"Failed: {status}"
