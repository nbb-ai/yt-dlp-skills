# Video Highlight Clipper

OpenCode 技能：从 YouTube/Bilibili 等平台下载视频、提取字幕、分析精彩片段并自动切片。

## 功能

- 📥 下载视频（支持 cookies 绕过 403）
- 📝 提取字幕（支持中/英/日等多语言）
- 🎯 智能分析精彩片段（四维度评分：内容/结构/情感/传播）
- ✂️ 视频切片（Fast/Accurate 双模式）
- 📄 生成精彩片段摘录文档

## 依赖

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载
- [ffmpeg](https://ffmpeg.org/) - 视频处理

```bash
# macOS
brew install yt-dlp ffmpeg

# 其他平台请参考官方文档
```

## 安装

将 `.opencode` 目录放置在你的项目根目录，或复制到 `~/.opencode/skills/`。

## 使用

在 OpenCode 中触发：

```
帮我下载这个视频并提取精彩片段：https://www.youtube.com/watch?v=xxx
```

## 工作流

```
1. 下载视频 (yt-dlp)
2. 下载字幕 (yt-dlp --write-subs)
3. 分析字幕内容，识别精彩片段
4. 根据时间戳切片视频 (ffmpeg)
5. 生成精彩片段摘录文档
```

## 目录结构

```
.opencode/skills/video-highlight-clipper/
├── SKILL.md              # 技能主文档
├── scripts/
│   └── clip_video.sh     # 视频切片脚本
└── assets/
    └── highlight_template.md  # 摘录文档模板
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| HTTP 403 | `--cookies-from-browser chrome` |
| 切片时间不准 | 使用 Accurate 模式（`-ss` 放 `-i` 后） |
| 无字幕 | 人工标注或使用语音识别工具 |

详见 [SKILL.md](.opencode/skills/video-highlight-clipper/SKILL.md)。

## License

MIT
