[English](README.md) | [简体中文](README_CN.md) | [繁體中文](README_TW.md) | [日本語](README_JP.md)

<div align="center">
<img src="resources/logo.svg" width="20%"/>

# GLM-ASR

[![Docker](https://img.shields.io/badge/Docker-neosun%2Fglm--asr-blue?logo=docker)](https://hub.docker.com/r/neosun/glm-asr)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)

**基于 GLM-ASR-Nano 的一站式语音识别服务**

Web 界面 • REST API • MCP 服务 • 长音频支持

</div>

---

## 🖥️ 界面截图

![Web UI](resources/ui-screenshot.png)

---

## ✨ 功能特性

- 🎯 **高精度识别** - 基于 GLM-ASR-Nano-2512 (1.5B)，性能超越 Whisper V3
- 🌍 **17 种语言** - 支持中文、英语、粤语、日语、韩语等
- 🎤 **长音频支持** - 分段处理，无音频长度限制
- 🖥️ **Web 界面** - 现代暗色主题，支持 4 种语言切换
- 🔌 **REST API** - 完整 API 接口，Swagger 文档
- 🤖 **MCP 服务** - 支持 Claude Desktop 集成
- 💾 **显存管理** - 手动加载/卸载模型，灵活控制显存
- 🐳 **Docker 部署** - 一键启动

---

## 🚀 快速开始

> [!IMPORTANT]  
> - 若是使用cuda, 最好在linux上使用, 因为torchcodec在win上支持的不好, 非得用win, 似乎只能用conda来安装, 因为`torchcodec-x.x.x-cudaxxx`只在[conda-forge](https://anaconda.org/channels/conda-forge/packages/torchcodec/overview)上提供了包, [pytorch/torchcodec](https://download.pytorch.org/whl/torchcodec/)**未提供**
> - 安装注意`torchcodec-torch-python`的版本对应关系, 详见[link](https://github.com/meta-pytorch/torchcodec?tab=readme-ov-file#installing-cpu-only-torchcodec)
> - 注意`auto`时自动加载的`dtype`, 是否为自己显卡支持的, 否则很慢. 参考[link](https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html#hardware-and-precision)
> 在[GPUManager.load()](gpu_manager.py#L47-L50)
> ```python
> # torch.cuda.get_device_capability()
> self.model: GlmAsrForConditionalGeneration = AutoModelForSeq2SeqLM.from_pretrained(
>     checkpoint_dir,
>     dtype="auto",
>     device_map="auto",
> )
> ```

### Docker 方式（推荐）

```bash
docker run -d --gpus all -p 7860:7860 neosun/glm-asr:latest
```

访问：http://localhost:7860

### Docker Compose

```bash
git clone https://github.com/neosun100/glm-asr.git
cd glm-asr
docker compose up -d
```

---

## 📦 安装部署

### 环境要求

- NVIDIA GPU（显存 6GB+）
- Docker + NVIDIA Container Toolkit
- 或：Python 3.10+、CUDA 12.x、FFmpeg

### 方式一：Docker 部署

```bash
# 拉取镜像
docker pull neosun/glm-asr:latest

# 启动容器
docker run -d \
  --name glm-asr \
  --gpus all \
  -p 7860:7860 \
  -v ./cache:/app/cache \
  neosun/glm-asr:latest

# 健康检查
curl http://localhost:7860/health
```

### 方式二：本地安装

```bash
# 克隆仓库
git clone https://github.com/neosun100/glm-asr.git
cd glm-asr

# 安装依赖
pip install -r requirements.txt
sudo apt install ffmpeg

# 启动服务
python app.py
```

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MODEL_PATH` | `zai-org/GLM-ASR-Nano-2512` | HuggingFace 模型路径 |
| `PORT` | `7860` | 服务端口 |
| `HF_HOME` | `/app/cache` | 模型缓存目录 |

### docker-compose.yml

```yaml
services:
  glm-asr:
    image: neosun/glm-asr:latest
    ports:
      - "7860:7860"
    volumes:
      - ./cache:/app/cache
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## 📖 使用说明

### Web 界面

打开 http://localhost:7860：
- 上传音频文件（wav/mp3/flac/m4a/ogg）
- 点击"转录"
- 复制结果

---

## 🔌 API 文档

### 基础地址
```
http://localhost:7860
```

### 接口列表

#### 健康检查
```http
GET /health
```
**响应：**
```json
{"status": "ok", "model_loaded": true}
```

#### 音频转录
```http
POST /api/transcribe
Content-Type: multipart/form-data
```
**参数：**
| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 音频文件（wav/mp3/flac/m4a/ogg） |
| max_new_tokens | int | 否 | 最大输出 token 数（默认：512） |

**示例：**
```bash
curl -X POST http://localhost:7860/api/transcribe \
  -F "file=@audio.mp3"
```
**响应：**
```json
{"status": "success", "text": "转录的文本内容..."}
```

#### GPU 状态
```http
GET /gpu/status
```
**响应：**
```json
{
  "model_loaded": true,
  "device": "cuda",
  "checkpoint": "zai-org/GLM-ASR-Nano-2512",
  "gpu_memory_used_mb": 4320.5,
  "gpu_memory_total_mb": 24576.0
}
```

#### 卸载模型
```http
POST /gpu/unload
```
**响应：**
```json
{"status": "unloaded"}
```

#### 加载模型
```http
POST /gpu/load
```
**响应：**
```json
{"status": "loaded"}
```

### Swagger 文档
交互式 API 文档：http://localhost:7860/docs

---

## 🤖 MCP 服务（Claude Desktop）

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "glm-asr": {
      "command": "python",
      "args": ["/path/to/glm-asr/mcp_server.py"]
    }
  }
}
```

可用工具：
- `transcribe` - 转录音频文件
- `gpu_status` - 获取 GPU/模型状态
- `gpu_load` - 加载模型到 GPU
- `gpu_unload` - 从 GPU 卸载模型

---

## 🏗️ 技术栈

| 组件 | 技术 |
|------|------|
| 模型 | GLM-ASR-Nano-2512 (1.5B) |
| 后端 | Flask + Flask-SocketIO |
| 前端 | HTML5 + Vanilla JS |
| 容器 | Docker + NVIDIA CUDA |
| API 文档 | Flasgger (Swagger) |
| MCP | FastMCP |

---

## 📊 性能对比

GLM-ASR-Nano 在同类模型中错误率最低（4.10）：

![Benchmark](resources/bench.png)

---

## 🤝 参与贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing`)
5. 提交 Pull Request

---

## 📝 更新日志

### v1.1.0 (2024-12-15)
- ✅ VAD 智能分段（silero-vad）
- ✅ 在自然停顿处切分，不切断词句
- ✅ 支持任意长度音频（已测试 1.5 小时）
- ✅ 每段 ≤ 25秒，防止 OOM
- ✅ 自动合并过短片段（≥ 2秒）

### v1.0.2 (2024-12-14)
- ✅ 长音频保护（最大 30 分钟截断）
- ✅ 改进错误处理

### v1.0.1 (2024-12-14)
- ✅ 添加 UI 界面截图
- ✅ 完善 API 文档

### v1.0.0 (2024-12-14)
- ✅ 长音频分段转录
- ✅ 4 语言 Web 界面
- ✅ REST API + Swagger 文档
- ✅ MCP 服务集成
- ✅ Docker 一体化镜像

---

## 📄 开源协议

[Apache License 2.0](LICENSE)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=neosun100/glm-asr&type=Date)](https://star-history.com/#neosun100/glm-asr)

## 📱 关注公众号

<img src="https://img.aws.xin/uPic/扫码_搜索联合传播样式-标准色版.png" width="300"/>
