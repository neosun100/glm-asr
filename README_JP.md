[English](README.md) | [简体中文](README_CN.md) | [繁體中文](README_TW.md) | [日本語](README_JP.md)

<div align="center">
<img src="resources/logo.svg" width="20%"/>

# GLM-ASR

[![Docker](https://img.shields.io/badge/Docker-neosun%2Fglm--asr-blue?logo=docker)](https://hub.docker.com/r/neosun/glm-asr)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)

**GLM-ASR-Nano ベースのオールインワン音声認識サービス**

Web UI • REST API • MCP サーバー • 長時間音声対応

</div>

---

## ✨ 機能

- 🎯 **高精度認識** - GLM-ASR-Nano-2512 (1.5B) 搭載、Whisper V3 を上回る性能
- 🌍 **17言語対応** - 中国語、英語、広東語、日本語、韓国語など
- 🎤 **長時間音声** - チャンク処理で音声長制限なし
- 🖥️ **Web UI** - モダンなダークテーマ、4言語対応
- 🔌 **REST API** - 完全な API、Swagger ドキュメント
- 🤖 **MCP サーバー** - Claude Desktop 統合対応
- 💾 **GPU 管理** - モデルの手動ロード/アンロード
- 🐳 **Docker 対応** - ワンコマンドデプロイ

---

## 🚀 クイックスタート

### Docker（推奨）

```bash
docker run -d --gpus all -p 7860:7860 neosun/glm-asr:latest
```

アクセス：http://localhost:7860

### Docker Compose

```bash
git clone https://github.com/neosun100/glm-asr.git
cd glm-asr
docker compose up -d
```

---

## 📦 インストール

### 必要条件

- NVIDIA GPU（VRAM 6GB以上）
- Docker + NVIDIA Container Toolkit
- または：Python 3.10+、CUDA 12.x、FFmpeg

### 方法1：Docker

```bash
# イメージ取得
docker pull neosun/glm-asr:latest

# コンテナ起動
docker run -d \
  --name glm-asr \
  --gpus all \
  -p 7860:7860 \
  -v ./cache:/app/cache \
  neosun/glm-asr:latest

# ヘルスチェック
curl http://localhost:7860/health
```

### 方法2：ローカルインストール

```bash
# リポジトリクローン
git clone https://github.com/neosun100/glm-asr.git
cd glm-asr

# 依存関係インストール
pip install -r requirements.txt
sudo apt install ffmpeg

# サービス起動
python app.py
```

---

## ⚙️ 設定

### 環境変数

| 変数 | デフォルト | 説明 |
|------|------------|------|
| `MODEL_PATH` | `zai-org/GLM-ASR-Nano-2512` | HuggingFace モデルパス |
| `PORT` | `7860` | サービスポート |
| `HF_HOME` | `/app/cache` | モデルキャッシュディレクトリ |

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

## 📖 使用方法

### Web UI

http://localhost:7860 を開く：
- 音声ファイルをアップロード（wav/mp3/flac/m4a/ogg）
- 「文字起こし」をクリック
- 結果をコピー

### REST API

```bash
# 音声文字起こし
curl -X POST http://localhost:7860/api/transcribe \
  -F "file=@audio.mp3"

# GPU ステータス
curl http://localhost:7860/gpu/status

# モデルアンロード
curl -X POST http://localhost:7860/gpu/unload

# モデル再ロード
curl -X POST http://localhost:7860/gpu/load
```

### API ドキュメント

Swagger UI：http://localhost:7860/docs

### MCP サーバー（Claude Desktop）

`claude_desktop_config.json` に追加：

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

## 🏗️ 技術スタック

| コンポーネント | 技術 |
|----------------|------|
| モデル | GLM-ASR-Nano-2512 (1.5B) |
| バックエンド | Flask + Flask-SocketIO |
| フロントエンド | HTML5 + Vanilla JS |
| コンテナ | Docker + NVIDIA CUDA |
| API ドキュメント | Flasgger (Swagger) |
| MCP | FastMCP |

---

## 📊 ベンチマーク

GLM-ASR-Nano は同等モデル中最低のエラー率（4.10）を達成：

![Benchmark](resources/bench.png)

---

## 🤝 コントリビュート

1. リポジトリをフォーク
2. フィーチャーブランチ作成 (`git checkout -b feature/amazing`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing`)
5. Pull Request を作成

---

## 📝 変更履歴

### v1.0.0 (2024-12-14)
- ✅ 長時間音声チャンク文字起こし
- ✅ 4言語 Web UI
- ✅ REST API + Swagger ドキュメント
- ✅ MCP サーバー統合
- ✅ Docker オールインワンイメージ

---

## 📄 ライセンス

[Apache License 2.0](LICENSE)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=neosun100/glm-asr&type=Date)](https://star-history.com/#neosun100/glm-asr)

## 📱 フォローする

<img src="https://img.aws.xin/uPic/扫码_搜索联合传播样式-标准色版.png" width="300"/>
