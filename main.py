"""FastAPI 主服务 - 异步支持 + SSE 进度推送"""
import os
import json
import asyncio
import tempfile
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from gpu_manager import gpu_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'webm'}

# 全局进度
progress_state = {"current": 0, "total": 0, "text": "", "done": False}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时加载模型
    logger.info("启动时加载模型...")
    checkpoint = os.environ.get('MODEL_CHECKPOINT', 'zai-org/GLM-ASR-Nano-2512')
    gpu_manager.load(checkpoint)
    yield
    # 关闭时清理
    gpu_manager.unload()


app = FastAPI(
    title="GLM-ASR API",
    description="""
## 🎯 GLM-ASR 语音识别服务

基于 GLM-ASR-Nano-2512 模型的高精度语音转文字服务。

### ✨ 特性
- 支持 17 种语言（中文、英文、粤语、日语、韩语等）
- 智能 VAD 分段，支持任意长度音频
- 双模式 API：同步返回 / SSE 流式返回
- GPU 显存管理，支持手动加载/卸载模型

### 📦 支持格式
`wav`, `mp3`, `flac`, `m4a`, `ogg`, `webm`

### 🔗 相关链接
- [GitHub](https://github.com/neosun100/glm-asr)
- [Docker Hub](https://hub.docker.com/r/neosun/glm-asr)
""",
    version="2.0.1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ==================== 静态文件 ====================
@app.get("/", include_in_schema=False)
async def index():
    return FileResponse("static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================== 系统 API ====================
@app.get("/health", tags=["系统"], summary="健康检查",
    description="检查服务是否正常运行，以及模型是否已加载。",
    responses={200: {"description": "服务状态", "content": {"application/json": {"example": {"status": "ok", "model_loaded": True}}}}})
async def health():
    return {"status": "ok", "model_loaded": gpu_manager.model is not None}


# ==================== GPU 管理 ====================
@app.get("/gpu/status", tags=["GPU管理"], summary="获取GPU状态",
    description="获取当前 GPU 显存使用情况和模型加载状态。",
    responses={200: {"description": "GPU状态信息", "content": {"application/json": {"example": {
        "model_loaded": True, "device": "cuda", "checkpoint": "zai-org/GLM-ASR-Nano-2512",
        "gpu_memory_used_mb": 4320.5, "gpu_memory_total_mb": 24576.0}}}}})
async def gpu_status():
    return gpu_manager.get_status()


@app.post("/gpu/load", tags=["GPU管理"], summary="加载模型",
    description="将模型加载到 GPU 显存。启动时会自动加载，一般无需手动调用。",
    responses={200: {"description": "加载成功", "content": {"application/json": {"example": {"status": "loaded", "model_loaded": True}}}}})
async def gpu_load():
    gpu_manager.load('zai-org/GLM-ASR-Nano-2512')
    return {"status": "loaded", **gpu_manager.get_status()}


@app.post("/gpu/unload", tags=["GPU管理"], summary="卸载模型",
    description="从 GPU 显存中卸载模型，释放显存。需要再次使用时调用 `/gpu/load` 重新加载。",
    responses={200: {"description": "卸载成功", "content": {"application/json": {"example": {"status": "unloaded"}}}}})
async def gpu_unload():
    return gpu_manager.unload()


# ==================== 转录 API ====================
@app.post("/api/transcribe", tags=["语音转录"], summary="同步转录（推荐短音频）",
    description="""
将音频文件转录为文字，等待处理完成后一次性返回结果。

**适用场景：** 短音频（< 1分钟）

**处理流程：**
1. 上传音频文件
2. 服务器处理（短音频直接处理，长音频自动 VAD 分段）
3. 返回完整转录结果

**注意：** 长音频处理时间较长，可能导致请求超时，建议使用 `/api/transcribe/stream` 流式接口。
""",
    responses={
        200: {"description": "转录成功", "content": {"application/json": {"example": {"status": "success", "text": "这是转录出来的文字内容。"}}}},
        400: {"description": "无效的文件格式", "content": {"application/json": {"example": {"detail": "无效的文件格式"}}}},
        503: {"description": "模型未加载", "content": {"application/json": {"example": {"detail": "模型未加载，请先加载模型"}}}}
    })
async def transcribe(
    file: UploadFile = File(..., description="音频文件（支持 wav/mp3/flac/m4a/ogg/webm）"),
    max_new_tokens: int = Form(512, description="最大生成 token 数，影响输出长度，建议 256-1024", ge=1, le=2048)
):
    if not file.filename or not allowed_file(file.filename):
        raise HTTPException(400, "无效的文件格式")
    
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    try:
        result = gpu_manager.transcribe(filepath, max_new_tokens)
        return {"status": "success", "text": result}
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, f"转录失败: {str(e)}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.post("/api/transcribe/stream", tags=["语音转录"], summary="SSE 流式转录（推荐长音频）",
    description="""
使用 Server-Sent Events (SSE) 流式返回转录进度和结果，避免长音频处理超时。

**适用场景：** 长音频（> 1分钟）

**SSE 事件类型：**

| type | 说明 | 数据示例 |
|------|------|----------|
| `start` | 开始处理 | `{}` |
| `progress` | 处理进度 | `{"current": 3, "total": 10, "duration": 22.5}` |
| `partial` | 分段结果 | `{"text": "这是第三段的文字..."}` |
| `heartbeat` | 心跳保活 | `{}` |
| `done` | 处理完成 | `{"text": "完整的转录结果..."}` |
| `error` | 处理出错 | `{"message": "错误信息"}` |

**调用示例（curl）：**
```bash
curl -X POST http://localhost:7860/api/transcribe/stream \\
  -F "file=@long_audio.mp3" \\
  -F "max_new_tokens=512"
```

**调用示例（JavaScript）：**
```javascript
const formData = new FormData();
formData.append('file', audioFile);
formData.append('max_new_tokens', 512);

const response = await fetch('/api/transcribe/stream', {
  method: 'POST',
  body: formData
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  // 解析 SSE 数据: data: {"type": "progress", ...}
  console.log(chunk);
}
```
""",
    responses={
        200: {"description": "SSE 流式响应", "content": {"text/event-stream": {"example": 'data: {"type": "progress", "current": 1, "total": 5, "duration": 20.5}\n\ndata: {"type": "partial", "text": "转录文字..."}\n\ndata: {"type": "done", "text": "完整结果"}'}}},
        400: {"description": "无效的文件格式"}
    })
async def transcribe_stream(
    file: UploadFile = File(..., description="音频文件（支持 wav/mp3/flac/m4a/ogg/webm）"),
    max_new_tokens: int = Form(512, description="最大生成 token 数", ge=1, le=2048)
):
    if not file.filename or not allowed_file(file.filename):
        raise HTTPException(400, "无效的文件格式")
    
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)
    
    async def generate():
        loop = asyncio.get_event_loop()
        progress_queue = asyncio.Queue()
        
        def on_progress(current, total, duration, text):
            asyncio.run_coroutine_threadsafe(
                progress_queue.put({"current": current, "total": total, "duration": duration, "text": text}),
                loop
            )
        
        async def do_transcribe():
            try:
                result = await loop.run_in_executor(
                    None, lambda: gpu_manager.transcribe(filepath, max_new_tokens, on_progress)
                )
                await progress_queue.put({"done": True, "result": result})
            except Exception as e:
                await progress_queue.put({"error": str(e)})
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        task = asyncio.create_task(do_transcribe())
        yield f"data: {json.dumps({'type': 'start'})}\n\n"
        
        while True:
            try:
                msg = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                if "error" in msg:
                    yield f"data: {json.dumps({'type': 'error', 'message': msg['error']})}\n\n"
                    break
                elif "done" in msg:
                    yield f"data: {json.dumps({'type': 'done', 'text': msg['result']})}\n\n"
                    break
                else:
                    yield f"data: {json.dumps({'type': 'progress', 'current': msg['current'], 'total': msg['total'], 'duration': round(msg['duration'], 1)})}\n\n"
                    if msg['text']:
                        yield f"data: {json.dumps({'type': 'partial', 'text': msg['text']})}\n\n"
            except asyncio.TimeoutError:
                if task.done():
                    break
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        
        await task
    
    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 7860))
    logger.info(f"服务启动: http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
