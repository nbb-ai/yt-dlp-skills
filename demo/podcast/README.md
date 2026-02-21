# Gemini TTS 多人播客 Demo

测试 Google Gemini 2.5 的多说话人语音合成能力。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 设置 API Key

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

获取 API Key: https://aistudio.google.com/apikey

### 3. 运行 Demo

```bash
# 生成多人播客
python gemini_tts_demo.py

# 生成单人语音（对比测试）
python gemini_tts_demo.py single
```

### 4. 播放音频

```bash
# macOS
afplay podcast_multi_speaker.wav

# Linux
aplay podcast_multi_speaker.wav
```

## 支持的音色

Gemini TTS 提供多种预置音色，常用：

| Voice Name | 特点 |
|------------|------|
| Kore | 男声，稳定 |
| Charon | 女声，自然 |
| Fenrir | 男声，深沉 |
| Aoede | 女声，明亮 |

完整列表见: https://ai.google.dev/gemini-api/docs/speech-generation

## 注意事项

- 模型 `gemini-2.5-flash-preview-tts` 需要 Gemini API 访问权限
- 中国大陆可能需要代理
- 音频输出为 WAV 格式 (24000Hz, 16bit, 单声道)
