# Shell监控与AI运维助手 - 部署文档

## 目录

1. [环境要求](#环境要求)
2. [本地部署](#本地部署)
3. [Docker部署](#docker部署)
4. [配置说明](#配置说明)
5. [安全配置](#安全配置)
6. [运维指南](#运维指南)
7. [故障排查](#故障排查)

---

## 环境要求

### 服务端要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Linux (Ubuntu 18.04+) / macOS / Windows | Ubuntu 20.04 LTS |
| Python | 3.8+ | 3.11+ |
| 内存 | 512MB | 2GB+ |
| 磁盘 | 100MB | 1GB+ (用于日志存储) |
| 网络 | 能访问LLM API | 稳定网络连接 |

### 客户端要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux / macOS |
| Python | 3.8+ |
| Shell | bash / zsh / sh |

### LLM后端要求

**OpenAI兼容API：**
- OpenAI API Key
- 或其他兼容API（如Azure OpenAI、Claude等）

**Ollama本地模型：**
- Ollama服务已安装并运行
- 推荐至少8GB内存（取决于模型大小）

---

## 本地部署

### 步骤1：获取代码

```bash
# 克隆项目
git clone <repository-url>
cd Linux-Goalkeeper
```

### 步骤2：安装Python依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 步骤3：配置

```bash
# 复制配置模板
cp config.yaml.example config.yaml

# 编辑配置文件
vim config.yaml  # 或使用其他编辑器
```

**最小配置示例：**

```yaml
llm:
  backend: "openai"
  model: "gpt-4"
  api_key: "your-api-key-here"  # 或使用环境变量

security:
  auth_enabled: true
  auth_tokens:
    - "your-secure-token-here"
```

### 步骤4：配置环境变量（可选）

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

**环境变量说明：**

```bash
# LLM配置
LLM_BACKEND=openai          # 或 ollama
LLM_MODEL=gpt-4             # 模型名称
LLM_API_KEY=sk-xxx          # API密钥
LLM_BASE_URL=https://api.openai.com/v1  # API地址

# 认证配置
AUTH_TOKENS=token1,token2   # 多个Token用逗号分隔
```

### 步骤5：启动服务

**方式一：使用启动脚本**

```bash
# 添加执行权限
chmod +x start.sh

# 启动服务
./start.sh
```

**方式二：直接启动**

```bash
# 启动服务
python -m server.main
```

**方式三：后台运行**

```bash
# 使用nohup后台运行
nohup python -m server.main > logs/server.log 2>&1 &

# 查看日志
tail -f logs/server.log
```

### 步骤6：验证服务

```bash
# 检查服务状态
curl http://localhost:8080/health

# 预期输出
{"status": "healthy"}
```

### 步骤7：使用客户端

```bash
# 启动客户端
python -m client.main --server ws://localhost:8765 --token your-token

# 或使用PTY捕获模式
python -m client.shell_capture --server ws://localhost:8765 --token your-token
```

---

## Docker部署

### 步骤1：准备配置

```bash
# 创建配置文件
cp config.yaml.example config.yaml

# 编辑配置
vim config.yaml

# 创建环境变量文件
cp .env.example .env
vim .env
```

### 步骤2：构建镜像

```bash
# 构建镜像
docker build -t shell-monitor:latest .

# 或使用docker-compose
docker-compose build
```

### 步骤3：启动服务

**方式一：使用docker-compose（推荐）**

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

**方式二：使用docker run**

```bash
# 启动容器
docker run -d \
  --name shell-monitor \
  -p 8765:8765 \
  -p 8080:8080 \
  -e LLM_API_KEY=your-api-key \
  -e AUTH_TOKENS=your-token \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  shell-monitor:latest

# 查看日志
docker logs -f shell-monitor

# 停止容器
docker stop shell-monitor
docker rm shell-monitor
```

### 步骤4：验证服务

```bash
# 检查容器状态
docker ps

# 检查健康状态
docker inspect --format='{{.State.Health.Status}}' shell-monitor

# 访问Web界面
curl http://localhost:8080/health
```

### 步骤5：使用客户端

客户端需要在目标服务器运行，连接到服务端：

**方式一：PTY后台捕获模式（推荐）**

```bash
# 在目标服务器上运行，会启动一个新的shell并监控
python -m client.shell_monitor --server ws://your-server:8765 --token your-token

# 或使用启动脚本
./client/run.sh ws://your-server:8765 your-token
```

**方式二：简单测试模式**

```bash
# 手动输入命令测试连接
python -m client.main --server ws://your-server:8765 --token your-token
```

**客户端特性：**
- 客户端名称格式：`IP_shellPID`（如 `192.168.1.100_shell12345`）
- 自动心跳保持连接（每30秒）
- 断线自动重连（指数退避，最大30秒）
- 不影响用户正常shell操作体验

---

## 客户端部署所需文件

### 必需文件

```
client/
├── __init__.py
├── shell_monitor.py   # PTY后台捕获模式（推荐）
├── main.py            # 简单测试模式
└── run.sh             # 启动脚本

requirements.txt       # 依赖文件（客户端只需要 websockets）
```

### 快速部署步骤

**方式一：完整项目部署**

```bash
# 复制整个项目到目标服务器
scp -r Linux-Goalkeeper user@server:/path/to/

# 在目标服务器上
cd /path/to/Linux-Goalkeeper
pip install websockets  # 客户端只需要这一个依赖

# 启动客户端（PTY后台捕获模式）
python -m client.shell_monitor --server ws://your-server:8765 --token your-token
```

**方式二：最小化部署（推荐）**

只需复制以下文件到目标服务器：

```bash
# 创建客户端目录
mkdir -p shell-client/client

# 复制必要文件
cp client/__init__.py shell-client/client/
cp client/shell_monitor.py shell-client/client/
cp client/run.sh shell-client/

# 创建最小依赖文件
echo "websockets>=12.0" > shell-client/requirements.txt

# 打包传输
tar -czf shell-client.tar.gz shell-client/
```

在目标服务器上：

```bash
# 解压
tar -xzf shell-client.tar.gz
cd shell-client

# 安装依赖
pip install websockets

# 启动客户端
chmod +x run.sh
./run.sh ws://your-server:8765 your-token
```

### 客户端命令参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--server` / `-s` | 服务端WebSocket地址 | `ws://192.168.1.100:8765` |
| `--token` / `-t` | 认证Token | `your-secure-token` |

### 客户端特性

| 特性 | 说明 |
|------|------|
| **PTY后台捕获** | 在后台捕获shell输入输出，不影响用户操作 |
| **心跳机制** | 每30秒发送心跳，保持连接 |
| **断线重连** | 自动重连，指数退避（1-30秒） |
| **客户端名称** | 格式：`IP_shellPID`（如 `192.168.1.100_shell12345`） |

### 示例

```bash
# 连接到远程服务端
python -m client.shell_monitor -s ws://192.168.1.100:8765 -t my-secret-token

# 使用WSS加密连接
python -m client.shell_monitor -s wss://secure.example.com:8765 -t my-secret-token
```

---

## 配置说明

### 完整配置文件

```yaml
# 服务配置
server:
  host: "0.0.0.0"           # 监听地址
  port: 8765                # WebSocket端口
  web_port: 8080            # Web界面端口

# LLM配置
llm:
  backend: "openai"         # 后端类型: openai / ollama
  model: "gpt-4"            # 模型名称
  api_key: ""               # API密钥（建议使用环境变量）
  base_url: "https://api.openai.com/v1"  # API地址
  temperature: 0.7          # 温度参数
  max_tokens: 2000          # 最大输出tokens
  timeout: 30               # 超时时间（秒）

# 上下文管理
context:
  max_length: 4000          # 最大上下文长度
  head_length: 500          # 头部保留长度
  tail_length: 500          # 尾部保留长度

# 安全配置
security:
  auth_enabled: true        # 是否启用认证
  auth_tokens: []           # 认证Token列表
  wss_enabled: false        # 是否启用WSS加密
  cert_file: ""             # SSL证书文件
  key_file: ""              # SSL密钥文件

# 存储配置
storage:
  history_enabled: true     # 是否启用历史记录
  history_path: "./data/history"  # 历史记录路径
  audit_enabled: true       # 是否启用审计日志
  audit_path: "./data/audit"      # 审计日志路径

# 日志配置
logging:
  level: "INFO"             # 日志级别: DEBUG/INFO/WARNING/ERROR
  file: "./logs/app.log"    # 日志文件路径
```

### 环境变量优先级

环境变量优先级高于配置文件：

| 环境变量 | 配置项 |
|---------|--------|
| LLM_BACKEND | llm.backend |
| LLM_MODEL | llm.model |
| LLM_API_KEY | llm.api_key |
| LLM_BASE_URL | llm.base_url |
| AUTH_TOKENS | security.auth_tokens |

---

## 安全配置

### 1. 启用认证

```yaml
security:
  auth_enabled: true
  auth_tokens:
    - "secure-random-token-1"
    - "secure-random-token-2"
```

**生成安全Token：**

```bash
# 生成随机Token
openssl rand -hex 32
```

### 2. 启用WSS加密

**生成自签名证书（测试用）：**

```bash
# 生成私钥
openssl genrsa -out server.key 2048

# 生成证书
openssl req -new -x509 -key server.key -out server.crt -days 365

# 配置
security:
  wss_enabled: true
  cert_file: "/path/to/server.crt"
  key_file: "/path/to/server.key"
```

**使用Let's Encrypt证书（生产环境）：**

```bash
# 安装certbot
sudo apt install certbot

# 获取证书
sudo certbot certonly --standalone -d your-domain.com

# 配置
security:
  wss_enabled: true
  cert_file: "/etc/letsencrypt/live/your-domain.com/fullchain.pem"
  key_file: "/etc/letsencrypt/live/your-domain.com/privkey.pem"
```

### 3. API Key安全存储

**推荐方式：使用环境变量**

```bash
# 设置环境变量
export LLM_API_KEY="sk-your-api-key"

# 或在.env文件中
LLM_API_KEY=sk-your-api-key
```

**不要在配置文件中明文存储API Key！**

### 4. 防火墙配置

```bash
# 开放端口
sudo ufw allow 8765/tcp  # WebSocket
sudo ufw allow 8080/tcp  # Web界面

# 启用防火墙
sudo ufw enable
```

---

## 运维指南

### 服务管理

**启动服务：**

```bash
# 本地部署
python -m server.main

# Docker部署
docker-compose up -d
```

**停止服务：**

```bash
# 本地部署
Ctrl+C  # 或 kill <pid>

# Docker部署
docker-compose down
```

**重启服务：**

```bash
# Docker部署
docker-compose restart
```

### 日志管理

**查看实时日志：**

```bash
# 本地部署
tail -f logs/app.log

# Docker部署
docker-compose logs -f
```

**日志轮转配置：**

```bash
# 安装logrotate配置
cat > /etc/logrotate.d/shell-monitor << EOF
/path/to/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF
```

### 数据备份

**备份历史数据：**

```bash
# 创建备份
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# 定时备份（crontab）
0 2 * * * cd /path/to/project && tar -czf /backup/shell-monitor-$(date +\%Y\%m\%d).tar.gz data/
```

### 监控告警

**健康检查脚本：**

```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8080/health"
ALERT_WEBHOOK="https://your-webhook-url"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$response" != "200" ]; then
    curl -X POST $ALERT_WEBHOOK \
        -H "Content-Type: application/json" \
        -d '{"text": "Shell Monitor服务异常！状态码: '$response'"}'
    exit 1
fi

echo "Service is healthy"
```

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

**症状：** 启动时报错

**排查步骤：**

```bash
# 检查Python版本
python --version  # 需要3.8+

# 检查依赖
pip list | grep websockets
pip list | grep aiohttp

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

#### 2. 客户端无法连接

**症状：** 客户端连接超时

**排查步骤：**

```bash
# 检查服务是否运行
curl http://localhost:8080/health

# 检查端口是否监听
netstat -tlnp | grep 8765

# 检查防火墙
sudo ufw status

# 检查认证Token是否正确
```

#### 3. LLM调用失败

**症状：** 分析返回错误

**排查步骤：**

```bash
# 检查API Key是否配置
echo $LLM_API_KEY

# 测试API连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"

# 检查网络连接
ping api.openai.com
```

#### 4. 内存占用过高

**症状：** 服务内存持续增长

**解决方案：**

```yaml
# 减少上下文长度
context:
  max_length: 2000
  head_length: 300
  tail_length: 300

# 禁用历史记录
storage:
  history_enabled: false
```

#### 5. Docker容器健康检查失败

**症状：** 容器状态显示unhealthy

**排查步骤：**

```bash
# 查看容器日志
docker logs shell-monitor

# 进入容器检查
docker exec -it shell-monitor bash
curl http://localhost:8080/health

# 检查健康检查配置
docker inspect shell-monitor | grep -A 10 Health
```

### 日志分析

**查看错误日志：**

```bash
grep ERROR logs/app.log
grep -i "failed\|error\|exception" logs/app.log
```

**查看特定时间段日志：**

```bash
grep "2024-01-01 10:" logs/app.log
```

### 性能调优

**调整并发连接数：**

```yaml
# 在server配置中添加
server:
  max_connections: 100
```

**调整LLM超时时间：**

```yaml
llm:
  timeout: 60  # 增加超时时间
```

---

## 附录

### A. 端口说明

| 端口 | 用途 | 协议 |
|------|------|------|
| 8765 | WebSocket服务 | WS/WSS |
| 8080 | Web界面 | HTTP/HTTPS |

### B. 文件说明

| 文件/目录 | 说明 |
|----------|------|
| config.yaml | 主配置文件 |
| .env | 环境变量文件 |
| logs/ | 日志目录 |
| data/history/ | 历史记录 |
| data/audit/ | 审计日志 |

### C. 命令速查

```bash
# 启动服务
python -m server.main

# 启动客户端
python -m client.main -s ws://localhost:8765 -t your-token

# 运行测试
pytest tests/ -v

# 查看日志
tail -f logs/app.log

# Docker启动
docker-compose up -d

# Docker日志
docker-compose logs -f

# Docker重启
docker-compose restart
```

---

## 联系支持

如有问题，请：
1. 查看本文档的故障排查部分
2. 查看项目GitHub Issues
3. 提交新的Issue并附上错误日志
