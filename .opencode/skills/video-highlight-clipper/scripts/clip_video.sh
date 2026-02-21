#!/bin/bash
# 视频切片脚本 - 根据时间戳从视频中提取片段
# 用法: ./clip_video.sh "视频文件路径" "开始时间" "结束时间" "输出文件名"
# 示例: ./clip_video.sh "video.webm" "00:04:37" "00:05:13" "01_精彩片段"

set -e

# 检查参数
if [ $# -lt 4 ]; then
    echo "用法: $0 <视频文件> <开始时间> <结束时间> <输出文件名>"
    echo "示例: $0 \"video.webm\" \"00:04:37\" \"00:05:13\" \"01_精彩片段\""
    exit 1
fi

VIDEO="$1"
START="$2"
END="$3"
OUTPUT="$4"

# 检查文件是否存在
if [ ! -f "$VIDEO" ]; then
    echo "错误: 文件不存在: $VIDEO"
    exit 1
fi

# 创建输出目录
mkdir -p video_clips

# 获取文件扩展名
EXT="${VIDEO##*.}"

# 执行切片
echo "切片中: $START -> $END"
ffmpeg -y -ss "$START" -to "$END" -i "$VIDEO" -c copy "video_clips/${OUTPUT}.mp4" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 切片完成: video_clips/${OUTPUT}.mp4"
else
    echo "❌ 切片失败"
    exit 1
fi
