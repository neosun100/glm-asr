FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV HF_HOME=/app/cache
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg libsndfile1 \
    git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir git+https://github.com/huggingface/transformers.git

COPY . .
RUN mkdir -p static cache

# 预下载模型
RUN python3 -c "from huggingface_hub import snapshot_download; snapshot_download('zai-org/GLM-ASR-Nano-2512', cache_dir='/app/cache')"

EXPOSE 7860

CMD ["python3", "main.py"]
