---
name: video-highlight-clipper
description: 从 YouTube/Bilibili 等平台下载视频、提取字幕、分析精彩片段并自动切片。支持 Whisper 语音转录（无字幕视频）。触发词：下载视频、视频切片、提取字幕、yt-dlp、精彩片段、视频剪辑、subtitles、video clips、highlight extraction、whisper、语音转录。当用户需要下载在线视频、获取字幕、从长视频中提取精彩片段、或处理无字幕视频时使用此技能。
---

# Video Highlight Clipper

从在线视频下载到精彩片段切片的一站式工作流。

## 完整工作流

```
1. 下载视频 (yt-dlp)
2. 下载字幕 (yt-dlp --write-subs)
   └─ 无字幕时 → Whisper 语音转录
3. 分析字幕内容，识别精彩片段
4. 根据时间戳切片视频 (ffmpeg)
5. 生成精彩片段摘录文档
```

## 依赖安装

```bash
# 必需依赖
brew install yt-dlp ffmpeg

# 可选：Whisper 语音识别（无字幕视频需要）
brew install whisper-cpp

# 下载 Whisper 模型（首次使用）
mkdir -p ~/.cache/whisper
curl -L -o ~/.cache/whisper/ggml-base.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
```

## Step 1: 下载视频

### 1.1 推荐默认命令

```bash
# 推荐命令（覆盖大多数场景）
yt-dlp --cookies-from-browser chrome \
  --no-playlist \
  --merge-output-format mp4 \
  -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" \
  -o "%(id)s.%(ext)s" \
  "URL"
```

**参数说明**：
- `--no-playlist`：避免误下载整个播放列表
- `--merge-output-format mp4`：音视频合并为 MP4（需 ffmpeg）
- `-o "%(id)s.%(ext)s"`：用视频 ID 命名，避免文件名混乱
- `-f "..."`：格式选择器，优先 MP4，兼容回退

### 1.2 常用变体

```bash
# 基础下载（可能遇到 403 错误）
yt-dlp "https://www.youtube.com/watch?v=VIDEO_ID"

# 使用浏览器 cookies 绕过 403（推荐）
yt-dlp --cookies-from-browser chrome "URL"
yt-dlp --cookies-from-browser safari "URL"

# 指定分辨率下载
yt-dlp --cookies-from-browser chrome -f "bestvideo[height<=1080]+bestaudio" "URL"

# 仅下载最佳 MP4 格式
yt-dlp --cookies-from-browser chrome -f "best[ext=mp4]" "URL"

# 国内网络（需要代理）
yt-dlp --cookies-from-browser chrome --proxy socks5://127.0.0.1:1080 "URL"
```

### 1.3 常见失败处理

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `HTTP 403 Forbidden` | 需要登录/地区限制 | `--cookies-from-browser chrome` |
| `Requested format is not available` | 格式选择器不匹配 | 改用 `-f "best"` 或检查可用格式：`-F` |
| `HTTP 429 Too Many Requests` | 下载频繁被限流 | 等待几分钟后重试，或 `--sleep-requests 5` |
| `ffmpeg not found` | 未安装 ffmpeg | `brew install ffmpeg` (macOS) |
| `Could not extract cookies` | 浏览器 cookies 读取失败 | 确保浏览器已关闭，或手动导出 cookies 文件 |
| `No such file or directory` | 路径问题 | URL 用**双引号**包裹（Zsh 中 `?` 是通配符） |

### 1.4 预检查流程

```bash
# 1. 检查可用格式（先不下载）
yt-dlp -F "URL"

# 2. 获取视频信息
yt-dlp --print "title: %(title)s\nduration: %(duration)s" "URL"

# 3. 确认 ffmpeg 已安装
ffmpeg -version
```

## Step 2: 提取字幕

### 2.1 推荐默认命令

```bash
# 推荐命令（优先人工字幕，回退自动字幕，转为 SRT）
yt-dlp --write-subs --write-auto-subs \
  --sub-langs "zh-Hans,zh-CN,zh.*,en.*,ja.*" \
  --sub-format "srt/best" --convert-subs srt \
  --skip-download \
  -o "%(id)s.%(ext)s" \
  "URL"
```

**参数说明**：
- `--write-subs`：下载人工上传字幕（优先）
- `--write-auto-subs`：人工字幕不存在时下载自动生成字幕（回退）
- `--sub-langs "zh-Hans,zh-CN,zh.*,en.*"`：语言优先级链，支持回退
- `--sub-format "srt/best"`：优先 SRT，平台只给 VTT 时自动选最佳
- `--convert-subs srt`：强制转换为 SRT 格式

### 2.2 常用变体

```bash
# 列出可用字幕
yt-dlp --list-subs "URL"

# 仅下载指定语言字幕
yt-dlp --write-subs --sub-langs zh-Hans --skip-download --sub-format srt "URL"

# 仅下载自动生成的字幕
yt-dlp --write-auto-subs --sub-langs zh-Hans --skip-download --sub-format srt "URL"

# 下载所有字幕
yt-dlp --write-subs --write-auto-subs --sub-langs all --skip-download "URL"
```

### 2.3 常用语言代码

| 代码 | 语言 | 备注 |
|------|------|------|
| `zh-Hans` | 简体中文 | 优先使用 |
| `zh-CN` | 简体中文（中国） | 部分平台使用 |
| `zh.*` | 中文（通配） | 回退选项 |
| `zh-Hant` | 繁体中文 | |
| `en` | 英文 | |
| `en.*` | 英文（通配） | 回退选项 |
| `ja` | 日文 | |

### 2.4 无字幕边界处理

```bash
# 先检查是否有字幕
yt-dlp --list-subs "URL" 2>&1 | grep -q "has no subtitles" && echo "无字幕" || echo "有字幕"
```

**无字幕时的处理策略**：

| 策略 | 适用场景 | 说明 |
|------|----------|------|
| **Whisper 转录** | 推荐 | 自动语音识别，生成 SRT 字幕 |
| **人工标注** | 短视频/特殊需求 | 手动观看记录时间点 |
| **退出提示** | 无法处理 | 告知用户无法自动分析 |

---

## Step 2.5: Whisper 语音转录（无字幕视频）

当视频没有字幕时，使用 Whisper 进行语音识别转录。

### 2.5.1 安装 Whisper.cpp

```bash
# macOS
brew install whisper-cpp

# 验证安装
which whisper-cli && echo "Whisper 已安装"
```

### 2.5.2 下载模型

```bash
# 创建模型目录
mkdir -p ~/.cache/whisper

# 下载 base 模型（推荐，平衡速度和质量，142MB）
curl -L -o ~/.cache/whisper/ggml-base.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"

# 可选：下载其他模型
# tiny   - 最快，质量较低 (75MB)
# small  - 较快，质量中等 (466MB)
# medium - 较慢，质量较好 (1.5GB)
# large  - 最慢，质量最好 (2.9GB)
```

**模型选择建议**：

| 模型 | 大小 | 速度 | 质量 | 适用场景 |
|------|------|------|------|----------|
| `tiny` | 75MB | 最快 | 较低 | 快速预览、实时转录 |
| `base` | 142MB | 快 | 良好 | **推荐**，大多数场景 |
| `small` | 466MB | 中等 | 很好 | 需要更高质量的转录 |
| `medium` | 1.5GB | 慢 | 优秀 | 专业场景、口音复杂 |

### 2.5.3 提取音频

```bash
# 从视频提取音频（Whisper 要求 16kHz 单声道 WAV）
ffmpeg -y -i "VIDEO_ID.mp4" \
  -vn -acodec pcm_s16le -ar 16000 -ac 1 \
  "VIDEO_ID_audio.wav"
```

### 2.5.4 转录命令

```bash
# 基础转录（中文）
whisper-cli \
  -m ~/.cache/whisper/ggml-base.bin \
  -l zh \
  -osrt \
  -of VIDEO_ID \
  -t 8 \
  --split-on-word \
  VIDEO_ID_audio.wav

# 参数说明：
# -m          模型路径
# -l zh       语言（中文），可改为 en/ja/auto
# -osrt       输出 SRT 格式
# -of         输出文件名（不含扩展名）
# -t 8        使用 8 线程
# --split-on-word  按词分割，提高断句质量
```

### 2.5.5 常用语言代码

| 代码 | 语言 | 备注 |
|------|------|------|
| `zh` | 中文 | 自动识别简繁体 |
| `en` | 英文 | |
| `ja` | 日文 | |
| `ko` | 韩文 | |
| `auto` | 自动检测 | 速度较慢 |

### 2.5.6 转录质量优化

```bash
# 高质量转录（使用 small 模型）
whisper-cli \
  -m ~/.cache/whisper/ggml-small.bin \
  -l zh \
  -osrt \
  -of VIDEO_ID \
  -t 8 \
  --split-on-word \
  --print-progress \
  VIDEO_ID_audio.wav

# 带初始提示（提高专有名词识别准确率）
whisper-cli \
  -m ~/.cache/whisper/ggml-base.bin \
  -l zh \
  --prompt "这是一个关于 Docker 技术的视频，涉及编程和 DevOps" \
  -osrt \
  -of VIDEO_ID \
  VIDEO_ID_audio.wav
```

### 2.5.7 转录后处理

```bash
# 清理临时音频文件
rm -f VIDEO_ID_audio.wav

# 检查生成的字幕
head -50 VIDEO_ID.srt

# 验证字幕时间戳
grep -E "^[0-9]{2}:[0-9]{2}:[0-9]{2}" VIDEO_ID.srt | head -10
```

### 2.5.8 Whisper 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `whisper-cli not found` | 未安装 whisper-cpp | `brew install whisper-cpp` |
| `model not found` | 未下载模型 | 执行模型下载命令 |
| 转录质量差 | 模型太小或音频质量差 | 使用 small/medium 模型 |
| 专有名词识别错误 | 缺少上下文 | 使用 `--prompt` 参数 |
| 转录速度慢 | 模型太大或线程太少 | 使用 base 模型，增加 `-t` 线程数 |
| 中文识别为其他语言 | 语言参数错误 | 明确指定 `-l zh` |

### 2.5.9 完整转录脚本

```bash
#!/bin/bash
# whisper_transcribe.sh - 视频语音转录脚本

VIDEO_FILE="$1"
VIDEO_ID="${VIDEO_FILE%.*}"
MODEL="${2:-base}"  # 默认使用 base 模型

# 检查参数
if [ -z "$VIDEO_FILE" ]; then
  echo "用法: $0 <视频文件> [模型名称]"
  echo "示例: $0 video.mp4 small"
  exit 1
fi

# 检查依赖
command -v whisper-cli >/dev/null || { echo "错误: 未安装 whisper-cpp"; exit 1; }
command -v ffmpeg >/dev/null || { echo "错误: 未安装 ffmpeg"; exit 1; }

# 检查模型
MODEL_PATH="$HOME/.cache/whisper/ggml-${MODEL}.bin"
if [ ! -f "$MODEL_PATH" ]; then
  echo "模型不存在，正在下载 ${MODEL} 模型..."
  curl -L -o "$MODEL_PATH" \
    "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-${MODEL}.bin"
fi

# 提取音频
echo "正在提取音频..."
ffmpeg -y -i "$VIDEO_FILE" \
  -vn -acodec pcm_s16le -ar 16000 -ac 1 \
  "${VIDEO_ID}_audio.wav" 2>/dev/null

# 转录
echo "正在转录..."
whisper-cli \
  -m "$MODEL_PATH" \
  -l zh \
  -osrt \
  -of "$VIDEO_ID" \
  -t 8 \
  --split-on-word \
  "${VIDEO_ID}_audio.wav"

# 清理
rm -f "${VIDEO_ID}_audio.wav"
echo "完成！字幕文件: ${VIDEO_ID}.srt"
```

### 2.6 字幕质量检查

**下载的字幕检查**：
- 文件是否为空或只有几行
- 是否有大量乱码（尝试 `--sub-format srt` 或 `--convert-subs srt`）
- 时间戳是否合理（无负数、无超大跳跃）
- 是否有说话人标记（如 `主持人：`）

**Whisper 转录字幕检查**：
- 检查是否有明显的识别错误（同音字、专有名词）
- 检查时间戳是否连续（Whisper 有时会跳跃）
- 检查是否有大量重复或无意义内容
- 如质量不佳，考虑使用更大的模型重新转录

## Step 3: 分析字幕识别精彩片段

目标：基于 SRT 字幕，识别"内容完整、情绪有效、可传播"的高质量片段，并输出可直接用于切片的时间范围与标题。

### 3.1 字幕预处理

#### 3.1.1 SRT 格式解析要点

标准块结构：
```
1
00:04:37,000 --> 00:05:13,000
精彩内容文本...
```

解析时需提取 4 类信息：
- `index`：字幕序号
- `start_time` / `end_time`：起止时间
- `text`：字幕文本（可能多行）
- `raw_block`：原始块（用于回溯定位）

预处理建议：
- 去除 HTML 标签、无意义符号（如重复 `♪`、`...` 过多连写）
- 统一中英文标点（`，。！？；：`），保留语气词（如"啊""嗯"）用于情绪判断
- 保留说话人标记（如"主持人：""嘉宾："），用于对话结构识别

#### 3.1.2 断句合并策略（把"碎字幕"合成完整句）

字幕常被硬切成短片段，必须先合并为"语义句单元"。

合并规则（按顺序执行）：
1. **时间连续**：相邻字幕时间间隔 `gap <= 1.2s`，优先考虑合并
2. **语义未完成**：前一条未以句末标点结束（`。！？`），且下一条是续句，合并
3. **连接词续接**：下一条以"但是/所以/然后/因为/其实/另外"等开头，优先合并到前句
4. **说话人切换即断开**：检测到说话人变化（`A:`→`B:`）时强制断句
5. **长度上限保护**：单句合并后超过 `120` 汉字或 `24s`，强制切分
6. **问题-回答配对**：对话类视频中，问句与紧随回答可组合成一个分析单元

输出结构（句级）：
- `sentence_id` / `sentence_text` / `sentence_start` / `sentence_end`
- `source_indices`（由哪些字幕块合并而来）

#### 3.1.3 时间戳提取与格式转换

SRT 时间戳：`HH:MM:SS,mmm`

统一转换：
- 毫秒整数：`total_ms = HH*3600000 + MM*60000 + SS*1000 + mmm`
- FFmpeg 格式：`HH:MM:SS.mmm`（**逗号改点**，这是常见错误源！）

---

### 3.2 精彩片段识别维度（评分矩阵）

对每个候选句单元按 4 个维度打分（0-5 分）：

| 维度 | 关键识别信号 | 评分参考 |
|---|---|---|
| **内容维度** (40%) | 深度观点、反常识结论、具体数据、案例、方法论、金句 | 信息密度高且有"新知"=高分 |
| **结构维度** (25%) | 开头钩子、转折点、冲突推进、高潮、结尾升华 | 有完整起承转合=高分 |
| **情感维度** (20%) | 幽默、感动、震撼、愤怒、争议、紧张释放 | 情绪明显且自然=高分 |
| **传播维度** (15%) | 可引用性、易复述性、话题性、评论触发潜力 | 一句话能概括并引发讨论=高分 |

**总分公式**：`总分 = 内容*0.40 + 结构*0.25 + 情感*0.20 + 传播*0.15`

**筛选阈值**：
- `>= 3.8`：优先切片
- `>= 3.2`：进入候选池
- `< 3.2`：仅保留备选

---

### 3.3 片段边界确定

#### 3.3.1 开始时间（不能从句子中间切）

1. 从"高分句"向前回溯到最近的**完整句首**
2. 若是对话亮点，优先包含触发该回答的问句尾部（前置 1-3 秒）
3. 开头可加 `0.2-0.6s` 缓冲，避免听感突兀
4. **禁止**从连词中间起切（如"但是/所以"后半句才开始）

#### 3.3.2 结束时间（要完整收尾）

1. 必须落在语义收束处（结论句、笑点落点、情绪释放后）
2. 若句末后有观众反应（笑声/停顿/掌声），可后延 `0.3-1.0s`
3. 出现"总结一下/所以结论是/最后一句"时，尽量包含完整总结
4. **禁止**在关键词前戛然而止（造成"被截断感"）

#### 3.3.3 合理时长范围

| 时长 | 适用场景 |
|------|----------|
| `15-30s` | 强钩子、单一金句、短冲突 |
| `30-60s` | **最常用**，信息与完播平衡最佳 |
| `60-120s` | 需要完整故事或完整论证链 |
| `>120s` | 仅保留极强叙事片段，否则建议拆分 |

---

### 3.4 不同视频类型的分析策略

| 视频类型 | 识别重点 | 边界策略 |
|---|---|---|
| **访谈/对话类** | 犀利提问、反转回答、立场冲突、真实经历 | 尽量保留"问 + 答"闭环 |
| **演讲/TED类** | 观点主张、论证链、故事高潮、结尾升华 | 保留"铺垫 -> 论点 -> 结论"三段 |
| **纪录片/纪实类** | 真实事件、人物命运、关键事实、现场细节 | 需补足最小上下文，避免断章 |
| **新闻/解说类** | 关键事实、时间地点人物、影响解读 | 保留"发生了什么 + 为什么重要" |
| **娱乐/综艺类** | 笑点、反应、名场面、意外结果 | 前后多留反应时间，保证笑点落地 |

---

### 3.5 片段命名规范

**核心原则：标题必须独立可理解**

标题本身要携带足够的上下文信息，让没看过原视频的人也能立刻明白"这是关于什么的、为什么值得看"。

---

#### 命名规则（按重要性排序）

1. **独立可理解**（最重要）
   - 标题必须自包含，不依赖视频标题、序号、前后片段
   - 包含"谁/什么"（主体）+ "怎么了"（发生了什么/结论是什么）
   
2. **信息完整**
   - 长度建议 `15-35` 字（中文），宁可稍长也不要信息缺失
   - 必须包含：**主体**（人/事/物）+ **动作/观点**（做了什么/说了什么）+ **结果/意义**（意味着什么）

3. **可检索性**
   - 优先使用实体名、专有名词、数字、行业术语
   - 包含问题词（"为什么""如何""是什么"）能提升搜索命中率

4. **避免空泛词**
   - ❌ 太牛了、绝了、震惊、必看、干货、精彩、重磅
   - ✅ 具体说了什么、给了什么数据、得出什么结论

---

#### 推荐模板（按场景）

| 场景 | 模板 | 示例 |
|------|------|------|
| **观点类** | `[人物/机构]：[核心观点]` | `Sam Altman：AI 将在 5 年内取代 50% 的白领工作` |
| **数据类** | `[主题] + [关键数字/数据]` | `美国失业率降至 3.4%，创 54 年新低` |
| **问答类** | `[问题]？[一句话答案]` | `为什么年轻人不爱买房了？收入房价比从 6 倍涨到 15 倍` |
| **案例类** | `[公司/人物] + [发生了什么] + [结果]` | `字节跳动 2023 年营收超 1200 亿美元，首次超越腾讯` |
| **冲突类** | `[甲方]与[乙方]的[冲突焦点]，最后[结果]` | `OpenAI 与微软的算力分配之争，最终微软获得优先权` |
| **方法论** | `[人物]如何[达成目标]：[核心方法]` | `巴菲特如何选股：只买能看懂 10 年后现金流的公司` |
| **趋势类** | `[领域]正在发生什么变化：[具体变化]` | `手机市场正在发生什么变化：折叠屏销量同比增长 280%` |

---

#### ❌ 反例 vs ✅ 正例

| ❌ 反例（依赖上下文） | ✅ 正例（独立可理解） |
|---|---|
| `核心概念` | `无就业繁荣：GDP 增长但就业率下降的经济学现象` |
| `三大外挂理论` | `李笑来的三大外挂理论：复利、自学、长期主义` |
| `为什么投资 BTC` | `为什么 A16z 合伙人投资比特币：稀缺性 + 数字黄金叙事` |
| `精彩观点` | `黄仁勋：摩尔定律已死，AI 算力需求每 6 个月翻一倍` |
| `数据分析` | `2024 年中国新能源车销量：比亚迪 300 万辆 vs 特斯拉 60 万辆` |
| `他这么说` | `马斯克谈 AI 风险：有 20% 概率导致人类灭绝` |

---

#### 自检清单（命名后必过）

- [ ] 不看原视频标题，能理解这个片段在讲什么吗？
- [ ] 标题里有"谁/什么"吗？
- [ ] 标题里有"怎么了/结论是什么"吗？
- [ ] 去掉任何词，标题会变得模糊吗？（如果会，说明每个词都有用）
- [ ] 搜索这个标题，能找到相关内容吗？

---

### 3.6 质量评估检查清单（切片前必过）

**逐项检查**：
- [ ] **字幕准确**：关键专有名词、数字、否定词无明显识别错误
- [ ] **语义完整**：片段可独立理解，不依赖大量外部上下文
- [ ] **边界自然**：开头不从半句起，结尾不在核心词前截断
- [ ] **结构完整**：至少包含"引入 -> 信息点 -> 收束"中的 2 个以上
- [ ] **情绪有效**：有明确情绪或观点驱动，不是平铺直叙
- [ ] **传播潜力**：能用一句话复述亮点，具备标题提炼空间
- [ ] **时长合理**：落在目标分发场景可接受区间（优先 30-60s）
- [ ] **无重复冗余**：与已选片段重合度低，避免同质化输出
- [ ] **合规安全**：无明显侵权、隐私泄露、极端误导性表述风险

**一票否决**（出现任一条直接淘汰）：
- 关键结论被截断或语义反转
- 主要信息依赖前文且片段内无法自洽
- 字幕错误导致事实含义变化（尤其数字与人名）

---

### 3.7 建议输出格式

每个候选片段输出以下字段，便于后续自动切片：

```
clip_id: 01
title: 无就业繁荣核心概念
start_time: 00:01:00.000
end_time: 00:03:30.000
duration_sec: 150
score_total: 4.2
score_content: 4.5 / score_structure: 4.0 / score_emotion: 4.0 / score_viral: 4.0
reason: 核心概念阐释，数据支撑强，观点反常识
keywords: 无就业繁荣, GDP, 裁员, 经济脱钩
```

## Step 4: 切片视频

### 4.1 双模式选择

| 模式 | 特点 | 适用场景 | 输出格式 |
|------|------|----------|----------|
| **Fast (copy)** | 速度快，不重编码，但可能不帧精确 | 快速预览、批量处理 | `.mkv`（兼容性更好） |
| **Accurate (re-encode)** | 帧精确，兼容性好，但速度慢 | 最终输出、精确卡点 | `.mp4`（通用格式） |

### 4.2 Fast 模式（推荐先用）

```bash
# 创建输出目录
mkdir -p video_clips

# Fast 模式（直接复制流，速度快，建议输出 mkv）
ffmpeg -y -ss 00:04:37 -to 00:05:13 -i "input.mp4" -c copy "video_clips/01_片段名.mkv"

# 批量切片示例
VIDEO="txqaJ_r0IvY.mp4"

# 片段1
ffmpeg -y -ss 00:01:00 -to 00:03:30 -i "$VIDEO" -c copy "video_clips/01_无就业繁荣核心概念.mkv"

# 片段2
ffmpeg -y -ss 00:04:56 -to 00:06:20 -i "$VIDEO" -c copy "video_clips/02_三大外挂理论.mkv"
```

**注意事项**：
- `-ss` 放在 `-i` **前面**是快速定位（seek），但可能不帧精确
- 输出用 `.mkv` 避免 webm/av1 编码塞进 mp4 的兼容性问题
- 如果切片开头/结尾有黑帧或卡顿，改用 Accurate 模式

### 4.3 Accurate 模式（精确卡点）

```bash
# Accurate 模式（重编码，帧精确，输出标准 mp4）
ffmpeg -y -i "input.mp4" -ss 00:04:37 -to 00:05:13 \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  "video_clips/01_片段名.mp4"
```

**参数说明**：
- `-ss` 放在 `-i` **后面**是精确帧定位（但需要先解码到该点）
- `-c:v libx264 -preset fast -crf 23`：H.264 编码，质量平衡
- `-c:a aac -b:a 128k`：AAC 音频
- `-movflags +faststart`：优化网络播放（元数据前置）

### 4.4 参数详解

| 参数 | 说明 |
|------|------|
| `-y` | 覆盖已存在文件 |
| `-ss` | 开始时间（`HH:MM:SS` 或 `HH:MM:SS.mmm`） |
| `-to` | 结束时间（绝对时间点） |
| `-t` | 持续时长（秒） |
| `-i` | 输入文件 |
| `-c copy` | 直接复制流，不重编码（快） |
| `-c:v libx264` | 视频重编码为 H.264 |
| `-c:a aac` | 音频重编码为 AAC |

### 4.5 时间不准问题

**原因**：`-ss` 在 `-i` 前是关键帧定位，可能偏离几秒

**解决方案**：
1. 用 Accurate 模式（`-ss` 放 `-i` 后）
2. 或提前几秒开始，确保包含目标内容
3. 或先用 Fast 模式预览，微调时间戳后再 Accurate 模式输出

### 4.6 切片质量检查

切片后检查：
- [ ] 文件大小是否正常（不是 0 或异常小）
- [ ] 用播放器打开，确认有画面和声音
- [ ] 确认开始/结束时间是否准确
- [ ] 确认画面无花屏、音频无爆音

## Step 5: 生成精彩片段文档

### 5.1 推荐文档模板

```markdown
# 精彩片段摘录

> **来源**: 视频标题
> **链接**: 原始 URL
> **时长**: XX:XX
> **上传者**: Uploader
> **日期**: YYYY-MM-DD
> **字幕**: 原字幕 / Whisper 转录（原视频无字幕）

---

## 📌 视频概要

[1-3 句视频核心内容概括]

---

## 🎬 片段一：[标题]

> **时间戳**: [HH:MM:SS - HH:MM:SS] | **文件**: `01_标题.mp4`

**核心观点**：[1-2 句说明为什么这个片段值得看]

**金句摘录**:
- "原文引用1..."
- "原文引用2..."

**关键数据**：
- 数据点 1
- 数据点 2

**洞察**：[你的分析]

---

## 📁 文件清单

| 序号 | 文件名 | 时长 | 大小 |
|------|--------|------|------|
| 1 | `01_标题.mp4` | X:XX | XM |
| ... | ... | ... | ... |

**原始视频**: `VIDEO_ID.mp4` (XXM, XX:XX)
**字幕文件**: `VIDEO_ID.srt`（来源：原字幕 / Whisper 转录）
```

### 5.2 标准化字段（便于自动化处理）

每个片段应包含以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| `clip_id` | 片段序号 | `01` |
| `title` | 片段标题 | `无就业繁荣核心概念` |
| `start_time` | 开始时间 | `00:01:00.000` |
| `end_time` | 结束时间 | `00:03:30.000` |
| `duration_sec` | 时长（秒） | `150` |
| `score_total` | 总评分 | `4.2` |
| `reason` | 入选原因 | `核心概念阐释，数据支撑强` |
| `keywords` | 关键词 | `无就业繁荣, GDP, 裁员` |
| `output_path` | 输出文件路径 | `video_clips/01_无就业繁荣核心概念.mp4` |
| `source_sub_file` | 源字幕文件 | `txqaJ_r0IvY.zh-Hans.srt` |

### 5.3 YAML 格式输出（可选）

```yaml
clips:
  - clip_id: "01"
    title: "无就业繁荣核心概念"
    start_time: "00:01:00"
    end_time: "00:03:30"
    duration_sec: 150
    score_total: 4.2
    reason: "核心概念阐释，数据支撑强，观点反常识"
    keywords: ["无就业繁荣", "GDP", "裁员", "经济脱钩"]
    output_path: "video_clips/01_无就业繁荣核心概念.mp4"
```

## 常见问题

### 下载相关

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Zsh 报错 `no matches found` | URL 中 `?` 被当作通配符 | URL 加**双引号** |
| HTTP 403 Forbidden | 需要登录/地区限制 | `--cookies-from-browser chrome` |
| HTTP 429 Too Many Requests | 下载频繁被限流 | 等待几分钟或 `--sleep-requests 5` |
| `Requested format is not available` | 格式选择器不匹配 | 改用 `-f "best"` 或先用 `-F` 查看可用格式 |
| `ffmpeg not found` | 未安装 ffmpeg | `brew install ffmpeg` (macOS) |
| Cookies 读取失败 | 浏览器正在运行 | 关闭浏览器后重试 |

### 字幕相关

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 字幕格式乱码 | 编码问题 | 尝试 `--sub-format srt` 或 `--convert-subs srt` |
| 无字幕可用 | 视频没有字幕 | 使用 Whisper 语音转录 |
| 字幕语言不对 | 语言代码不匹配 | 使用通配符 `zh.*` 或先 `--list-subs` 查看 |
| 字幕被切成碎片 | SRT 格式特性 | 按 Step 3.1.2 断句合并策略处理 |

### Whisper 转录相关

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `whisper-cli not found` | 未安装 | `brew install whisper-cpp` |
| 模型下载失败 | 网络问题 | 使用代理或手动下载模型文件 |
| 转录质量差 | 模型太小 | 使用 `small` 或 `medium` 模型 |
| 专有名词错误 | 缺少上下文 | 使用 `--prompt` 提供提示词 |
| 转录太慢 | 模型太大 | 使用 `base` 模型，增加 `-t 8` 线程 |
| 语言识别错误 | 未指定语言 | 明确指定 `-l zh` 或 `-l en` |

### 切片相关

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 切片时间不准 | `-ss` 在 `-i` 前是关键帧定位 | 用 Accurate 模式（`-ss` 放 `-i` 后） |
| 切片无声/黑屏 | 源文件编码问题 | 检查源文件，或用 Accurate 模式重编码 |
| 切片画质下降 | 意外触发了重编码 | Fast 模式用 `-c copy` |
| MP4 无法播放 | 容器/编码不匹配 | Fast 模式输出用 `.mkv`，或用 Accurate 模式 |
| 切片开头卡顿 | 关键帧定位偏差 | 提前 1-2 秒开始，或用 Accurate 模式 |

### 流程相关

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 不知道视频有没有字幕 | 未预检查 | 先用 `yt-dlp --list-subs "URL"` 检查 |
| 切片太多不知道选哪个 | 缺乏评分标准 | 按 Step 3.2 评分矩阵筛选 `>= 3.8` 分的片段 |
| 片段标题起不好 | 缺乏命名规范 | 按 Step 3.5 命名模板处理 |
| 切片内容不完整 | 边界选择问题 | 按 Step 3.3 边界规则回溯完整句 |

### 快速诊断流程

```
1. 下载失败？→ 检查 cookies、格式、网络
2. 无字幕？
   ├─ 确认无字幕：yt-dlp --list-subs "URL"
   ├─ 安装 Whisper：brew install whisper-cpp
   ├─ 下载模型：curl -L -o ~/.cache/whisper/ggml-base.bin ...
   └─ 转录：whisper-cli -m ~/.cache/whisper/ggml-base.bin -l zh -osrt ...
3. 切片问题？→ Fast 模式先预览，Accurate 模式最终输出
4. 质量存疑？→ 跑 Step 3.6 质量检查清单
```

### 无字幕视频处理流程

```
┌─────────────────────────────────────────────────────────────┐
│                    检测视频是否有字幕                          │
│                  yt-dlp --list-subs "URL"                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         有字幕 ✓                        无字幕 ✗
              │                               │
              ▼                               ▼
    ┌─────────────────┐           ┌─────────────────────┐
    │  下载字幕        │           │  检查 Whisper 是否安装 │
    │  yt-dlp --write-subs     │     which whisper-cli   │
    └─────────────────┘           └─────────────────────┘
              │                               │
              │                    ┌──────────┴──────────┐
              │                    │                     │
              │               已安装 ✓              未安装 ✗
              │                    │                     │
              │                    ▼                     ▼
              │           ┌─────────────────┐   ┌─────────────────┐
              │           │  提取音频        │   │ brew install    │
              │           │  ffmpeg -i ...   │   │ whisper-cpp     │
              │           └─────────────────┘   └─────────────────┘
              │                    │                     │
              │                    ▼                     │
              │           ┌─────────────────┐           │
              │           │  Whisper 转录    │◄──────────┘
              │           │  whisper-cli     │
              │           └─────────────────┘
              │                    │
              └────────────────────┼────────────────────┐
                                   │                    │
                                   ▼                    ▼
                          ┌─────────────────┐  ┌─────────────────┐
                          │  分析精彩片段    │  │  生成切片        │
                          │  Step 3         │  │  Step 4         │
                          └─────────────────┘  └─────────────────┘
```
