#!/usr/bin/env python3
"""
Video to Podcast Generator
从视频字幕生成多人对话播客

用法:
    python generate_podcast.py --url "https://youtube.com/..." --output podcast.wav
    python generate_podcast.py --srt video.srt --output podcast.wav
    python generate_podcast.py --script podcast_script.txt --output podcast.wav
"""

import argparse
import json
import os
import re
import sys
import wave
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv

SKILL_DIR = Path(__file__).parent.parent
load_dotenv(SKILL_DIR / "assets" / ".env")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("错误: 请安装 google-genai")
    print("  pip install google-genai")
    sys.exit(1)


# ============================================================
# 配置
# ============================================================

DEFAULT_DURATION = 8  # 默认播客时长（分钟）


# ============================================================
# 字幕处理
# ============================================================


def parse_srt(srt_path: str) -> list[dict]:
    """解析 SRT 字幕文件"""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n\n+", content.strip())
    subtitles = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        time_line = lines[1]
        time_match = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            time_line,
        )
        if not time_match:
            continue

        start_ms = (
            int(time_match.group(1)) * 3600000
            + int(time_match.group(2)) * 60000
            + int(time_match.group(3)) * 1000
            + int(time_match.group(4))
        )
        end_ms = (
            int(time_match.group(5)) * 3600000
            + int(time_match.group(6)) * 60000
            + int(time_match.group(7)) * 1000
            + int(time_match.group(8))
        )

        # 解析文本
        text = "\n".join(lines[2:]).strip()

        subtitles.append(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text,
            }
        )

    return subtitles


def format_timestamp(ms: int) -> str:
    """格式化时间戳"""
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02d}:{minutes % 60:02d}:{seconds % 60:02d}"


def extract_text_from_srt(srt_path: str) -> str:
    """从字幕提取纯文本"""
    subtitles = parse_srt(srt_path)
    texts = []
    current_time = 0

    for sub in subtitles:
        # 添加时间标记（每分钟）
        if sub["start_ms"] - current_time >= 60000:
            texts.append(f"\n[{format_timestamp(sub['start_ms'])}]")
            current_time = sub["start_ms"]
        texts.append(sub["text"])

    return " ".join(texts)


# ============================================================
# 核心观点提取
# ============================================================

INSIGHT_EXTRACTION_PROMPT = """你是播客内容研究员。分析以下视频字幕，提取适合播客讨论的核心内容。

## 字幕内容
{subtitles}

## 要求
1. 识别 3-5 个最值得深入讨论的观点
2. 每个观点标注：
   - type: 论点/数据/案例/争议/方法论
   - confidence: high/medium/low（是否需要验证）
   - needs_research: true/false
   - timestamp: 原文时间戳
3. 过滤掉过于依赖画面的内容
4. 给出视频的一句话总结

## 输出格式（JSON）
{{
  "video_summary": "一句话概括视频主题",
  "core_insights": [
    {{
      "insight": "核心观点描述",
      "type": "论点/数据/案例/争议/方法论",
      "confidence": "high/medium/low",
      "needs_research": true/false,
      "timestamp": "00:05:30",
      "original_text": "原文引用..."
    }}
  ]
}}
"""


def extract_insights(subtitles_text: str, api_key: str) -> dict:
    """使用 LLM 提取核心观点"""
    client = genai.Client(api_key=api_key)

    # 限制长度（避免超出上下文）
    max_chars = 30000
    if len(subtitles_text) > max_chars:
        subtitles_text = subtitles_text[:max_chars] + "\n... (内容已截断)"

    prompt = INSIGHT_EXTRACTION_PROMPT.format(subtitles=subtitles_text)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    # 解析 JSON
    text = response.text or ""
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        return json.loads(json_match.group())
    return {"video_summary": "", "core_insights": []}


# ============================================================
# 播客脚本生成
# ============================================================

SCRIPT_GENERATION_PROMPT = """你是一位资深的播客制作人，擅长创作像 NotebookLM Audio Overview 那样自然、引人入胜的对话式播客。

## 原始素材（字幕原文）
{subtitles}

## 核心观点摘要
{insights}

## 视频主题
{summary}

## 目标时长
{duration} 分钟

---

## 创作指南

### 对话风格（最重要）
你们是两位老朋友在闲聊一个有趣的话题，而不是在做访谈节目。

- **自然互动**：打断对方、追问、表示惊讶、表示怀疑
- **口语化**：用"哎""等下""不是吧""我靠""真的假的"这类口语
- **有化学反应**：一人抛出观点，另一人要有反应——可能质疑、可能补充、可能延伸
- **不要轮流念稿**：避免"问：... 答：..."这种僵硬格式

### 内容来源（优先级）
1. **优先引用原文**：直接引用字幕中的具体内容、数据、故事
2. **原文不够时**：可以说"我记得好像还有..."、"我查了一下..."来补充背景
3. **适度延伸**：可以加入常识性补充，但不要编造核心事实

### 对话节奏
- 开场（20-30秒）：自然引入，像"诶你最近有没有刷到..."
- 主体：深入讨论 2-3 个核心点，每个点要有来回互动
- 收尾（20-30秒）：自然总结，不是念稿

### 说话人标记
- 用 "A:" 和 "B:" 标记（不是主持人/嘉宾）
- A 通常是提出话题的人
- B 通常是追问、补充的人
- 两人角色可以自然切换

---

## 输出格式
直接输出对话脚本，不要有任何说明文字或代码块标记。

示例风格：
A: 诶你最近有没有刷到闲鱼上那个离谱的事？
B: 啥事？
A: 有人把一毛钱硬币卖两千块！
B: 不是吧？谁会买啊？
A: 对吧！我也觉得离谱，但还真有人点"想要"...
"""


TITLE_GENERATION_PROMPT = """你是一位播客运营专家，擅长创作吸引点击的标题。

## 播客脚本
{script}

## 核心观点
{insights}

## 视频主题
{summary}

---

## 任务
为这期播客生成一个合适的标题。

## 标题原则
1. **制造反差**：用数据对比、矛盾现象制造好奇心
2. **具体化**：用具体数字、地点、人物代替泛泛而谈
3. **避免标题党**：内容必须真实，但表达要有冲击力
4. **中文友好**：适合中文播客平台（小宇宙、喜马拉雅等）
5. **15-25字**：简洁有力，不要太长

## 常见套路（选一个最适合的）
- 数据反差式：「月薪1000，满街法拉利」
- 疑问式：「XX真的是YY吗？」
- 反常识式：「首都建在边境上？」
- 故事式：「10万湖南人悄悄占领了XX」
- 画面式：「法拉利和破木屋只隔一条街」

---

## 输出格式（JSON）
{{
  "title": "主标题（15-25字）",
  "subtitle": "副标题（补充说明，10-20字）",
  "description": "一句话简介（20-40字，用于播客平台展示）"
}}

只输出 JSON，不要其他内容。
"""


def generate_title(script: str, insights: dict, api_key: str) -> dict:
    client = genai.Client(api_key=api_key)

    insights_text = "\n".join(
        [f"- {i.get('insight', '')}" for i in insights.get("core_insights", [])[:5]]
    )

    prompt = TITLE_GENERATION_PROMPT.format(
        script=script[:3000],
        insights=insights_text,
        summary=insights.get("video_summary", ""),
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    text = response.text or ""
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        return json.loads(json_match.group())
    return {"title": "", "subtitle": "", "description": ""}


def generate_script(
    subtitles_text: str, insights: dict, duration: int, api_key: str
) -> str:
    client = genai.Client(api_key=api_key)

    # 格式化观点
    insights_text = ""
    for i, insight in enumerate(insights.get("core_insights", []), 1):
        insights_text += f"""
{i}. [{insight.get("type", "论点")}] {insight.get("insight", "")}
   原文引用："{insight.get("original_text", "")}"
"""

    # 截取字幕（避免超出上下文）
    max_subtitle_chars = 20000
    if len(subtitles_text) > max_subtitle_chars:
        subtitles_text = subtitles_text[:max_subtitle_chars] + "\n... (内容已截断)"

    prompt = SCRIPT_GENERATION_PROMPT.format(
        subtitles=subtitles_text,
        insights=insights_text,
        summary=insights.get("video_summary", ""),
        duration=duration,
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    return response.text or ""


# ============================================================
# 语音合成
# ============================================================


def save_wave_file(
    filename: str,
    pcm_data: bytes,
    channels: int = 1,
    rate: int = 24000,
    sample_width: int = 2,
):
    """保存 PCM 数据为 WAV 文件"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)


def synthesize_podcast(
    script: str, output_path: str, api_key: str, speakers: int = 2, title: str = ""
) -> str:
    import base64
    import httpx
    import time

    if title:
        safe_title = title.replace("/", "-").replace("\\", "-")[:80]
        output_dir = Path(output_path).parent
        output_path = str(output_dir / f"{safe_title}.wav")

    speaker_configs = [
        {"speaker": "A", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}},
        {
            "speaker": "B",
            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Charon"}},
        },
    ]

    if speakers >= 3:
        speaker_configs.append(
            {
                "speaker": "C",
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Fenrir"}},
            }
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"

    MAX_CHARS_PER_SEGMENT = 500

    if len(script) > MAX_CHARS_PER_SEGMENT:
        return _synthesize_in_segments(
            script, output_path, api_key, speaker_configs, MAX_CHARS_PER_SEGMENT
        )

    data = {
        "contents": [{"parts": [{"text": script}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "multiSpeakerVoiceConfig": {"speakerVoiceConfigs": speaker_configs}
            },
        },
    }

    print("正在生成播客音频...")

    with httpx.Client(proxy=None, timeout=180) as client:
        response = client.post(url, json=data)
        response.raise_for_status()
        result = response.json()

    audio_data = base64.b64decode(
        result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    )

    save_wave_file(output_path, audio_data)

    print(f"✅ 播客已生成: {output_path}")
    print(f"   文件大小: {len(audio_data) / 1024:.1f} KB")

    return output_path


def _synthesize_in_segments(
    script: str, output_path: str, api_key: str, speaker_configs: list, max_chars: int
) -> str:
    import base64
    import httpx
    import time

    raw_segments = [s for s in script.strip().split("\n\n") if s.strip()]

    if len(raw_segments) <= 1:
        raw_segments = [s.strip() for s in script.strip().split("\n") if s.strip()]

    merged_segments = []
    current_batch = []
    current_length = 0
    TARGET_CHARS = 150
    MAX_CHARS = 200

    for seg in raw_segments:
        seg_len = len(seg)

        if current_length + seg_len + 2 > MAX_CHARS and current_batch:
            merged_segments.append("\n\n".join(current_batch))
            current_batch = [seg]
            current_length = seg_len
        else:
            current_batch.append(seg)
            current_length += seg_len + 2

            if current_length >= TARGET_CHARS:
                merged_segments.append("\n\n".join(current_batch))
                current_batch = []
                current_length = 0

    if current_batch:
        merged_segments.append("\n\n".join(current_batch))

    print(f"脚本较长 ({len(script)} 字符)，合并为 {len(merged_segments)} 段生成...")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"

    all_audio = []

    for i, segment in enumerate(merged_segments):
        if not segment.strip():
            continue

        data = {
            "contents": [{"parts": [{"text": segment}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "multiSpeakerVoiceConfig": {"speakerVoiceConfigs": speaker_configs}
                },
            },
        }

        print(
            f"  [{i + 1}/{len(merged_segments)}] {len(segment)} 字符...",
            end=" ",
            flush=True,
        )

        audio_data = None
        for attempt in range(3):
            try:
                with httpx.Client(proxy=None, timeout=90) as client:
                    response = client.post(url, json=data)
                    if response.status_code == 200:
                        result = response.json()
                        if "candidates" in result and result["candidates"]:
                            audio_data = base64.b64decode(
                                result["candidates"][0]["content"]["parts"][0][
                                    "inlineData"
                                ]["data"]
                            )
                            print(f"✓ ({len(audio_data) / 1024:.0f} KB)")
                            break
                        else:
                            print(
                                "✗ 无数据" if attempt == 2 else "重试...",
                                end=" " if attempt < 2 else "\n",
                            )
                    else:
                        print(
                            f"✗ HTTP {response.status_code}"
                            if attempt == 2
                            else "重试...",
                            end=" " if attempt < 2 else "\n",
                        )
            except Exception as e:
                print(
                    f"✗ {e}" if attempt == 2 else "重试...",
                    end=" " if attempt < 2 else "\n",
                )

            if attempt < 2:
                time.sleep(2)

        if audio_data:
            all_audio.append(audio_data)

        time.sleep(0.5)

    if all_audio:
        combined = b"".join(all_audio)
        save_wave_file(output_path, combined)

        duration = len(combined) / 24000 / 2
        print(f"\n✅ 播客已生成: {output_path}")
        print(f"   成功: {len(all_audio)}/{len(merged_segments)} 段")
        print(f"   大小: {len(combined) / 1024 / 1024:.2f} MB")
        print(f"   时长: ~{duration / 60:.1f} 分钟")

    return output_path


# ============================================================
# 主流程
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="从视频字幕生成播客")
    parser.add_argument("--url", help="视频 URL")
    parser.add_argument("--srt", help="字幕文件路径")
    parser.add_argument("--script", help="已有脚本路径（跳过生成直接合成）")
    parser.add_argument("--output", default="podcast.wav", help="输出文件路径")
    parser.add_argument(
        "--duration", type=int, default=DEFAULT_DURATION, help="目标时长（分钟）"
    )
    parser.add_argument("--script-only", action="store_true", help="仅生成脚本")
    parser.add_argument("--no-research", action="store_true", help="跳过网络研究")
    parser.add_argument("--speakers", type=int, default=2, help="说话人数量")

    args = parser.parse_args()

    # 检查 API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("错误: 请设置 GEMINI_API_KEY 环境变量")
        print("  或在 .opencode/skills/video-to-podcast/assets/.env 中配置")
        sys.exit(1)

    # 工作目录
    work_dir = Path(args.output).parent
    work_dir.mkdir(parents=True, exist_ok=True)

    script_content = None

    # 1. 如果已有脚本，直接读取
    if args.script:
        with open(args.script, "r", encoding="utf-8") as f:
            script_content = f.read()
        print(f"已加载脚本: {args.script}")

        script_dir = Path(args.script).parent
        meta_path = script_dir / "podcast_meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {"title": "", "subtitle": "", "description": ""}

    # 2. 如果有字幕，提取观点并生成脚本
    elif args.srt:
        print(f"正在解析字幕: {args.srt}")
        subtitles_text = extract_text_from_srt(args.srt)

        print("正在提取核心观点...")
        insights = extract_insights(subtitles_text, api_key)

        # 保存观点
        insights_path = work_dir / "insights.json"
        with open(insights_path, "w", encoding="utf-8") as f:
            json.dump(insights, f, ensure_ascii=False, indent=2)
        print(f"✅ 观点已保存: {insights_path}")

        print("正在生成播客脚本...")
        script_content = generate_script(
            subtitles_text, insights, args.duration, api_key
        )

        # 保存脚本
        script_path = work_dir / "podcast_script.txt"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        print(f"✅ 脚本已保存: {script_path}")

        print("正在生成播客标题...")
        title_info = generate_title(script_content, insights, api_key)

        meta = {
            "title": title_info.get("title", ""),
            "subtitle": title_info.get("subtitle", ""),
            "description": title_info.get("description", ""),
            "duration_minutes": args.duration,
            "source": args.srt or args.url or "",
        }

        meta_path = work_dir / "podcast_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"✅ 标题: {meta['title']}")
        if meta["subtitle"]:
            print(f"   副标题: {meta['subtitle']}")

    # 3. 如果有 URL，需要先下载字幕
    elif args.url:
        print("请先使用 yt-dlp 下载字幕:")
        print(
            f'  yt-dlp --write-subs --sub-langs "zh-Hans,en" --skip-download "{args.url}"'
        )
        sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)

    # 4. 如果仅生成脚本，到此结束
    if args.script_only:
        print("✅ 脚本生成完成")
        return

    # 5. 合成音频
    if script_content:
        title_for_output = meta.get("title", "") if "meta" in dir() else ""
        final_output = synthesize_podcast(
            script_content, args.output, api_key, args.speakers, title_for_output
        )
        if title_for_output and final_output != args.output:
            print(f"   文件名: {Path(final_output).name}")


if __name__ == "__main__":
    main()
