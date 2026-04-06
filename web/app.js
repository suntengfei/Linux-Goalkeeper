let ws = null;
let isConnected = false;
let isAuthenticated = false;
let currentClientId = '';
let sessionId = '';
let llmStatus = null;
let term = null;

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
    
    term.open(elements.terminalContainer);
    
    setTimeout(() => {
        term.fit();
    }, 100);
    
    window.addEventListener('resize', () => {
        if (term) {
            term.fit();
        }
    });
}

function updateConnectionStatus(connected) {
    isConnected = connected;
    elements.statusIndicator.className = `status-dot ${connected ? 'connected' : 'disconnected'}`;
    elements.statusText.textContent = connected ? '已连接' : '未连接';
    elements.connectBtn.textContent = connected ? '断开' : '连接';
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
    
    try {
        ws = new WebSocket(serverUrl);
        
        ws.onopen = async () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
            
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
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };
        
    } catch (error) {
        console.error('Connection failed:', error);
        updateConnectionStatus(false);
    }
}

function disconnect() {
    if (ws) {
        ws.close();
        ws = null;
    }
    updateConnectionStatus(false);
    isAuthenticated = false;
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

document.addEventListener('DOMContentLoaded', () => {
    initTerminal();
    initEventListeners();
    checkLLMStatus();
    
    setTimeout(() => {
        connect();
    }, 500);
});
