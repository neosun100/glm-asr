"""GPU 资源管理器 - 模型常驻显存，手动卸载"""
import threading
import logging
import torch
from pathlib import Path
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, WhisperFeatureExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WHISPER_FEAT_CFG = {
    "chunk_length": 30,
    "feature_extractor_type": "WhisperFeatureExtractor",
    "feature_size": 128,
    "hop_length": 160,
    "n_fft": 400,
    "n_samples": 480000,
    "nb_max_frames": 3000,
    "padding_side": "right",
    "padding_value": 0.0,
    "processor_class": "WhisperProcessor",
    "return_attention_mask": False,
    "sampling_rate": 16000,
}


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
        self.tokenizer = None
        self.feature_extractor = None
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
            
            self.tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
            self.feature_extractor = WhisperFeatureExtractor(**WHISPER_FEAT_CFG)
            self.config = AutoConfig.from_pretrained(checkpoint_dir, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                checkpoint_dir,
                config=self.config,
                torch_dtype=torch.bfloat16,
                trust_remote_code=True,
            ).to(self.device)
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

    def transcribe(self, audio_path: str, max_new_tokens: int = 512, max_duration: int = 1800) -> str:
        """转录音频 - 支持长音频分段处理
        
        Args:
            audio_path: 音频文件路径
            max_new_tokens: 每段最大生成 token 数
            max_duration: 最大音频时长（秒），默认 30 分钟，超过则截断
        """
        if self.model is None:
            raise RuntimeError("模型未加载，请先加载模型")
        
        import torchaudio
        from inference import build_prompt, prepare_inputs
        
        with self.lock:
            # 加载音频获取时长
            wav, sr = torchaudio.load(str(audio_path))
            wav = wav[:1, :]  # 只取单声道
            if sr != 16000:
                wav = torchaudio.transforms.Resample(sr, 16000)(wav)
            duration = wav.shape[1] / 16000
            
            # 超长音频截断保护
            if duration > max_duration:
                logger.warning(f"音频时长 {duration:.0f}s 超过限制 {max_duration}s，将截断处理")
                wav = wav[:, :max_duration * 16000]
                duration = max_duration
            
            # 短音频直接处理
            if duration <= 30:
                batch = build_prompt(
                    Path(audio_path),
                    self.tokenizer,
                    self.feature_extractor,
                    merge_factor=self.config.merge_factor,
                )
                model_inputs, prompt_len = prepare_inputs(batch, self.device)
                
                with torch.inference_mode():
                    generated = self.model.generate(
                        **model_inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=False,
                    )
                
                transcript_ids = generated[0, prompt_len:].cpu().tolist()
                return self.tokenizer.decode(transcript_ids, skip_special_tokens=True).strip()
            
            # 长音频分段处理
            import tempfile
            import os
            
            chunk_size = 25 * 16000  # 25秒一段，留余量
            results = []
            
            for start in range(0, wav.shape[1], chunk_size):
                chunk = wav[:, start:start + chunk_size]
                if chunk.shape[1] < 16000:  # 跳过不足1秒的片段
                    continue
                
                # 保存临时文件
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    tmp_path = f.name
                    torchaudio.save(tmp_path, chunk, 16000)
                
                try:
                    batch = build_prompt(
                        Path(tmp_path),
                        self.tokenizer,
                        self.feature_extractor,
                        merge_factor=self.config.merge_factor,
                    )
                    model_inputs, prompt_len = prepare_inputs(batch, self.device)
                    
                    with torch.inference_mode():
                        generated = self.model.generate(
                            **model_inputs,
                            max_new_tokens=max_new_tokens,
                            do_sample=False,
                        )
                    
                    transcript_ids = generated[0, prompt_len:].cpu().tolist()
                    text = self.tokenizer.decode(transcript_ids, skip_special_tokens=True).strip()
                    if text:
                        results.append(text)
                finally:
                    os.unlink(tmp_path)
            
            return ''.join(results)


# 全局单例
gpu_manager = GPUManager()
