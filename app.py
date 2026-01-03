"""Flask 主服务 - UI + API + WebSocket"""
import os
import json
import tempfile
import traceback
import logging
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flasgger import Swagger
from werkzeug.utils import secure_filename

from gpu_manager import gpu_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Swagger 配置
swagger_config = {
    "headers": [],
    "specs": [{"endpoint": "apispec", "route": "/apispec.json"}],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}
swagger = Swagger(app, config=swagger_config, template={
    "info": {
        "title": "GLM-ASR API",
        "description": "语音识别服务 API",
        "version": "1.0.0"
    }
})

UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'ogg', 'webm'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== UI ====================
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ==================== API ====================
@app.route('/health', methods=['GET'])
def health():
    """健康检查
    ---
    tags: [System]
    responses:
      200:
        description: 服务正常
    """
    return jsonify({"status": "ok", "model_loaded": gpu_manager.model is not None})


@app.route('/gpu/status', methods=['GET'])
def gpu_status():
    """获取 GPU 状态
    ---
    tags: [GPU]
    responses:
      200:
        description: GPU 状态信息
    """
    return jsonify(gpu_manager.get_status())


@app.route('/gpu/load', methods=['POST'])
def gpu_load():
    """加载模型到 GPU
    ---
    tags: [GPU]
    responses:
      200:
        description: 加载成功
    """
    checkpoint = 'zai-org/GLM-ASR-Nano-2512'
    try:
        data = request.get_json(force=True, silent=True)
        if data and 'checkpoint' in data:
            checkpoint = data['checkpoint']
    except:
        pass
    gpu_manager.load(checkpoint)
    return jsonify({"status": "loaded", **gpu_manager.get_status()})


@app.route('/gpu/unload', methods=['POST'])
def gpu_unload():
    """卸载模型释放显存
    ---
    tags: [GPU]
    responses:
      200:
        description: 卸载成功
    """
    result = gpu_manager.unload()
    return jsonify(result)


@app.route('/gpu/reload', methods=['POST'])
def gpu_reload():
    """重新加载模型
    ---
    tags: [GPU]
    responses:
      200:
        description: 重载成功
    """
    gpu_manager.reload()
    return jsonify({"status": "reloaded", **gpu_manager.get_status()})


@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    """转录音频文件
    ---
    tags: [ASR]
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: 音频文件
      - name: max_new_tokens
        in: formData
        type: integer
        default: 128
        description: 最大生成 token 数
    responses:
      200:
        description: 转录结果
    """
    if 'file' not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "无效的文件格式"}), 400
    
    max_new_tokens = int(request.form.get('max_new_tokens', 512))
    
    # 保存临时文件
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    try:
        result = gpu_manager.transcribe(filepath, max_new_tokens)
        return jsonify({"text": result, "status": "success"})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"转录失败: {e}")
        return jsonify({"error": f"转录失败: {str(e)}"}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


# 全局进度状态
transcribe_progress = {"current": 0, "total": 0, "text": ""}

@app.route('/api/transcribe/progress', methods=['GET'])
def get_progress():
    """获取转录进度"""
    return jsonify(transcribe_progress)


@app.route('/api/transcribe/long', methods=['POST'])
def transcribe_long():
    """长音频转录（带进度）"""
    global transcribe_progress
    
    if 'file' not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "无效的文件格式"}), 400
    
    max_new_tokens = int(request.form.get('max_new_tokens', 512))
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    transcribe_progress["current"] = 0
    transcribe_progress["total"] = 0
    transcribe_progress["text"] = ""
    
    def on_progress(current, total, duration, text):
        transcribe_progress["current"] = current
        transcribe_progress["total"] = total
        if text:
            transcribe_progress["text"] += text
    
    try:
        result = gpu_manager.transcribe(filepath, max_new_tokens, on_progress)
        transcribe_progress["current"] = 0
        transcribe_progress["total"] = 0
        transcribe_progress["text"] = ""
        return jsonify({"text": result, "status": "success"})
    except Exception as e:
        transcribe_progress["current"] = 0
        transcribe_progress["total"] = 0
        transcribe_progress["text"] = ""
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/transcribe/stream', methods=['POST'])
def transcribe_stream():
    """流式转录音频（SSE）- 带进度
    ---
    tags: [ASR]
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
    responses:
      200:
        description: SSE 流式响应
    """
    if 'file' not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "无效的文件格式"}), 400
    
    max_new_tokens = int(request.form.get('max_new_tokens', 128))
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    def generate():
        progress_data = []
        
        def on_progress(current, total, seg_dur, text):
            progress_data.append((current, total, seg_dur, text))
        
        try:
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            # 使用线程执行转录，主线程发送进度
            import threading
            result_holder = [None]
            error_holder = [None]
            
            def do_transcribe():
                try:
                    result_holder[0] = gpu_manager.transcribe(filepath, max_new_tokens, on_progress)
                except Exception as e:
                    error_holder[0] = str(e)
                    # 打印出错误栈以便调试
                    traceback.print_exception(e)
            
            thread = threading.Thread(target=do_transcribe)
            thread.start()
            
            sent_count = 0
            while thread.is_alive() or sent_count < len(progress_data):
                while sent_count < len(progress_data):
                    cur, tot, dur, txt = progress_data[sent_count]
                    yield f"data: {json.dumps({'type': 'progress', 'current': cur, 'total': tot, 'duration': round(dur, 1)})}\n\n"
                    if txt:
                        yield f"data: {json.dumps({'type': 'partial', 'text': txt})}\n\n"
                    sent_count += 1
                if thread.is_alive():
                    import time
                    time.sleep(0.1)
            
            thread.join()
            
            if error_holder[0]:
                yield f"data: {json.dumps({'type': 'error', 'message': error_holder[0]})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'done', 'text': result_holder[0] or ''})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return Response(generate(), mimetype='text/event-stream')


# ==================== WebSocket ====================
@socketio.on('connect')
def handle_connect():
    emit('status', gpu_manager.get_status())


@socketio.on('transcribe')
def handle_transcribe(data):
    """WebSocket 转录"""
    try:
        filepath = data.get('file_path')
        max_new_tokens = data.get('max_new_tokens', 128)
        
        if not filepath or not os.path.exists(filepath):
            emit('error', {'error': '文件不存在'})
            return
        
        emit('start', {'status': 'processing'})
        result = gpu_manager.transcribe(filepath, max_new_tokens)
        emit('result', {'text': result})
        emit('done', {'status': 'completed'})
    except Exception as e:
        emit('error', {'error': str(e)})


@socketio.on('gpu_status')
def handle_gpu_status():
    emit('status', gpu_manager.get_status())


@socketio.on('gpu_unload')
def handle_gpu_unload():
    result = gpu_manager.unload()
    emit('status', {**result, **gpu_manager.get_status()})


@socketio.on('gpu_load')
def handle_gpu_load(data=None):
    checkpoint = data.get('checkpoint', 'zai-org/GLM-ASR-Nano-2512') if data else 'zai-org/GLM-ASR-Nano-2512'
    gpu_manager.load(checkpoint)
    emit('status', gpu_manager.get_status())


def main():
    port = int(os.environ.get('PORT', 7860))
    checkpoint = os.environ.get('MODEL_CHECKPOINT', 'zai-org/GLM-ASR-Nano-2512')
    
    # 启动时立即加载模型
    logger.info("启动时加载模型...")
    gpu_manager.load(checkpoint)
    
    logger.info(f"服务启动: http://0.0.0.0:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
