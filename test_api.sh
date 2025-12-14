#!/bin/bash
# GLM-ASR API 测试脚本

PORT=${PORT:-7860}
BASE_URL="http://localhost:$PORT"

echo "=========================================="
echo "  GLM-ASR API 测试"
echo "=========================================="

# 1. 健康检查
echo -e "\n[1] 健康检查..."
curl -s "$BASE_URL/health" | python3 -m json.tool

# 2. GPU 状态
echo -e "\n[2] GPU 状态..."
curl -s "$BASE_URL/gpu/status" | python3 -m json.tool

# 3. 测试转录（使用示例文件）
if [ -f "examples/example_zh.wav" ]; then
    echo -e "\n[3] 测试转录 (中文)..."
    curl -s -X POST "$BASE_URL/api/transcribe" \
        -F "file=@examples/example_zh.wav" \
        -F "max_new_tokens=128" | python3 -m json.tool
fi

if [ -f "examples/example_en.wav" ]; then
    echo -e "\n[4] 测试转录 (英文)..."
    curl -s -X POST "$BASE_URL/api/transcribe" \
        -F "file=@examples/example_en.wav" \
        -F "max_new_tokens=128" | python3 -m json.tool
fi

echo -e "\n=========================================="
echo "  测试完成"
echo "=========================================="
