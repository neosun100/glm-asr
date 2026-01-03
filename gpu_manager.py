"""GPU 资源管理器 - 模型常驻显存，手动卸载"""
import threading
import logging
import torch
from pathlib import Path
from transformers import AutoConfig, AutoModelForSeq2SeqLM, AutoProcessor
from transformers.models import GlmAsrProcessor, GlmAsrConfig, GlmAsrForConditionalGeneration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GPUManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.model = None
        self.processor = None
        self.config = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.checkpoint_dir = None
        self.lock = threading.Lock()

    def load(self, checkpoint_dir: str = "zai-org/GLM-ASR-Nano-2512"):
        """加载模型到 GPU（启动时调用）"""
        with self.lock:
            if self.model is not None:
                logger.info("模型已加载")
                return True
            
            logger.info(f"正在加载模型: {checkpoint_dir}")
            self.checkpoint_dir = checkpoint_dir
            
            self.processor: GlmAsrProcessor = AutoProcessor.from_pretrained(checkpoint_dir)
            self.config: GlmAsrConfig = AutoConfig.from_pretrained(checkpoint_dir, trust_remote_code=True)
            self.model: GlmAsrForConditionalGeneration = AutoModelForSeq2SeqLM.from_pretrained(
                checkpoint_dir,
                dtype="auto", # 需要根据显卡选择是否有硬件加速的dtype, 否则auto默认就是bf16, 若是不支持就很慢
                device_map="auto",
            )
            self.model.eval()
            
            logger.info(f"模型加载完成，设备: {self.device}")
            return True

    def unload(self):
        """手动卸载模型"""
        with self.lock:
            if self.model is None:
                return {"status": "already_unloaded"}
            
            del self.model
            self.model = None
            torch.cuda.empty_cache()
            logger.info("模型已卸载，显存已释放")
            return {"status": "unloaded"}

    def reload(self):
        """重新加载模型"""
        self.unload()
        return self.load(self.checkpoint_dir or "zai-org/GLM-ASR-Nano-2512")

    def get_status(self) -> dict:
        """获取 GPU 状态"""
        status = {
            "model_loaded": self.model is not None,
            "device": self.device,
            "checkpoint": self.checkpoint_dir,
        }
        if torch.cuda.is_available():
            status["gpu_memory_used_mb"] = torch.cuda.memory_allocated() / 1024 / 1024
            status["gpu_memory_total_mb"] = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024
        return status

    def transcribe(self, audio_path: str, max_new_tokens: int = 512, progress_callback=None) -> str:
        """转录音频 - VAD 智能分段，支持任意长度音频
        
        Args:
            audio_path: 音频文件路径
            max_new_tokens: 每段最大生成 token 数
            progress_callback: 进度回调函数 (current, total, segment_duration, text)
        """
        if self.model is None:
            raise RuntimeError("模型未加载，请先加载模型")
        
        import torchaudio
        import tempfile
        import os
        from vad_segmenter import smart_segment
        
        with self.lock:
            wav, sr = torchaudio.load(str(audio_path))
            wav = wav[:1, :]
            # sr, sampling rate 统一为 16k
            if sr != 16000:
                wav = torchaudio.transforms.Resample(sr, 16000)(wav)
                sr = 16000
            
            duration = wav.shape[1] / sr
            logger.info(f"音频时长: {duration:.1f}s")
            
            if duration <= 25:
                if progress_callback:
                    progress_callback(1, 1, duration, None)
                inputs = self.processor.apply_transcription_request(str(audio_path))
                inputs = inputs.to(self.model.device, dtype=self.model.dtype)
                with torch.inference_mode():
                    outputs = self.model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens)
                decoded = self.processor.batch_decode(outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)
                text = decoded[0].strip() if decoded else ""
                if progress_callback:
                    progress_callback(1, 1, duration, text)
                return text
            
            segments = smart_segment(wav[0], sr=sr, max_duration=25.0, min_duration=2.0)
            if not segments:
                return ""
            
            total = len(segments)
            results = []
            for i, (start, end) in enumerate(segments):
                seg_dur = (end - start) / sr
                if progress_callback:
                    progress_callback(i + 1, total, seg_dur, None)
                
                chunk = wav[:, start:end]
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    tmp_path = f.name
                    torchaudio.save(tmp_path, chunk, sr)
                
                try:
                    inputs = self.processor.apply_transcription_request(tmp_path)
                    inputs = inputs.to(self.model.device, dtype=self.model.dtype)
                    with torch.inference_mode():
                        outputs = self.model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens)
                    decoded = self.processor.batch_decode(outputs[:, inputs.input_ids.shape[1]:], skip_special_tokens=True)
                    text = decoded[0].strip() if decoded else ""
                    if text:
                        results.append(text)
                        if progress_callback:
                            progress_callback(i + 1, total, seg_dur, text)
                finally:
                    os.unlink(tmp_path)
            
            return ''.join(results)


# 全局单例
gpu_manager = GPUManager()
