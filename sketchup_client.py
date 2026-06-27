"""
sketchup_client.py
==================
TCP 通信层：负责与 SketchUp 内部 TCP Server（端口 9876）对话。

协议说明：
  - SketchUp 侧（su_mcp 插件）每次处理一条请求：accept -> read line -> respond -> close
  - 所以我们每次都新建一条 TCP 连接，发完即断（短连接模式）
  - 格式：JSON-RPC 2.0，每条消息以 \\n 结尾
"""

import json
import logging
import socket
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 默认连接参数，可通过外部传入覆盖
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT = 30.0  # 秒，SketchUp 建模操作可能耗时


def send_command(
    method: str,
    params: Dict[str, Any],
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
    request_id: int = 1,
) -> Dict[str, Any]:
    """
    向 SketchUp TCP Server 发送一条 JSON-RPC 2.0 请求并返回响应。
    每次调用都会新建 TCP 连接（与 SketchUp 插件的 accept-per-request 机制匹配）。

    Args:
        method:     JSON-RPC 方法名，例如 "tools/call"
        params:     请求参数字典
        host:       SketchUp 监听的主机，默认 127.0.0.1
        port:       SketchUp 监听的端口，默认 9876
        timeout:    等待响应的超时时间（秒）
        request_id: JSON-RPC 请求 ID

    Returns:
        SketchUp 返回的 JSON-RPC 响应字典

    Raises:
        ConnectionRefusedError: SketchUp 未启动或 MCP Server 未开启
        TimeoutError:           SketchUp 在超时时间内无响应
        Exception:              其他通信错误
    """
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }
    message = json.dumps(request, ensure_ascii=False) + "\n"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        logger.info(f"[TCP] 连接 {host}:{port}")
        sock.connect((host, port))

        sock.sendall(message.encode("utf-8"))
        logger.debug(f"[TCP] 已发送: {message.strip()}")

        # 持续接收数据，直到凑齐一个合法的 JSON 为止
        buffer = b""
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                # 连接被对端关闭
                break
            buffer += chunk
            try:
                response = json.loads(buffer.decode("utf-8"))
                logger.info(f"[TCP] 收到响应: {json.dumps(response, ensure_ascii=False)[:200]}")
                return response
            except json.JSONDecodeError:
                # 数据还没接完，继续等
                continue

        # 如果循环结束还没解析成功
        if buffer:
            # 最后尝试一次
            return json.loads(buffer.decode("utf-8"))
        raise Exception("SketchUp 连接已关闭，未收到任何数据。")

    except socket.timeout as e:
        raise TimeoutError(
            f"SketchUp {timeout}s 内无响应。建模操作是否太复杂？可尝试增大 timeout 参数。"
        ) from e
    finally:
        sock.close()
        logger.info("[TCP] 连接已关闭")


def eval_ruby(
    code: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """
    最常用的快捷方法：在 SketchUp 中执行一段任意 Ruby 代码。

    Args:
        code:    要执行的 Ruby 代码字符串
        host:    SketchUp 主机
        port:    SketchUp 端口
        timeout: 超时时间

    Returns:
        JSON-RPC 响应字典，包含 result 或 error 字段
    """
    logger.info(f"[eval_ruby] 准备执行 Ruby 代码（{len(code)} 字符）")
    return send_command(
        method="tools/call",
        params={
            "name": "eval_ruby",
            "arguments": {"code": code},
        },
        host=host,
        port=port,
        timeout=timeout,
    )
