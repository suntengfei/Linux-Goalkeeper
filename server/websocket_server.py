import asyncio
import json
import ssl
from datetime import datetime
from typing import Dict, Any, Optional
import websockets
from websockets.server import WebSocketServerProtocol

from server.logger import get_logger
from server.config import get_server_config, get_security_config
from server.session_manager import session_manager
from server.llm_backend import create_llm_backend
from server.prompts import get_chat_system_prompt

logger = get_logger("websocket")

class WebSocketServer:
    def __init__(self):
        self.config = get_server_config()
        self.security_config = get_security_config()
        self.llm = None
        self.message_handlers = {}
        self.heartbeat_timeout = self.config.get("heartbeat_timeout", 180)
        self._register_handlers()
    
    def _register_handlers(self):
        self.message_handlers = {
            "auth": self._handle_auth,
            "log": self._handle_log,
            "chat": self._handle_chat,
            "ping": self._handle_ping,
            "get_clients": self._handle_get_clients,
            "get_client_history": self._handle_get_client_history,
            "register": self._handle_register,
        }
    
    async def _broadcast_to_all(self, data: Dict[str, Any], exclude_session_id: str = None):
        message = json.dumps(data, ensure_ascii=False)
        sessions = await session_manager.get_all_sessions()
        for session_id, session in sessions.items():
            if exclude_session_id and session_id == exclude_session_id:
                continue
            try:
                await session.websocket.send(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
    
    async def _broadcast_client_list(self):
        clients = await session_manager.get_all_clients()
        await self._broadcast_to_all({
            "type": "clients_update",
            "clients": clients,
            "timestamp": datetime.now().isoformat()
        })
    
    async def start(self):
        host = self.config.get("host", "0.0.0.0")
        port = self.config.get("port", 8765)
        
        ssl_context = None
        if self.security_config.get("wss_enabled", False):
            cert_file = self.security_config.get("cert_file")
            key_file = self.security_config.get("key_file")
            if cert_file and key_file:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(cert_file, key_file)
                logger.info("WSS enabled")
        
        self.llm = create_llm_backend(self._get_llm_config())
        
        asyncio.create_task(self._heartbeat_check())
        
        logger.info(f"Starting WebSocket server on {host}:{port}")
        async with websockets.serve(
            self._handle_connection,
            host,
            port,
            ssl=ssl_context,
            ping_interval=20,
            ping_timeout=60,
            close_timeout=5
        ):
            logger.info(f"WebSocket server started on ws{'s' if ssl_context else ''}://{host}:{port}")
            await asyncio.Future()
    
    async def _heartbeat_check(self):
        """定期检查客户端心跳超时"""
        while True:
            try:
                await asyncio.sleep(10)
                
                now = datetime.now()
                sessions = await session_manager.get_all_sessions()
                
                for session_id, session in sessions.items():
                    last_active = session.last_activity
                    if (now - last_active).total_seconds() > self.heartbeat_timeout:
                        logger.warning(f"Client {session.client_id} heartbeat timeout, removing session")
                        try:
                            await session.websocket.close()
                        except:
                            pass
                        await session_manager.remove_session(session_id)
                
                clients = await session_manager.get_all_clients()
                await self._broadcast_to_all({
                    "type": "clients_update",
                    "clients": clients,
                    "timestamp": now.isoformat()
                })
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat check error: {e}")
    
    def _get_llm_config(self):
        from server.config import get_llm_config
        return get_llm_config()
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str = ""):
        session = None
        try:
            session = await session_manager.create_pending_session(websocket)
            
            logger.info(f"New connection pending, session: {session.session_id}")
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return
        
        try:
            await self._send_message(websocket, {
                "type": "connected",
                "session_id": session.session_id,
                "timestamp": datetime.now().isoformat()
            })
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(session, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from {session.session_id}")
                    await self._send_error(websocket, "Invalid JSON format")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await self._send_error(websocket, str(e))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {session.session_id}")
        finally:
            await session_manager.remove_session(session.session_id)
            await self._broadcast_client_list()
    
    async def _handle_message(self, session, data: Dict[str, Any]):
        msg_type = data.get("type")
        handler = self.message_handlers.get(msg_type)
        
        if handler:
            session.last_activity = datetime.now()
            await handler(session, data)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    async def _handle_auth(self, session, data: Dict[str, Any]):
        token = data.get("token", "")
        success = await session_manager.authenticate_session(session.session_id, token)
        
        await self._send_message(session.websocket, {
            "type": "auth_result",
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_log(self, session, data: Dict[str, Any]):
        logger.info(f"Received log from {session.client_id}, authenticated={session.authenticated}")
        
        if not session.authenticated and self.security_config.get("auth_enabled", True):
            await self._send_error(session.websocket, "Not authenticated")
            return
        
        content = data.get("content", "")
        
        if not content:
            return
        
        logger.info(f"Processing log: {len(content)} chars")
        
        client_context = session_manager.get_client_context(session.client_id)
        if client_context:
            client_context.add_raw_log(content)
        
        log_data = {
            "type": "shell_log",
            "client_id": session.client_id,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        await self._broadcast_to_all(log_data)
    
    async def _handle_chat(self, session, data: Dict[str, Any]):
        logger.info(f"Handle chat from {session.client_id}, data: {data}")
        
        if not session.authenticated and self.security_config.get("auth_enabled", True):
            await self._send_error(session.websocket, "Not authenticated")
            return
        
        message = data.get("message", "")
        target_client_id = data.get("client_id")
        
        logger.info(f"Chat message: {message}, target_client_id: {target_client_id}")
        
        if not message:
            logger.warning("Empty message, skipping")
            return
        
        if not target_client_id or target_client_id.startswith("web_client_"):
            all_clients = await session_manager.get_all_clients()
            shell_clients = [c for c in all_clients if not c["client_id"].startswith("web_client_")]
            logger.info(f"Shell clients: {shell_clients}")
            if shell_clients:
                target_client_id = shell_clients[0]["client_id"]
            else:
                target_client_id = session.client_id
        
        logger.info(f"Using target_client_id: {target_client_id}")
        
        client_context = session_manager.get_client_context(target_client_id)
        if not client_context:
            logger.info(f"Creating new context for {target_client_id}")
            client_context = session_manager.get_or_create_client_context(target_client_id)
        
        chat_messages = client_context.get_llm_messages(get_chat_system_prompt())
        chat_messages.append({"role": "user", "content": message})
        
        try:
            if not self.llm:
                response = "LLM 后端未配置，请检查 config.yaml"
                logger.error("LLM backend not configured")
            else:
                logger.info(f"Calling LLM with {len(chat_messages)} messages")
                response = await asyncio.wait_for(
                    self.llm.chat(message, chat_messages),
                    timeout=60.0
                )
                logger.info(f"LLM response: {response[:100]}...")
        except asyncio.TimeoutError:
            response = "抱歉，LLM 响应超时，请重试。"
            logger.error("LLM timeout")
        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            response = f"抱歉，发生错误: {str(e)}"
        
        client_context.add_chat_message("user", message)
        client_context.add_chat_message("assistant", response)
        
        logger.info(f"Sending chat_response to {session.client_id}")
        await self._send_message(session.websocket, {
            "type": "chat_response",
            "client_id": session.client_id,
            "target_client_id": target_client_id,
            "message": response,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_ping(self, session, data: Dict[str, Any]):
        session.last_activity = datetime.now()
        await self._send_message(session.websocket, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_get_clients(self, session, data: Dict[str, Any]):
        clients = await session_manager.get_all_clients()
        await self._send_message(session.websocket, {
            "type": "clients_list",
            "clients": clients,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_get_client_history(self, session, data: Dict[str, Any]):
        client_id = data.get("client_id")
        if not client_id:
            return
        
        context = session_manager.get_client_context(client_id)
        if context:
            buffer = context.get_terminal_buffer()
            if buffer:
                await self._send_message(session.websocket, {
                    "type": "shell_log",
                    "client_id": client_id,
                    "content": buffer,
                    "is_history": True,
                    "timestamp": datetime.now().isoformat()
                })
    
    async def _handle_register(self, session, data: Dict[str, Any]):
        client_id = data.get("client_id")
        
        if not client_id or client_id == "unknown":
            await self._send_error(session.websocket, "Invalid client_id")
            return
        
        success = await session_manager.register_session(session.session_id, client_id)
        
        if not success:
            await self._send_error(session.websocket, "Registration failed")
            return
        
        session.last_activity = datetime.now()
        
        logger.info(f"Client registered: {client_id} (session: {session.session_id})")
        
        if client_id.startswith("web_client_"):
            all_clients = await session_manager.get_all_clients()
            for client in all_clients:
                if not client["client_id"].startswith("web_client_"):
                    context = session_manager.get_client_context(client["client_id"])
                    if context:
                        buffer = context.get_terminal_buffer()
                        if buffer:
                            await self._send_message(session.websocket, {
                                "type": "shell_log",
                                "client_id": client["client_id"],
                                "content": buffer,
                                "is_history": True,
                                "timestamp": datetime.now().isoformat()
                            })
        
        await self._broadcast_client_list()
    
    async def _send_message(self, websocket, data: Dict[str, Any]):
        try:
            await websocket.send(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def _send_error(self, websocket, error: str):
        await self._send_message(websocket, {
            "type": "error",
            "message": error,
            "timestamp": datetime.now().isoformat()
        })

async def main():
    from server.config import load_config, get_logging_config
    load_config()
    
    logging_config = get_logging_config()
    setup_kwargs = {"name": "shell_monitor", "level": logging_config.get("level", "INFO")}
    if logging_config.get("file"):
        setup_kwargs["log_file"] = logging_config["file"]
    
    from server.logger import setup_logging
    setup_logging(**setup_kwargs)
    
    server = WebSocketServer()
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
