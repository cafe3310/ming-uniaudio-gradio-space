import gradio as gr
import json
import os
from loguru import logger

class AudioInstructTab:
    def __init__(self, speech_service):
        self.service = speech_service
        self.prompt_audio_path_example = "audio/00000309-00000300.wav"

    def create_tab(self):
        with gr.TabItem("可控 TTS (Audio Instruct)"):
            gr.Markdown("## 可控语音合成演示")

            with gr.Tabs() as sub_tabs:
                # --- Tab 1: 结构化模式 ---
                with gr.TabItem("结构化模式"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            instruct_type = gr.Radio(
                                ["basic", "dialect", "emotion", "IP", "style"],
                                label="指令类型",
                                value="basic"
                            )
                            text_input = gr.Textbox(label="输入文本")
                            prompt_audio = gr.Audio(type="filepath", label="参考音频")
                            speaker_id = gr.Textbox(label="说话人ID", value="speaker_1")

                            # 动态显示的控件组
                            with gr.Group(visible=True) as basic_controls:
                                pitch_radio = gr.Radio(["低", "中", "高"], label="基频", value="中")
                                volume_radio = gr.Radio(["低", "中", "高"], label="音量", value="中")
                                speed_radio = gr.Radio(["慢速", "中速", "快速"], label="语速", value="中速")

                            with gr.Group(visible=False) as dialect_controls:
                                dialect_input = gr.Textbox(label="方言")
                            with gr.Group(visible=False) as emotion_controls:
                                emotion_input = gr.Textbox(label="情感")
                            with gr.Group(visible=False) as ip_controls:
                                ip_character_input = gr.Textbox(label="IP角色")
                                album_input = gr.Textbox(label="所属剧名", placeholder="可选")
                            with gr.Group(visible=False) as style_controls:
                                style_input = gr.Textbox(label="风格")

                            seed = gr.Number(value=1234, label="随机种子", precision=0)

                            # 示例列表 (Adapting examples from input)
                            # Note: Path adjustment needed for real environment
                            examples_data = [
                                # Gradio 的坑：如果某列全部都是 None, 将会在 inputs 中缺失该列，导致绑定错误
                                ["basic", "这是一个高音调、高音量的快速语音示例。", self.prompt_audio_path_example, "speaker_1", "高", "高", "快速", None, None, None, None, None, 1234],
                                ["basic", "这是一个低音调、低音量的慢速语音示例。", self.prompt_audio_path_example, "speaker_1", "低", "低", "慢速", None, None, None, None, None, 5678],
                                ["dialect", "其实好多广州小学幼稚园都系噉样", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", "广粤话", None, None, None, None, 1234],
                                ["dialect", "那你们有啥子喜欢看的电视剧吗？", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", "川渝话", None, None, None, None, 5678],
                                ["emotion", "我今天非常开心，阳光明媚！", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", None, "高兴", None, None, None, 1234],
                                ["emotion", "这个消息太令人难过了。", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", None, "悲伤", None, None, None, 5678],
                                ["IP", "四个兄弟互相一商量，说道，我们的机会来了，让我们各展所能吧。", None, "speaker_1", "中", "中", "中速", None, None, "四郎", "甄嬛传", None, 1234],
                                ["IP", "也只有到村也只有到过村口的小动物，才知道村口有一家大熊拉面馆。", None, "speaker_1", "中", "中", "中速", None, None, "野原新之助 (小新)", "蜡笔小新", None, 5678],
                                ["style", "号召更多渴望突破自我的年轻力量，加入到敢于突破破界的队伍中来", None, "speaker_1", "中", "中", "中速", None, None, None, "一位女性以柔和、缓慢且富有情感的方式讲述一个深刻而悲伤的故事，营造出沉思和略带忧郁的氛围。", None, 1234],
                                ["style", "你现在马上把全套再复印一份，给我的司机武大", None, "speaker_1", "中", "中", "中速", None, None, None, "一位年幼男孩用缓慢清晰但略显模糊的语调，富有表现力地讲述故事，语调带有唱歌般的韵律。", None, 5678],
                                ["basic", "", self.prompt_audio_path_example, "speaker_1", "中", "中", "中速", '', '', '', '', '', 0], # 这一行用于填充可能为空的列
                            ]

                            structured_param_inputs = [
                                speaker_id, pitch_radio, volume_radio, speed_radio,
                                dialect_input, emotion_input, ip_character_input,
                                style_input, album_input
                            ]

                            # 保存引用以供事件绑定使用
                            self.examples_component = gr.Examples(
                                examples=examples_data,
                                inputs=[instruct_type, text_input, prompt_audio] + structured_param_inputs + [seed],
                                label="点击示例以填充输入"
                            )

                            generate_btn = gr.Button("生成音频", variant="primary")

                        with gr.Column(scale=1):
                            audio_output = gr.Audio(label="合成结果", interactive=False)
                            # 状态和轮询组件
                            task_id_state = gr.State(None)
                            polling_counter = gr.Number(value=0, visible=False)
                            status_msg = gr.Markdown("")

                # --- Tab 2: 自由输入模式 ---
                with gr.TabItem("自由输入模式"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("在此模式下, 您可以组合所有参数进行合成。")
                            expert_text = gr.Textbox(label="输入文本")
                            expert_prompt_audio = gr.Audio(type="filepath", label="参考音频 (IP/风格模式下可选)")
                            expert_speaker_id = gr.Textbox(label="说话人ID", value="speaker_1")
                            expert_pitch = gr.Radio(["低", "中", "高"], label="基频", value="中")
                            expert_volume = gr.Radio(["低", "中", "高"], label="音量", value="中")
                            expert_speed = gr.Radio(["慢速", "中速", "快速"], label="语速", value="中速")
                            expert_dialect = gr.Textbox(label="方言")
                            expert_emotion = gr.Textbox(label="情感")
                            expert_ip_character = gr.Textbox(label="IP角色")
                            expert_album = gr.Textbox(label="所属剧名", placeholder="可选")
                            expert_style = gr.Textbox(label="风格")
                            expert_seed = gr.Number(value=1234, label="随机种子", precision=0)
                            expert_generate_btn = gr.Button("生成音频", variant="primary")
                        with gr.Column(scale=1):
                            expert_audio_output = gr.Audio(label="合成结果", interactive=False)
                            expert_task_id_state = gr.State(None)
                            expert_polling_counter = gr.Number(value=0, visible=False)
                            expert_status_msg = gr.Markdown("")

                # --- Tab 3: JSON 输入模式 ---
                with gr.TabItem("JSON 输入模式"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            json_input = gr.Textbox(lines=15, label="JSON 输入", placeholder='请在此输入JSON...')
                            free_prompt_audio = gr.Audio(type="filepath", label="参考音频")
                            free_seed = gr.Number(value=1234, label="随机种子", precision=0)
                            free_generate_btn = gr.Button("生成音频", variant="primary")
                        with gr.Column(scale=1):
                            free_audio_output = gr.Audio(label="合成结果", interactive=False)
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
        """根据指令类型更新 UI 控件的可见性"""
        if instruct_type in ["IP", "style"]:
            new_audio_label = "参考音频 (在此模式下可选/不起作用)"
        else:
            new_audio_label = "参考音频 (Prompt Audio)"

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
        """构建 caption 字典"""

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

        # 结构化模式
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
        """
        内部任务提交方法。
        调用 SpeechService 的 submit_instruct_task 方法。
        """
        logger.info(f"AudioInstructTab submitting task with payload: {payload}")

        # 调用 SpeechService 的新接口
        # payload 已经包含了 text, prompt_audio, caption, seed
        return self.service.submit_instruct_task(payload)

    def _check_task(self, task_id):
        """
        内部任务状态检查方法。
        调用 SpeechService 的 poll_instruct_task 方法。
        """

        logger.info(f"AudioInstructTab checking task status for task_id: {task_id}")

        return self.service.poll_instruct_task(task_id)

    def submit_structured_task(self, instruct_type, text, prompt_audio,
                             speaker_id, pitch, volume, speed, dialect, emotion,
                             ip_character, style, album, seed):
        """提交结构化任务"""
        logger.info(f"Submitting structured task: type={instruct_type}, text={text}")
        if not text:
            return None, 0, "错误: 请输入文本", None

        # 校验: 非 IP/Style 模式必须提供参考音频
        if not prompt_audio and instruct_type not in ["IP", "style"]:
            return None, 0, "错误: 此模式需要上传参考音频以提取音色", None

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

        if task_id.startswith("错误"):
            return None, 0, task_id, None

        return task_id, 1, f"任务已提交 (ID: ...{task_id[-6:]})", None

    def submit_expert_task(self, text, prompt_audio,
                         speaker_id, pitch, volume, speed, dialect, emotion,
                         ip_character, style, album, seed):
        """提交专家模式任务"""

        logger.info(f"Submitting expert task with text: {text}")

        return self.submit_structured_task("expert", text, prompt_audio,
                                         speaker_id, pitch, volume, speed, dialect, emotion,
                                         ip_character, style, album, seed)

    def submit_json_task(self, json_str, prompt_audio, seed):
        """提交 JSON 模式任务"""

        logger.info(f"Submitting JSON task with input: {json_str}")

        if not json_str or not json_str.strip():
            return None, 0, "错误: 请输入 JSON", None

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
                 return None, 0, "错误: JSON 中必须包含 'text' 和 'caption' 字段", None

            # 检查是否包含 IP 或 风格，如果包含则无需 prompt_audio
            is_ip_or_style = False
            if isinstance(caption_dict, dict) and "audio_sequence" in caption_dict and caption_dict["audio_sequence"]:
                first_item = caption_dict["audio_sequence"][0]
                # 注意：key 可能是中文 "影视IP"/"风格"
                if first_item.get("影视IP") or first_item.get("风格"):
                    is_ip_or_style = True

            if not prompt_audio and not is_ip_or_style:
                return None, 0, "错误: 此模式需要上传参考音频 (除非指定了影视IP or 风格)", None

        except (json.JSONDecodeError, TypeError) as e:
            return None, 0, f"错误: JSON 格式无效或处理失败: {e}", None

        payload = {
            "text": text,
            "prompt_audio": prompt_audio,
            "caption": json.dumps(caption_dict, ensure_ascii=False),
            "seed": seed,
        }

        task_id = self._submit_task(payload)

        if task_id.startswith("错误"):
            return None, 0, task_id, None

        return task_id, 1, f"任务已提交 (ID: ...{task_id[-6:]})", None

    def check_task_status(self, task_id, polling_counter):
        """检查任务状态"""

        # 如果没有任务ID或者轮询计数器归零（任务已结束），则停止轮询逻辑
        if not task_id or polling_counter == 0:
             return gr.update(), 0, gr.update()

        logger.info(f"Checking task status for task_id: {task_id}, polling_counter: {polling_counter}")

        # 调用内部检查方法
        status, result = self._check_task(task_id)

        if status == "pending":
            elapsed = polling_counter * 2
            return gr.update(), polling_counter + 1, f"合成中... ({elapsed}s)"
        elif status == "done" or status == "completed":
            return gr.update(value=result), 0, "合成成功！"
        else:
            return gr.update(), 0, f"失败: {status}"
