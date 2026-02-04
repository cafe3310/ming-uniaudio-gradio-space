import gradio as gr
import requests
import json
import base64
import time
import os
import uuid
import gzip
import io
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Any, Optional
from loguru import logger

# --- 静态数据 ---
DROPDOWN_CHOICES = {
    "bgm_genres": list(set(["凯尔特民间音乐", "独立流行乐", "中国流行乐", "歌剧", "都市流行乐", "流行乐", "浩室音乐", "中国民间音乐", "灵魂乐", "独立流行乐", "中国传统民间音乐", "其他流派", "流行灵魂乐", "日本流行乐", "灵魂乐", "室内流行乐", "乡村音乐", "弛放音乐", "舞曲流行乐", "世界音乐", "中世纪音乐", "青少年流行乐", "现代流行抒情曲", "其他", "后波普爵士乐", "舒缓节拍音乐", "原声钢琴", "轻松聆听音乐", "基督教音乐", "灵魂乐", "流行灵魂乐", "怀旧流行乐", "轻摇滚", "世界音乐", "爵士嘻哈", "新爵士", "节日音乐", "乡村蓝调", "凯尔特民间音乐", "日本摇滚", "新世纪音乐", "意大利流行乐", "轻摇滚", "青少年流行乐", "休闲音乐", "古风音乐", "工业金属", "爵士蓝调", "电子舞曲", "中世纪音乐", "乡村音乐", "电子舞曲陷阱音乐", "碎拍音乐", "新金属", "电影原声带", "传统爵士乐", "拉丁流行乐", "放克音乐", "电影原声带", "氛围音乐", "史诗音乐", "独立摇滚", "低保真摇滚", "韩国流行乐", "轻松聆听音乐", "氛围音乐", "爵士乐", "艺术歌曲", "梦幻流行乐", "配乐", "氛围音乐", "民谣流行乐", "爵士乐", "印象派音乐", "当代民间音乐", "当代古典音乐", "传统民间音乐", "伦巴", "爵士流行乐", "电影原声带", "慢拍电子乐", "泽西俱乐部音乐", "新灵魂乐", "新浪潮音乐", "雷鬼顿", "当代古典音乐", "怀旧流行乐", "休闲音乐", "中国民间音乐", "凯尔特流行乐", "桑巴", "英国车库音乐", "流行灵魂乐", "世界音乐", "慢拍电子乐", "电子民谣", "巴洛克音乐", "氛围音乐", "凯尔特民间音乐", "休闲音乐", "大房间浩室音乐", "硬摇滚", "法国民间音乐", "凯尔特民间音乐", "嘻哈/说唱", "民谣流行乐", "印象派音乐", "印象派音乐", "神游舞曲", "爵士流行乐", "歌剧", "爵士嘻哈", "古典音乐", "神游舞曲", "硬摇滚", "轻松聆听音乐", "放克音乐", "新世纪音乐", "爵士乐", "流行乐", "深度流行电子舞曲", "日本流行乐", "流行说唱", "中国传统民间音乐", "电子民谣", "古风音乐", "舒缓节拍音乐", "新世纪音乐", "流行朋克", "舒缓节拍音乐", "轻松聆听音乐", "民间音乐", "怀旧流行乐", "中国民间音乐", "传统民间音乐", "古风音乐", "东方流行乐", "轻摇滚", "独立摇滚", "中国传统民间音乐", "独立民谣"])),
    "bgm_moods": list(set(["兴奋", "鼓舞人心 / 充满希望,抒情 / 民谣", "抒情 / 民谣,其他音频情绪", "多愁善感 / 忧郁 / 孤独", "抒情 / 民谣", "其他音频情绪", "自信 / 坚定,神秘", "多愁善感 / 忧郁 / 孤独", "治愈", "鼓舞人心 / 充满希望,甜蜜的音频情绪", "闲适", "甜蜜的音频情绪,可爱 / 俏皮", "抒情 / 民谣", "自信 / 坚定,轻快 / 无忧无虑", "自信 / 坚定", "平静 / 放松", "温暖 / 友善,鼓舞人心 / 充满希望", "轻快 / 无忧无虑,抒情 / 民谣", "想念 / 回忆,轻快 / 无忧无虑", "严肃 / 沉思", "闲适", "快乐", "神奇 / 童话般,可爱 / 俏皮", "甜蜜的音频情绪", "浪漫", "多愁善感 / 忧郁 / 孤独", "多愁善感 / 忧郁 / 孤独", "怀旧 / 回忆", "治愈", "温暖 / 友善,兴奋", "壮丽 / 宏大,怀旧 / 回忆", "轻快 / 无忧无虑", "其他音频情绪", "想念 / 回忆,悲伤 / 哀愁", "平静 / 放松", "优雅 / 精致,快乐", "想念 / 回忆,怀旧 / 回忆", "鼓舞人心 / 充满希望", "鼓舞人心 / 充满希望,想念 / 回忆", "可爱 / 俏皮", "温暖 / 友善,多愁善感 / 忧郁 / 孤独", "鼓舞人心/充满希望", "想念/回忆", "快乐", "轻快/无忧无虑", "平静/放松", "紧张/刺激/悬疑/紧绷", "怀旧/回忆", "鼓舞人心/充满希望", "神秘", "怀旧/回忆", "兴奋", "活力四射/精力充沛", "自信/坚定", "想念/回忆", "闲适", "自信/坚定", "温暖/友善", "想念/回忆", "治愈", "深沉", "鼓舞人心/充满希望", "闲适", "兴奋", "温暖/友善", "闲适", "优雅/精致", "怀旧/回忆", "优雅/精致", "优雅/精致", "想念/回忆", "甜蜜的音频情绪", "怀旧/回忆", "轻快/无忧无虑", "温暖/友善", "治愈", "想念/回忆", "轻快/无忧无虑", "抒情/民谣", "壮丽/宏大", "平静/放松", "酷帅/有型", "多愁善感/忧郁/孤独", "兴奋", "自信/坚定", "鼓舞人心/充满希望", "轻快/无忧无虑", "闲适", "怀旧/回忆", "想念/回忆", "温暖/友善", "酷帅/有型", "快乐", "平静/放松", "严肃/沉思", "闲适", "优雅/精致", "怀旧/回忆", "神奇/童话般", "轻快/无忧无虑", "兴奋", "酷帅/有型", "悲伤/哀愁", "怀旧/回忆", "酷帅/有型", "可爱/俏皮", "抒情/民谣", "轻快/无忧无虑", "悲伤/哀愁", "温暖/友善", "深沉", "酷帅/有型", "优雅/精致", "闲适", "活力四射/精力充沛", "怀旧/回忆", "快乐", "抒情/民谣", "怀旧/回忆", "轻快/无忧无虑", "兴奋", "鼓舞人心/充满希望", "酷帅/有型", "怀旧/回忆", "怀旧/回忆", "悲伤/哀愁", "平静/放松", "怀旧/回忆", "快乐", "闲适", "闲适", "抒情/民谣", "想念/回忆", "平静/放松", "神奇/童话般", "优雅/精致", "怀旧/回忆", "怀旧/回忆", "酷帅/有型", "平静/放松", "闲适"])),
    "bgm_instruments": list(set(["手风琴", "钟琴,原声吉他,吊镲/碎音镲", "风铃,节奏镲,克拉维棍", "单簧管", "萨克斯管", "原声钢琴,踩镲", "合成主音", "排箫,合成垫音,箫", "上低音萨克斯,管风琴,萨克斯管", "电钢琴,合成主音", "陶笛", "键盘乐器,颤音琴,班卓琴", "清音电吉他", "陶笛,尤克里里", "原声钢琴,拨奏低音提琴,管风琴", "小提琴", "卡洪鼓 / 箱鼓", "民族乐器,合成鼓", "清音电吉他,嗵鼓", "陶笛,键盘乐器", "笛,三角铁", "颤音琴,合成主音,合唱团声乐", "颤音琴,钢琴,弦乐器", "钢琴,铃鼓,交响竖琴", "低音提琴", "电钢琴,原声吉他", "原声钢琴,单簧管", "尤克里里,低音鼓", "曼陀林", "打击乐感,小号", "铜管乐组", "哨子", "曼陀林", "英国管,琵琶", "笛,打击乐器", "上低音萨克斯,马林巴琴,原声钢琴", "合成垫音,管乐器,钟琴", "拨奏低音提琴", "长笛,交响竖琴", "架子鼓,打击乐感", "马林巴琴", "弦乐器", "键盘乐器", "键盘乐器", "原声吉他", "弦乐器", "电吉他", "贝斯", "打击乐器", "弦乐合奏", "原声吉他", "合成鼓", "贝斯", "低音鼓", "键盘乐器", "低音提琴", "打击乐感", "电贝斯", "合唱团声乐", "手碟", "交响竖琴", "电贝斯", "键盘乐器", "架子鼓", "长笛", "古筝", "颤音琴", "合唱团声乐", "合成垫音", "管乐器", "长笛", "钟琴", "原声钢琴", "长笛", "长笛", "弦乐器", "古筝", "键盘乐器", "长笛", "大提琴", "电钢琴", "贝斯", "原声钢琴", "合成主音", "低音鼓", "管风琴", "清音电吉他", "原声钢琴", "扬琴", "小提琴", "原声吉他", "键盘乐器", "原声钢琴", "中国传统乐器", "合成垫音", "原声钢琴", "弦乐合奏", "清音电吉他", "小提琴", "铃鼓", "打击乐感", "嗵鼓", "原声吉他", "原声吉他", "合成拨弦", "清音电吉他", "弦乐合奏", "钢琴", "电钢琴", "原声钢琴", "圆号", "爵士吉他", "圆号", "钢琴", "失真电吉他", "大提琴", "低音鼓", "双簧管", "键盘乐器", "合成拨弦", "电贝斯", "铃鼓", "合成主音", "排箫", "清音电吉他", "中国传统乐器", "原声钢琴", "爱尔兰哨笛", "架子鼓", "手碟", "双簧管", "管乐器", "键盘乐器", "弦乐合奏", "民族乐器", "阮", "合成垫音", "电贝斯", "键盘乐器", "古筝", "低音提琴"])),
    "bgm_themes": list(set(["旅行", "中秋节", "水", "日落 / 下午", "暧昧", "美容 / 时尚", "足球", "公园", "家庭", "婴儿/宝宝", "睡眠", "校园", "生活", "户外", "祈祷", "公路旅行", "旅行", "自然", "傍晚", "水", "早晨", "棒球", "购物", "动漫", "约会", "花卉", "葬礼", "散步", "无主题", "复活节", "舞蹈", "励志", "视频博客 / 日常生活", "视频博客", "情感的", "摄影", "醒来", "黎明", "工作", "通勤", "醒来", "节日", "生活", "购物", "视频博客", "家庭", "高能视频", "周末", "驾驶", "冒险/探索", "婚礼", "汽车", "夜总会", "健身房", "旅游", "野餐", "健身房", "购物", "雪", "雨天", "电影", "派对", "傍晚", "派对", "宠物/动物", "艺术", "摄影", "回忆", "午夜", "风景", "葬礼", "婚礼", "夜晚", "公园", "儿童", "延时摄影", "森林", "招待会", "周末", "历史", "学习", "汽车", "分手", "视频博客", "适合跳舞的", "教堂", "餐厅", "好时光", "家庭", "森林", "食物", "广告", "旅游", "回忆", "睡前", "日出", "文化活动", "阅读", "花卉", "假期", "游戏", "汽车", "冬天", "钓鱼", "有氧运动", "家庭", "纪录片配乐", "醒来", "日落/下午", "城镇", "剧院/音乐厅", "汽车", "秋天", "咖啡馆", "运动", "树木", "网球", "纪录片配乐", "旅途", "夏天", "夜总会", "好时光", "驾驶", "秋天", "风景", "戏剧/剧情", "思考", "浪漫", "庆典与喜悦", "水", "阅读", "圣诞节", "日落/下午", "风景", "婴儿/宝宝", "浪漫", "生活", "公路旅行", "好时光", "田园", "冬天"])),
    "dialects": list(set(["四川话","广粤话"])),
    "env_sounds": [] # 原 Demo 未使用
}

IP_DICT = {
    "何幸福": "幸福到万家_何幸福", "朱元璋": "山河月明_朱元璋", "朱标": "山河月明_朱标",
    "朱棣": "山河月明_朱棣", "潘金莲": "水浒传_潘金莲", "公孙胜": "水浒传_公孙胜",
    "齐铁嘴": "老九门_齐铁嘴", "爱新觉罗·弘时": "雍正王朝_爱新觉罗·弘时", "邬思道": "雍正王朝_邬思道",
    "孝庄": "康熙王朝_孝庄", "吴三桂": "康熙王朝_吴三桂", "司徒末": "致我们暖暖的小时光_司徒末",
    "宋慈": "大宋提刑官_宋慈", "刁光斗": "大宋提刑官_刁光斗", "萧崇": "少年歌行_萧崇",
    "余则成": "潜伏_余则成", "左蓝": "潜伏_左蓝", "曹操": "三国演义_曹操", "四郎": "甄嬛传_四郎",
    "李蔷": "法医秦明_李蔷", "陆建勋": "老九门_陆建勋", "野原美伢 (美伢)": "蜡笔小新_野原美伢 (美伢)",
    "荣妃": "康熙王朝_荣妃", "青年康熙": "康熙王朝_青年康熙", "许半夏": "风吹半夏_许半夏",
    "朱颜": "玉骨遥_朱颜", "王翠平": "潜伏_王翠平", "李涯": "潜伏_李涯", "穆晚秋": "潜伏_穆晚秋",
    "陆桥山": "潜伏_陆桥山", "徐文昌": "安家_徐文昌", "关涛": "幸福到万家_关涛",
    "铁铉": "山河月明_铁铉", "苏培盛": "甄嬛传_苏培盛", "武松": "水浒传_武松", "秦明": "法医秦明_秦明",
    "裘德考": "老九门_裘德考", "张启山": "老九门_张启山", "爱新觉罗·弘历": "雍正王朝_爱新觉罗·弘历",
    "年羹尧": "雍正王朝_年羹尧", "雍正": "雍正王朝_雍正", "野原新之助 (小新)": "蜡笔小新_野原新之助 (小新)",
    "潘越": "哈尔滨一九四四_潘越", "关雪": "哈尔滨一九四四_关雪", "佩奇": "小猪佩奇_佩奇",
    "康熙": "康熙王朝_康熙", "苏麻喇姑": "康熙王朝_苏麻喇姑", "郭启东": "风吹半夏_郭启东",
    "卢怀德": "大宋提刑官_卢怀德", "丰兰息": "且试天下_丰兰息", "灰太狼": "喜羊羊与灰太狼_灰太狼",
    "唐僧": "西游记_唐僧", "郭德纲": "郭德纲_郭德纲", "于谦": "于谦_于谦", "孙颖莎": "孙颖莎_孙颖莎"
}

class UniAudioDemoTab:
    """
    一个集成的 Gradio Tab，移植自原独立的 'instuct-tts-gradio.py' 演示脚本。
    包含：指令TTS、零样本TTS、播客、BGM生成、音效生成等多个功能。
    独立实现了基于 UniAudio V4 MOE (WebGW) 的请求逻辑。
    """
    def __init__(self, webgw_url, webgw_api_key, webgw_app_id, api_project="260203-ming-uniaudio-v4-moe-lite"):
        self.webgw_url = webgw_url
        self.api_key = webgw_api_key
        self.app_id = webgw_app_id
        self.api_project = api_project

    def create_tab(self):
        with gr.TabItem("UniAudio V4 MOE 综合演示"):
            gr.Markdown("## UniAudio V4 MOE 综合能力演示")

            with gr.Tabs():
                # --- Tab 1: 指令TTS ---
                with gr.TabItem("指令TTS (Instruct TTS)"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            i_tts_type = gr.Dropdown(["dialect", "emotion", "IP", "style", "basic"], label="指令类型", value="emotion")
                            i_tts_text = gr.Textbox(label="合成文本", info="输入要合成的语音文本。")
                            i_tts_prompt = gr.Audio(type="filepath", label="参考音频 (3-7秒)上传一段清晰的人声音频用于克隆基础音色。", sources=["upload"])

                            with gr.Accordion("指令详情 (根据指令类型填写)", open=True):
                                i_tts_emotion = gr.Dropdown(["高兴", "悲伤", "愤怒"], label="情感", value="高兴")
                                i_tts_dialect = gr.Dropdown(DROPDOWN_CHOICES["dialects"], label="方言", value="广粤话", visible=False)
                                i_tts_ip = gr.Dropdown(list(IP_DICT.keys()), label="IP角色", visible=False)
                                i_tts_style = gr.Textbox(label="风格描述", info="e.g., '一位男性歌手用清晰有力的声音演唱充满激情与史诗感的流行摇滚情歌'", visible=False)
                                i_tts_speed = gr.Dropdown(["慢速", "中速", "快速"], label="语速", value="中速", visible=False)
                                i_tts_pitch = gr.Dropdown(["低", "中", "高"], label="基频", value="中", visible=False)
                                i_tts_volume = gr.Dropdown(["低", "中", "高"], label="音量", value="中", visible=False)

                            i_tts_btn = gr.Button("生成指令语音", variant="primary")

                        with gr.Column(scale=1):
                            i_tts_status = gr.Markdown(value="💡 请选择指令类型并填写参数。")
                            i_tts_output = gr.Audio(label="生成结果", type="filepath", interactive=False)

                    def update_details_visibility(instruct_type):
                        prompt_visible = instruct_type not in ["IP", "style"]
                        return {
                            i_tts_prompt: gr.update(visible=prompt_visible),
                            i_tts_emotion: gr.update(visible=instruct_type == 'emotion'),
                            i_tts_dialect: gr.update(visible=instruct_type == 'dialect'),
                            i_tts_ip: gr.update(visible=instruct_type == 'IP'),
                            i_tts_style: gr.update(visible=instruct_type == 'style'),
                            i_tts_speed: gr.update(visible=instruct_type == 'basic'),
                            i_tts_pitch: gr.update(visible=instruct_type == 'basic'),
                            i_tts_volume: gr.update(visible=instruct_type == 'basic'),
                        }
                    i_tts_type.change(fn=update_details_visibility, inputs=i_tts_type, outputs=[i_tts_prompt, i_tts_emotion, i_tts_dialect, i_tts_ip, i_tts_style, i_tts_speed, i_tts_pitch, i_tts_volume])

                # --- Tab 2: 零样本TTS (音色克隆) ---
                with gr.TabItem("音色克隆 (Zero-shot TTS)"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            zs_tts_text = gr.Textbox(label="目标文本", info="输入您想合成的语音文本。")
                            zs_tts_prompt = gr.Audio(type="filepath", label="参考音频 (3-7秒)上传一段清晰的人声音频用于克隆音色。", sources=["upload"])
                            zs_tts_btn = gr.Button("克隆并生成语音", variant="primary")
                        with gr.Column(scale=1):
                            zs_tts_status = gr.Markdown(value="💡 请输入文本并上传参考音频。")
                            zs_tts_output = gr.Audio(label="生成结果", type="filepath", interactive=False)

                # --- Tab 3: 多人播客 ---
                with gr.TabItem("播客 (Podcast)"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            pod_text = gr.Textbox(lines=5, label="对话脚本", info="使用 'speaker_1:', 'speaker_2:' 区分不同说话人。e.g. speaker_1:就比如说各种就是给别人提供，提供帮助的都可以说是服务的\n speaker_2:是的 不管是什么，就是说感觉都是，大家都，都可以说是服务业的一方面\n")
                            pod_prompt1 = gr.Audio(type="filepath", label="说话人1参考音频", sources=["upload"])
                            pod_prompt2 = gr.Audio(type="filepath", label="说话人2参考音频", sources=["upload"])
                            pod_btn = gr.Button("生成播客", variant="primary")
                        with gr.Column(scale=1):
                            pod_status = gr.Markdown(value="💡 请填写脚本并上传两位说话人的参考音频。")
                            pod_output = gr.Audio(label="生成结果", type="filepath", interactive=False)

                # --- Tab 4: 带背景音乐的语音 ---
                with gr.TabItem("带背景音乐的语音 (Speech with BGM)"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            swb_text = gr.Textbox(label="语音文本")
                            swb_prompt = gr.Audio(type="filepath", label="说话人参考音频", sources=["upload"])
                            gr.Markdown("##### 背景音乐描述")
                            with gr.Row():
                                swb_genre = gr.Dropdown(DROPDOWN_CHOICES["bgm_genres"], label="风格 (Genre)", value="硬摇滚")
                                swb_mood = gr.Dropdown(DROPDOWN_CHOICES["bgm_moods"], label="情绪 (Mood)", value="酷帅/有型")
                            with gr.Row():
                                swb_instrument = gr.Dropdown(DROPDOWN_CHOICES["bgm_instruments"], label="乐器 (Instrument)", value="键盘乐器")
                                swb_theme = gr.Dropdown(DROPDOWN_CHOICES["bgm_themes"], label="主题 (Theme)", value="派对")
                            with gr.Row():
                                swb_snr = gr.Slider(0, 20, value=10.0, step=0.5, label="信噪比 (SNR)", info="值越小，背景音乐音量越大。")
                            swb_btn = gr.Button("生成带BGM的语音", variant="primary")
                        with gr.Column(scale=1):
                            swb_status = gr.Markdown(value="💡 请填写所有字段并上传参考音频。")
                            swb_output = gr.Audio(label="生成结果", type="filepath", interactive=False)

                # --- Tab 5: 纯背景音乐生成 ---
                with gr.TabItem("背景音乐生成 (BGM)"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            bgm_genre = gr.Dropdown(DROPDOWN_CHOICES["bgm_genres"], label="风格 (Genre)", value="新灵魂乐")
                            bgm_mood = gr.Dropdown(DROPDOWN_CHOICES["bgm_moods"], label="情绪 (Mood)", value="多愁善感 / 忧郁 / 孤独")
                            bgm_instrument = gr.Dropdown(DROPDOWN_CHOICES["bgm_instruments"], label="乐器 (Instrument)", value="原声钢琴")
                            bgm_theme = gr.Dropdown(DROPDOWN_CHOICES["bgm_themes"], label="主题 (Theme)", value="分手")
                            bgm_duration = gr.Slider(30, 120, value=35, step=1, label="时长 (秒)")
                            bgm_btn = gr.Button("生成背景音乐", variant="primary")
                        with gr.Column(scale=1):
                            bgm_status = gr.Markdown(value="💡 请描述您想要的音乐。")
                            bgm_output = gr.Audio(label="生成结果", type="filepath", interactive=False)

                # --- Tab 6: 音效生成 ---
                with gr.TabItem("音效生成 (TTA)"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            tta_text = gr.Textbox(label="音效描述", info="建议使用英文描述，效果更佳。例如: 'Rain is falling continuously'。")
                            tta_btn = gr.Button("生成音效", variant="primary")
                        with gr.Column(scale=1):
                            tta_status = gr.Markdown(value="💡 请输入音效的文本描述。")
                            tta_output = gr.Audio(label="生成结果", type="filepath", interactive=False)

            # --- 事件绑定 ---
            def i_tts_submit(instruct_type, text, prompt_audio, emotion, dialect, ip_choice, style, speed, pitch, volume):
                details = {}
                if instruct_type == 'emotion': details = {"情感": emotion}
                elif instruct_type == 'dialect': details = {"方言": dialect}
                elif instruct_type == 'IP':
                    backend_ip = IP_DICT.get(ip_choice)
                    if not backend_ip: raise gr.Error(f"未找到IP角色'{ip_choice}'的配置。")
                    details = {"IP": backend_ip}
                elif instruct_type == 'style': details = {"风格": style}
                elif instruct_type == 'basic': details = {"语速": speed, "基频": pitch, "音量": volume}
                yield from self._submit_and_poll("TTS", instruct_type, text, prompt_audio, details)

            i_tts_btn.click(
                fn=i_tts_submit,
                inputs=[i_tts_type, i_tts_text, i_tts_prompt, i_tts_emotion, i_tts_dialect, i_tts_ip, i_tts_style, i_tts_speed, i_tts_pitch, i_tts_volume],
                outputs=[i_tts_status, i_tts_btn, i_tts_output]
            )

            zs_tts_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("zero_shot_TTS", *args)),
                inputs=[zs_tts_text, zs_tts_prompt], outputs=[zs_tts_status, zs_tts_btn, zs_tts_output]
            )
            pod_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("podcast", *args)),
                inputs=[pod_text, pod_prompt1, pod_prompt2], outputs=[pod_status, pod_btn, pod_output]
            )
            swb_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("speech_with_bgm", *args)),
                inputs=[swb_text, swb_prompt, swb_genre, swb_mood, swb_instrument, swb_theme, swb_snr],
                outputs=[swb_status, swb_btn, swb_output]
            )
            bgm_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("bgm", *args)),
                inputs=[bgm_genre, bgm_mood, bgm_instrument, bgm_theme, bgm_duration],
                outputs=[bgm_status, bgm_btn, bgm_output]
            )
            tta_btn.click(
                fn=lambda *args: (yield from self._submit_and_poll("TTA", *args)),
                inputs=[tta_text], outputs=[tta_status, tta_btn, tta_output]
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

            files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) 
                     if os.path.isfile(os.path.join(output_dir, f))]
            
            # 按修改时间排序（从旧到新）
            files.sort(key=os.path.getmtime)
            
            if len(files) >= max_files:
                num_to_delete = len(files) - max_files + 1 # +1 是为了给即将新创建的文件腾位置，保持总数 <= 10
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
            gr.update(value=None)
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
                    "caption": json.dumps(caption_obj, ensure_ascii=False), # 序列化
                    "prompt_wav_b64": prompt_b64
                }
            elif task_type == "zero_shot_TTS":
                text, prompt_audio = args
                logger.info(f"[Zero-shot TTS] Preparing task. Text: '{text[:20]}...', Audio: {prompt_audio}")
                prompt_b64 = self._file_to_b64(prompt_audio)
                if not text or not prompt_b64:
                     logger.error("[Zero-shot TTS] Validation failed: Missing text or prompt audio.")
                     raise ValueError("文本和参考音频不能为空。")
                payload = {"task_type": "zero_shot_TTS", "text": text, "prompt_wav_b64": prompt_b64}
                logger.info("[Zero-shot TTS] Payload constructed successfully.")
            elif task_type == "podcast":
                text, prompt_audio_1, prompt_audio_2 = args
                prompt_b64_1, prompt_b64_2 = self._file_to_b64(prompt_audio_1), self._file_to_b64(prompt_audio_2)
                if not text or not prompt_b64_1 or not prompt_b64_2:
                     raise ValueError("对话脚本和两个参考音频均不能为空。")
                payload = {"task_type": "podcast", "text": text, "prompt_wavs_b64": [prompt_b64_1, prompt_b64_2]}
            elif task_type == "bgm":
                genre, mood, instrument, theme, duration = args
                prompt_text = f"Genre: {genre}. Mood: {mood}. Instrument: {instrument}. Theme: {theme}. Duration: {duration}s."
                payload = {"task_type": "bgm", "prompt_text": prompt_text}
            elif task_type == "TTA":
                text, = args
                if not text:
                    raise ValueError("音效描述不能为空。")
                payload = {"task_type": "TTA", "text": text}
            elif task_type == "speech_with_bgm":
                text, prompt_audio, genre, mood, instrument, theme, snr = args
                prompt_b64 = self._file_to_b64(prompt_audio)
                if not text or not prompt_b64:
                    raise ValueError("文本和参考音频不能为空。")
                bgm_data = {
                    "Genre": f"{genre}.", "Mood": f"{mood}.", "Instrument": f"{instrument}.",
                    "Theme": f"{theme}.", "SNR": str(float(snr)), "ENV": None
                }
                payload = {
                    "task_type": "speech_with_bgm",
                    "text": text,
                    "prompt_wav_b64": prompt_b64,
                    "caption": json.dumps(bgm_data, ensure_ascii=False) # 序列化
                }
            else:
                raise ValueError(f"未知的任务类型: {task_type}")

        except Exception as e:
            yield (gr.update(value=f"❌ 错误：输入参数组装失败 - {e}"), gr.update(interactive=True), gr.update(value=None))
            return

        yield (gr.update(value="🚀 任务提交中..."), gr.update(interactive=False), gr.update(value=None))

        # --- 发起 WebGW 请求 (Submit) ---
        call_token = str(uuid.uuid4())
        logger.info(f"[{task_type}] Submitting task to WebGW. Token: {call_token}")
        
        request_body = {
            "api_key": self.api_key,
            "api_project": self.api_project,
            "call_name": "submit_task",
            "call_token": call_token,
            "call_args": payload
        }

        headers = {
            "Content-Type": "application/json",
            "x-webgw-appid": self.app_id,
            "x-webgw-version": "2.0"
        }

        try:
            logger.info(f"Submitting task to WebGW: {self.webgw_url}")
            r = requests.post(url=self.webgw_url, json=request_body, headers=headers, timeout=30)
            r.raise_for_status()
            res_data = r.json()

            if not res_data.get('success'):
                raise ConnectionError(f"WebGW 请求失败: {res_data.get('errorMessage', '未知错误')}")

            # 解析内部结果
            result_obj = res_data.get('resultObj', {})
            inner_result_str = result_obj.get('result')

            if not inner_result_str:
                # 可能是直接返回在 resultObj 里，视具体实现而定，但标准 WebGW 通常在 result 字段返回字符串
                # 这里的解析逻辑需要适配 Chair FaaS 的 AudioProxyController 返回
                # 回顾 AudioProxyController，它返回 { result: object }
                # 如果是 AudioProxyController.ts:
                # return { success: true, resultObj: { ..., result: res } }
                # 所以 res 就是 payload
                inner_result = result_obj.get('result')
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
            yield (gr.update(value=f"❌ 错误：任务提交失败 - {e}"), gr.update(interactive=True), gr.update(value=None))
            return

        # --- 轮询逻辑 (Poll) ---
        max_polls = 60 # 2分钟超时
        poll_interval = 2

        for i in range(max_polls):
            yield (gr.update(value=f"🔄 生成中... ({i*poll_interval}s)"), gr.update(interactive=False), gr.update(value=None))
            time.sleep(poll_interval)

            poll_body = {
                "api_key": self.api_key,
                "api_project": self.api_project,
                "call_name": "poll_task",
                "call_token": str(uuid.uuid4()),
                "call_args": {"task_id": task_id}
            }

            try:
                r = requests.post(url=self.webgw_url, json=poll_body, headers=headers, timeout=30)
                r.raise_for_status()
                res_data = r.json()

                if not res_data.get('success'):
                    logger.warning(f"Poll request failed: {res_data.get('errorMessage')}")
                    continue # 轮询失败暂不中断，重试

                result_obj = res_data.get('resultObj', {})
                inner_result = result_obj.get('result') # 对象或字符串

                if not inner_result: continue

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
                            "signature": query_params.get("Signature", [None])[0]
                        }
                        
                        logger.info(f"Downloading audio via Proxy: {proxy_args['filename']}")
                        
                        proxy_payload = {
                            "api_key": self.api_key,
                            "api_project": self.api_project,
                            "call_name": "get_audio",
                            "call_token": str(uuid.uuid4()),
                            "call_args": proxy_args
                        }
                        
                        # 发起代理下载请求 (POST)
                        audio_resp = requests.post(url=self.webgw_url, json=proxy_payload, headers=headers, timeout=60)
                        audio_resp.raise_for_status()
                        
                        res_json = audio_resp.json()
                        if not res_json.get('success'):
                            raise RuntimeError(f"Proxy download error: {res_json.get('errorMessage', 'Unknown error')}")

                        # 解析 Gzip+Base64 响应
                        result_obj = res_json.get('resultObj', {})
                        # result 可能是 JSON 对象也可能是字符串
                        inner_result = result_obj.get('result')
                        if isinstance(inner_result, str):
                            try:
                                inner_result = json.loads(inner_result)
                            except json.JSONDecodeError:
                                pass # 应该不会发生，除非格式错乱

                        if not isinstance(inner_result, dict) or 'gzippedRaw' not in inner_result:
                            raise ValueError("Invalid proxy response: missing 'gzippedRaw' field")
                        
                        gzipped_b64 = inner_result['gzippedRaw']
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
                        self._cleanup_temp_files("temp_audio") # 清理旧文件
                        
                        audio_file = os.path.join("temp_audio", f"{task_id}.wav")
                        with open(audio_file, "wb") as f_out:
                            f_out.write(content)

                        yield (gr.update(value="✅ 成功！"), gr.update(interactive=True), gr.update(value=audio_file))
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

        yield (gr.update(value="⏰ 错误：任务超时。", color="red"), gr.update(interactive=True), gr.update(value=None))
