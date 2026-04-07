import asyncio
import uuid
from datetime import datetime
from typing import Dict, Set, Optional, Any, List
from server.logger import get_logger
from server.config import get_security_config

logger = get_logger("session")

class ClientContext:
    MAX_TERMINAL_BUFFER = 50000
    MAX_SHELL_HISTORY = 500
    MAX_CONTEXT = 4000
    MAX_CHAT_HISTORY = 20
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.terminal_buffer: str = ""
        self.shell_history: List[Dict[str, Any]] = []
        self.chat_history: List[Dict[str, str]] = []
        self.context: str = ""
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.cleared_at: Optional[datetime] = None
    
    def add_raw_log(self, content: str):
        self.terminal_buffer += content
        if len(self.terminal_buffer) > self.MAX_TERMINAL_BUFFER:
            self.terminal_buffer = self.terminal_buffer[-self.MAX_TERMINAL_BUFFER:]
        
        self.shell_history.append({
            "timestamp": datetime.now().isoformat(),
            "content": content
        })
        if len(self.shell_history) > self.MAX_SHELL_HISTORY:
            self.shell_history = self.shell_history[-self.MAX_SHELL_HISTORY:]
        
        self.context += f"\n{content}"
        if len(self.context) > self.MAX_CONTEXT:
            self.context = self.context[-self.MAX_CONTEXT:]
        self.last_activity = datetime.now()
    
    def get_terminal_buffer(self) -> str:
        return self.terminal_buffer
    
    def clear_logs(self):
        self.terminal_buffer = ""
        self.shell_history = []
        self.context = ""
        self.cleared_at = datetime.now()
        self.last_activity = datetime.now()
    
    def add_chat_message(self, role: str, content: str):
        self.chat_history.append({
            "role": role,
            "content": content
        })
        if len(self.chat_history) > self.MAX_CHAT_HISTORY:
            self.chat_history = self.chat_history[-self.MAX_CHAT_HISTORY:]
        self.last_activity = datetime.now()
    
    def get_llm_messages(self, system_prompt: str) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "system", "content": f"当前Shell会话上下文:\n{self.context[-2000:]}"})
        messages.extend(self.chat_history)
        return messages

class Session:
    def __init__(self, session_id: str, client_id: str, websocket):
        self.session_id = session_id
        self.client_id = client_id
        self.websocket = websocket
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.authenticated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "authenticated": self.authenticated
        }

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.client_sessions: Dict[str, Set[str]] = {}
        self.client_contexts: Dict[str, ClientContext] = {}
        self._lock = asyncio.Lock()
    
    async def create_pending_session(self, websocket) -> Session:
        """创建待注册的会话（尚未关联client_id）"""
        session_id = str(uuid.uuid4())
        session = Session(session_id, "pending", websocket)
        
        async with self._lock:
            self.sessions[session_id] = session
        
        logger.info(f"Pending session created: {session_id}")
        return session
    
    async def register_session(self, session_id: str, client_id: str) -> bool:
        """注册会话，关联client_id"""
        async with self._lock:
            if session_id not in self.sessions:
                return False
            
            session = self.sessions[session_id]
            old_client_id = session.client_id
            session.client_id = client_id
            
            if client_id not in self.client_sessions:
                self.client_sessions[client_id] = set()
            self.client_sessions[client_id].add(session_id)
            
            if client_id not in self.client_contexts:
                self.client_contexts[client_id] = ClientContext(client_id)
            
            logger.info(f"Session registered: {session_id} -> {client_id}")
            return True
    
    async def create_session(self, client_id: str, websocket) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id, client_id, websocket)
        
        async with self._lock:
            self.sessions[session_id] = session
            if client_id not in self.client_sessions:
                self.client_sessions[client_id] = set()
            self.client_sessions[client_id].add(session_id)
            
            if client_id not in self.client_contexts:
                self.client_contexts[client_id] = ClientContext(client_id)
        
        logger.info(f"Session created: {session_id} for client: {client_id}")
        return session
    
    async def remove_session(self, session_id: str):
        async with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                client_id = session.client_id
                
                if client_id in self.client_sessions:
                    self.client_sessions[client_id].discard(session_id)
                    if not self.client_sessions[client_id]:
                        del self.client_sessions[client_id]
                        if client_id in self.client_contexts:
                            del self.client_contexts[client_id]
                
                del self.sessions[session_id]
                logger.info(f"Session removed: {session_id}")
    
    def get_client_context(self, client_id: str) -> Optional[ClientContext]:
        return self.client_contexts.get(client_id)
    
    def get_or_create_client_context(self, client_id: str) -> ClientContext:
        if client_id not in self.client_contexts:
            self.client_contexts[client_id] = ClientContext(client_id)
        return self.client_contexts[client_id]
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)
    
    async def get_client_sessions(self, client_id: str) -> Set[str]:
        return self.client_sessions.get(client_id, set())
    
    async def get_all_sessions(self) -> Dict[str, Session]:
        return self.sessions.copy()
    
    async def get_all_clients(self) -> List[Dict[str, Any]]:
        result = []
        for client_id, session_ids in self.client_sessions.items():
            if client_id == "pending":
                continue
            
            sessions_info = []
            for sid in session_ids:
                if sid in self.sessions:
                    sessions_info.append(self.sessions[sid].to_dict())
            context = self.client_contexts.get(client_id)
            result.append({
                "client_id": client_id,
                "session_count": len(session_ids),
                "sessions": sessions_info,
                "shell_count": len(context.shell_history) if context else 0,
                "chat_count": len(context.chat_history) if context else 0
            })
        return result
    
    async def authenticate_session(self, session_id: str, token: str) -> bool:
        security_config = get_security_config()
        
        if not security_config.get("auth_enabled", True):
            session = await self.get_session(session_id)
            if session:
                session.authenticated = True
                logger.info(f"Auth disabled, auto authenticated session: {session_id}")
            return True
        
        valid_tokens = security_config.get("auth_tokens", [])
        if token in valid_tokens:
            session = await self.get_session(session_id)
            if session:
                session.authenticated = True
                logger.info(f"Session authenticated: {session_id}")
            return True
        
        logger.warning(f"Authentication failed for session: {session_id}")
        return False
    
    async def is_authenticated(self, session_id: str) -> bool:
        session = await self.get_session(session_id)
        return session.authenticated if session else False

session_manager = SessionManager()
