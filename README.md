# Video Skills

OpenCode 技能集合：从 YouTube/Bilibili 等平台下载视频、提取字幕、生成播客。

## 技能列表

| 技能 | 功能 |
|------|------|
| **video-highlight-clipper** | 下载视频、提取字幕、分析精彩片段并自动切片 |
| **video-to-podcast** | 从视频字幕生成多人对话播客（NotebookLM 风格） |

---

## 依赖安装

```bash
# 必需
brew install yt-dlp ffmpeg

# Python 依赖
pip install google-genai python-dotenv

# 可选：Whisper（无字幕视频需要）
brew install whisper-cpp
```

---

## Video to Podcast

从视频内容到多人对话播客的完整工作流。

### 快速开始

```bash
# 从字幕生成播客（脚本 + 标题 + 音频）
python .opencode/skills/video-to-podcast/scripts/generate_podcast.py \
  --srt video.srt --output output/podcast.wav

# 仅生成脚本（不合成语音）
python .opencode/skills/video-to-podcast/scripts/generate_podcast.py \
  --srt video.srt --output output/podcast.wav --script-only

# 从已有脚本生成音频
python .opencode/skills/video-to-podcast/scripts/generate_podcast.py \
  --script output/podcast_script.txt --output output/podcast.wav
```

### 工作流

```
1. 下载视频 & 提取字幕
   ├─ 有字幕 → yt-dlp 直接下载
   └─ 无字幕 → Whisper 转录
   
2. 分析字幕，提取核心观点
   ├─ 识别关键论点、数据、案例
   └─ 标注是否需要补充研究
   
3. 生成播客脚本
   ├─ NotebookLM 风格对话
   ├─ 口语化、自然互动
   └─ 自动生成标题
   
4. 语音合成 (Gemini TTS)
   ├─ 多音色配音（Kore + Charon）
   └─ 智能分段，避免超时
```

### 输出示例

```
output/
├── 上海小姐姐月开销大公开：房租算啥？衣服才是"生产资料"！.wav  # 播客音频
├── podcast_meta.json      # 标题和元信息
├── podcast_script.txt     # 对话脚本
└── insights.json          # 核心观点
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--srt` | 字幕文件路径 | - |
| `--script` | 已有脚本路径 | - |
| `--output` | 输出路径 | podcast.wav |
| `--duration` | 目标时长（分钟） | 8 |
| `--script-only` | 仅生成脚本 | false |
| `--speakers` | 说话人数量 | 2 |

### API 配置

在 `.opencode/skills/video-to-podcast/assets/.env` 中配置：

```bash
GEMINI_API_KEY=your-api-key
```

获取 API Key: https://aistudio.google.com/apikey

---

## Video Highlight Clipper

从视频提取精彩片段并自动切片。

### 快速开始

```bash
# 下载字幕
yt-dlp --write-subs --write-auto-subs \
  --sub-langs "zh-Hans,zh-CN,zh.*,en.*" \
  --sub-format "srt/best" --convert-subs srt \
  --skip-download \
  -o "%(id)s.%(ext)s" \
  "URL"

# 无字幕视频：Whisper 转录
yt-dlp --cookies-from-browser chrome -f "bestaudio" -o "%(id)s.%(ext)s" "URL"
ffmpeg -y -i "VIDEO_ID.webm" -vn -acodec pcm_s16le -ar 16000 -ac 1 "VIDEO_ID_audio.wav"
whisper-cli -m ~/.cache/whisper/ggml-base.bin -l zh -osrt -of VIDEO_ID -t 8 VIDEO_ID_audio.wav
```

### 工作流

```
1. 下载视频 (yt-dlp)
2. 下载字幕 (yt-dlp --write-subs)
3. 分析字幕内容，识别精彩片段
4. 根据时间戳切片视频 (ffmpeg)
5. 生成精彩片段摘录文档
```

---

## 目录结构

```
.opencode/skills/
├── video-highlight-clipper/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── clip_video.sh
│   └── assets/
│       └── highlight_template.md
│
└── video-to-podcast/
    ├── SKILL.md
    ├── scripts/
    │   └── generate_podcast.py
    └── assets/
        └── .env
```

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| HTTP 403 | `--cookies-from-browser chrome` |
| 无字幕 | 使用 Whisper 转录 |
| TTS 超时 | 脚本已自动分段（150-200 字符/段） |
| API 报错 | 检查 `.env` 中的 `GEMINI_API_KEY` |
| 代理问题 | 脚本已内置 `proxy=None` 绕过系统代理 |

---

## License

MIT
