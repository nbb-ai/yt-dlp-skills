"""
Gemini TTS 多人播客 Demo
测试 Gemini 2.5 的多说话人语音合成能力

依赖安装:
pip install -r requirements.txt

API Key 从 .env 文件读取
"""

import os
import wave
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 加载 .env 文件
load_dotenv(Path(__file__).parent / ".env")


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


def generate_multi_speaker_podcast():
    """生成多人播客音频"""

    # 初始化客户端
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("请设置 GEMINI_API_KEY 环境变量")

    client = genai.Client(api_key=api_key)

    # 多人对话脚本
    # 使用 Speaker 名称标记每个说话人
    script = """
    主持人: 大家好，欢迎收听今天的科技快报节目！我是主持人若木。
    
    嘉宾: 大家好，我是今天的技术嘉宾小红，很高兴来到节目。
    
    主持人: 今天我们要聊聊最近很火的 AI 语音技术。小红，你能给大家介绍一下吗？
    
    嘉宾: 当然可以！最近 Google 推出的 Gemini 2.5 模型，支持多说话人语音合成了。这意味着我们可以用一个 API，就生成像我们现在这样自然的对话。
    
    主持人: 听起来很厉害啊！那它和传统的文字转语音有什么区别呢？
    
    嘉宾: 最大的区别是可控性。你可以用自然语言来控制语气、语速，甚至情绪。而且多人对话时，每个角色都有独立的声音，听起来更真实。
    
    主持人: 这对播客制作来说太方便了！感谢小红的分享。
    
    嘉宾: 谢谢邀请，期待下次再来！
    
    主持人: 好的，今天的节目就到这里，我们下期再见！
    """

    # 配置多说话人语音
    speech_config = types.SpeechConfig(
        multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=[
                types.SpeakerVoiceConfig(
                    speaker="主持人",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore"  # 男声
                        )
                    ),
                ),
                types.SpeakerVoiceConfig(
                    speaker="嘉宾",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Charon"  # 女声
                        )
                    ),
                ),
            ]
        )
    )

    print("正在生成多人播客音频...")

    # 调用 API
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=script,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"], speech_config=speech_config
        ),
    )

    # 提取音频数据
    # 响应中包含 inline_data，里面有音频的 PCM 数据
    audio_data = response.candidates[0].content.parts[0].inline_data.data

    # 保存为 WAV 文件
    output_file = "podcast_multi_speaker.wav"
    save_wave_file(output_file, audio_data)

    print(f"✅ 播客已生成: {output_file}")
    print(f"   文件大小: {len(audio_data) / 1024:.1f} KB")

    return output_file


def generate_single_speaker():
    """生成单人语音（作为对比）"""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("请设置 GEMINI_API_KEY 环境变量")

    client = genai.Client(api_key=api_key)

    text = """
    大家好，欢迎收听今天的科技快报节目！
    今天我们要聊聊最近很火的 AI 语音技术。
    Google 推出的 Gemini 2.5 模型，现在已经支持多说话人语音合成了。
    这对播客制作来说太方便了！
    """

    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
        )
    )

    print("正在生成单人语音...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"], speech_config=speech_config
        ),
    )

    audio_data = response.candidates[0].content.parts[0].inline_data.data

    output_file = "podcast_single_speaker.wav"
    save_wave_file(output_file, audio_data)

    print(f"✅ 单人语音已生成: {output_file}")
    print(f"   文件大小: {len(audio_data) / 1024:.1f} KB")

    return output_file


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("Gemini TTS 多人播客 Demo")
    print("=" * 50)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "single":
        generate_single_speaker()
    else:
        generate_multi_speaker_podcast()

    print()
    print("播放生成的音频:")
    print("  macOS: afplay podcast_multi_speaker.wav")
    print("  Linux: aplay podcast_multi_speaker.wav")
