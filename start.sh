#!/bin/bash
set -e

echo "=========================================="
echo "  GLM-ASR Docker 启动脚本"
echo "=========================================="

# 检查 nvidia-docker
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ 错误: nvidia-smi 未找到，请确保已安装 NVIDIA 驱动"
    exit 1
fi

if ! docker info 2>/dev/null | grep -q "Runtimes.*nvidia"; then
    echo "⚠️  警告: nvidia-docker runtime 可能未配置"
fi

# 自动选择显存占用最少的 GPU
echo "🔍 检测 GPU..."
GPU_ID=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | \
         sort -t',' -k2 -n | head -1 | cut -d',' -f1 | tr -d ' ')

if [ -z "$GPU_ID" ]; then
    echo "❌ 错误: 未检测到可用 GPU"
    exit 1
fi

GPU_MEM=$(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits -i $GPU_ID)
echo "✅ 选择 GPU $GPU_ID (显存使用: $GPU_MEM MB)"

# 设置环境变量
export NVIDIA_VISIBLE_DEVICES=$GPU_ID

# 加载 .env 文件（如果存在）
if [ -f .env ]; then
    echo "📄 加载 .env 配置..."
    export $(grep -v '^#' .env | xargs)
fi

# 设置默认端口
PORT=${PORT:-7860}

# 创建缓存目录
mkdir -p cache

# 构建并启动
echo "🚀 启动服务..."
docker compose up --build -d

# 等待服务启动
echo "⏳ 等待服务启动..."
for i in {1..60}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo ""
        echo "=========================================="
        echo "✅ 服务启动成功!"
        echo "=========================================="
        echo "🌐 UI 界面:    http://0.0.0.0:$PORT"
        echo "📚 API 文档:   http://0.0.0.0:$PORT/docs"
        echo "💻 GPU:        $GPU_ID"
        echo "=========================================="
        echo ""
        echo "📝 常用命令:"
        echo "   查看日志:   docker compose logs -f"
        echo "   停止服务:   docker compose down"
        echo "   重启服务:   docker compose restart"
        echo "=========================================="
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "⚠️  服务启动超时，请检查日志: docker compose logs"
exit 1
