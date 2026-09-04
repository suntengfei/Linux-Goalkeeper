let ws = null;
let isConnected = false;
let isAuthenticated = false;
let currentClientId = '';
let sessionId = '';
let llmStatus = null;
let term = null;
let fitAddon = null;
let heartbeatInterval = null;
let reconnectAttempts = 0;
let isManualDisconnect = false;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 5000;
const HEARTBEAT_INTERVAL = 30000;

const elements = {
    statusIndicator: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    llmStatusIndicator: document.getElementById('llm-status-indicator'),
    llmStatusText: document.getElementById('llm-status-text'),
    llmModel: document.getElementById('llm-model'),
    serverUrl: document.getElementById('server-url'),
    authToken: document.getElementById('auth-token'),
    authBtn: document.getElementById('auth-btn'),
    connectBtn: document.getElementById('connect-btn'),
    clientSelect: document.getElementById('client-select'),
    clientCount: document.getElementById('client-count'),
    terminalContainer: document.getElementById('terminal-container'),
    chatMessages: document.getElementById('chat-messages'),
    chatInput: document.getElementById('chat-input'),
    chatSendBtn: document.getElementById('chat-send-btn'),
    clearLogBtn: document.getElementById('clear-log-btn'),
    copyLogBtn: document.getElementById('copy-log-btn')
};

function initTerminal() {
    if (term) {
        term.dispose();
    }
    
    term = new Terminal({
        theme: {
            background: '#0a0a1a',
            foreground: '#e0e0e0',
            cursor: '#4ecdc4',
            cursorAccent: '#0a0a1a',
            selection: 'rgba(78, 205, 196, 0.3)',
            black: '#000000',
            red: '#e94560',
            green: '#4ecdc4',
            yellow: '#f39c12',
            blue: '#3498db',
            magenta: '#9b59b6',
            cyan: '#1abc9c',
            white: '#ecf0f1',
            brightBlack: '#7f8c8d',
            brightRed: '#ff6b6b',
            brightGreen: '#2ecc71',
            brightYellow: '#f1c40f',
            brightBlue: '#5dade2',
            brightMagenta: '#a569bd',
            brightCyan: '#48c9b0',
            brightWhite: '#ffffff'
        },
        fontFamily: 'Consolas, Monaco, monospace',
        fontSize: 14,
        lineHeight: 1.2,
        scrollback: 5000,
        allowTransparency: true
    });
    
    fitAddon = new FitAddon.FitAddon();
    term.loadAddon(fitAddon);
    term.open(elements.terminalContainer);
    
    setTimeout(() => {
        fitAddon.fit();
    }, 100);
    
    window.addEventListener('resize', () => {
        if (term && fitAddon) {
            fitAddon.fit();
        }
    });
}

function updateConnectionStatus(connected) {
    isConnected = connected;
    elements.statusIndicator.className = `status-dot ${connected ? 'connected' : 'disconnected'}`;
    elements.statusText.textContent = connected ? '已连接' : '未连接';
    elements.connectBtn.textContent = connected ? '断开' : '连接';
}

function startHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
    }
    
    heartbeatInterval = setInterval(() => {
        if (ws && isConnected && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'ping'
            }));
        }
    }, HEARTBEAT_INTERVAL);
    
    console.log('Heartbeat started');
}

function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
        console.log('Heartbeat stopped');
    }
}

function reconnect() {
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        elements.statusText.textContent = `重连中 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`;
        console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
        
        setTimeout(() => {
            connect();
        }, RECONNECT_DELAY);
    } else {
        console.log('Max reconnection attempts reached');
        elements.statusText.textContent = '连接失败';
        reconnectAttempts = 0;
    }
}

function updateLLMStatus(status) {
    llmStatus = status;
    const configured = status.status === 'configured';
    elements.llmStatusIndicator.className = `status-dot ${configured ? 'connected' : 'disconnected'}`;
    elements.llmStatusText.textContent = configured ? '已配置' : '未配置';
    
    if (status.model) {
        elements.llmModel.textContent = status.model;
        elements.llmModel.title = `后端: ${status.backend}\n地址: ${status.base_url || '本地'}`;
    }
}

async function checkLLMStatus() {
    try {
        const response = await fetch('/api/llm-status');
        const data = await response.json();
        updateLLMStatus(data);
    } catch (e) {
        console.error('Failed to check LLM status:', e);
        updateLLMStatus({ status: 'error' });
    }
}

function appendShellLog(content) {
    if (term) {
        term.write(content);
    }
}

function clearTerminal() {
    if (term) {
        term.clear();
    }
    
    if (ws && isConnected && currentClientId) {
        ws.send(JSON.stringify({
            type: 'clear_logs',
            client_id: currentClientId
        }));
    }
}

function copyTerminalLog() {
    if (term) {
        const lines = [];
        for (let i = 0; i < term.buffer.active.length; i++) {
            const line = term.buffer.active.getLine(i);
            if (line) {
                lines.push(line.translateToString(true));
            }
        }
        const text = lines.join('\n');
        navigator.clipboard.writeText(text).then(() => {
            alert('日志已复制到剪贴板');
        }).catch(err => {
            console.error('复制失败:', err);
        });
    } else {
        alert('没有日志可复制');
    }
}

function addChatMessage(role, content) {
    const placeholder = elements.chatMessages.querySelector('.chat-placeholder');
    if (placeholder) {
        placeholder.remove();
    }

    const message = document.createElement('div');
    message.className = `chat-message ${role}`;
    
    const roleDiv = document.createElement('div');
    roleDiv.className = 'role';
    roleDiv.textContent = role === 'user' ? '👤 用户' : '🤖 AI助手';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'content';
    contentDiv.textContent = content;
    
    message.appendChild(roleDiv);
    message.appendChild(contentDiv);
    
    elements.chatMessages.appendChild(message);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

function updateClientList(clients) {
    if (!Array.isArray(clients)) {
        clients = Object.values(clients || {});
    }
    
    const previousSelection = elements.clientSelect.value;
    
    elements.clientSelect.innerHTML = '<option value="">-- 选择客户端 --</option>';
    elements.clientCount.textContent = `(${clients.length} 个连接)`;
    
    clients.forEach(client => {
        const option = document.createElement('option');
        option.value = client.client_id;
        const ip = client.client_id.split('_')[0] || 'unknown';
        option.textContent = `${client.client_id} (${ip})`;
        elements.clientSelect.appendChild(option);
    });
    
    if (previousSelection && elements.clientSelect.querySelector(`option[value="${previousSelection}"]`)) {
        elements.clientSelect.value = previousSelection;
    }
}

function handleAuthResult(data) {
    if (data.success) {
        isAuthenticated = true;
        elements.authToken.disabled = true;
        elements.authToken.style.backgroundColor = '#1a3a1a';
        elements.authToken.title = '已认证';
        if (elements.authBtn) {
            elements.authBtn.textContent = '已认证';
            elements.authBtn.disabled = true;
        }
    } else {
        isAuthenticated = false;
        alert('认证失败: ' + (data.message || '无效的Token'));
    }
}

async function authenticate() {
    const authToken = elements.authToken.value.trim();
    
    if (!authToken) {
        alert('请输入认证Token');
        return false;
    }
    
    if (!ws || !isConnected) {
        alert('未连接到服务器');
        return false;
    }
    
    ws.send(JSON.stringify({
        type: 'auth',
        token: authToken
    }));
    return true;
}

async function connect() {
    const serverUrl = elements.serverUrl.value;
    const authToken = elements.authToken.value;

    isManualDisconnect = false;

    // 校验服务器地址，仅允许 ws/wss 协议，并用解析结果重建URL，避免任意URL注入
    let parsedUrl;
    try {
        parsedUrl = new URL(serverUrl);
    } catch (e) {
        alert('无效的服务器地址');
        return;
    }
    if (parsedUrl.protocol !== 'ws:' && parsedUrl.protocol !== 'wss:') {
        alert('服务器地址必须以 ws:// 或 wss:// 开头');
        return;
    }
    // 仅允许常见主机名字符，拦截控制字符与空白
    if (!/^[\w.\-:#[\]@!$&'()*+,;=~/?%]+$/.test(parsedUrl.host)) {
        alert('服务器地址包含非法字符');
        return;
    }
    const sanitizedUrl = parsedUrl.protocol + '//' + parsedUrl.host + parsedUrl.pathname + parsedUrl.search;

    try {
        ws = new WebSocket(sanitizedUrl);
        
        ws.onopen = async () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
            reconnectAttempts = 0;
            
            ws.send(JSON.stringify({
                type: 'register',
                client_id: 'web_client_' + Date.now()
            }));
            
            if (authToken) {
                ws.send(JSON.stringify({
                    type: 'auth',
                    token: authToken
                }));
            }
            
            startHeartbeat();
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };
        
        ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus(false);
            isAuthenticated = false;
            elements.authToken.disabled = false;
            elements.authToken.style.backgroundColor = '';
            elements.authToken.title = '';
            if (elements.authBtn) {
                elements.authBtn.textContent = '认证';
                elements.authBtn.disabled = false;
            }
            
            stopHeartbeat();
            
            if (!isManualDisconnect) {
                reconnect();
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };
        
    } catch (error) {
        console.error('Connection failed:', error);
        updateConnectionStatus(false);
        
        if (!isManualDisconnect) {
            reconnect();
        }
    }
}

function disconnect() {
    isManualDisconnect = true;
    stopHeartbeat();
    
    if (ws) {
        ws.close();
        ws = null;
    }
    
    updateConnectionStatus(false);
    isAuthenticated = false;
    reconnectAttempts = 0;
    elements.authToken.disabled = false;
    elements.authToken.style.backgroundColor = '';
    elements.authToken.title = '';
    if (elements.authBtn) {
        elements.authBtn.textContent = '认证';
        elements.authBtn.disabled = false;
    }
}

function handleMessage(data) {
    switch (data.type) {
        case 'connected':
            sessionId = data.session_id;
            break;
            
        case 'auth_result':
            handleAuthResult(data);
            break;
            
        case 'shell_log':
            if (data.content) {
                const logClientId = data.client_id;
                if (!currentClientId || logClientId === currentClientId || logClientId === sessionId) {
                    if (data.is_history && term) {
                        term.clear();
                        term.write(data.content);
                    } else {
                        appendShellLog(data.content);
                    }
                }
            }
            break;
            
        case 'chat_response':
            addChatMessage('agent', data.message || data.content || '无响应');
            break;
            
        case 'clients_update':
            updateClientList(data.clients);
            break;
            
        case 'pong':
            break;
            
        case 'logs_cleared':
            console.log('Logs cleared for client:', data.client_id);
            if (term && data.client_id === currentClientId) {
                term.clear();
            }
            break;
            
        case 'error':
            console.error('Server error:', data.message);
            break;
            
        default:
            console.log('Unknown message type:', data.type);
    }
}

async function sendChatMessage() {
    const message = elements.chatInput.value.trim();
    
    if (!message) {
        return;
    }
    
    if (!ws || !isConnected) {
        alert('未连接到服务器');
        return;
    }
    
    if (!isAuthenticated) {
        alert('请先输入Token并点击认证按钮进行认证');
        return;
    }
    
    addChatMessage('user', message);
    elements.chatInput.value = '';
    
    ws.send(JSON.stringify({
        type: 'chat',
        client_id: currentClientId || elements.clientSelect.value,
        message: message
    }));
}

function initEventListeners() {
    elements.connectBtn.addEventListener('click', () => {
        if (isConnected) {
            disconnect();
        } else {
            connect();
        }
    });
    
    if (elements.authBtn) {
        elements.authBtn.addEventListener('click', () => {
            if (isAuthenticated) {
                return;
            }
            authenticate();
        });
    }
    
    elements.chatSendBtn.addEventListener('click', sendChatMessage);
    
    elements.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    elements.clearLogBtn.addEventListener('click', clearTerminal);
    elements.copyLogBtn.addEventListener('click', copyTerminalLog);
    
    elements.clientSelect.addEventListener('change', (e) => {
        currentClientId = e.target.value;
        if (term) {
            term.clear();
        }
        if (ws && isConnected && currentClientId) {
            ws.send(JSON.stringify({
                type: 'get_client_history',
                client_id: currentClientId
            }));
        }
    });
}

function initResizer() {
    const resizer = document.getElementById('resizer');
    const leftPanel = document.querySelector('.left-panel');
    const rightPanel = document.querySelector('.right-panel');
    const mainContent = document.querySelector('.main-content');
    
    let isResizing = false;
    let startX = 0;
    let startLeftWidth = 0;
    let startRightWidth = 0;
    
    resizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        startLeftWidth = leftPanel.offsetWidth;
        startRightWidth = rightPanel.offsetWidth;
        resizer.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const deltaX = e.clientX - startX;
        const containerWidth = mainContent.offsetWidth;
        const minPanelWidth = 300;
        
        let newLeftWidth = startLeftWidth + deltaX;
        let newRightWidth = startRightWidth - deltaX;
        
        if (newLeftWidth < minPanelWidth) {
            newLeftWidth = minPanelWidth;
            newRightWidth = containerWidth - minPanelWidth - resizer.offsetWidth;
        }
        
        if (newRightWidth < minPanelWidth) {
            newRightWidth = minPanelWidth;
            newLeftWidth = containerWidth - minPanelWidth - resizer.offsetWidth;
        }
        
        const leftFlex = newLeftWidth / (newLeftWidth + newRightWidth);
        const rightFlex = newRightWidth / (newLeftWidth + newRightWidth);
        
        leftPanel.style.flex = leftFlex;
        rightPanel.style.flex = rightFlex;
        
        if (term && fitAddon) {
            fitAddon.fit();
        }
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            resizer.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    initTerminal();
    initEventListeners();
    initResizer();
    checkLLMStatus();
    
    setTimeout(() => {
        connect();
    }, 500);
});
