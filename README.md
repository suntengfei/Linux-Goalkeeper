# Shell监控与AI运维助手

一个基于LLM的Shell操作监控系统，实时捕获Shell输入输出，提供AI运维辅助对话。

## 功能特性

- 🔍 **实时Shell监控**：使用 `script` 命令捕获Shell输入输出，实时同步到服务端
- 🖥️ **终端模拟显示**：Web端使用 xterm.js 终端模拟器，完美同步客户端显示（包括删除、光标移动等操作）
- 🤖 **AI运维助手**：基于LLM的智能对话，解答运维问题，分析命令输出
- 🔄 **多客户端支持**：支持多个Shell客户端同时连接，可切换查看不同客户端
- 🛡️ **安全认证**：Token认证机制，防止未授权访问
- 💬 **人机对话**：与AI助手交互获取运维建议
- 🔗 **稳定连接**：心跳机制保持连接稳定，断线自动重连

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`，配置LLM API：

```yaml
llm:
  backend: "openai"
  model: "deepseek-chat"  # 或其他模型
  api_key: "your-api-key"
  base_url: "https://api.deepseek.com/v1"
```

### 3. 启动服务器

```bash
# Linux/macOS
./start.sh

# Windows
start.bat

# 或直接运行
python -m server.main
```

服务器启动后：
- WebSocket服务：`ws://localhost:8765`
- Web界面：`http://localhost:8080`

### 4. 启动客户端

在需要监控的Linux机器上：

```bash
# 只需要这一个文件
python3 shell_monitor.py --server ws://SERVER_IP:8765 --token YOUR_TOKEN --shell
```

## 使用说明

### 客户端

```bash
# 方式一：使用启动脚本（推荐）
cd client
./run.sh ws://192.168.1.100:8765 your-token

# 方式二：直接运行Python
python3 shell_monitor.py --server ws://192.168.1.100:8765 --token your-token --shell

# 参数说明
--server, -s    WebSocket服务器地址（支持 ws:// 或 wss://）
--token, -t     认证Token
--shell         启动监控shell模式（启动一个新的shell会话并监控）
```

**客户端特性：**
- 客户端ID格式：`IP_shellPID`（如 `192.168.1.100_shell12345`）
- 心跳间隔：30秒
- 断线重连：指数退避（1-30秒）
- 日志文件：`/tmp/shell_monitor_<client_id>.log`

### Web界面

1. 打开浏览器访问 `http://localhost:8080`
2. 左侧显示Shell终端日志（实时同步，使用xterm.js渲染）
3. 右侧是AI运维助手对话区
4. 下拉菜单可以切换不同的客户端
5. 点击"复制日志"按钮可复制当前终端内容

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Linux Client                              │
│  script -f → typescript 文件（原始终端输出）                  │
│           → shell_monitor.py 读取并发送                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Server                                    │
│  WebSocket (8765) ◄────────► Web UI (8080)                  │
│                              │                               │
│                              ▼                               │
│                    LLM Backend (DeepSeek/OpenAI)             │
└─────────────────────────────────────────────────────────────┘
```

## 配置说明

### config.yaml

```yaml
server:
  host: "0.0.0.0"
  port: 8765          # WebSocket端口
  web_port: 8080      # Web界面端口
  heartbeat_timeout: 180

llm:
  backend: "openai"   # 支持: openai, ollama
  model: "deepseek-chat"
  api_key: ""         # API密钥
  base_url: "https://api.deepseek.com/v1"
  temperature: 0.7
  max_tokens: 2000

security:
  auth_enabled: true
  auth_tokens:
    - "123123"        # 认证Token列表
```

### 支持的LLM后端

| 后端 | 配置示例 |
|------|----------|
| DeepSeek | `backend: "openai"`, `base_url: "https://api.deepseek.com/v1"` |
| OpenAI | `backend: "openai"`, `base_url: "https://api.openai.com/v1"` |
| Ollama | `backend: "ollama"`, `base_url: "http://localhost:11434"` |

## 项目结构

```
Linux-Goalkeeper/
├── client/
│   ├── __init__.py
│   ├── run.sh              # 客户端启动脚本
│   └── shell_monitor.py    # 客户端主程序（PTY捕获模式）
├── server/
│   ├── __init__.py
│   ├── config.py           # 配置管理
│   ├── context_manager.py  # 敏感数据脱敏
│   ├── llm_backend.py      # LLM后端抽象
│   ├── logger.py           # 日志模块
│   ├── main.py             # 服务入口
│   ├── prompts.py          # AI提示词模板
│   ├── session_manager.py  # 会话管理
│   ├── websocket_server.py # WebSocket服务
│   └── webui.py            # Web界面服务
├── web/
│   ├── app.js              # 前端逻辑（xterm.js集成）
│   ├── index.html          # 页面结构
│   └── style.css           # 样式
├── tests/                  # 测试文件
├── docs/
│   └── DEPLOYMENT.md       # 详细部署文档
├── config.yaml             # 配置文件
├── requirements.txt        # Python依赖
├── Dockerfile              # Docker构建文件
├── docker-compose.yml      # Docker编排
├── start.sh                # Linux启动脚本
└── start.bat               # Windows启动脚本
```

## 安全建议

1. **生产环境启用WSS加密**：使用SSL证书加密WebSocket通信
2. **配置强认证Token**：使用随机生成的Token，避免简单密码
   ```bash
   openssl rand -hex 32
   ```
3. **API Key安全存储**：使用环境变量存储，不要明文写入配置文件
   ```bash
   export LLM_API_KEY="your-api-key"
   ```
4. **定期检查日志**：监控异常连接和操作
5. **防火墙配置**：只开放必要端口
   ```bash
   sudo ufw allow 8765/tcp  # WebSocket
   sudo ufw allow 8080/tcp  # Web界面
   ```

## 更多文档

详细的部署和配置说明请参考：
- [部署文档](docs/DEPLOYMENT.md) - 包含Docker部署、安全配置、故障排查等

## 技术栈

- **后端**：Python 3.8+, asyncio, websockets, aiohttp
- **前端**：原生JavaScript, xterm.js (终端模拟器)
- **LLM**：支持 OpenAI API 兼容的后端（DeepSeek, OpenAI, Ollama等）

## License

MIT
