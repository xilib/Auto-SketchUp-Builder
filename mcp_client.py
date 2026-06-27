import socket
import json
import logging
import uuid
from typing import Dict, Any

logger = logging.getLogger(__name__)

class RawMcpClient:
    """Raw TCP JSON-RPC Client for SketchUp MCP Server (Persistent Connection)"""
    
    def __init__(self, host="127.0.0.1", port=9876):
        self.host = host
        self.port = port
        self.socket = None
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(60.0) # 60s timeout for long generations
            self.socket.connect((self.host, self.port))
            logger.info(f"[MCP Client] Connected to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"[MCP Client] Failed to connect: {e}")
            self.socket = None
            raise

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            logger.info("[MCP Client] Disconnected.")

    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _call(self, method: str, params: dict = None) -> Any:
        if not self.socket:
            return {"isError": True, "error": "Not connected"}
            
        try:
            req_id = str(uuid.uuid4())
            req = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params or {}
            }
            self.socket.sendall((json.dumps(req) + "\n").encode("utf-8"))
            
            buffer = ""
            while "\n" not in buffer:
                data = self.socket.recv(8192).decode("utf-8")
                if not data:
                    # Connection closed by server
                    raise ConnectionError("Server closed connection")
                buffer += data
                
            if buffer:
                # Get the first line of the buffer
                line = buffer.split("\n")[0]
                resp = json.loads(line.strip())
                if "error" in resp:
                    logger.error(f"MCP RPC Error: {resp['error']}")
                    return {"isError": True, "error": resp['error']}
                return resp.get("result")
            return None
        except Exception as e:
            logger.error(f"MCP Call Error: {e}")
            return {"isError": True, "error": str(e)}

    def list_tools(self):
        result = self._call("tools/list")
        if result and "tools" in result:
            return result["tools"]
        return []

    def call_tool(self, name: str, arguments: dict):
        logger.info(f"[MCP] Calling tool: {name}")
        result = self._call("tools/call", {"name": name, "arguments": arguments})
        return result
