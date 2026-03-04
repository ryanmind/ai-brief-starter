# 信息源配置

信息源通过 `sources.txt` 文件配置，每行一个源。

## 支持的源类型

### 1. RSS Feed

直接填写 RSS 链接：

```
https://openai.com/blog/rss.xml
https://www.anthropic.com/news/rss
https://arxiv.org/rss/cs.AI
```

### 2. Twitter/X

填写用户主页链接，会自动转换为 Nitter RSS：

```
https://x.com/OpenAI
https://x.com/anthropicai
https://x.com/sama
```

### 3. GitHub

支持多种格式：

```
# Releases
https://github.com/openai/openai-python/releases.atom

# Commits
https://github.com/anthropics/anthropic-sdk-python/commits/main.atom

# Changelog 跟踪
https://github.com/owner/repo/blob/main/CHANGELOG.md
```

---

## 默认信息源

查看项目 `sources.txt` 获取完整列表，包括：

- **官方博客**：OpenAI、Anthropic、Google DeepMind、Meta AI
- **研究平台**：arXiv cs.AI、Hugging Face
- **社交媒体**：X/Twitter 账号
- **开源项目**：主流 AI 框架 Releases

---

## 推荐信息源分类

### AI 创始人大佬动态

跟踪 AI 领域顶级大佬的一手动向，了解行业趋势与技术前瞻。

| 人物 | 身份 | X 账号 | 简介 |
|------|------|--------|------|
| Sam Altman | OpenAI CEO | `https://x.com/sama` | GPT 系列、ChatGPT 掌舵人 |
| Demis Hassabis | Google DeepMind CEO | `https://x.com/demishassabis` | AlphaGo、AlphaFold 之父 |
| Elon Musk | xAI 创始人 | `https://x.com/elonmusk` | Tesla、SpaceX、Grok |
| Dario Amodei | Anthropic CEO | `https://x.com/AnthropicAI` | Claude 系列主导者 |
| Arthur Mensch | Mistral CEO | `https://x.com/MistralAI` | 欧洲开源大模型领军者 |
| Andrej Karpathy | AI 研究员/教育家 | `https://x.com/karpathy` | 前 OpenAI/Tesla AI 总监，Eureka Labs 创始人 |
| Ilya Sutskever | Safe Superintelligence | `https://x.com/ilyasut` | 前 OpenAI 首席科学家，AlexNet 共同作者 |
| Jim Fan | NVIDIA 高级研究员 | `https://x.com/DrJimFan` | 具身智能、机器人学习专家 |
| Ian Goodfellow | Google DeepMind | `https://x.com/goodfellow_ian` | GAN 发明者 |
| Yann LeCun | Meta AI 首席科学家 | `https://x.com/ylecun` | 卷积神经网络之父，图灵奖得主 |
| Andrew Ng | DeepLearning.AI | `https://x.com/AndrewYNg` | 深度学习教育先驱 |
| Jensen Huang | NVIDIA CEO | `https://x.com/nvidia` | AI 算力基建领袖 |

**中国 AI 创始人/领军人物**：

| 人物 | 身份 | X 账号 |
|------|------|--------|
| 杨植麟 | 月之暗面 Kimi 创始人 | `https://x.com/tszzq` |
| 李开复 | 创新工场/零一万物 | `https://x.com/kaifulee` |
| 周明 | 澜舟科技创始人 | `https://x.com/ictclp` |

---

### 视频 AI 动态

AI 视频生成领域正快速发展，以下是最值得关注的源：

#### 官方渠道

| 产品 | 公司 | 官网 | X 账号 | GitHub |
|------|------|------|--------|--------|
| Sora | OpenAI | https://openai.com/sora | `@OpenAI` | - |
| Runway Gen-3 | Runway | https://runwayml.com | `@runwayml` | `runwayml/sdk-python` |
| Pika | Pika Labs | https://pika.art | `@pika_labs` | - |
| Kling (可灵) | 快手 | https://klingai.com | - | - |
| Hailuo (海螺) | MiniMax | https://hailuoai.com/video | `@MiniMax_AIAgent` | `MiniMax-AI` |
| Luma Dream Machine | Luma AI | https://lumalabs.ai/dream-machine | `@LumaLabsAI` | - |
| Stable Video Diffusion | Stability AI | https://stability.ai | `@StabilityAI` | `Stability-AI/generative-models` |

#### 推荐 RSS/Atom 源

```
# Runway SDK 更新
https://github.com/runwayml/sdk-python/commits/main/CHANGELOG.md.atom

# Stability AI 视频模型
https://github.com/Stability-AI/generative-models/commits/main/CHANGELOG.md.atom

# OpenAI Sora 官方博客
https://openai.com/news/rss.xml

# MiniMax 视频模型
https://github.com/MiniMax-AI/MiniMax-M2.1/commits/main/CHANGELOG.md.atom
```

---

### AI 生图动态

图像生成是 AI 应用最广泛的领域之一。

#### 主流产品

| 产品 | 公司 | 官网 | X 账号 |
|------|------|------|--------|
| DALL·E 3 | OpenAI | https://openai.com/dall-e-3 | `@OpenAI` |
| Midjourney | Midjourney | https://midjourney.com | `@midjourney` |
| Stable Diffusion | Stability AI | https://stability.ai | `@StabilityAI` |
| Ideogram | Ideogram | https://ideogram.ai | `@ideogram_ai` |
| FLUX | Black Forest Labs | https://blackforestlabs.ai | `@blklabsai` |
| Leonardo.AI | Leonardo | https://leonardo.ai | `@LeonardoAi_` |
| Imagen | Google DeepMind | https://deepmind.google | `@GoogleDeepMind` |
| Adobe Firefly | Adobe | https://firefly.adobe.com | `@AdobeFirefly` |

#### 中国产品

| 产品 | 公司 | 官网 |
|------|------|------|
| 通义万象 | 阿里云 | https://tongyi.aliyun.com/wanxiang |
| 文心一格 | 百度 | https://yige.baidu.com |
| 即梦 Dreamina | 字节跳动 | https://jimeng.jianying.com |
| LiblibAI | LiblibAI | https://liblib.ai |

#### 推荐 RSS/Atom 源

```
# Stability AI 生成模型
https://github.com/Stability-AI/generative-models/commits/main/CHANGELOG.md.atom

# ComfyUI（Stable Diffusion 工作流工具）
https://github.com/comfyanonymous/ComfyUI/commits/main/CHANGELOG.md.atom

# Fooocus（简化版 SD）
https://github.com/lllyasviel/Fooocus/commits/main/CHANGELOG.md.atom

# 阿里通义万象
https://github.com/QwenLM/Qwen-VL/commits/main/CHANGELOG.md.atom
```

---

### AI 音乐/音频动态

AI 音乐和语音合成领域发展迅猛。

#### 主流产品

| 产品 | 公司 | 官网 | X 账号 | GitHub |
|------|------|------|--------|--------|
| Suno | Suno | https://suno.com | `@suno_ai_` | `suno-ai/bark` |
| Udio | Udio | https://udio.com | `@udiomusic` | - |
| ElevenLabs | ElevenLabs | https://elevenlabs.io | `@elevenlabsio` | `elevenlabs/elevenlabs-python` |
| OpenAI TTS | OpenAI | https://openai.com | `@OpenAI` | - |
| Whisper | OpenAI | https://openai.com | `@OpenAI` | `openai/whisper` |
| Stable Audio | Stability AI | https://stableaudio.com | `@StabilityAI` | `Stability-AI/stable-audio-tools` |
| MusicGen | Meta AI | https://ai.meta.com | `@MetaAI` | `facebookresearch/audiocraft` |

#### 推荐 RSS/Atom 源

```
# ElevenLabs SDK 更新
https://github.com/elevenlabs/elevenlabs-python/commits/main/CHANGELOG.md.atom

# Suno Bark 开源模型
https://github.com/suno-ai/bark/commits/main/CHANGELOG.md.atom

# Stability Audio 工具
https://github.com/Stability-AI/stable-audio-tools/commits/main/CHANGELOG.md.atom

# Meta AudioCraft（MusicGen）
https://github.com/facebookresearch/audiocraft/commits/main/CHANGELOG.md.atom

# OpenAI Whisper
https://github.com/openai/whisper/releases.atom
```

---

### AI 办公/生产力工具

提升日常工作效率的 AI 工具动态。

#### 代码助手

| 产品 | 公司 | 官网 | X 账号 | GitHub Feed |
|------|------|------|--------|-------------|
| GitHub Copilot | GitHub/Microsoft | https://github.com/features/copilot | `@GitHubCopilot` | - |
| Cursor | Cursor | https://cursor.com | `@codeeditapp` | `getcursor/cursor` |
| Windsurf | Codeium | https://windsurf.com | `@codeiumdev` | `Codeium/windsurf` |
| Claude Code | Anthropic | https://claude.ai | `@AnthropicAI` | `anthropics/claude-code` |
| Replit AI | Replit | https://replit.com | `@replit` | `replit/replit` |
| Amazon CodeWhisperer | AWS | https://aws.amazon.com/codewhisperer | `@awscloud` | - |
| Tabnine | Tabnine | https://tabnine.com | `@tabnine` | - |

#### 推荐 RSS/Atom 源

```
# Cursor 更新
https://github.com/getcursor/cursor/commits/main/CHANGELOG.md.atom

# Claude Code 更新
https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md

# Replit 更新
https://github.com/replit/replit/commits/main/CHANGELOG.md.atom

# Vercel AI SDK
https://github.com/vercel/ai/commits/main/CHANGELOG.md.atom
```

#### 文档/写作助手

| 产品 | 公司 | 官网 | X 账号 |
|------|------|------|--------|
| Notion AI | Notion | https://notion.so | `@NotionHQ` |
| Grammarly AI | Grammarly | https://grammarly.com | `@Grammarly` |
| Jasper | Jasper | https://jasper.ai | `@jasper_ai` |
| Copy.ai | Copy.ai | https://copy.ai | `@copy_ai` |
| Gamma | Gamma | https://gamma.app | `@gammaapp` |
| Perplexity | Perplexity | https://perplexity.ai | `@perplexity_ai` |

---

### AI 娱乐/创意动态

游戏、创意、虚拟角色等娱乐领域 AI 应用。

#### 3D/游戏 AI

| 产品/项目 | 公司/团队 | 官网 | GitHub |
|-----------|-----------|------|--------|
| Unreal Engine AI | Epic Games | https://unrealengine.com | - |
| Unity Muse | Unity | https://unity.com/products/muse | - |
| NVIDIA ACE | NVIDIA | https://nvidia.com/en-us/ai-data-science/generative-ai/ace | - |
| Inworld AI | Inworld | https://inworld.ai | `inworld-ai` |
| Character.AI | Character.AI | https://character.ai | - |
| Genie 2 | Google DeepMind | https://deepmind.google | - |

#### 虚拟角色/数字人

| 产品 | 公司 | 官网 | X 账号 |
|------|------|------|--------|
| HeyGen | HeyGen | https://heygen.com | `@HeyGen_Official` |
| D-ID | D-ID | https://d-id.com | `@d_id_ai` |
| Synthesia | Synthesia | https://synthesia.io | `@synthesiaAV` |
| Soul Machines | Soul Machines | https://soulmachines.com | `@Soul_Machines` |
| AvatarAI | AvatarAI | https://avatarmind.ai | - |

#### 推荐 RSS/Atom 源

```
# Inworld AI SDK
https://github.com/inworld-ai/inworld-unity-sdk/commits/main/CHANGELOG.md.atom

# NVIDIA 开源项目
https://github.com/NVIDIA/GenerativeAIExamples/commits/main/CHANGELOG.md.atom
```

---

### AI 研究前沿

跟踪最新学术论文和研究动态。

#### 学术平台

| 平台 | RSS 源 |
|------|--------|
| arXiv cs.AI | `https://export.arxiv.org/rss/cs.AI` |
| arXiv cs.CL (NLP) | `https://export.arxiv.org/rss/cs.CL` |
| arXiv cs.CV (视觉) | `https://export.arxiv.org/rss/cs.CV` |
| arXiv cs.LG (机器学习) | `https://export.arxiv.org/rss/cs.LG` |
| arXiv cs.RO (机器人) | `https://export.arxiv.org/rss/cs.RO` |
| Hugging Face Papers | https://huggingface.co/papers |

#### 顶级实验室博客

| 实验室 | 博客 RSS |
|--------|----------|
| OpenAI Research | `https://openai.com/blog/rss.xml` |
| Google DeepMind | `https://deepmind.google/research/` |
| Meta AI Research | `https://ai.meta.com/blog/rss.xml` |
| Microsoft Research | `https://www.microsoft.com/en-us/research/blog/feed/` |
| Allen AI | `https://allenai.org/blog` |
| Berkeley AI Research | `https://bair.berkeley.edu/blog/` |

---

## 源健康检查

运行健康检查脚本：

```bash
python scripts/source_health_check.py --output reports/source_health.md
```

输出内容包括：
- 各源可用状态
- 近期条目数量
- 多样性分析

---

## 过滤机制

### 一手来源过滤

开启后（默认），只保留：

- 官方博客域名
- 官方 X 账号
- GitHub 官方仓库

可通过环境变量覆盖：

```bash
PRIMARY_SOURCE_DOMAINS=openai.com,anthropic.com
PRIMARY_X_HANDLES=OpenAI,anthropicai
```

### 二手媒体过滤

默认屏蔽二手媒体域名，避免转载内容。

```bash
SECOND_HAND_DOMAINS=36kr.com,jiqizhixin.com
```

### AI 主题过滤

只保留与 AI 相关的内容：

```bash
AI_TOPIC_KEYWORDS=AI,GPT,LLM,大模型
```

---

## 如何添加新信息源

### 1. 编辑 sources.txt

在项目根目录打开 `sources.txt`，按格式添加：

```
# 分类注释（可选）
https://example.com/feed.rss
https://x.com/username
https://github.com/org/repo/releases.atom
```

### 2. 运行健康检查

```bash
python scripts/source_health_check.py
```

确认新源可用。

### 3. 本地测试

```bash
python main.py
```

检查生成的早报是否包含新源内容。

---

## 最佳实践

1. **定期检查源健康** - 每周运行一次健康检查
2. **保持源多样性** - 避免单一来源刷屏
3. **优先一手来源** - 确保信息准确性
4. **控制总量** - `MAX_ITEMS` 和 `TOP_N` 平衡质量与数量
5. **分类管理** - 用注释分隔不同类别的源，便于维护
6. **及时清理** - 移除长期无更新或失效的源
