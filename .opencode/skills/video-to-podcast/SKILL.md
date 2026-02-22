---
name: video-to-podcast
description: 从视频字幕提取核心观点，结合网络深度研究，生成多人对话式语音播客。触发词：视频转播客、生成播客、字幕转语音、AI播客、podcast generator、video podcast。当用户需要把视频内容转化为播客节目时使用此技能。
---

# Video to Podcast

从视频内容到多人对话播客的完整工作流。

## 完整工作流

```
1. 下载视频 & 提取字幕 (复用 video-highlight-clipper)
   ├─ 有字幕 → 直接下载
   └─ 无字幕 → Whisper 转录
   
2. 分析字幕，提取核心观点
   ├─ 识别关键论点
   ├─ 提取数据与案例
   └─ 标注争议点/深度点
   
3. 深度研究（网络搜索）
   ├─ 补充背景信息
   ├─ 验证数据准确性
   ├─ 查找相关案例
   └─ 收集不同观点
   
4. 生成播客脚本
   ├─ 多人对话结构
   ├─ 主持人 + 嘉宾人设
   └─ 口语化表达
   
5. 语音合成 (Gemini TTS)
   ├─ 多音色配音
   └─ 输出 WAV/MP3
```

## 依赖安装

```bash
# 必需依赖
brew install yt-dlp ffmpeg

# Python 依赖
pip install google-genai python-dotenv

# 可选：Whisper（无字幕视频需要）
brew install whisper-cpp
```

## API 配置

在 `.opencode/skills/video-to-podcast/assets/.env` 中配置：

```bash
GEMINI_API_KEY=your-api-key
```

获取 API Key: https://aistudio.google.com/apikey

---

## Step 1: 下载视频 & 提取字幕

复用 `video-highlight-clipper` 技能的能力。

### 1.1 下载字幕

```bash
# 推荐命令
yt-dlp --write-subs --write-auto-subs \
  --sub-langs "zh-Hans,zh-CN,zh.*,en.*,ja.*" \
  --sub-format "srt/best" --convert-subs srt \
  --skip-download \
  -o "%(id)s.%(ext)s" \
  "URL"
```

### 1.2 无字幕处理

```bash
# 先下载视频
yt-dlp --cookies-from-browser chrome -f "best[ext=mp4]" -o "%(id)s.%(ext)s" "URL"

# 提取音频
ffmpeg -y -i "VIDEO_ID.mp4" -vn -acodec pcm_s16le -ar 16000 -ac 1 "VIDEO_ID_audio.wav"

# Whisper 转录
whisper-cli -m ~/.cache/whisper/ggml-base.bin -l zh -osrt -of VIDEO_ID -t 8 VIDEO_ID_audio.wav
```

---

## Step 2: 提取核心观点

### 2.1 观点提取维度

从字幕中识别以下类型的内容：

| 类型 | 识别信号 | 优先级 |
|------|----------|--------|
| **核心论点** | "我认为/核心是/关键在于/结论是" | ⭐⭐⭐ |
| **反常识观点** | 与常识相反、颠覆认知 | ⭐⭐⭐ |
| **数据支撑** | 具体数字、百分比、排名 | ⭐⭐⭐ |
| **案例故事** | "比如/举个例子/我曾经" | ⭐⭐ |
| **争议话题** | "有人说/但我不这么认为/这很复杂" | ⭐⭐ |
| **方法论** | "步骤是/方法是/流程如下" | ⭐⭐ |
| **金句** | 简洁有力、可独立传播 | ⭐ |

### 2.2 输出结构

```yaml
video_summary: "一句话概括视频主题"
core_insights:
  - insight: "核心观点描述"
    type: "论点/数据/案例/争议/方法论"
    confidence: "high/medium/low"  # 是否需要验证
    needs_research: true/false     # 是否需要补充研究
    timestamp: "00:05:30"
    original_text: "原文引用..."
```

### 2.3 提取提示词

```markdown
你是播客内容研究员。分析以下视频字幕，提取适合播客讨论的核心内容。

要求：
1. 识别 3-5 个最值得深入讨论的观点
2. 标注每个观点的类型（论点/数据/案例/争议/方法论）
3. 标注是否需要网络验证或补充研究
4. 保留时间戳，方便后续定位
5. 过滤掉过于依赖画面的内容（无法仅通过音频理解）

输出 JSON 格式。
```

---

## Step 3: 深度研究

### 3.1 研究触发条件

| 条件 | 行动 |
|------|------|
| 视频中有具体数据 | 验证数据准确性，补充最新数据 |
| 提到人名/公司名 | 查找背景信息 |
| 有争议性观点 | 收集正反两方观点 |
| 涉及历史事件 | 补充时间线背景 |
| 提到研究报告 | 查找原始来源 |
| 涉及行业趋势 | 搜索最新动态 |

### 3.2 研究工具

使用 **librarian agent** 进行网络研究：

```
[CONTEXT]: 正在为播客节目收集背景资料，视频主题是 {topic}
[GOAL]: 补充深度信息，让播客内容更丰富可信
[DOWNSTREAM]: 将研究结果融入播客脚本
[REQUEST]: 
1. 验证视频中的关键数据是否准确
2. 补充相关案例和背景故事
3. 收集不同立场观点（如有争议）
4. 查找最新的相关动态
返回结构化摘要，标注来源
```

### 3.3 研究输出格式

```markdown
## 研究摘要：{主题}

### 数据验证
- ✅ 原数据正确：{内容}
- ⚠️ 需更新：{原内容} → {新内容}
- ❌ 无法验证：{内容}

### 补充案例
1. {案例1}（来源）
2. {案例2}（来源）

### 多方观点
- 观点A: {内容}
- 观点B: {内容}

### 最新动态
- {日期}：{事件}

### 可用金句
- "{引用}" — {出处}
```

---

## Step 4: 生成播客脚本

### 4.1 播客角色设计

**推荐 2-3 人配置**：

| 角色 | 定位 | 语气特点 | Gemini 音色 |
|------|------|----------|-------------|
| 主持人 | 引导话题、总结升华 | 亲切、好奇、中立 | Kore (男) |
| 嘉宾A | 专业解读、深度分析 | 专业、有见地 | Charon (女) |
| 嘉宾B | 提出质疑、平衡观点 | 批判、挑战 | Fenrir (男) |

### 4.2 脚本结构模板

```
【开场】(30-60秒)
- 主持人：问候 + 话题引入 + 嘉宾介绍
- 钩子：为什么这个话题重要/有趣

【主体】(按观点分段，每段 2-4 分钟)
┌─────────────────────────────────────┐
│ 观点 1                              │
│ 主持人：引入话题/抛出问题            │
│ 嘉宾A：核心观点 + 数据/案例支撑      │
│ 嘉宾B：补充/质疑/延伸                │
│ 主持人：总结过渡                     │
└─────────────────────────────────────┘

【收尾】(30-60秒)
- 主持人：总结核心洞察
- 嘉宾：各自一句话收尾
- 主持人：下期预告 + CTA
```

### 4.3 脚本生成提示词（NotebookLM 风格）

```markdown
你是一位资深的播客制作人，擅长创作像 NotebookLM Audio Overview 那样自然、引人入胜的对话式播客。

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
```

### 4.4 脚本质量检查

- [ ] 对话自然，像朋友聊天
- [ ] 有追问、质疑、补充等互动
- [ ] 优先引用原文内容和数据
- [ ] 口语化表达，避免书面语
- [ ] 用 A/B 标记说话人
- [ ] 时长合理（中文约 180-200 字/分钟）

---

## Step 5: 语音合成

### 5.1 使用 Gemini TTS

```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY")

speech_config = types.SpeechConfig(
    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
        speaker_voice_configs=[
            types.SpeakerVoiceConfig(
                speaker="A",  # 说话人 A
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"  # 男声
                    )
                ),
            ),
            types.SpeakerVoiceConfig(
                speaker="B",  # 说话人 B
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"  # 女声
                    )
                ),
            ),
        ]
    )
)

response = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=script,
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=speech_config
    )
)
```

### 5.2 可用音色

| 音色 | 性别 | 特点 |
|------|------|------|
| Kore | 男 | 稳重自然 |
| Charon | 女 | 自然亲切 |
| Fenrir | 男 | 深沉有力 |
| Aoede | 女 | 明亮活泼 |
| Leda | 女 | 温柔柔和 |
| Orus | 男 | 活力年轻 |

**推荐组合**：Kore + Charon（一男一女，最自然）

### 5.3 音频后处理

```bash
# 转换为 MP3（更小的文件体积）
ffmpeg -i podcast.wav -codec:a libmp3lame -qscale:a 2 podcast.mp3

# 调整音量（播客标准 -16 LUFS）
ffmpeg -i podcast.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11" podcast_normalized.wav

# 添加片头片尾（可选）
ffmpeg -i intro.mp3 -i podcast.wav -i outro.mp3 \
  -filter_complex "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]" \
  -map "[out]" podcast_final.mp3
```

---

## 完整示例

### 输入
```
视频：https://www.youtube.com/watch?v=xxx
主题：AI 对就业市场的影响
时长目标：8-10 分钟
```

### 执行流程

```bash
# 1. 下载字幕
yt-dlp --write-subs --sub-langs "zh-Hans,en" --skip-download "URL"

# 2. 提取观点（AI 分析）
# 输出：3-5 个核心观点 + 研究需求

# 3. 深度研究（网络搜索）
# 验证数据、补充案例、收集观点

# 4. 生成脚本
# 输出：主持人 + 嘉宾对话脚本

# 5. 语音合成
python scripts/generate_podcast.py --script podcast_script.txt --output podcast.wav
```

### 输出

```
📁 output/
├── VIDEO_ID.srt           # 原始字幕
├── insights.json          # 提取的观点
├── research.md            # 研究结果
├── podcast_script.txt     # 播客脚本
└── podcast.wav            # 最终音频 (2-3 MB/分钟)
```

---

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 脚本太书面 | 提示词不够强调口语化 | 加入"避免书面语"的负面示例 |
| 内容太空泛 | 缺乏具体案例 | 增加网络研究环节 |
| 语音机械 | 脚本缺乏停顿标记 | 加入 [停顿][强调] 标记 |
| 音色太像 | 使用了相同音色 | 为不同角色配置不同 voice_name |
| 时长超出预期 | 语速估算不准 | 中文约 180-200 字/分钟 |
| API 报错 | Key 无效或配额不足 | 检查 .env 配置 |

---

## 工具脚本

### generate_podcast.py

```bash
# 完整流程
python scripts/generate_podcast.py --url "https://youtube.com/..." --output podcast.wav

# 仅生成脚本（不合成语音）
python scripts/generate_podcast.py --url "..." --script-only

# 使用现有字幕
python scripts/generate_podcast.py --srt video.srt --output podcast.wav

# 指定时长
python scripts/generate_podcast.py --url "..." --duration 10 --output podcast.wav
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--url` | 视频 URL | 必填（或 --srt） |
| `--srt` | 字幕文件路径 | - |
| `--output` | 输出音频路径 | podcast.wav |
| `--duration` | 目标时长（分钟） | 8 |
| `--script-only` | 仅生成脚本 | false |
| `--no-research` | 跳过网络研究 | false |
| `--speakers` | 说话人数量 | 2 |
