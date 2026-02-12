import base64
import gzip
import io
import json
import os
import random
import re
import tempfile
import time
import uuid
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from loguru import logger

# ============================================================
# 1. 预设选项和数据
# ============================================================

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
# 2. 综合播客生成器主类
# ============================================================
class CompositePodcastGenerator:
    def __init__(self, webgw_url, api_key, api_project, app_id, ip_dict):
        # 统一使用主框架的WebGW配置
        self.webgw_url = webgw_url
        self.api_key = api_key
        self.api_project = api_project
        self.app_id = app_id

        # 独立的功能配置
        self.ip_dict = ip_dict
        self.ip_lines_dict = self._get_ip_lines()
        self.bgm_params_list = self._get_bgm_params()

    def _file_to_b64(self, filepath: Optional[str]) -> Optional[str]:
        if not filepath or not os.path.exists(filepath):
            return None
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

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

    def _get_headers(self) -> Dict:
        return {
            "Content-Type": "application/json",
            "x-webgw-appid": self.app_id,
            "x-webgw-version": "2.0",
        }

    def _parse_inner_result(self, res: Dict) -> Dict:
        """从 WebGW 响应中解析出内层结果字典。"""
        if not res.get("success"):
            raise ConnectionError(f"WebGW 请求失败: {res.get('errorMessage', '未知错误')}")
        result_str = res.get("resultObj", {}).get("result", "{}")
        if isinstance(result_str, str):
            inner_result = json.loads(result_str)
        else:
            inner_result = result_str
        # 处理 rawResult 嵌套
        if "task_id" not in inner_result and "status" not in inner_result:
            raw_request = inner_result.get("rawResult", {})
            if isinstance(raw_request, str):
                try:
                    raw_request = json.loads(raw_request)
                    inner_result = raw_request.get("data", {})
                except json.JSONDecodeError:
                    pass
        return inner_result

    def _submit_task(self, payload: Dict, task_name: str) -> str:
        """提交任务，返回 task_id。单次 HTTP 请求，不阻塞。"""
        submit_body = {
            "api_key": self.api_key,
            "api_project": self.api_project,
            "call_name": "submit_task",
            "call_token": str(uuid.uuid4()),
            "call_args": payload,
        }
        r = requests.post(self.webgw_url, json=submit_body, headers=self._get_headers(), timeout=7)
        r.raise_for_status()
        inner_result = self._parse_inner_result(r.json())
        task_id = inner_result.get("task_id")
        if not task_id:
            raise ValueError(f"[{task_name}] 未能获取 task_id: {inner_result}")
        logger.info(f"[{task_name}] 任务提交成功, Task ID: {task_id}")
        return task_id

    def _poll_task(self, task_id: str) -> Dict:
        """轮询一次任务状态，返回解析后的结果字典。单次 HTTP 请求，不阻塞。"""
        poll_body = {
            "api_key": self.api_key,
            "api_project": self.api_project,
            "call_name": "poll_task",
            "call_token": str(uuid.uuid4()),
            "call_args": {"task_id": task_id},
        }
        r = requests.post(self.webgw_url, json=poll_body, headers=self._get_headers(), timeout=7)
        r.raise_for_status()
        return self._parse_inner_result(r.json())

    def _download_via_proxy(self, url: str, output_path: str) -> str:
        """通过 WebGW 代理下载文件（单次请求）。"""
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        proxy_args = {
            "filename": os.path.basename(parsed_url.path),
            "oss_access_key_id": query_params.get("OSSAccessKeyId", [None])[0],
            "expires": query_params.get("Expires", [None])[0],
            "signature": query_params.get("Signature", [None])[0],
        }
        proxy_payload = {
            "api_key": self.api_key,
            "api_project": self.api_project,
            "call_name": "get_audio",
            "call_token": str(uuid.uuid4()),
            "call_args": proxy_args,
        }
        resp = requests.post(
            self.webgw_url, json=proxy_payload, headers=self._get_headers(), timeout=7
        )
        resp.raise_for_status()
        res_json = resp.json()
        if not res_json.get("success"):
            raise RuntimeError(f"代理下载失败: {res_json.get('errorMessage', '未知')}")

        inner = res_json.get("resultObj", {}).get("result", {})
        if isinstance(inner, str):
            inner = json.loads(inner)
        if "gzippedRaw" not in inner:
            raise ValueError("代理响应中缺少 'gzippedRaw' 字段")

        compressed_data = base64.b64decode(inner["gzippedRaw"])
        with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as f_gz:
            content = f_gz.read()

        with open(output_path, "wb") as f_out:
            f_out.write(content)
        logger.info(f"文件下载成功: {output_path}")
        return output_path

    def _poll_until_done(self, task_id: str, task_name: str, timeout: int = 600):
        """
        轮询生成器：每次轮询后 yield 已等待秒数。
        调用方用 for elapsed in self._poll_until_done(...) 来驱动。
        任务完成时自动退出；失败或超时则抛异常。
        """
        start_time = time.time()
        poll_interval = 2
        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            logger.info(f"[{task_name}] 轮询中... 已等待 {int(time.time() - start_time)} 秒")
            elapsed = int(time.time() - start_time)
            try:
                poll_data = self._poll_task(task_id)
                status = poll_data.get("status")
                if status in ("completed", "success"):
                    logger.info(f"[{task_name}] 任务完成, Task ID: {task_id}")
                    return  # 正常退出生成器
                elif status == "failed":
                    error_msg = poll_data.get("error_message", poll_data.get("error", "未知错误"))
                    raise RuntimeError(f"[{task_name}] 任务失败: {error_msg}")
                # pending 则继续
            except RuntimeError:
                raise
            except Exception as e:
                logger.warning(f"[{task_name}] 轮询异常，继续重试: {e}")
            yield elapsed
        raise TimeoutError(f"[{task_name}] 任务 {task_id} 超时({timeout}秒)")

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
            f"格式化后: {result[:100]}"
        )

        return result

    def _split_chunks(self, text: str, max_chars: int = 280) -> List[str]:
        lines = [line for line in text.split("\n") if line.strip()]

        if not lines:
            return []
        if not lines[0].startswith(" speaker_1"):
            raise ValueError("文本必须以'speaker_1'的发言开始。")

        # 步骤 1: 将连续的行按“轮次”分组
        # 每一轮都由一个 'speaker_1' 的发言和其后所有 'speaker_2' 的连续发言构成
        turns = []
        current_turn = []
        for line in lines:
            if line.startswith(" speaker_1"):
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
        核心生成逻辑，改为生成器函数。
        yield ("progress", "消息") 表示进度更新。
        yield ("done", (status_msg, audio_path, video_path)) 表示完成。
        yield ("error", error_msg) 表示失败。
        """
        logger.info("=" * 20 + " 开始执行综合播客生成任务 " + "=" * 20)

        try:
            if not text or not text.strip().startswith("speaker_1"):
                raise ValueError("播客台本不能为空或格式错误。")

            raw_text = text
            text = self._normalize_script(text)
            persistent_dir = "temp_audio"
            os.makedirs(persistent_dir, exist_ok=True)

            # ========== 步骤1: 准备说话人音色 ==========
            prompt_b64s = [None, None]
            choices = [
                (spk1_choice, spk1_ip, spk1_audio, 1),
                (spk2_choice, spk2_ip, spk2_audio, 2),
            ]

            for choice, ip_name, audio_file, spk_num in choices:
                if choice == "IP音色":
                    if not ip_name:
                        raise ValueError(f"请为说话人{spk_num}选择一个IP角色。")

                    # 确定 IP TTS 文本
                    if ip_name in self.ip_lines_dict:
                        ip_tts_text = self.ip_lines_dict[ip_name]
                    else:
                        ip_tts_text = None
                        for line in text.split("\n"):
                            line = line.strip()
                            if line.startswith(f"speaker_{spk_num}:"):
                                extracted = line.split(":", 1)[1].strip()
                                if extracted:
                                    ip_tts_text = extracted
                                    break
                        if not ip_tts_text:
                            raise ValueError(
                                f"IP角色 '{ip_name}' 无预设台词，"
                                f"且台本中未找到 speaker_{spk_num} 的有效发言。"
                            )

                    yield ("progress", f"正在生成说话人{spk_num}的IP音色...")

                    payload = {
                        "task_type": "TTS",
                        "instruct_type": "IP",
                        "text": ip_tts_text,
                        "caption": json.dumps({"audio_sequence": [{"IP": self.ip_dict[ip_name]}]}),
                    }
                    ip_task_id = self._submit_task(payload, f"ip-gen-spk{spk_num}")

                    # 轮询等待 IP 音色生成完成
                    for elapsed in self._poll_until_done(
                        ip_task_id, f"IP音色-说话人{spk_num}", 600
                    ):
                        yield ("progress", f"正在生成说话人{spk_num}的IP音色... ({elapsed}s)")

                    # IP 完成后需要下载音频用作后续输入
                    poll_data = self._poll_task(ip_task_id)
                    audio_url = poll_data.get("output_audio_url")
                    if not audio_url:
                        raise ValueError(f"IP音色任务完成但未返回音频URL")

                    with tempfile.TemporaryDirectory() as tmp:
                        ip_audio_path = os.path.join(tmp, f"ip_spk{spk_num}.wav")
                        self._download_via_proxy(audio_url, ip_audio_path)
                        prompt_b64s[spk_num - 1] = self._file_to_b64(ip_audio_path)
                else:
                    if not audio_file:
                        raise ValueError(f"请为说话人{spk_num}提供参考音频。")
                    prompt_b64s[spk_num - 1] = self._file_to_b64(audio_file)

            # ========== 步骤2: 分片生成播客音频 ==========
            chunks = self._split_chunks(text)
            speech_task_ids = []

            for i, chunk in enumerate(chunks):
                yield ("progress", f"正在提交播客分片 {i+1}/{len(chunks)}...")
                task_id = self._submit_task(
                    {"task_type": "podcast", "text": chunk, "prompt_wavs_b64": prompt_b64s},
                    f"podcast-chunk-{i}",
                )
                # 轮询等待该分片完成
                for elapsed in self._poll_until_done(task_id, f"播客分片{i+1}", 600):
                    yield ("progress", f"正在生成播客分片 {i+1}/{len(chunks)}... ({elapsed}s)")

                speech_task_ids.append(task_id)

            logger.info(f"所有播客分片任务已完成，共 {len(speech_task_ids)} 个 task_id")

            # ========== 步骤3: 可选BGM ==========
            bgm_task_id = None
            if add_bgm:
                yield ("progress", "正在生成背景音乐...")
                bgm_params = random.choice(self.bgm_params_list)
                bgm_prompt = (
                    f"Genre: {bgm_params['genre']}. "
                    f"Mood: {bgm_params['mood']}. "
                    f"Instrument: {bgm_params['instrument']}. "
                    f"Theme: {bgm_params['theme']}. "
                    f"Duration: 60s."
                )
                bgm_task_id = self._submit_task(
                    {"task_type": "bgm", "prompt_text": bgm_prompt}, "bgm-gen"
                )
                for elapsed in self._poll_until_done(bgm_task_id, "BGM生成", 600):
                    yield ("progress", f"正在生成背景音乐... ({elapsed}s)")

                logger.info(f"BGM 任务已完成，task_id: {bgm_task_id}")

            # ========== 步骤4: 提交 composite_audio_video ==========
            yield ("progress", "正在提交最终合成任务...")

            composite_payload = {
                "task_type": "composite_audio_video",
                "speech_task_id_list": speech_task_ids,
            }
            if generate_video:
                composite_payload["raw_text"] = raw_text
            if bgm_task_id:
                composite_payload["bgm_task_id"] = bgm_task_id
                composite_payload["mix_snr"] = float(bgm_snr)

            composite_task_id = self._submit_task(composite_payload, "composite-final")

            for elapsed in self._poll_until_done(composite_task_id, "最终合成", 600):
                yield ("progress", f"正在进行最终合成... ({elapsed}s)")

            # ========== 步骤5: 下载最终产物 ==========
            yield ("progress", "正在下载最终产物...")

            poll_data = self._poll_task(composite_task_id)
            video_url = poll_data.get("output_video_url")
            audio_url = poll_data.get("output_audio_url")
            download_url = video_url or audio_url

            if not download_url:
                raise ValueError("合成任务完成但未返回任何输出URL")

            if video_url:
                out_path = os.path.join(persistent_dir, f"podcast_video_{uuid.uuid4()}.mp4")
                self._download_via_proxy(video_url, out_path)
                yield ("done", ("✅ 成功！", None, out_path))
            else:
                out_path = os.path.join(persistent_dir, f"podcast_{uuid.uuid4()}.wav")
                self._download_via_proxy(audio_url, out_path)
                yield ("done", ("✅ 成功！", out_path, None))

            logger.info("=" * 20 + " 综合播客生成任务成功 " + "=" * 20)

        except Exception as e:
            logger.error("综合播客任务失败！", exc_info=True)
            yield ("error", str(e))
