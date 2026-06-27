# ai_service_v2.py - v3.0 Full Architectural Detail Engine
import json
import logging
import base64
import time
from typing import Optional, Dict, Any, List
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ==================== 核心提示词 ====================

VISION_SYSTEM_PROMPT = """你是一名世界顶级建筑分析师，拥有 20 年建筑细部设计经验。
你的任务是用极其精确的眼光观察图片中的建筑，提取完整的建筑参数（包括宏观造型与微观细节），以 JSON 格式输出。

  == 建模策略 ==

  【极端重要：绝对零遗漏原则】
  你的眼睛必须像高精度雷达一样，从左到右、从下到上扫描整个建筑，绝对不能遗漏任何一个元素！
  - 所有的侧翼、附属建筑（无论是左边、右边还是后面）。
  - 所有的窗户（尤其是主楼一楼的窗户、侧面墙上的窗户，务必逐个数清楚）。**如果同一面墙上有多个窗户（例如右侧墙有2个窗户），你必须在 `windows` 数组中输出2个独立的 JSON 对象！绝对不能合并或遗漏！**
  - 所有的门（包括正门、侧门、车库门，一个都不能少）。
  - 所有的老虎窗、雨棚、门廊、烟囱、檐口装饰。
  如果你漏掉了任何一个元素，生成的模型就会残缺不全。请在 reasoning 字段中强迫自己逐一列出这些元素，然后再输出 JSON。

  【极端重要：体块拆解铁律】
将建筑拆解为多个矩形积木块（blocks）。如果一个复杂的裙房或侧翼同时包含了“斜坡屋顶”和“平顶露台”，**绝对不允许用一个 Block 来糊弄！必须将其严格拆分为 2 个独立的 Block**（例如：左翼的斜顶房间作为一个独立 Block，紧挨着它的露台作为另一个独立 Block）。每个 block 拥有独立的位置、尺寸、屋顶和细节。
所有尺寸单位：英寸。坐标原点(0,0)通常在主体建筑左前角。x轴=建筑正面宽度方向，y轴=深度方向。

【极端重要：侧翼屋顶与连接铁律】
1. **拓扑关联**：对于非主楼的侧翼，绝对禁止随意猜测绝对坐标 (x,y)！必须使用 `attachment` 字段，严格描述它吸附在主楼的哪一面，以及退进/突出的尺寸。
2. **屋顶类型**：对于附着在主楼旁边的侧翼，如果是传统的两面坡，`roof.type` 必须强制设定为 `gable` 并且 `direction` 设定为 `side-side`。**绝对禁止**误写成 `hip`（四坡顶），否则会导致侧翼边缘塌陷成奇怪的斜坡！

【极端重要：交叉山墙 (Cross-Gable) vs 老虎窗 (Dormer)】
如果建筑正面有两个巨大的三角形凸起，且它们的**前墙与一楼外墙完全平齐（上下贯通）**，它们**绝对不是**老虎窗 (dormer)！你必须将它们作为独立的 Block（依附在主楼 front 面，roof.type 为 gable，direction 为 front-back）。只有那些孤立地长在屋顶斜坡中间、体积较小的小窗户，才能使用 `dormers` 字段！对于侧翼上的小老虎窗，一定要控制其 width 不要过宽（如 48-72 英寸），避免夸张变形。

  【极端重要：绝对不要遗漏门窗】
  很多时候 AI 会忽略一楼的窗户或者侧翼上的车库门。请像扫描仪一样，逐个检查每一面墙（特别是主楼一楼门旁边的窗户，以及侧翼上的车库门或窗户）。
  如果侧边有车库门，请使用 doors 字段并设定 style 为 garage。不要漏掉主楼右侧或左侧的一楼窗户！
  
  == 输出 JSON 格式 ==
  {
    "reasoning": "<必须先在这里用中文写下你的二维观察：比如主楼左侧一楼和二楼各有几个窗，右侧一楼和二楼各有几个窗，门旁边是否有窗户，侧翼是否有车库门，千万不要遗漏！同时，请估算照片的拍摄角度>",
  "spatial_reasoning": {
    "depth_analysis": "<基于透视原理，深度剖析主楼与两侧翼的前后错落关系，比如：左侧翼比主楼凸出多少英寸？主楼的进深大约是多少？>",
    "perspective_correction": "<【极端重要】透视畸变补偿测算：这是一张带有极点透视的照片。离镜头远的部分（通常是左右两侧）会被严重压缩（Foreshortening）。请你在这里强制进行透视校正推理，例如：『右侧建筑离镜头更远，图像上看起来只有左侧一半宽，但在真实物理世界中，它的实际宽度应该是它的 1.5 倍，因此参数应设定为 XXX 英寸。』必须把放大补偿的思考过程写出来，才能得出最终真实的 width 和 x_offset 参数！>",
    "2d_grid_layout": "<用文字绘制一个简易的俯视二维网格关系（如：[后排：主楼] [前排左：左侧翼] [前排右：右侧翼]），并标明各体块之间的坐标绝对偏移关系(x,y)。警告：你在下方填写的所有 position(x,y) 必须与此处的分析严格吻合！>"
  },
  "camera": {
    "azimuth": <水平方位角(-180到180，正对为0，偏左拍为负数，偏右拍为正数，例如-30)>,
    "elevation": <仰角(-90到90，站在平地仰拍一般为15，平视为0)>,
    "fov": <视野角度(35-90，通常为45)>
  },
  "blocks": [
    {
      "id": "main_body",
      "shape": "<rectangle|octagon|cylinder> (极端重要：如果发现是中式宝塔或八角塔，必须为每一层设置 octagon；如果是欧式圆柱塔楼，必须设置 cylinder！默认 rectangle)",
      "position": {"x": 0, "y": 0}, 
      "attachment": {
        "parent": "<依附的父级block_id，如果是主楼则设为空>",
        "face": "<front|back|left|right|top> (注意：如果是往高处盖的复式/宝塔/退台，必须选 top)",
        "align": "<front|back|left|right|center> (例如依附在左右墙，选front表示与前墙对齐；选center表示居中)",
        "offset": <偏离对齐基准的英寸数(正数表示向后/向右退缩，产生层次感，例如退缩36英寸)>
      },
      "size": {"width": <英寸>, "depth": <英寸>, "height": <墙高英寸>},
      "roof": {
        "type": "<gable|hip|shed|flat|chinese_hip>",
        "direction": "<front-back|side-side>",
        "pitch_deg": <15-60>,
        "overhang": <12-24>,
        "fascia_height": <屋檐封檐板厚度, 通常4-8>
      },
      "baseboard": {"height": <0-18>, "protrusion": <0-6>},
      "belt_courses": [
        {"z_height": <距地英寸>, "protrusion": <2-4>, "height": <3-6>}
      ],
      "verandas": [
        {
          "face": "<front|back|left|right>",
          "x_offset": <起始距该面左边缘距离>, "width": <覆盖宽度>,
          "depth": <深度, 比如48-120>,
          "height": <高度, 比如108-144>,
          "style": "<shed|flat>"
        }
      ],
    "windows": [
      {
        "face": "<front|back|left|right>",
        "x_offset": <距该面左边缘>, "z_offset": <距地面高度(一楼36，二楼约120)>,
        "width": <宽>, "height": <高>,
        "panes_x": <横向玻璃格数>, "panes_y": <纵向玻璃格数>,
        "style": "<rectangular|arch_top|round|bay_window|picture|awning|chinese_lattice>",
        "has_sill": <true|false 立体窗台>,
        "has_louvers": <true|false 两侧百叶窗板>,
        "frame_thickness": <窗框厚度, 通常2-4>,
        "mullion_thickness": <窗棂/内部玻璃分隔条厚度, 通常1-2>,
        "sill_protrusion": <窗台向外凸出深度, 通常2-6>
      }
    ],
    
        "dormers": [
      {
        "face": "<front|back|left|right>",
        "x_offset": <距该面左边缘>, "z_offset": <距地面高度，通常在屋顶面上(一般一楼100-120)>,
        "width": <宽>, "height": <高>,
        "style": "<gable|shed>",
        "window_style": "<rectangular|arch_top>"
      }
    ],
    "canopies": [
      {
        "face": "<front|back|left|right>",
        "x_offset": <距该面左边缘>, "z_offset": <距地面高度>,
        "width": <宽>, "depth": <突出深度>,
        "style": "<gable|shed|flat>",
        "support": "<none|brackets|posts>"
      }
    ],
    "doors": [
      {
        "face": "<front|back|left|right>",
        "x_offset": <距该面左边缘>,
        "width": <宽(双开门通常60-72)>, "height": <高>,
        "style": "<solid|glass|french|sliding|garage_roller|garage_panel>",
        "panes_x": <横向玻璃格数>, "panes_y": <纵向玻璃格数>,
        "arch_top": <true/false, 是否为拱形门>,
        "has_transom": <true/false, 顶部是否有气窗>,
        "frame_depth": <门框向外凸出厚度, 默认2>,
        "leaf_recess": <门板向内凹陷深度, 默认2>
      }
    ],
      "chimneys": [
        {"x_ratio": <0-1>, "y_ratio": <0-1>, "width": <宽>, "depth": <深>, "height": <高出屋脊>}
      ],
      "steps": [
        {"face": "<front|back|left|right>", "x_offset": <偏移>, "width": <宽>, "num_steps": <1-6>}
      ],
      "columns": [
        {
          "face": "<front|back|left|right>",
          "x_start": <起始x偏移>, "x_end": <结束x偏移>,
          "num": <2-6>, "height": <与墙同高>,
          "width": <柱子宽度, 默认8-16>,
          "style": "<round|craftsman|square|fluted>"
        }
      ],
      "balconies": [
        {
          "face": "<front|back|left|right>",
          "x_offset": <偏移>, "z_offset": <楼层高度>,
          "width": <宽>, "depth": <24-48>,
          "rail_style": "<solid|baluster>"
        }
      ],
      "pilasters": [
        {"face": "<front|back|left|right>", "num": <2-6>, "depth": <2-4>, "width": <8-14>}
      ],
      "timber_framing": [
        {"face": "<front|back|left|right>", "style": "<cross_brace|left_brace|right_brace|grid>", "depth": <突出厚度,通常2>, "width": <木条宽度,通常6>}
      ],
      "quoins": {"enabled": <true|false>, "block_w": <10-16>, "block_h": <6-10>, "spacing": <3-5>, "depth": <2-3>},
      "finial": <true|false>,
      "terraces": [
        {"height": <护栏高度, 默认36>}
      ],
      "details": {
        "wall_lamps": [{"face": "<front|back|left|right>", "x_offset": <...>, "z_offset": <...>}],
        "corbels": [{"face": "<front|back|left|right>", "x_offset": <...>, "z_offset": <...>}]
      }
    }
  ],
  "platforms": [
    {"x": <坐标>, "y": <坐标>, "width": <宽>, "depth": <深>, "height": <高度>, "has_planters": <true/false>, "paving_grid": <true/false>}
  ],
  "fences": [
    {"p1": {"x": <坐标>, "y": <坐标>}, "p2": {"x": <坐标>, "y": <坐标>}, "height": <高度>}
  ],
  "texture_prompts": {
    "roof": "<请仔细观察原图屋顶的材质（如：红色陶土瓦片、黑色沥青瓦、生锈金属波纹板等），用纯英文写一段专用于 AI 生图的材质 Prompt，不需要写 seamless 等词汇，只需描述颜色和材质细节>",
    "wall": "<请仔细观察原图墙体的材质（如：白色风化石膏墙、红砖、横向灰色木挂板等），用纯英文写一段材质 Prompt>"
  },
  "materials": {
    "body": "#HEX颜色",
    "roof": "#HEX颜色",
    "trim": "#HEX颜色",
    "door": "#HEX颜色",
    "garage_door": "#HEX颜色 (如白色则为#FFFFFF)",
    "accent": "#HEX颜色",
    "ground": "#HEX颜色"
  },
  "wall_texture": "<siding | brick | smooth>",
  "ground": {"enabled": true, "path_width": <36-60>}
}

== 建筑几何常识推理规则 (CRITICAL) ==
1. 【门窗不悬空与不越界】：门必须接触地面(除非有台阶)，窗户和门的总宽度与位置 (x_offset + width) 绝不能超出所在墙体的总长度；其高度 (z_offset + height) 绝不能超出墙体高度。
2. 【物理对齐推理】：观察原图，同一楼层的窗户通常在水平方向上是对齐的（即它们的 z_offset 应该相等）。如果上下楼层有窗户，它们通常在垂直方向是对齐的（即它们的 x_offset 或中心点应对齐）。
3. 【相对比例推理】：不要死记硬背尺寸，而要观察原图中门与窗、第一层与第二层的相对高度比例，以此来推算合理的高度 (height) 与离地距离 (z_offset)。
4. 【相机方位强制映射】：照片中正对镜头的那个主要立面，必须标记为 "front"。照片中左侧的面标记为 "left"，右侧为 "right"。
5. 【1:1 像素级复刻】：必须精确地数出每个立面的门窗数量并在 "reasoning" 字段中写明你的推导过程（如：一楼左边1个门，右边2个窗，二楼3个窗排成一排对齐）。不要合并，也不要遗漏。
6. 【极度穷尽细节 (CRITICAL)】：为了保证建筑还原的绝对精准度，你必须像拿着放大镜一样去寻找图片里的每一个建筑特征。
7. 【半木骨架识别 (CRITICAL)】：如果建筑墙面上（尤其是山墙和侧墙）有明显的斜向交叉木条（Tudor / 传统欧洲农舍风格），必须使用 `"timber_framing": [{"face": "front", "style": "cross_brace"}]`！**严禁使用 pilasters，因为系统已不再支持 pilasters。**

只输出 JSON，禁止任何其他文字。
"""

def _get_loader_ruby() -> str:
    import os
    rb_path = os.path.join(os.path.dirname(__file__), "building_tools.rb")
    try:
        with open(rb_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"puts 'ERROR loading building_tools.rb: {e}'"

def generate_front_view_image(ai_client, original_image_bytes: bytes) -> bytes:
    """
    Plan A: Use an Image Generation model to create a flat front view.
    """
    logger.info("[Plan A] 尝试调用图像生成模型生成正面图...")
    try:
        # Since we don't know the exact image-to-image API the user has configured,
        # we will use the OpenAI client (if available) to call DALL-E or a compatible endpoint,
        # or just log that it requires a specific Image-to-Image endpoint.
        # For demonstration of Plan A, we will pass the image to the Vision model
        # and ask it to describe the front view, then (if text-to-image is available) generate it.
        # However, real Image-to-Image (like Stable Diffusion img2img or ControlNet) is needed for accuracy.
        
        # Here we insert a placeholder or an API call to the user's preferred image generator.
        logger.warning("[Plan A] 当前环境缺少直接的 img2img (ControlNet) API。将跳过物理生成，采用大模型双重视角推理模拟。")
        return original_image_bytes # Fallback
    except Exception as e:
        logger.error(f"[Plan A] 生成正面图失败: {e}")
        return original_image_bytes

def analyze_image_and_build(
    ai_client, 
    heavy_model: str,
    image_bytes: bytes,
    image_mime: str,
    mcp_client,
    user_prompt: str = ""
) -> Dict[str, Any]:
    logger.info("[v5.0] 开始 视觉分析 + 逻辑推理自纠错建模")

    # Plan A: 生成正面图
    front_view_bytes = generate_front_view_image(ai_client, image_bytes)

    # 初次提取 (蓝军)
    params = _analyze_image(ai_client, heavy_model, image_bytes, image_mime, user_prompt)
    if "error" in params:
        return {"status": "error", "message": params["error"]}

    # --- Multi-Agent Review (红军审查) ---
    logger.info("[v4.0] 启动红军审查者 (Multi-Agent Review)...")
    import json
    review_prompt = f"""你是红军架构审查员。蓝军（初级分析师）刚才分析了这张建筑图片，并生成了以下 JSON 参数：
{json.dumps(params, ensure_ascii=False)}

请用极其苛刻的眼光对比原图与上述 JSON：
1. 【检查漏报】：蓝军是否遗漏了建筑的侧翼附房、车库？（如果图片明明是多个体块拼接，但 JSON 里却只有一个 main block，这是严重事故！必须拆分添加）
2. 【检查细节】：是否漏掉了墙边的小窗户、侧窗、烟囱或独立门廊？

请直接输出一份【完整修复并补充后】的终极版 JSON（保留正确的，补上缺失的）。
如果你认为蓝军完美无缺，请原样输出原 JSON。

只输出 JSON，禁止任何文字。"""
    
    reviewed_params = _analyze_image(ai_client, heavy_model, image_bytes, image_mime, review_prompt)
    if "error" not in reviewed_params:
        params = reviewed_params
        logger.info("[v4.0] 红军审查完毕，已应用补充补丁。")
    else:
        logger.warning(f"[v4.0] 红军审查异常，退回蓝军方案: {reviewed_params['error']}")

    # 循环尝试建模，利用 Ruby 抛出的逻辑错误进行自动自我纠正
    max_retries = 2
    for attempt in range(max_retries + 1):
        logger.info(f"[v5.0] 正在渲染 (Attempt {attempt+1}/{max_retries+1})")
        build_result = _build_from_params(params, mcp_client, _get_loader_ruby(), image_bytes)
        
        # 寻找逻辑错误
        logical_errors = [err for err in build_result.get("errors", []) if "Logical Error" in err]
        
        if not logical_errors:
            # 如果没有逻辑越界错误，直接完成
            return build_result
            
        if attempt == max_retries:
            logger.warning("[v5.0] 已达到最大重试次数，返回带错误的最终模型。")
            return build_result
            
        # 把逻辑错误发回给大模型进行纠错
        error_msg = "; ".join(logical_errors)
        logger.warning(f"[v5.0] 捕获到物理几何逻辑错误，正在请求大模型基于数据自纠错: {error_msg}")
        
        correction_prompt = f"""
你的上一次生成的 JSON 参数在渲染时触发了以下物理几何边界错误：
{error_msg}

请不要修改没有报错的其他完好结构，专门针对这些报错的门窗（调整它们的 x_offset, z_offset, width, height），使它们满足物理世界的常识，不要超出墙的边界。
你必须返回一份完整修复后的 JSON。
"""
        params = _analyze_image(ai_client, heavy_model, image_bytes, image_mime, correction_prompt)
        if "error" in params:
            return build_result # 如果纠错失败，直接返回上一次的结果
            
    return build_result

def _build_from_params(params: dict, mcp_client, loader_ruby: str, image_bytes: bytes = None) -> dict:
    # Step 2: 加载工具库
    loader_result = mcp_client.call_tool("execute_ruby", {"code": loader_ruby})
    logger.info(f"[v3.0] 工具库加载: {loader_result}")

    results = []
    errors = []

    def run_ruby(code: str, desc: str) -> str:
        try:
            result = mcp_client.call_tool("execute_ruby", {"code": code})
            if result and not str(result).startswith("ERROR"):
                logger.info(f"[v3.0] ✓ {desc}")
                results.append(desc)
            else:
                logger.warning(f"[v3.0] ✗ {desc}: {result}")
                errors.append(f"{desc}: {result}")
            return str(result) if result else ""
        except Exception as e:
            logger.error(f"[v3.0] ✗✗ {desc}: {e}")
            errors.append(f"{desc}: {e}")
            return ""

    run_ruby("BuildingTools.clear_scene", "清场")
    time.sleep(0.3)

    blocks = params.get("blocks", [])
    if not blocks and "body" in params:
        blocks = [{
            "id": "main", "position": {"x": 0, "y": 0},
            "size": params.get("body", {}),
            "roof": params.get("roof", {}),
            "windows": params.get("windows", []),
            "doors": params.get("doors", []),
            "baseboard": params.get("baseboard", {}),
            "chimneys": [params.get("chimney")] if params.get("chimney") else [],
            "steps": [params.get("steps")] if params.get("steps") else []
        }]

    # --- Topological Graph Resolution ---
    block_dict = {b.get("id", f"block_{i}"): b for i, b in enumerate(blocks)}
    
    def resolve_pos(b, visited=None):
        if visited is None: visited = set()
        bid = b.get("id", "")
        if bid in visited: return 0, 0
        visited.add(bid)
        
        if "calculated_x" in b: return b["calculated_x"], b["calculated_y"], b.get("calculated_z", 0)
        
        attach = b.get("attachment")
        if attach and attach.get("parent") and attach.get("parent") in block_dict:
            parent = block_dict[attach.get("parent")]
            px, py, pz = resolve_pos(parent, visited)
            pw = parent.get("size", {}).get("width", 0)
            pd = parent.get("size", {}).get("depth", 0)
            ph = parent.get("size", {}).get("height", 0)
            bw = b.get("size", {}).get("width", 0)
            bd = b.get("size", {}).get("depth", 0)
            
            face = attach.get("face", "right")
            align = attach.get("align", "front")
            offset = attach.get("offset", 0)
            
            z = pz
            if face == "top":
                z = pz + ph
                if align == "center":
                    x = px + pw/2.0 - bw/2.0
                    y = py + pd/2.0 - bd/2.0
                else:
                    x = px + pw/2.0 - bw/2.0
                    y = py
            elif face == "right":
                x = px + pw
                if align == "center": y = py + pd/2.0 - bd/2.0 + offset
                elif align == "back": y = py + pd - bd - offset
                else: y = py + offset
            elif face == "left":
                x = px - bw
                if align == "center": y = py + pd/2.0 - bd/2.0 + offset
                elif align == "back": y = py + pd - bd - offset
                else: y = py + offset
            elif face == "front":
                y = py - bd
                if align == "center": x = px + pw/2.0 - bw/2.0 + offset
                elif align == "right": x = px + pw - bw - offset
                else: x = px + offset
            elif face == "back":
                y = py + pd
                if align == "center": x = px + pw/2.0 - bw/2.0 + offset
                elif align == "right": x = px + pw - bw - offset
                else: x = px + offset
            else:
                x = px; y = py
                
            b["calculated_x"] = x
            b["calculated_y"] = y
            b["calculated_z"] = z
            return x, y, z
            
        pos = b.get("position", {})
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        z = 0
        b["calculated_x"] = x
        b["calculated_y"] = y
        b["calculated_z"] = z
        return x, y, z

    for b in blocks:
        resolve_pos(b)

    for i, b in enumerate(blocks):
        bid = b.get("id", f"block_{i}")

        x = b.get("calculated_x", b.get("position", {}).get("x", 0))
        y = b.get("calculated_y", b.get("position", {}).get("y", 0))
        z = b.get("calculated_z", 0)
        size = b.get("size", {})
        w = size.get("width", 300)
        d = size.get("depth", 240)
        h = size.get("height", 108)

        # ── Block Body ──
        run_ruby(f'BuildingTools.build_block("{bid}", {x}, {y}, {w}, {d}, {h}, {z}, "{b.get("shape", "rectangle")}")', f"Block({bid})")
        time.sleep(0.15)

        # ── Baseboard ──
        bb = b.get("baseboard", {})
        if bb and bb.get("height", 0) > 0:
            run_ruby(f'BuildingTools.add_baseboard("{bid}", {bb["height"]}, {bb.get("protrusion", 3)})', f"Baseboard({bid})")
            time.sleep(0.1)

        # ── Roof ──
        rf = b.get("roof", {})
        if rf and rf.get("type"):
            run_ruby(f'BuildingTools.build_roof("{bid}", "{rf["type"]}", "{rf.get("direction","side-side")}", {rf.get("pitch_deg",35)}, {rf.get("overhang",16)})', f"Roof({bid})")
            time.sleep(0.2)

        # ── Belt Courses (腰线) ──
        for bc in b.get("belt_courses", []):
            if bc and bc.get("z_height", 0) > 0:
                run_ruby(f'BuildingTools.add_belt_course("{bid}", {bc["z_height"]}, {bc.get("protrusion",2.5)}, {bc.get("height",4)})', f"BeltCourse({bid})")
                time.sleep(0.1)

        # ── Verandas ──
        for ver in b.get("verandas", []):
            run_ruby(f'BuildingTools.add_veranda("{bid}", "{ver["face"]}", {ver.get("x_offset",0)}, {ver.get("width",w)}, {ver.get("depth",72)}, {ver.get("height",120)}, "{ver.get("style","shed")}")', f"Veranda({bid})")
            time.sleep(0.1)

        # ── Dormers ──
        for j, dormer in enumerate(b.get("dormers", [])):
            if not dormer: continue
            face = dormer.get("face", "front")
            xo = dormer.get("x_offset", 0); zo = dormer.get("z_offset", 120) + z
            ww = dormer.get("width", 36); wh = dormer.get("height", 48)
            style = dormer.get("style", "gable")
            w_style = dormer.get("window_style", "rectangular")
            run_ruby(f'BuildingTools.add_dormer("{bid}", "{face}", {xo}, {zo}, {ww}, {wh}, "{style}", "{w_style}")', f"Dormer({bid}_{j})")
            time.sleep(0.1)

        # ── Canopies ──
        for j, canopy in enumerate(b.get("canopies", [])):
            if not canopy: continue
            face = canopy.get("face", "front")
            xo = canopy.get("x_offset", 0); zo = canopy.get("z_offset", 90) + z
            ww = canopy.get("width", 60); wd = canopy.get("depth", 36)
            style = canopy.get("style", "gable")
            supp = canopy.get("support", "brackets")
            run_ruby(f'BuildingTools.add_canopy("{bid}", "{face}", {xo}, {zo}, {ww}, {wd}, "{style}", "{supp}")', f"Canopy({bid}_{j})")
            time.sleep(0.1)

        # ── Doors ──
        for j, door in enumerate(b.get("doors", [])):
            if not door: continue
            face = door.get("face", "front")
            xo = door.get("x_offset", 0)
            
            # --- Python Auto-Snapping (X Grid) ---
            xo = round(xo / 4.0) * 4
            
            dw = door.get("width", 36); dh = door.get("height", 84)
            style = door.get("style", "solid")
            px = door.get("panes_x", 1); py = door.get("panes_y", 1)
            arch = str(door.get("arch_top", False)).lower()
            transom = str(door.get("has_transom", False)).lower()
            fd = door.get("frame_depth", 2.0)
            lr = door.get("leaf_recess", 2.0)
            run_ruby(f'BuildingTools.add_door("{bid}", "{face}", {xo}, {dw}, {dh}, "{style}", {px}, {py}, {arch}, {transom}, {fd}, {lr})', f"Door({bid}_{j})")
            time.sleep(0.1)

        # ── Quoins (角隅石) ──
        qo = b.get("quoins", {})
        if qo and qo.get("enabled"):
            run_ruby(f'BuildingTools.add_quoins("{bid}", {qo.get("block_w",12)}, {qo.get("block_h",8)}, {qo.get("spacing",3)}, {qo.get("depth",2)})', f"Quoins({bid})")
            time.sleep(0.1)

        # ── Pilasters (壁柱) ──
        for j, pl in enumerate(b.get("pilasters", [])):
            if pl:
                run_ruby(f'BuildingTools.add_pilasters("{bid}", "{pl["face"]}", {pl.get("num",2)}, {pl.get("depth",3)}, {pl.get("width",10)})', f"Pilasters({bid}_{j})")
                time.sleep(0.1)

        # ── Columns (立柱) ──
        for j, col in enumerate(b.get("columns", [])):
            if col:
                run_ruby(f'BuildingTools.add_columns("{bid}", "{col["face"]}", {col.get("x_start",0)}, {col.get("x_end",w)}, {col.get("num",2)}, {col.get("height",h)}, "{col.get("style","square")}")', f"Columns({bid}_{j})")
                time.sleep(0.15)

        # ── Chimneys ──
        for j, ch in enumerate(b.get("chimneys", [])):
            if ch and ch.get("x_ratio") is not None:
                run_ruby(f'BuildingTools.build_chimney("{bid}", {ch["x_ratio"]}, {ch.get("y_ratio",0.5)}, {ch["width"]}, {ch["depth"]}, {ch["height"]})', f"Chimney({bid}_{j})")
                time.sleep(0.1)

        # ── Windows ──
        for j, win in enumerate(b.get("windows", [])):
            if not win: continue
            face = win.get("face", "front")
            xo = win.get("x_offset", 0); zo = win.get("z_offset", 36) + z
            
            # --- Python Auto-Snapping (X Grid & Z Floor Datums) ---
            xo = round(xo / 4.0) * 4
            for floor_z in [36, 136, 236]:
                if abs(zo - floor_z) <= 12:
                    zo = floor_z + z
                    break
                    
            ww = win.get("width", 36); wh = win.get("height", 48)
            px = win.get("panes_x", 2); py = win.get("panes_y", 2)
            style = win.get("style", "rectangular")
            has_sill = str(win.get("has_sill", True)).lower()
            has_louvers = str(win.get("has_louvers", False)).lower()
            ft = win.get("frame_thickness", 2.0)
            mt = win.get("mullion_thickness", 1.0)
            sp = win.get("sill_protrusion", 2.0)
            run_ruby(f'BuildingTools.add_window("{bid}", "{face}", {xo}, {zo}, {ww}, {wh}, {px}, {py}, "{style}", {has_sill}, {has_louvers}, {ft}, {mt}, {sp})', f"Window({bid}_{j})")
            time.sleep(0.1)
            

        # ── Balconies ──
        for j, bal in enumerate(b.get("balconies", [])):
            if not bal: continue
            run_ruby(f'BuildingTools.add_balcony("{bid}", "{bal["face"]}", {bal.get("x_offset",0)}, {bal.get("z_offset",108)}, {bal.get("width",72)}, {bal.get("depth",36)}, "{bal.get("rail_style","baluster")}")', f"Balcony({bid}_{j})")
            time.sleep(0.15)

        # ── Steps ──
        for j, stp in enumerate(b.get("steps", [])):
            if stp and stp.get("num_steps", 0) > 0:
                run_ruby(f'BuildingTools.build_steps("{bid}", "{stp["face"]}", {stp.get("x_offset",0)}, {stp.get("width",w*0.4)}, {stp["num_steps"]})', f"Steps({bid}_{j})")
                time.sleep(0.1)

        # ── Ridge Finial ──
        if b.get("finial"):
            rf2 = b.get("roof", {})
            run_ruby(f'BuildingTools.add_ridge_finial("{bid}", "{rf2.get("direction","front-back")}")', f"Finial({bid})")
            time.sleep(0.1)

        # ── Terraces ──
        for t in b.get("terraces", []):
            if t:
                run_ruby(f'BuildingTools.add_terrace("{bid}", {t.get("height", 36)})', f"Terrace({bid})")
                time.sleep(0.1)

    # ── Ground Plane ──
    gnd = params.get("ground", {})
    if gnd and gnd.get("enabled", False):
        all_x = [b.get("position",{}).get("x",0) for b in blocks]
        all_y = [b.get("position",{}).get("y",0) for b in blocks]
        min_x = min(all_x) - 120; min_y = min(all_y) - 240
        max_x = max([b.get("position",{}).get("x",0)+b.get("size",{}).get("width",300) for b in blocks]) + 120
        max_y = max([b.get("position",{}).get("y",0)+b.get("size",{}).get("depth",240) for b in blocks]) + 120
        pw = gnd.get("path_width", 48)
        run_ruby(f'BuildingTools.add_ground_plane({min_x}, {min_y}, {max_x-min_x}, {max_y-min_y}, {pw})', "地面")
        time.sleep(0.1)

    # ── Materials ──
    mats = params.get("materials", {})
    body_c = mats.get("body", "#F0E8D5")
    roof_c = mats.get("roof", "#5C4A38")
    trim_c = mats.get("trim", "#FFFFFF")
    door_c = mats.get("door", "#6B3A1F")
    garage_c = mats.get("garage_door", "#FFFFFF")
    accent_c = mats.get("accent", "#808080")
    ground_c = mats.get("ground", "#5A7247")
    
    roof_tex_path = ""
    wall_tex_path = ""
    if "texture_prompts" in params:
        try:
            import os
            import concurrent.futures
            
            temp_dir = os.path.join(os.path.dirname(__file__), "textures")
            os.makedirs(temp_dir, exist_ok=True)
            
            def generate_ai_texture(prompt_text, filename):
                try:
                    full_prompt = f"{prompt_text}, perfectly seamless, tileable texture, flat frontal lighting, 4K resolution, highly detailed, architectural material, no shadows, no perspective, no lighting gradient"
                    result = client.models.generate_images(
                        model='gemini-2.5-flash-image',
                        prompt=full_prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type="image/jpeg",
                            aspect_ratio="1:1"
                        )
                    )
                    for generated_image in result.generated_images:
                        import io
                        from PIL import Image
                        image = Image.open(io.BytesIO(generated_image.image.image_bytes))
                        image.save(filename)
                        return True
                except Exception as ex:
                    logger.warning(f"Image gen failed for '{prompt_text}': {ex}")
                return False

            prompts = params.get("texture_prompts", {})
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                if "roof" in prompts and prompts["roof"]:
                    rp = os.path.abspath(os.path.join(temp_dir, "ai_roof_tex.jpg")).replace("\\", "/")
                    futures[executor.submit(generate_ai_texture, prompts["roof"], rp)] = ("roof", rp)
                if "wall" in prompts and prompts["wall"]:
                    wp = os.path.abspath(os.path.join(temp_dir, "ai_wall_tex.jpg")).replace("\\", "/")
                    futures[executor.submit(generate_ai_texture, prompts["wall"], wp)] = ("wall", wp)
                
                for future in concurrent.futures.as_completed(futures):
                    tex_type, path = futures[future]
                    success = future.result()
                    if success:
                        if tex_type == "roof":
                            roof_tex_path = path
                        elif tex_type == "wall":
                            wall_tex_path = path
        except Exception as e:
            logger.warning(f"V10 Texture Extraction Failed: {e}")
    
    run_ruby(f'BuildingTools.apply_materials("{body_c}", "{roof_c}", "{trim_c}", "{door_c}", "{accent_c}", "{ground_c}", "{garage_c}", "{roof_tex_path}", "{wall_tex_path}")', "材质涂装")
    time.sleep(0.2)

    # ── Platforms ──
    for p in params.get("platforms", []):
        hp = str(p.get("has_planters", False)).lower()
        pg = str(p.get("paving_grid", False)).lower()
        run_ruby(f'BuildingTools.add_platform({p.get("x",0)}, {p.get("y",0)}, {p.get("width",100)}, {p.get("depth",100)}, {p.get("height",6)}, {hp}, {pg})', "Platform")
        time.sleep(0.1)

    # ── Fences ──
    for f in params.get("fences", []):
        p1 = f.get("p1", {})
        p2 = f.get("p2", {})
        run_ruby(f'BuildingTools.add_fence(Sketchup.active_model.active_entities, [{p1.get("x",0)}, {p1.get("y",0)}, 0], [{p2.get("x",0)}, {p2.get("y",0)}, 0], {f.get("height", 36)})', "Fence")
        time.sleep(0.1)

    cam = params.get("camera", {})
    az = cam.get("azimuth", 0.0)
    el = cam.get("elevation", 15.0)
    fov = cam.get("fov", 45.0)
    run_ruby(f"BuildingTools.set_camera({az}, {el}, {fov})", "相机")
    
    run_ruby("BuildingTools.merge_geometry", "屋顶融合算法")
    
    wt = params.get("wall_texture", "smooth")
    if wt == "siding":
        run_ruby("BuildingTools.apply_siding(8.0)", "外墙挂板纹理")
    elif wt == "brick":
        run_ruby("BuildingTools.apply_siding(4.0)", "砖墙纹理")
    
    report = run_ruby("BuildingTools.report", "报告")

    logger.info(f"[v3.0] 完成! 成功: {len(results)}, 失败: {len(errors)}")
    return {
        "status": "success",
        "params": params,
        "completed_steps": results,
        "errors": errors,
        "report": report
    }

def refine_model_visually(
    ai_client,
    heavy_model: str,
    original_image_bytes: bytes,
    original_mime: str,
    rendered_image_bytes: bytes,
    rendered_mime: str,
    current_params: dict,
    mcp_client,
    user_prompt: str = ""
) -> dict:
    logger.info("[v5.0] 开始视觉找茬/对话式精修...")
    
    qa_prompt = f"""
你是一个极其严苛的建筑质检员 (QA) 和高级设计师。
图1是客户期望的建筑原图。
图2是根据你的初版数据生成的3D模型截图。

请严格对比两张图。主要检查：
1. 窗户和门的数量是否一一对应？（特别注意二楼是否漏了窗户，门上方是否有遗漏的窗户）
2. 位置、高度 (z_offset，绝不能用 y_offset) 是否正确？注意窗户离地高度必须使用 z_offset 字段（一楼约为36，二楼通常在120~140之间）。
3. 屋顶的类型和比例是否一致？

当前的 JSON 数据为：
{json.dumps(current_params, ensure_ascii=False)}

"""
    if user_prompt:
        qa_prompt += f"\n【用户额外的人工修改指令】：\n用户对目前的模型提出了明确的修改要求：“{user_prompt}”。请你必须优先满足用户的修改要求，调整对应的参数（例如调整位置、高度、样式等）。\n"
        
    qa_prompt += """
请在 `reasoning` 字段中详细指出图2漏掉或错误的所有细节（以及你对用户人工指令的响应方案），然后输出一份**完整且已修正的最终版 JSON**。
必须严格保持原有的 JSON 格式，修复缺失的窗户、修正错误的门、调整尺寸等。
"""
    try:
        from google.genai import types
        # 组装原图和截图
        part_orig = types.Part.from_bytes(data=original_image_bytes, mime_type=original_mime)
        part_render = types.Part.from_bytes(data=rendered_image_bytes, mime_type=rendered_mime)
        
        response = ai_client.models.generate_content(
            model=heavy_model,
            contents=[part_orig, part_render, qa_prompt]
        )
        text = response.text
        # 提取 JSON
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        else:
            json_str = text[text.find("{"):text.rfind("}")+1]
            
        new_params = json.loads(json_str)
        logger.info(f"[v5.0] 修正后参数: {json.dumps(new_params, ensure_ascii=False)[:400]}...")
        
        # 重新生成
        run_ruby = lambda code, desc: mcp_client.call_tool("execute_ruby", {"code": code})
        run_ruby("BuildingTools.clear_scene", "清场精修")
        time.sleep(0.5)
        
        # 生成新模型
        build_result = _build_from_params(new_params, mcp_client, _get_loader_ruby())
    except Exception as e:
        logger.error(f"[v5.0] QA失败: {e}")
        return {"error": str(e)}
    
    # Return the updated params and the build result
    return {
        "status": "success", 
        "params": new_params,
        "completed_steps": build_result.get("completed_steps", []),
        "report": build_result.get("report", "")
    }


def _analyze_image(
    ai_client, 
    model: str,
    image_bytes: bytes,
    image_mime: str,
    user_prompt: str = ""
) -> dict:
    import base64
    logger.info(f"[视觉分析] 使用模型: {model}")
    try:
        if "claude" in model.lower():
            import base64
            from anthropic import AnthropicVertex
            client = AnthropicVertex(region="global", project_id="project-12526171-d9fb-428a-b89")
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            
            sys_prompt = VISION_SYSTEM_PROMPT + "\n\nIMPORTANT: Output ONLY valid JSON, starting with { and ending with }, without markdown code blocks."
            
            message = client.messages.create(
                max_tokens=4000,
                system=sys_prompt,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt or "Analyze this building"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_mime,
                                "data": b64_img
                            }
                        }
                    ]
                }],
                model=model,
                temperature=0.1
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```json"):
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif raw.startswith("```"):
                raw = raw.split("```")[1].split("```")[0].strip()
        elif "gpt" in model.lower() or "4o" in model.lower():
            from openai import OpenAI
            import os
            # OpenAI config
            client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            
            sys_prompt = VISION_SYSTEM_PROMPT + "\\n\\nIMPORTANT: Output ONLY valid JSON, starting with { and ending with }, without markdown code blocks."
            
            messages = [
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt or "Analyze this building"},
                        {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{b64_img}"}}
                    ]
                }
            ]
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4000,
                temperature=0.1
            )
            raw = response.choices[0].message.content.strip()
            # Clean up potential markdown formatting
            if raw.startswith("```json"):
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif raw.startswith("```"):
                raw = raw.split("```")[1].split("```")[0].strip()
        else:
            from google.genai import types
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=image_mime)
            prompt = f"{VISION_SYSTEM_PROMPT}\\n\\nUser: {user_prompt}"
            response = ai_client.models.generate_content(
                model=model,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw = response.text.strip()
            
        logger.info(f"[视觉分析] 原始输出: {raw[:300]}")
        import json
        return json.loads(raw)
    except Exception as e:
        logger.error(f"[视觉分析] API调用失败: {e}")
        return {"error": str(e)}
