import asyncio
import os
from pathlib import Path
from aiohttp import web
from server.logger import get_logger
from server.config import get_llm_config

logger = get_logger("webui")

class WebUIServer:
    def __init__(self, port: int = 8080, static_dir: str = None):
        self.port = port
        self.static_dir = static_dir or Path(__file__).parent.parent / "web"
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        self.app.router.add_get('/', self._serve_index)
        self.app.router.add_get('/health', self._health_check)
        self.app.router.add_get('/api/llm-status', self._llm_status)
        self.app.router.add_static('/static', self.static_dir)
    
    async def _serve_index(self, request):
        index_path = Path(self.static_dir) / "index.html"
        if index_path.exists():
            return web.FileResponse(index_path)
        return web.Response(text="Web UI not found", status=404)
    
    async def _health_check(self, request):
        return web.json_response({"status": "healthy"})
    
    async def _llm_status(self, request):
        llm_config = get_llm_config()
        backend = llm_config.get("backend", "unknown")
        model = llm_config.get("model", "unknown")
        base_url = llm_config.get("base_url", "")
        has_api_key = bool(llm_config.get("api_key", ""))
        
        return web.json_response({
            "backend": backend,
            "model": model,
            "base_url": base_url,
            "api_key_configured": has_api_key,
            "status": "configured" if has_api_key or backend == "ollama" else "not_configured"
        })
    
    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Web UI server started on http://0.0.0.0:{self.port}")
        
        return runner
