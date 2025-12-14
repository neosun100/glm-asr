"""MCP 服务器 - GLM-ASR 工具"""
import os
from fastmcp import FastMCP
from gpu_manager import gpu_manager

mcp = FastMCP("glm-asr")


@mcp.tool()
def transcribe(audio_path: str, max_new_tokens: int = 128) -> dict:
    """
    转录音频文件为文本
    
    Args:
        audio_path: 音频文件路径（支持 wav/mp3/flac/m4a/ogg）
        max_new_tokens: 最大生成 token 数，默认 128
    
    Returns:
        转录结果，包含 text 字段
    """
    if not os.path.exists(audio_path):
        return {"status": "error", "error": f"文件不存在: {audio_path}"}
    
    try:
        result = gpu_manager.transcribe(audio_path, max_new_tokens)
        return {"status": "success", "text": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def get_gpu_status() -> dict:
    """
    获取 GPU 和模型状态
    
    Returns:
        GPU 状态信息，包含显存使用、模型加载状态等
    """
    return gpu_manager.get_status()


@mcp.tool()
def load_model(checkpoint: str = "zai-org/GLM-ASR-Nano-2512") -> dict:
    """
    加载模型到 GPU
    
    Args:
        checkpoint: 模型路径或 HuggingFace 模型 ID
    
    Returns:
        加载状态
    """
    try:
        gpu_manager.load(checkpoint)
        return {"status": "loaded", **gpu_manager.get_status()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def unload_model() -> dict:
    """
    卸载模型，释放 GPU 显存
    
    Returns:
        卸载状态
    """
    return gpu_manager.unload()


@mcp.tool()
def reload_model() -> dict:
    """
    重新加载模型
    
    Returns:
        重载状态
    """
    gpu_manager.reload()
    return {"status": "reloaded", **gpu_manager.get_status()}


if __name__ == "__main__":
    # 启动时加载模型
    checkpoint = os.environ.get('MODEL_CHECKPOINT', 'zai-org/GLM-ASR-Nano-2512')
    gpu_manager.load(checkpoint)
    mcp.run()
