const i18n = {
    en: {
        gpu_status: "GPU Status", model: "Model", memory: "Memory", device: "Device",
        load: "Load Model", unload: "Unload", upload_audio: "Upload Audio",
        drop_hint: "Click or drag audio file here", parameters: "Parameters",
        max_tokens: "Max New Tokens", transcribe: "Transcribe", result: "Result",
        copy: "Copy", result_placeholder: "Transcription result will appear here...",
        loaded: "Loaded", unloaded: "Unloaded", processing: "Processing...",
        copied: "Copied!", error: "Error", file_selected: "Selected: "
    },
    "zh-CN": {
        gpu_status: "GPU 状态", model: "模型", memory: "显存", device: "设备",
        load: "加载模型", unload: "卸载", upload_audio: "上传音频",
        drop_hint: "点击或拖拽音频文件到此处", parameters: "参数设置",
        max_tokens: "最大生成 Token", transcribe: "开始转录", result: "转录结果",
        copy: "复制", result_placeholder: "转录结果将显示在这里...",
        loaded: "已加载", unloaded: "未加载", processing: "处理中...",
        copied: "已复制!", error: "错误", file_selected: "已选择: "
    },
    "zh-TW": {
        gpu_status: "GPU 狀態", model: "模型", memory: "顯存", device: "設備",
        load: "載入模型", unload: "卸載", upload_audio: "上傳音頻",
        drop_hint: "點擊或拖拽音頻文件到此處", parameters: "參數設置",
        max_tokens: "最大生成 Token", transcribe: "開始轉錄", result: "轉錄結果",
        copy: "複製", result_placeholder: "轉錄結果將顯示在這裡...",
        loaded: "已載入", unloaded: "未載入", processing: "處理中...",
        copied: "已複製!", error: "錯誤", file_selected: "已選擇: "
    },
    ja: {
        gpu_status: "GPU ステータス", model: "モデル", memory: "メモリ", device: "デバイス",
        load: "モデル読込", unload: "アンロード", upload_audio: "音声アップロード",
        drop_hint: "クリックまたはドラッグしてファイルを選択", parameters: "パラメータ",
        max_tokens: "最大トークン数", transcribe: "文字起こし", result: "結果",
        copy: "コピー", result_placeholder: "文字起こし結果がここに表示されます...",
        loaded: "読込済", unloaded: "未読込", processing: "処理中...",
        copied: "コピーしました!", error: "エラー", file_selected: "選択済: "
    }
};

let currentLang = localStorage.getItem('lang') || 'en';
let selectedFile = null;

function setLang(lang) {
    currentLang = lang;
    localStorage.setItem('lang', lang);
    document.getElementById('lang').value = lang;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (i18n[lang][key]) {
            if (el.tagName === 'INPUT') el.placeholder = i18n[lang][key];
            else el.textContent = i18n[lang][key];
        }
    });
}

function t(key) { return i18n[currentLang][key] || key; }

async function fetchStatus() {
    try {
        const res = await fetch('/gpu/status');
        const data = await res.json();
        const status = document.getElementById('modelStatus');
        status.textContent = data.model_loaded ? t('loaded') : t('unloaded');
        status.className = 'value ' + (data.model_loaded ? 'loaded' : 'unloaded');
        document.getElementById('memoryUsed').textContent = data.gpu_memory_used_mb ? `${Math.round(data.gpu_memory_used_mb)} MB` : '-';
        document.getElementById('deviceInfo').textContent = data.device || '-';
        document.getElementById('loadBtn').disabled = data.model_loaded;
        document.getElementById('unloadBtn').disabled = !data.model_loaded;
    } catch (e) { console.error(e); }
}

async function loadModel() {
    document.getElementById('loadBtn').disabled = true;
    document.getElementById('statusMsg').textContent = t('processing');
    await fetch('/gpu/load', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    await fetchStatus();
    document.getElementById('statusMsg').textContent = '';
}

async function unloadModel() {
    document.getElementById('unloadBtn').disabled = true;
    await fetch('/gpu/unload', { method: 'POST' });
    await fetchStatus();
}

function handleFile(file) {
    if (!file) return;
    selectedFile = file;
    const badge = document.getElementById('fileBadge');
    badge.textContent = t('file_selected') + file.name + ` (${(file.size/1024/1024).toFixed(2)} MB)`;
    badge.classList.add('show');
}

function initUpload() {
    const zone = document.getElementById('uploadZone');
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('dragover'); handleFile(e.dataTransfer.files[0]); });
}

async function transcribe() {
    if (!selectedFile) { alert('Please select a file'); return; }
    const btn = document.getElementById('transcribeBtn');
    const progress = document.getElementById('progress');
    const progressBar = document.getElementById('progressBar');
    const statusMsg = document.getElementById('statusMsg');
    const result = document.getElementById('result');
    
    btn.disabled = true;
    progress.classList.add('show');
    progressBar.style.width = '30%';
    statusMsg.textContent = t('processing');
    result.textContent = '';
    result.classList.add('empty');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('max_new_tokens', document.getElementById('maxTokens').value);
    
    try {
        const res = await fetch('/api/transcribe', { method: 'POST', body: formData });
        progressBar.style.width = '90%';
        const data = await res.json();
        progressBar.style.width = '100%';
        
        if (data.error) throw new Error(data.error);
        result.textContent = data.text || '';
        result.classList.toggle('empty', !data.text);
        statusMsg.textContent = '';
    } catch (e) {
        result.textContent = t('error') + ': ' + e.message;
    } finally {
        btn.disabled = false;
        statusMsg.textContent = '';
        setTimeout(() => progress.classList.remove('show'), 500);
    }
}

function copyResult() {
    const text = document.getElementById('result').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        const orig = btn.textContent;
        btn.textContent = t('copied');
        setTimeout(() => btn.textContent = orig, 1500);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setLang(currentLang);
    initUpload();
    fetchStatus();
    setInterval(fetchStatus, 5000);
});
