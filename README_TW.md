[English](README.md) | [简体中文](README_CN.md) | [繁體中文](README_TW.md) | [日本語](README_JP.md)

<div align="center">
<img src="resources/logo.svg" width="20%"/>

# GLM-ASR

[![Docker](https://img.shields.io/badge/Docker-neosun%2Fglm--asr-blue?logo=docker)](https://hub.docker.com/r/neosun/glm-asr)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)

**基於 GLM-ASR-Nano 的一站式語音識別服務**

Web 介面 • REST API • MCP 服務 • 長音訊支援

</div>

---

## ✨ 功能特性

- 🎯 **高精度識別** - 基於 GLM-ASR-Nano-2512 (1.5B)，效能超越 Whisper V3
- 🌍 **17 種語言** - 支援中文、英語、粵語、日語、韓語等
- 🎤 **長音訊支援** - 分段處理，無音訊長度限制
- 🖥️ **Web 介面** - 現代暗色主題，支援 4 種語言切換
- 🔌 **REST API** - 完整 API 介面，Swagger 文件
- 🤖 **MCP 服務** - 支援 Claude Desktop 整合
- 💾 **顯存管理** - 手動載入/卸載模型，靈活控制顯存
- 🐳 **Docker 部署** - 一鍵啟動

---

## 🚀 快速開始

### Docker 方式（推薦）

```bash
docker run -d --gpus all -p 7860:7860 neosun/glm-asr:latest
```

存取：http://localhost:7860

### Docker Compose

```bash
git clone https://github.com/neosun100/glm-asr.git
cd glm-asr
docker compose up -d
```

---

## 📦 安裝部署

### 環境要求

- NVIDIA GPU（顯存 6GB+）
- Docker + NVIDIA Container Toolkit
- 或：Python 3.10+、CUDA 12.x、FFmpeg

### 方式一：Docker 部署

```bash
# 拉取映像
docker pull neosun/glm-asr:latest

# 啟動容器
docker run -d \
  --name glm-asr \
  --gpus all \
  -p 7860:7860 \
  -v ./cache:/app/cache \
  neosun/glm-asr:latest

# 健康檢查
curl http://localhost:7860/health
```

### 方式二：本地安裝

```bash
# 複製儲存庫
git clone https://github.com/neosun100/glm-asr.git
cd glm-asr

# 安裝依賴
pip install -r requirements.txt
sudo apt install ffmpeg

# 啟動服務
python app.py
```

---

## ⚙️ 配置說明

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `MODEL_PATH` | `zai-org/GLM-ASR-Nano-2512` | HuggingFace 模型路徑 |
| `PORT` | `7860` | 服務埠號 |
| `HF_HOME` | `/app/cache` | 模型快取目錄 |

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

## 📖 使用說明

### Web 介面

開啟 http://localhost:7860：
- 上傳音訊檔案（wav/mp3/flac/m4a/ogg）
- 點擊「轉錄」
- 複製結果

### REST API

```bash
# 轉錄音訊
curl -X POST http://localhost:7860/api/transcribe \
  -F "file=@audio.mp3"

# 查看 GPU 狀態
curl http://localhost:7860/gpu/status

# 卸載模型
curl -X POST http://localhost:7860/gpu/unload

# 重新載入模型
curl -X POST http://localhost:7860/gpu/load
```

### API 文件

Swagger UI：http://localhost:7860/docs

### MCP 服務（Claude Desktop）

在 `claude_desktop_config.json` 中新增：

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

---

## 🏗️ 技術棧

| 元件 | 技術 |
|------|------|
| 模型 | GLM-ASR-Nano-2512 (1.5B) |
| 後端 | Flask + Flask-SocketIO |
| 前端 | HTML5 + Vanilla JS |
| 容器 | Docker + NVIDIA CUDA |
| API 文件 | Flasgger (Swagger) |
| MCP | FastMCP |

---

## 📊 效能對比

GLM-ASR-Nano 在同類模型中錯誤率最低（4.10）：

![Benchmark](resources/bench.png)

---

## 🤝 參與貢獻

1. Fork 本儲存庫
2. 建立特性分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing`)
5. 提交 Pull Request

---

## 📝 更新日誌

### v1.0.0 (2024-12-14)
- ✅ 長音訊分段轉錄
- ✅ 4 語言 Web 介面
- ✅ REST API + Swagger 文件
- ✅ MCP 服務整合
- ✅ Docker 一體化映像

---

## 📄 開源協議

[Apache License 2.0](LICENSE)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=neosun100/glm-asr&type=Date)](https://star-history.com/#neosun100/glm-asr)

## 📱 關注公眾號

<img src="https://img.aws.xin/uPic/扫码_搜索联合传播样式-标准色版.png" width="300"/>
