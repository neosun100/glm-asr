# GLM-ASR MCP 使用指南

GLM-ASR 提供 MCP (Model Context Protocol) 接口，支持程序化调用语音识别功能。

## 快速开始

### 1. 配置 MCP 客户端

在你的 MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "glm-asr": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/GLM-ASR",
      "env": {
        "MODEL_CHECKPOINT": "zai-org/GLM-ASR-Nano-2512"
      }
    }
  }
}
```

### 2. Docker 环境配置

如果使用 Docker，配置如下：

```json
{
  "mcpServers": {
    "glm-asr": {
      "command": "docker",
      "args": ["exec", "-i", "glm-asr", "python", "mcp_server.py"]
    }
  }
}
```

## 可用工具

### transcribe

转录音频文件为文本。

**参数：**
| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| audio_path | string | ✅ | - | 音频文件路径 |
| max_new_tokens | int | ❌ | 128 | 最大生成 token 数 |

**示例：**
```python
result = await mcp.call_tool("transcribe", {
    "audio_path": "/path/to/audio.wav",
    "max_new_tokens": 256
})
# 返回: {"status": "success", "text": "转录结果..."}
```

### get_gpu_status

获取 GPU 和模型状态。

**返回：**
```json
{
  "model_loaded": true,
  "device": "cuda",
  "checkpoint": "zai-org/GLM-ASR-Nano-2512",
  "gpu_memory_used_mb": 3200,
  "gpu_memory_total_mb": 24576
}
```

### load_model

加载模型到 GPU。

**参数：**
| 参数 | 类型 | 必需 | 默认值 |
|------|------|------|--------|
| checkpoint | string | ❌ | zai-org/GLM-ASR-Nano-2512 |

### unload_model

卸载模型，释放 GPU 显存。

### reload_model

重新加载模型。

## 与 API 的区别

| 特性 | API | MCP |
|------|-----|-----|
| 访问方式 | HTTP/WebSocket | 进程间通信 |
| 适用场景 | Web 应用、远程调用 | AI Agent、本地集成 |
| 文件传输 | 上传文件 | 本地路径 |
| 延迟 | 较高（网络） | 较低（本地） |

## 使用示例

### Claude Desktop 集成

```json
{
  "mcpServers": {
    "glm-asr": {
      "command": "python",
      "args": ["/path/to/GLM-ASR/mcp_server.py"]
    }
  }
}
```

然后在 Claude 中：
> 请帮我转录这个音频文件：/home/user/meeting.wav

### Python 客户端

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        cwd="/path/to/GLM-ASR"
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 转录音频
            result = await session.call_tool(
                "transcribe",
                {"audio_path": "/path/to/audio.wav"}
            )
            print(result)
```

## 注意事项

1. MCP 服务器启动时会自动加载模型
2. 模型常驻 GPU，不会自动卸载
3. 如需释放显存，请调用 `unload_model` 工具
4. 支持的音频格式：wav, mp3, flac, m4a, ogg
