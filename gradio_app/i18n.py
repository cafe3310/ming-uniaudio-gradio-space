# -*- coding: utf-8 -*-
"""
Internationalization (i18n) support for the Gradio application.
Provides translations for UI text in English and Simplified Chinese.
"""

# Translation dictionary
TRANSLATIONS = {
    "en": {
        # Language selector
        "language": "Language",
        "english": "English",
        "chinese": "简体中文",
        
        # Main title and header
        "main_title": "Ming-omni-tts Voice Model Demo",
        "main_subtitle": "Provides comprehensive voice recognition, editing, and synthesis capabilities. [Ming-v2 Series](https://huggingface.co/collections/inclusionAI/ming-v2)",
        
        # Main tabs
        "tab_ming_omni": "Ming-omni-tts",
        "tab_basic_abilities": "Basic Abilities (ASR/Edit/TTS)",
        
        # ASR section
        "asr_title": "🎤 Speech Recognition (ASR)",
        "asr_description": "Automatically transcribe your uploaded audio files into text.",
        "asr_input_label": "Original Audio",
        "asr_play_button": "Play Audio",
        "asr_result_label": "Recognition Result",
        
        # Edit section
        "edit_title": "✏️ Intelligent Editing (Editing)",
        "edit_description": "Modify audio and text through simple natural language instructions.",
        "edit_continuous_label": "Enable Continuous Editing",
        "edit_instruction_label": "Edit Instruction",
        "edit_instruction_placeholder": "e.g., 'Denoise the audio'",
        "edit_execute_button": "Execute Edit",
        "edit_text_output_label": "Edited Text",
        "edit_audio_output_label": "Edited Audio",
        "edit_continuous_button": "Continuous Edit",
        
        # TTS section
        "tts_title": "🔊 Text-to-Speech (TTS)",
        "tts_description": "Upload reference audio, clone its timbre, and synthesize any text into natural speech.",
        "tts_prompt_audio_label": "Reference Audio",
        "tts_prompt_text_label": "Reference Text",
        "tts_text_label": "Synthesis Text",
        "tts_text_placeholder": "Enter the text to synthesize",
        "tts_button": "Synthesize Speech",
        "tts_output_label": "Synthesized Audio",
        
        # Examples
        "examples_edit_label": "Voice Editing Examples",
        "examples_tts_label": "Voice Synthesis Examples",
        
        # Ming-omni-tts tab
        "ming_omni_title": "Ming-omni-tts Comprehensive Capability Demo",
        
        # Instruct TTS
        "instruct_tts_tab": "Instruct TTS",
        "instruct_type_label": "Instruction Type",
        "instruct_type_dialect": "Dialect (dialect)",
        "instruct_type_emotion": "Emotion (emotion)",
        "instruct_type_ip": "IP (IP)",
        "instruct_type_style": "Style (style)",
        "instruct_type_basic": "Basic (basic)",
        "instruct_text_label": "Synthesis Text",
        "instruct_text_info": "Enter the text to synthesize.",
        "instruct_prompt_label": "Reference Audio (3-7 seconds) Upload a clear vocal audio to clone the basic timbre.",
        "instruct_details_accordion": "Instruction Details (Fill according to instruction type)",
        "instruct_emotion_label": "Emotion",
        "instruct_dialect_label": "Dialect",
        "instruct_ip_label": "IP Character",
        "instruct_style_label": "Style Description",
        "instruct_style_info": "e.g. Speak with loud and powerful volume, showing the resilience and majesty unique to males. The speech rate is relatively fast, and the tone is smooth from beginning to end, especially slightly slowing down at the ending words to enhance the authoritative and decisive tone",
        "instruct_speed_label": "Speech Rate",
        "instruct_pitch_label": "Pitch",
        "instruct_volume_label": "Volume",
        "instruct_speed_slow": "Slow",
        "instruct_speed_medium": "Medium",
        "instruct_speed_fast": "Fast",
        "instruct_pitch_low": "Low",
        "instruct_pitch_medium": "Medium",
        "instruct_pitch_high": "High",
        "instruct_volume_low": "Low",
        "instruct_volume_medium": "Medium",
        "instruct_volume_high": "High",
        "instruct_generate_button": "Generate Instruction Voice",
        "instruct_status_default": "💡 Please select instruction type and fill in parameters.",
        "instruct_output_label": "Generation Result",
        
        # Zero-shot TTS
        "zeroshot_tts_tab": "Voice Cloning (Zero-shot TTS)",
        "zeroshot_text_label": "Target Text",
        "zeroshot_text_info": "Enter the text you want to synthesize.",
        "zeroshot_prompt_label": "Reference Audio (3-7 seconds) Upload a clear vocal audio to clone the timbre.",
        "zeroshot_button": "Clone and Generate Voice",
        "zeroshot_status_default": "💡 Please enter text and upload reference audio.",
        "zeroshot_output_label": "Generation Result",
        
        # Podcast
        "podcast_tab": "Podcast",
        "podcast_script_label": "Dialogue Script",
        "podcast_script_info": "Use 'speaker_1:', 'speaker_2:' to distinguish different speakers. e.g. speaker_1: For example, various kinds of help provided to others can be said to be services\n speaker_2: Yes, no matter what, it feels like everyone can be said to be an aspect of the service industry\n",
        "podcast_prompt1_label": "Speaker 1 Reference Audio",
        "podcast_prompt2_label": "Speaker 2 Reference Audio",
        "podcast_button": "Generate Podcast",
        "podcast_status_default": "💡 Please fill in the script and upload reference audios for both speakers.",
        "podcast_output_label": "Generation Result",
        
        # Speech with BGM
        "swb_tab": "Speech with BGM",
        "swb_text_label": "Speech Text",
        "swb_prompt_label": "Speaker Reference Audio",
        "swb_bgm_title": "Background Music Description",
        "swb_genre_label": "Genre",
        "swb_mood_label": "Mood",
        "swb_instrument_label": "Instrument",
        "swb_theme_label": "Theme",
        "swb_button": "Generate Speech with BGM",
        "swb_status_default": "💡 Please enter text, upload reference audio, and describe background music.",
        "swb_output_label": "Generation Result",
        
        # Pure BGM
        "bgm_tab": "Background Music (BGM Generation)",
        "bgm_title": "Background Music Description",
        "bgm_genre_label": "Genre",
        "bgm_mood_label": "Mood",
        "bgm_instrument_label": "Instrument",
        "bgm_theme_label": "Theme",
        "bgm_duration_label": "Duration (seconds)",
        "bgm_button": "Generate Background Music",
        "bgm_status_default": "💡 Please describe the background music characteristics.",
        "bgm_output_label": "Generation Result",
        
        # TTA (Text-to-Audio)
        "tta_tab": "Sound Effect Generation (TTA)",
        "tta_text_label": "Sound Effect Description",
        "tta_text_info": "English descriptions are recommended for better results. For example: 'Rain is falling continuously'.",
        "tta_button": "Generate Sound Effect",
        "tta_status_default": "💡 Please enter a text description of the sound effect.",
        "tta_output_label": "Generation Result",
        
        # Microphone permission
        "mic_permission_title": "Microphone permission not working? Click here for solutions",
        "mic_permission_text": """
If you're using Chrome browser and the microphone permission is not working properly, and this application is deployed on a non-HTTPS site, please try the following steps:

1.  Enter `chrome://flags/#unsafely-treat-insecure-origin-as-secure` in the Chrome address bar
2.  Change the status of this flag to **Enabled**.
3.  In the "Enabled domains" input box that appears, enter the domain name of this application.
4.  **Important:** Completely close and restart the Chrome browser.

After completing these steps, you should be able to successfully grant microphone permission to this page.
""",
    },
    "zh": {
        # Language selector
        "language": "语言",
        "english": "English",
        "chinese": "简体中文",
        
        # Main title and header
        "main_title": "百灵系列 Ming-omni-tts 语音模型演示",
        "main_subtitle": "提供一站式语音识别、语音编辑和语音合成能力。 [Ming-v2 系列](https://huggingface.co/collections/inclusionAI/ming-v2)",
        
        # Main tabs
        "tab_ming_omni": "Ming-omni-tts",
        "tab_basic_abilities": "基础能力 (ASR/Edit/TTS)",
        
        # ASR section
        "asr_title": "🎤 语音转写（ASR）",
        "asr_description": "将您上传的音频文件自动转写为文字。",
        "asr_input_label": "原始音频",
        "asr_play_button": "播放音频",
        "asr_result_label": "识别结果",
        
        # Edit section
        "edit_title": "✏️ 智能编辑（Editing）",
        "edit_description": "通过简单的自然语言指令，对音频和文本进行修改。",
        "edit_continuous_label": "启用连续编辑",
        "edit_instruction_label": "编辑指令",
        "edit_instruction_placeholder": "例如: '给音频降噪'",
        "edit_execute_button": "执行编辑",
        "edit_text_output_label": "编辑后文本",
        "edit_audio_output_label": "编辑后音频",
        "edit_continuous_button": "连续编辑",
        
        # TTS section
        "tts_title": "🔊 语音合成（TTS）",
        "tts_description": "上传参考音频，克隆其音色，将任意文本合成为自然的语音。",
        "tts_prompt_audio_label": "参考音频",
        "tts_prompt_text_label": "参考文本",
        "tts_text_label": "合成文本",
        "tts_text_placeholder": "输入需要合成的文本",
        "tts_button": "合成语音",
        "tts_output_label": "合成音频",
        
        # Examples
        "examples_edit_label": "语音编辑示例",
        "examples_tts_label": "语音合成示例",
        
        # Ming-omni-tts tab
        "ming_omni_title": "## Ming-omni-tts 综合能力演示",
        
        # Instruct TTS
        "instruct_tts_tab": "指令TTS (Instruct TTS)",
        "instruct_type_label": "指令类型",
        "instruct_type_dialect": "方言 (dialect)",
        "instruct_type_emotion": "情感 (emotion)",
        "instruct_type_ip": "IP (IP)",
        "instruct_type_style": "风格 (style)",
        "instruct_type_basic": "基础 (basic)",
        "instruct_text_label": "合成文本",
        "instruct_text_info": "输入要合成的语音文本。",
        "instruct_prompt_label": "参考音频 (3-7秒)上传一段清晰的人声音频用于克隆基础音色。",
        "instruct_details_accordion": "指令详情 (根据指令类型填写)",
        "instruct_emotion_label": "情感",
        "instruct_dialect_label": "方言",
        "instruct_ip_label": "IP角色",
        "instruct_style_label": "风格描述",
        "instruct_style_info": "e.g. 以洪亮有力的音量发声,展示出男性特有的坚韧与威严感。语速偏快,语调从头至尾保持流畅,特别是在结尾词句上略微放慢,增强权威与果决的语气",
        "instruct_speed_label": "语速",
        "instruct_pitch_label": "基频",
        "instruct_volume_label": "音量",
        "instruct_speed_slow": "慢速",
        "instruct_speed_medium": "中速",
        "instruct_speed_fast": "快速",
        "instruct_pitch_low": "低",
        "instruct_pitch_medium": "中",
        "instruct_pitch_high": "高",
        "instruct_volume_low": "低",
        "instruct_volume_medium": "中",
        "instruct_volume_high": "高",
        "instruct_generate_button": "生成指令语音",
        "instruct_status_default": "💡 请选择指令类型并填写参数。",
        "instruct_output_label": "生成结果",
        
        # Zero-shot TTS
        "zeroshot_tts_tab": "音色克隆 (Zero-shot TTS)",
        "zeroshot_text_label": "目标文本",
        "zeroshot_text_info": "输入您想合成的语音文本。",
        "zeroshot_prompt_label": "参考音频 (3-7秒)上传一段清晰的人声音频用于克隆音色。",
        "zeroshot_button": "克隆并生成语音",
        "zeroshot_status_default": "💡 请输入文本并上传参考音频。",
        "zeroshot_output_label": "生成结果",
        
        # Podcast
        "podcast_tab": "播客 (Podcast)",
        "podcast_script_label": "对话脚本",
        "podcast_script_info": "使用 'speaker_1:', 'speaker_2:' 区分不同说话人。e.g. speaker_1:就比如说各种就是给别人提供，提供帮助的都可以说是服务的\n speaker_2:是的 不管是什么，就是说感觉都是，大家都，都可以说是服务业的一方面\n",
        "podcast_prompt1_label": "说话人1参考音频",
        "podcast_prompt2_label": "说话人2参考音频",
        "podcast_button": "生成播客",
        "podcast_status_default": "💡 请填写脚本并上传两位说话人的参考音频。",
        "podcast_output_label": "生成结果",
        
        # Speech with BGM
        "swb_tab": "带背景音乐的语音 (Speech with BGM)",
        "swb_text_label": "语音文本",
        "swb_prompt_label": "说话人参考音频",
        "swb_bgm_title": "##### 背景音乐描述",
        "swb_genre_label": "风格 (Genre)",
        "swb_mood_label": "情绪 (Mood)",
        "swb_instrument_label": "乐器 (Instrument)",
        "swb_theme_label": "主题 (Theme)",
        "swb_button": "生成带背景音乐的语音",
        "swb_status_default": "💡 请输入文本、上传参考音频并描述背景音乐。",
        "swb_output_label": "生成结果",
        
        # Pure BGM
        "bgm_tab": "背景音乐 (BGM Generation)",
        "bgm_title": "##### 背景音乐描述",
        "bgm_genre_label": "风格 (Genre)",
        "bgm_mood_label": "情绪 (Mood)",
        "bgm_instrument_label": "乐器 (Instrument)",
        "bgm_theme_label": "主题 (Theme)",
        "bgm_duration_label": "时长 (秒)",
        "bgm_button": "生成背景音乐",
        "bgm_status_default": "💡 请描述背景音乐特征。",
        "bgm_output_label": "生成结果",
        
        # TTA (Text-to-Audio)
        "tta_tab": "音效生成 (TTA)",
        "tta_text_label": "音效描述",
        "tta_text_info": "建议使用英文描述，效果更佳。例如: 'Rain is falling continuously'。",
        "tta_button": "生成音效",
        "tta_status_default": "💡 请输入音效的文本描述。",
        "tta_output_label": "生成结果",
        
        # Microphone permission
        "mic_permission_title": "麦克风权限不工作？点我查看解决方案",
        "mic_permission_text": """
如果你在使用 Chrome 浏览器时，麦克风权限无法正常工作，且本应用部署在非 HTTPS 站点上，请尝试以下步骤：

1.  在 Chrome 地址栏中输入 `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
2.  将该标志的状态改为 **Enabled**。
3.  在出现的"Enabled domains"或"启用的域名"输入框中，输入本应用的域名。
4.  **重要：** 彻底关闭并重新启动 Chrome 浏览器。

完成这些步骤后，你应该就能成功授予该页面麦克风权限了。
""",
    }
}


class I18nManager:
    """Manages internationalization for the application."""
    
    def __init__(self, default_lang="zh"):
        self.current_lang = default_lang
        
    def set_language(self, lang):
        """Set the current language."""
        if lang in TRANSLATIONS:
            self.current_lang = lang
            
    def get_text(self, key):
        """Get translated text for the current language."""
        return TRANSLATIONS.get(self.current_lang, {}).get(key, key)
    
    def __call__(self, key):
        """Shorthand for get_text."""
        return self.get_text(key)
