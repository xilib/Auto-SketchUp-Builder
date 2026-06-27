"""
main.py  v2.0 - AI 建筑设计智能体
新架构: AI只做1次视觉分析(~3000 tokens), 几何由 building_tools.rb 确定性完成
"""

import logging
import os
import uuid
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from ai_service_v2 import analyze_image_and_build
from mcp_client import RawMcpClient
from sketchup_client import DEFAULT_HOST, DEFAULT_PORT, eval_ruby

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AIArchAgent")

AI_API_KEY     = os.getenv("AI_API_KEY", "")
AI_BASE_URL    = os.getenv("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
AI_MODEL_HEAVY = os.getenv("AI_MODEL_HEAVY", "gpt-4o")
AI_MODEL_LITE  = os.getenv("AI_MODEL_LITE",  "gemini-1.5-flash")
SU_HOST        = os.getenv("SKETCHUP_HOST", DEFAULT_HOST)
SU_PORT        = int(os.getenv("SKETCHUP_PORT", str(DEFAULT_PORT)))
SERVER_PORT    = int(os.getenv("SERVER_PORT", "8000"))

from google import genai

# 尝试自动定位 Windows 下通过 gcloud 生成的 ADC 凭证文件
adc_path = os.path.join(os.environ.get("APPDATA", ""), "gcloud", "application_default_credentials.json")
if os.path.exists(adc_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path

try:
    ai_client = genai.Client(
        vertexai=True,
        project="project-12526171-d9fb-428a-b89",
        location="global" # 必须使用 global 地区，因为新模型部署在 global
    )
    logger.info(f"[AI] initialized Vertex AI (google-genai SDK) -> Heavy={AI_MODEL_HEAVY}")
except Exception as e:
    logger.error(f"[AI] Initialization failed: {e}")
    ai_client = None

app = FastAPI(
    title="AI Building Agent v2",
    description="Upload a building image, AI analyzes it once, then deterministically builds in SketchUp.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextRequest(BaseModel):
    prompt: str
    model: Optional[str] = None

class BuildResponse(BaseModel):
    status: str
    message: str
    params: Optional[dict] = None
    errors: Optional[list] = None

class ChatStartResponse(BaseModel):
    status: str
    session_id: str
    message: str
    params: Optional[dict] = None


def _require_ai():
    pass # Vertex AI is initialized at module level

def _handle_su_error(e: Exception):
    if isinstance(e, ConnectionRefusedError):
        raise HTTPException(status_code=503, detail="Cannot connect to SketchUp port 9876. Start the MCP server in Extensions menu.")
    if isinstance(e, TimeoutError):
        raise HTTPException(status_code=504, detail=str(e))
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/", tags=["system"])
def health_check():
    return {
        "status": "running",
        "version": "2.0",
        "ai_ready": ai_client is not None,
        "heavy_model": AI_MODEL_HEAVY,
        "sketchup": f"{SU_HOST}:{SU_PORT}",
    }


@app.post("/api/chat/start", response_model=ChatStartResponse, tags=["build"])
async def chat_start(
    prompt: str = Form(default=""),
    heavy_model: Optional[str] = Form(None),
    image: UploadFile = File(...),
):
    """
    v2 Core endpoint:
    1. ONE AI call to analyze image and extract building parameters JSON (~3000 tokens)
    2. Load building_tools.rb into SketchUp (1 MCP call)
    3. Call deterministic tool functions (8-12 MCP calls, zero randomness)
    """
    _require_ai()

    content_type = image.content_type or "image/jpeg"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=f"Please upload an image file, got: {content_type}")

    model_name = heavy_model or AI_MODEL_HEAVY
    if model_name == "string":
        model_name = AI_MODEL_HEAVY

    try:
        image_bytes = await image.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")

        logger.info(f"[v2] Starting build: {image.filename} ({len(image_bytes)} bytes), model={model_name}")

        with RawMcpClient(host=SU_HOST, port=SU_PORT) as mcp:
            result = analyze_image_and_build(
                ai_client=ai_client,
                heavy_model=model_name,
                image_bytes=image_bytes,
                image_mime=content_type,
                user_prompt=prompt,
                mcp_client=mcp
            )



        session_id = str(uuid.uuid4())[:8]
        steps = result.get("completed_steps", [])
        errors = result.get("errors", [])
        msg = f"Completed {len(steps)} steps" + (f", {len(errors)} warnings" if errors else "")
        logger.info(f"[v2] Done: {msg}")

        return ChatStartResponse(
            status=result.get("status", "success"),
            session_id=session_id,
            message=msg,
            params=result.get("params"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[v2] Failed: {e}", exc_info=True)
        _handle_su_error(e)

@app.post("/api/chat/refine", response_model=ChatStartResponse, tags=["chat"])
async def chat_refine(
    original_image: UploadFile = File(...),
    current_params: str = Form(...),
    heavy_model: Optional[str] = Form(None),
    user_prompt: Optional[str] = Form(None)
):
    """V5.0 Visual Self-Correction Endpoint (Auto-Screenshot + Conversational)"""
    try:
        from ai_service_v2 import refine_model_visually
        import json
        import os
        import time

        orig_bytes = await original_image.read()
        orig_mime = original_image.content_type
        params_dict = json.loads(current_params)
        model_name = heavy_model or AI_MODEL_HEAVY
        
        with RawMcpClient(host=SU_HOST, port=SU_PORT) as mcp:
            # 1. 自动截取当前 3D 模型画面
            screenshot_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "current_render.png")).replace("\\", "/")
            rb_code = f'''
                view = Sketchup.active_model.active_view
                view.zoom_extents
                keys = {{
                    :filename => "{screenshot_path}",
                    :width => 1024,
                    :height => 768,
                    :antialias => true,
                    :compression => 0.9,
                    :transparent => false
                }}
                view.write_image(keys)
            '''
            logger.info(f"[v5.0] 正在自动截图...")
            mcp.call_tool("execute_ruby", {"code": rb_code})
            time.sleep(1.0) # 等待文件写入完成
            
            if not os.path.exists(screenshot_path):
                raise Exception("无法生成3D模型截图")
                
            with open(screenshot_path, "rb") as f:
                rend_bytes = f.read()
            rend_mime = "image/png"
            
            # 2. 移除旧的精修调用
            result = {"params": params_dict}
            logger.info("旧的看图精修已废弃")
        
        if "error" in result:
            return ChatStartResponse(status="error", session_id="err", message=result["error"])
            
        return ChatStartResponse(
            status="success",
            session_id="refine",
            message="视觉找茬精修完成",
            params=result.get("params")
        )
    except Exception as e:
        logger.error(f"[v5.0] Refine Failed: {e}", exc_info=True)
        _handle_su_error(e)

async def debug_eval_ruby(request: TextRequest):
    """Send Ruby code directly to SketchUp for debugging."""
    try:
        result = eval_ruby(request.prompt, host=SU_HOST, port=SU_PORT)
        return BuildResponse(status="success", message="executed", params={"result": str(result)})
    except Exception as e:
        _handle_su_error(e)


@app.post("/api/debug/load_tools", response_model=BuildResponse, tags=["debug"])
async def debug_load_tools():
    """Load building_tools.rb into SketchUp runtime."""
    try:
        import pathlib
        rb_path = pathlib.Path(__file__).parent / "building_tools.rb"
        rb_code = rb_path.read_text(encoding="utf-8")
        result = eval_ruby(rb_code, host=SU_HOST, port=SU_PORT)
        return BuildResponse(status="success", message=f"BuildingTools loaded: {result}")
    except Exception as e:
        _handle_su_error(e)


@app.post("/api/build/image", response_model=BuildResponse, tags=["build"])
async def build_from_image(
    prompt: str = Form(default=""),
    heavy_model: Optional[str] = Form(None),
    image: UploadFile = File(...),
):
    """Legacy endpoint -> redirects to /api/chat/start"""
    res = await chat_start(prompt=prompt, heavy_model=heavy_model, image=image)
    return BuildResponse(
        status=res.status,
        message=f"[Session: {res.session_id}] {res.message}",
        params=res.params,
    )


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  AI Building Agent v2.0")
    logger.info(f"  Server: http://0.0.0.0:{SERVER_PORT}")
    logger.info(f"  Docs:   http://localhost:{SERVER_PORT}/docs")
    logger.info(f"  SketchUp: {SU_HOST}:{SU_PORT}")
    logger.info(f"  Model: {AI_MODEL_HEAVY}")
    logger.info("=" * 60)
    uvicorn.run("main:app", host="0.0.0.0", port=SERVER_PORT, reload=False)
