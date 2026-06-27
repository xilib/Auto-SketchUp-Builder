"""
ai_service.py
=============
MCP (Model Context Protocol) 架构的 Agent 服务（终极企业级并发版）
引入了 ThreadPoolExecutor 实现了 14节点微型智能体并行架构 (Micro-Agent DAG)。
"""

import base64
import logging
import json
import uuid
import os
import time
import random
import re
import concurrent.futures
from typing import Optional, List, Dict, Tuple

from openai import OpenAI
from mcp_client import RawMcpClient

logger = logging.getLogger(__name__)
SESSION_STORE = {}
SESSION_FILE = os.path.join(os.path.dirname(__file__), "data", "sessions.json")

def _save_sessions():
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    serializable_store = {}
    for sid, data in SESSION_STORE.items():
        s_data = {
            "messages": data.get("messages", []),
            "blueprint": data.get("blueprint", ""),
            "orig_img_mime": data.get("orig_img_mime", "image/jpeg"),
            "interaction_id": data.get("interaction_id")
        }
        if data.get("orig_img_bytes"):
            s_data["orig_img_bytes_b64"] = base64.b64encode(data["orig_img_bytes"]).decode("utf-8")
        serializable_store[sid] = s_data
        
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable_store, f, ensure_ascii=False, indent=2)

def _load_sessions():
    global SESSION_STORE
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                serializable_store = json.load(f)
            for sid, s_data in serializable_store.items():
                data = {
                    "messages": s_data.get("messages", []),
                    "blueprint": s_data.get("blueprint", ""),
                    "orig_img_mime": s_data.get("orig_img_mime", "image/jpeg"),
                    "interaction_id": s_data.get("interaction_id")
                }
                if s_data.get("orig_img_bytes_b64"):
                    data["orig_img_bytes"] = base64.b64decode(s_data["orig_img_bytes_b64"])
                SESSION_STORE[sid] = data
            logger.info(f"[Persistence] 成功恢复了 {len(SESSION_STORE)} 个历史会话。")
        except Exception as e:
            logger.error(f"[Persistence] 读取会话记录失败: {e}")

_load_sessions()

# ==========================================
# PROMPTS FOR PERCEPTION LAYER (STAGE 1)
# ==========================================
PROMPT_GEOMETRY = """你是一名【国际顶级计算几何学与建筑拓扑学博士 (Geometry & Topology AI)】。
你的视觉神经被设定为“仅识别欧几里得几何原语与布尔运算”。请完全忽略图片中的颜色、材质、光影和环境，只看建筑的骨架。
你的任务是将目标建筑拆解为可以通过代码精确还原的三维数学模型。

【思维链 (Chain of Thought) 约束】
请你严格遵循以下步骤进行深度思考与推理，最后输出结论：

[步骤1: 全局包围盒 (Bounding Box) 分析]
- 观察整栋建筑的外部轮廓，将其放进一个假想的长方体包围盒中。
- 描述这个长方体的粗略长宽比例（如：正面极宽、进深较浅，比例约 2:1:1.5）。

[步骤2: 拓扑结构分类 (Topological Classification)]
- 识别主建筑的形态分类（单体长方体、L型、U型、T型、圆柱形等）。
- 识别屋顶的严格拓扑类型（平屋顶 Flat、双坡屋顶 Gable、四坡屋顶 Hip、单坡 Shed、曼萨德 Mansard 等）。
- 如果是坡屋顶，估算其坡度（Pitch），例如是陡峭的 12/12 还是平缓的 4/12。

[步骤3: 布尔运算拆解 (Boolean Operations Breakdown)]
- 建筑是由哪些基础几何体（原语）通过“并集(Add)”和“差集(Subtract)”构成的？
- 举例：主屋体是长方体 (Box A)；屋顶是横跨其上的三角柱 (Prism B)；门是一个向内挖空的差集长方体 (Box C, Subtract)；烟囱是插入屋顶的细长方体 (Box D)。

[步骤4: 几何特征强化 (Geometric Features)]
- 观察屋檐 (Eaves/Cornices)：屋顶是否挑出墙体？悬挑的相对距离是多少？
- 观察基座 (Foundation)：建筑是否离地？有无明显凸起的裙边或地基块？

【输出要求】
请在 `<thinking>` 标签内完成上述四步的详细推理，最后在 `<output>` 标签内输出你极其严谨的几何拓扑报告。字数不得少于 500 字，必须使用专业的几何与建筑学术语。"""

PROMPT_MATERIAL = """你是一名【基于物理渲染的材质与光学分析专家 (PBR Material & Lighting AI)】。
你的视觉神经经过特殊校准，能够过滤掉物体的形状，仅解析其表面的物理属性和光子反射规律。
你的任务是为后端的 3D 渲染器提供绝对精确的材质参数。

【思维链 (Chain of Thought) 约束】
请严格按照以下步骤深度解析材质：

[步骤1: 漫反射与反照率 (Albedo & Base Color)]
- 提取建筑每一个主要部件（屋顶、主墙面、基座、门窗框、玻璃）的基础颜色。
- 绝对禁止仅使用“红色”、“蓝色”这种模糊词汇！你必须提供其在数字空间中最接近的 **Hex 颜色代码**（如 #3B5998）或严格的 RGB 值（如 59, 89, 152）。如果存在渐变或脏迹，请描述其基础主色。

[步骤2: 表面微观纹理 (Normal & Bump Characteristics)]
- 分析墙面：是光滑的涂料、粗糙的砖块、带有缝隙的木瓦（Shingles）、还是带有凹凸纹理的石材？
- 分析屋顶：是平滑的金属接缝、层叠的沥青瓦、还是立体的波浪形陶瓦？描述这些纹理的方向性和密集程度。

[步骤3: 光学属性与粗糙度 (Roughness, Metallic & Specular)]
- 评估每个材质的反光特性。
- 玻璃：反光率多少？是透明的、半透明磨砂的、还是像镜面一样反射天空的？
- 金属/木材/砖块：它们是哑光（High Roughness）还是光泽（Low Roughness）？有无金属光泽（Metallic）？

[步骤4: 场景光源方向 (Global Illumination)]
- 观察阴影的投射方向，推断主光源（太阳或灯光）是从图片的哪个方位（如左上方 45 度）照射过来的？这有助于后续 3D 建模时正确还原凹凸感。

【输出要求】
请在 `<thinking>` 标签内写下你对每一个像素的光学推导过程，然后在 `<output>` 标签内输出详细的材质参数字典，格式必须清晰严谨，字数不得少于 500 字。"""

PROMPT_SCALE = """你是一名【法医级尺度基准与逆向透视学AI (Forensic Scale & Reverse Perspective AI)】。
你的任务是从一张没有标注尺寸的 2D 照片中，利用人类社会的常识和物理法则，逆向推算出一整栋建筑的真实 3D 绝对尺寸（以英寸 Inches 为标准单位）。

【思维链 (Chain of Thought) 约束】
请严格执行以下逆向工程：

[步骤1: 寻找绝对物理常数参考锚点 (Anthropometric Anchors)]
- 仔细扫描图片，寻找符合国际建筑规范 (IBC) 或人体工程学的已知参照物。
- 可靠参照物优先级：1. 标准房门（国际通用高度约为 80 英寸 / 203 厘米）；2. 楼梯踏步（标准踢面高度约为 7 英寸 / 18 厘米）；3. 栏杆扶手（标准高度约为 36 英寸 / 91 厘米）；4. 标准砖块或外墙挂板的单片高度；5. 画面中的人或车辆。
- 明确指出你选择的参照物，并确立其绝对尺寸（英寸）。

[步骤2: 像素比例尺映射 (Pixel-to-Inch Mapping)]
- 在大脑中建立一个二维像素网格。比较你选择的“参考锚点”的像素高度与“建筑主体”的像素高度。
- 考虑到镜头透视畸变（近大远小），进行合理的比例折算。例如：如果门高 80 英寸占据了画面 1/4 的高度，而整栋楼占据了全高，那么楼高约为 320 英寸。

[步骤3: 三维绝对尺寸反推 (3D Dimensions Extrapolation)]
- 根据步骤 2 推导出的比例尺，分别计算出以下核心数据（必须给出明确的英寸数值）：
  1. 建筑整体总高度（包含屋顶顶端）。
  2. 建筑主体墙面高度（不含屋顶，通常单层约为 100-120 英寸）。
  3. 建筑正面总宽度。
  4. 建筑侧面进深（如果可见或可推测）。
  5. 窗户和门的绝对宽高。
  6. 烟囱、台阶等附件的绝对尺寸。

[步骤4: 防冰箱畸变强制校验 (Anti-Refrigerator Validation - 极其重要)]
- 大模型极易犯的错误：算出宽度极小（如 60 英寸），高度极大（如 300 英寸），导致建出来的房子像一个细长的“双开门大冰箱”！
- 你必须对算出的结果进行常识复核：标准的单层独栋木屋，正面宽度通常在 200 到 400 英寸以上，高度通常在 120 到 180 英寸。宽度绝大多数情况下**必定远大于**墙体高度！
- 如果你发现算出的高度大于宽度，说明你的像素透视计算彻底失败，必须强行覆盖数据，按照人类真实乡村小屋的比例（宽：高约为 1.5 : 1 或 2 : 1）重新修正基础长宽！

【输出要求】
请在 `<thinking>` 标签中展现你惊人的数学计算与常识推理过程，最后在 `<output>` 中输出所有部件的绝对尺寸估算清单。字数不得少于 500 字，尺寸数据必须精确到英寸。"""

PROMPT_COMPONENT_ENUMERATOR = """你是一名【建筑结构拆解专家与BIM工程师 (BIM Component Enumerator AI)】。
你的任务是像外科医生一样，将照片中的建筑无情地解剖为一个个独立的、可以被参数化建模的零件 (Components)。

【思维链 (Chain of Thought) 约束】
你必须严格按照国际建筑信息模型 (BIM) 的自下而上层级结构进行扫描和提取：

[步骤1: 基础层 (Foundation & Base)]
- 建筑是否有独立凸起的地基 (Foundation Slab)？
- 是否有与地基相连的外部设施（如台阶 Steps、坡道 Ramps、底座挑台）？

[步骤2: 承重主体 (Main Framing & Walls)]
- 识别主墙体 (Main Walls)。如果是 L 型建筑，请将其拆分为“主楼墙体”和“侧翼墙体”。
- 是否有外部的承重柱 (Columns)、飞扶壁或支撑结构？

[步骤3: 开口与连接 (Fenestration & Openings)]
- 枚举所有的门 (Doors)。有几扇？分布在哪个立面？
- 枚举所有的窗户 (Windows)。是单扇窗、双扇窗、凸窗(Bay Window)还是落地窗？必须把每一种明显不同的窗户作为一个独立零件列出。

[步骤4: 屋顶与覆盖层 (Roofing Structure)]
- 枚举主屋顶 (Main Roof)。
- 如果有老虎窗 (Dormers) 附着在屋顶上，请将其单独列出。
- 屋檐下是否有支撑托架 (Brackets) 或檐口装饰 (Cornices)？

[步骤5: 附属物与装饰 (Attachments & Ornamentation)]
- 屋顶上是否有烟囱 (Chimneys)、天窗 (Skylights)？
- 墙面上是否有雨棚 (Awnings)、壁灯、空调外机等凸出物？

【强制规则】
- 尝试推断由于视角遮挡导致的不可见结构（例如：如果正面有双坡屋顶，必定存在后墙支撑）。
- 绝不遗漏任何一个可能需要单独编写代码来生成的独立三维块。

【输出要求】
请在 `<thinking>` 中记录你的层级扫描过程。然后在 `<output>` 中输出一个严格的零件清单（用逗号分隔，或 JSON 数组形式），字数不得少于 500 字，必须详尽到令人发指的程度。"""

PROMPT_COMPONENT_DESCRIBER = """你是一名【参数化组件逆向工程师 (Parametric Component Reverse-Engineer AI)】。
你的任务是死死盯着传入的**特定建筑零件**，将其所有视觉特征逆向翻译为机器可读的参数化数学变量。你不需要管其他零件，只需对指定的零件进行深度微观剖析。

【思维链 (Chain of Thought) 约束】
对于目标零件，请严格执行以下微观解剖：

[步骤1: 3D 几何原语归类 (Primitive Classification)]
- 该零件在拓扑学上最接近什么几何体？（长方体 Box、三棱柱 Triangular Prism、圆柱体 Cylinder、圆锥体 Cone、球体 Sphere、或复杂的多边形挤压体 Polygon Extrusion）。
- 它在 X、Y、Z 轴向上的长宽厚大致比例是多少？（例如：这是一个极其扁平的长方体，比例约为 10:1:20）。

[步骤2: 微观内部细分 (Micro-Structure Sub-division)]
- 这个零件是一个实心块，还是一个复合体？
- 如果是【窗户】：它是否由外框 (Outer Frame)、内框 (Inner Frame)、竖向窗棂 (Mullions)、横向窗格 (Muntins) 和玻璃面板 (Glass Panes) 组成？窗框的厚度和凸出墙面的距离大概是多少英寸？
- 如果是【门】：是否有门把手 (Doorknob)、门框边缘装饰 (Trim)、或者面板雕花 (Panels)？
- 如果是【烟囱】：顶部是否有缩进的排烟口？

[步骤3: 连接与布尔关系 (Connection & Boolean Type)]
- 这个零件与建筑的依附关系是什么？
- 它是**贴附**在墙表面 (Attached)？还是向内**挖空**嵌入的 (Recessed/Subtract)？或者是悬挂挑出在半空中的 (Cantilevered)？

[步骤4: 截面剖析 (Cross-section Analysis)]
- 如果我用一把刀从正中垂直切开这个零件，它的侧切面 (Profile) 会是什么形状？（例如：普通墙壁是矩形；带挑檐的屋顶可能是“T”字形或“伞”形）。

【输出要求】
请在 `<thinking>` 标签内写下你的微观解剖过程，最后在 `<output>` 标签内输出一份极度硬核的、可以直接指导程序员写代码的参数化分析报告，字数必须大于 500 字。"""

PROMPT_SPATIAL_RELATION = """你是一名【3D 笛卡尔空间坐标与拓扑矩阵对齐专家 (Cartesian Space & Alignment Matrix AI)】。
你的任务是将图片中的所有二维建筑零件，映射到一个绝对严格的三维 X-Y-Z 坐标系中，并精确计算它们之间的对齐与约束关系。

【思维链 (Chain of Thought) 约束】
请你严格遵循以下坐标系映射法则进行空间推导：

[步骤1: 确立世界坐标系原点 (World Origin Placement)]
- 假设建筑最底层基座的几何中心点（贴合地面）为全局坐标系原点 (0, 0, 0)。
- 设定：X 轴平行于建筑正面宽度，Y 轴为进深方向，Z 轴为绝对高度（向上为正）。

[步骤2: 关键节点的相对坐标系 (Local Coordinate Mapping)]
- 逐个分析之前枚举出的所有组件（如门、窗、屋顶、烟囱）。
- 使用带百分比或绝对英寸估算的方式，描述它们的局部原点 (Local Origin) 位于何处。
- 例如：“正门 (Main Door) 的底面中心，位于主墙体正面 X 轴中心 (50%)，Z 轴贴合地基顶部，Y 轴与墙面齐平。”
- 例如：“烟囱 (Chimney) 的中心位于屋顶 X 轴从左向右 75% 处，Y 轴偏后 60% 处，Z 轴穿透屋顶。”

[步骤3: 高程与共面约束对齐 (Elevation & Coplanar Constraints)]
- **高程对齐 (Z-Axis Alignment)**：寻找水平方向上相互对齐的构件。例如：所有一楼窗户的顶部边界 (Top Edge) 是否与正门的顶部边界处于同一 Z 轴高度？二楼的阳台底面是否与一楼的天花板标高一致？
- **共面约束 (Coplanar Alignment)**：哪些构件的表面是完全平齐的 (Flush)？例如：窗框是凸出墙面 2 英寸，还是与墙面绝对共面？
- **对等距离 (Equidistant Spacing)**：如果有并排的多个窗户，它们之间的间距是否均等？它们距离左右墙壁边缘的距离是否对称？

[步骤4: 遮挡与布尔嵌套逻辑 (Occlusion & Boolean Nesting)]
- 描述构件之间的寄生与挖空关系。
- 门和窗户必须嵌套 (Nested) 并挖空 (Subtract) 在它们所在的承重墙上。明确指出哪一扇窗属于哪一堵墙。
- 烟囱是被屋顶遮挡还是贯穿了屋顶？
- 台阶是依附在基座前方，还是切入了基座内部？

【输出要求】
请在 `<thinking>` 中画出你在大脑里构建的 3D 坐标系矩阵，并在 `<output>` 中输出一份严谨的空间关系定位表，用于指导代码生成器在 `[x,y,z]` 空间中放置模型。字数不得少于 500 字，禁止使用含糊不清的方位词（如“旁边”），必须使用“X 轴正向偏移”、“Z 轴对齐”等数学词汇。"""

# ==========================================
# PROMPTS FOR FUSION & PLANNING (STAGE 3 & 4)
# ==========================================
PROMPT_FUSION = """你是一名【多模态参数融合与冲突仲裁专家 (Multimodal Fusion & Conflict Resolution AI)】。
你的任务是接收来自前端 7 个专业感知 AI（几何、材质、尺度、枚举、零件剖析、空间矩阵等）提交的冗长、碎片化、甚至互相矛盾的分析报告，并将它们统合为一份绝对精确、无歧义的**“上帝视角 JSON 施工图纸”**。

【思维链 (Chain of Thought) 与冲突仲裁约束】
在生成 JSON 之前，你必须在 `<thinking>` 标签内执行以下仲裁逻辑：

[步骤1: 提取与对齐 (Extraction & Alignment)]
- 提取【尺度基准AI】给出的全尺寸数据（如房屋总高 320 英寸）。
- 将【零件深度描述AI】给出的百分比数据，与全尺寸数据相乘，得出每个零件的绝对英寸尺寸（如：门高 = 320 * 25% = 80 英寸）。

[步骤2: 冲突仲裁 (Conflict Arbitration Algorithm)]
- 跨模型校验：如果【几何结构AI】认为屋顶是红色的（越权判定），而【材质光影AI】认为是蓝色的，你必须遵循权限覆盖原则——材质数据只能听材质专家的。
- 空间冲突校验：如果【空间关系矩阵AI】算出两个窗户的坐标会发生重叠，你必须根据常识在 X 轴上为它们分配平均间隔，强行修正坐标冲突。

[步骤3: JSON Schema 结构化 (Data Serialization)]
- 你必须同时输出一段通俗易懂的自然语言描述，以及一段绝对严谨的 JSON。
- JSON 必须包含全局环境 (Global Environment)、材质映射表 (Materials Dictionary)、以及嵌套的组件树 (Component Tree)。
- 对于每一个 Component，必须包含：name (名称), shape (拓扑原语), dimensions_inches (长宽高的绝对英寸), coordinates (相对于局部或全局原点的 [x,y,z]), boolean_type (add 还是 subtract), material_ref (指向材质映射表的键)。

【输出要求】
先在 `<thinking>` 标签中完成数据清洗与冲突修复。
然后在 `<human_summary>` 标签中，用通俗易懂的自然语言（像正常人类描述图片一样）列出你识别出的所有核心实体及其颜色/材质（例如：“白色小屋主体\n蓝色双坡屋顶\n灰色烟囱”），并在结尾写上“实体数量：X”。
最后在 `<output>` 标签中**输出且仅输出一段合法的 JSON 字符串**。这份 JSON 将是整个 SketchUp 代码生成器的唯一真理，绝对不允许漏掉任何一个微小的零件或颜色数据！"""

PROMPT_PLANNER = """你是一名【图论与施工拓扑排序规划大师 (Construction DAG Topology & Planner AI)】。
你的任务是接收前端 Fusion AI 输出的“上帝视角 JSON 施工图纸”，并将其转换为一份严格的**【施工有向无环图 (Directed Acyclic Graph, DAG)】**。
你不需要写任何 Ruby 代码，你的任务是写“剧本”——规定接下来写代码的人，必须先画什么，再画什么。

【思维链 (Chain of Thought) 约束】
请你严格遵循物理定律和三维布尔运算的逻辑，推导施工顺序：

[步骤1: 依赖图谱构建 (Dependency Graph Construction)]
- 物理支撑依赖：你不可能在没有墙壁的情况下悬空建屋顶。因此，[主墙体] -> 必须在 -> [屋顶] 之前。
- 布尔运算依赖：你不可能在没有墙的情况下挖窗户洞。因此，[主墙体] -> 必须在 -> [开窗洞] 之前。
- 材质覆盖依赖：通常是在模型几何体创建完毕后，再进行全局或局部的材质贴图。

[步骤2: 拓扑排序 (Topological Sorting)]
- 将上述依赖图谱展开为线性的、分阶段的施工工序列表。
- 强制标准流程：
  1. 阶段 A：基座与地坪 (Foundation & Floor Slab)。
  2. 阶段 B：承重主体结构 (Main Framing - 所有的实心墙体)。
  3. 阶段 C：减法布尔运算 (Subtractive Operations - 挖去门洞、窗洞、排烟孔)。
  4. 阶段 D：附加组件与覆盖物 (Additives & Roofing - 屋顶、挑檐、台阶、烟囱)。
  5. 阶段 E：细节填充 (Details Filling - 在洞口里画玻璃、窗框、门把手)。
  6. 阶段 F：材质与渲染上色 (Texturing & Painting)。

[步骤3: 异常死锁检测 (Deadlock Detection)]
- 检查你的工序列表中是否存在循环依赖？例如：“建屋顶需要烟囱作为基准，建烟囱又需要屋顶作为基准”。如果有，立刻打破循环，指定一个绝对的原点基准。

【输出要求】
先在 `<thinking>` 标签中写下你的 DAG 推理过程。
然后在 `<human_plan>` 标签中，用通俗易懂的自然语言向人类汇报你的施工计划与风险评估（例如：“计划：1. 建立白色墙体... 2. 生成蓝色双坡屋顶... 风险点：生成的是几何模型，不会做到照片级细节”）。
最后在 `<output>` 标签中，严格输出一份带编号的施工规划大纲。这份大纲将直接决定代码生成器是否会因为逻辑错乱而崩溃，字数不得少于 500 字！"""

# ==========================================
# PROMPTS FOR VISUAL REVIEW (STAGE 5)
# ==========================================
PROMPT_SILHOUETTE_CRITIC = """你是一名【轮廓重合度审查官 (Silhouette Critic)】。
左图为原图，右图为当前 SketchUp 建模截图。
请严格对比建筑的整体轮廓、宽高比例、屋顶倾角等大框架是否吻合。
输出两部分：
PASS: [YES 或 NO]
FEEDBACK: [详细的形状修正建议]"""

PROMPT_DETAIL_CHECKER = """你是一名【零件清点审查官 (Detail Checker)】。
左图为原图，右图为当前 SketchUp 建模截图。
请拿着放大镜清点小部件：门窗数量对不对？有没有屋檐？台阶层数对不对？烟囱有没有？颜色对不对？
输出两部分：
PASS: [YES 或 NO]
FEEDBACK: [列出缺失的零件清单和补齐要求]"""

PROMPT_STEP_REVIEWER = """你是一名【阶段验收视觉感知AI】。
左图为原建筑照片，右图为目前 SketchUp 刚刚执行完一步代码后的【当前进度截图】。
请对比两张图，告诉施工员：
1. 刚刚这一步画出的形状对不对？有无明显比例或位置错误？
2. 对比原图，下一步应该画什么？（提供场景感知和下一步建议）。
请尽量简短、犀利地指出问题和下一步方向。"""


MCP_SYSTEM_PROMPT_TEMPLATE = """你是一名世界顶级的【SketchUp 强迫症代码员 (MCP Coder)】。
你现在通过 MCP 协议直接接入了 SketchUp 软件内核。

【终极指令】
前方规划师为你制定了严格的施工顺序 (DAG)，以及融合后的精确参数 (JSON)。
你可以使用 `get_model_info`、`get_entity_info` 获取上下文。进行建筑建模时，**绝对禁止使用 `create_geometry` 工具**！你必须从头到尾使用终极底牌 `execute_ruby` 来编写高级的参数化建模逻辑。严格遵循参数尺寸和施工顺序执行建模。

【严苛规范】
1. 必须使用 Ruby 代码（`execute_ruby`）自定义高级绘图模块来画出实体墙、带挑檐的屋顶，严禁使用 `create_geometry` 工具！
2. 任何洞口必须用实体挖穿 `pushpull(-thickness)`。
3. 必须通过 `material.color=` 进行上色，绝对不允许纯白模型交卷！
4. 绝对禁止一次性写完所有代码！你必须【分步执行】。每次调用工具只完成一个零件或一个逻辑步骤（例如先调用 `get_model_info` 获取上下文，再用 `execute_ruby` 画地基）。任何修改模型的工具执行后，你将收到【阶段视觉反馈】，请根据原图和反馈再决定下一步动作。如果一次性输出长篇大论的代码将被严厉惩罚！

【参数化拓扑算法手册 (RUBY_BEST_PRACTICES) - 必须严格套用】
你必须像顶级建筑师一样，使用以下高级拓扑算法来构建复杂结构，绝不能只瞎蒙坐标：
1. **相对面拉伸定律 (Relative Face Extrusion - 极其重要)**
   - 绝不要用绝对坐标 (如 `[0,0,0]`) 去盲猜拼凑房子！你必须像雕塑一样生长房子：
   - 画完地基后，第二步画墙时，必须用 Ruby 获取地基的最高顶面：`top_face = group.entities.grep(Sketchup::Face).max_by {{ |f| f.bounds.center.z }}`
   - 在该 `top_face` 上绘制或偏移边界，然后直接 `pushpull` 拉伸出墙体高度！这样墙体会 100% 死死长在地基上，绝对不会悬空或错位！
2. **带厚度的实体墙体 (Solid Walls)**
   - 绝不允许画只有外壳的纸盒子空心墙！拉伸墙体前，必须将边界向内偏移(offset)一定厚度（如 8 英寸），将外圈的面向上拉伸，形成真正的空心实体墙，以便后续挖洞！
3. **带挑檐的坡屋顶 (Pitched Roof with Eaves)**
   - 算法：找到墙体顶面(top_face) -> `top_face.pushpull(roof_base_thickness)` 向上拉伸出屋顶底板厚度 -> 找到底板四周的侧立面(side faces)，每个向外 `pushpull(overhang)` 形成挑檐 -> 找到新的顶面，在中间画一条线段(`add_line`)将其一分为二 -> 获取这条线段的 Edge 对象，使用 `transform_entities(Geom::Transformation.translation([0, 0, roof_height]), edge)` 向上提拉中线，瞬间形成完美双坡屋顶！
4. **深度立体窗户与玻璃 (Detailed Windows)**
   - 算法：在墙面上画窗洞矩形 -> `face.pushpull(-wall_thickness)` 挖空 -> 在洞口内部新建 Group 画窗框：先画外框矩形，再通过坐标计算画内框矩形，删除内部面形成回字形窗框面 -> `pushpull(frame_thickness)` 做出立体窗框 -> 在内框再画一个面作为玻璃，赋予天蓝色半透明材质（`mat = model.materials.add('Glass'); mat.color='SkyBlue'; mat.alpha=0.6; glass_face.material=mat`）。
5. **墙裙与烟囱 (Details)**
   - 烟囱必须穿透屋顶：在屋顶斜面上画矩形，直接向上 `pushpull` 出高度，再向内缩进画小矩形向下挖空作为排烟口。
6. **强制上色与材质 (Mandatory Stylization)**
   - 画完每个组件后，必须遍历其面 (`entities.grep(Sketchup::Face)`) 赋予高饱和度材质（例如深蓝屋顶、纯白墙壁、深灰烟囱），绝对不交纯白模型！

【施工参数 JSON】
{json_blueprint}

【施工工序 DAG】
{dag_plan}

【执行流程与强制工具调用限制】
1. **强制调用工具**：只要房子还没完全建完，你在每一轮回复中【必须且只能】调用 `execute_ruby` 工具！绝对禁止只输出解释性的聊天文字（如果你只输出文字而不调用工具，系统会认为你试图提前交卷并立刻拉去审查，然后被直接驳回）。
2. **分步验收**：每次调用 `execute_ruby` 后，系统会自动发给你最新的模型截图和视觉建议，请根据截图决定下一步画什么。
3. **最终交卷**：只有当你非常确信所有 DAG 规划的组件（包括地基、墙体、屋顶、门窗、烟囱、上色）都已经 100% 画完并且毫无瑕疵时，你才可以放弃调用工具，并纯文本回复“【提交验收】”。
"""

CRITIC_SYSTEM_PROMPT = """你是一名【Ruby 代码审查员】。
审查施工员写的 `execute_ruby` 代码是否符合高精度要求（如窗户必须有厚度和玻璃）。

【Ruby 合规标准与打回要求】
- **精确拦截**：只有当你明确看到代码正在画【窗户 (Window)】或【门 (Door)】，但却没有写 `pushpull(-thickness)` 向内挖洞的逻辑时，才必须打回 (SCORE: 0.0)！
- **正常放行**：如果当前代码明显是在画地基、墙体、屋顶或简单的几何拉伸，只要它使用了合理的 SketchUp Ruby API (如 `add_face`, `pushpull`)，请一律给予高分通过 (SCORE: 1.0)！绝对禁止因为“没有画门窗”而把画地基的代码打回！
- 如果打回，你必须在 FEEDBACK 中**附带一段合法的 Ruby 代码骨架/示例**，告诉施工员正确的 API 用法。

输出格式:
SCORE: [0.0 - 1.0]
FEEDBACK: [评语和修正用的 Ruby 代码片段]"""

# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def _map_mcp_tool_to_openai(mcp_tool: dict) -> dict:
    return {"type": "function", "function": {"name": mcp_tool["name"], "description": mcp_tool.get("description", ""), "parameters": mcp_tool.get("inputSchema", {})}}

def compress_tool_output(ai_client: OpenAI, lite_model: str, tool_name: str, raw_output: str) -> str:
    if len(raw_output) < 300: return raw_output
    logger.info(f"[Lite Agent] 压缩 {tool_name} 输出...")
    try:
        res = _safe_chat_create(ai_client, model=lite_model, messages=[{"role": "user", "content": f"极简概括日志(50字内)：\n{raw_output[:2000]}"}], temperature=0.1)
        return res.choices[0].message.content.strip()
    except Exception:
        return raw_output[:300] + "..."

def _safe_chat_create(ai_client, model: str, messages: list, temperature: float = 0.2, **kwargs):
    clients = ai_client if isinstance(ai_client, list) else [ai_client]
    for attempt in range(8):
        client = random.choice(clients)
        try:
            return client.chat.completions.create(model=model, messages=messages, temperature=temperature, **kwargs)
        except Exception as e:
            err_str = str(e)
            # 中转平台常见的高并发拒载报错（429、503、通道耗尽）均纳入退避重试
            if any(x in err_str for x in ["429", "Too Many Requests", "503", "No available channel", "model_not_found", "Quota"]):
                wait_t = 3 + attempt * 3
                logger.warning(f"中转节点繁忙/通道耗尽，退避 {wait_t} 秒后重试 (第{attempt+1}次)...")
                time.sleep(wait_t)
            else:
                raise e
    raise RuntimeError("连续多次请求失败，中转节点可能宕机。")

def _call_vision_subagent(ai_client: OpenAI, model_name: str, b64_image: str, mime: str, sys_prompt: str, role_name: str) -> str:
    logger.info(f"[Stage 1] 启动 {role_name}...")
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": [{"type": "text", "text": "请执行你的专属分析任务："}, {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_image}", "detail": "high"}}]}
    ]
    
    try:
        res = _safe_chat_create(ai_client, model=model_name, messages=messages, temperature=0.2)
        result = res.choices[0].message.content.strip()
        logger.info(f"[Stage 1] {role_name} 报告已出。")
        return f"【{role_name}报告】\n{result}"
    except Exception as e:
        return f"【{role_name}报告】\n执行失败: {e}"

def _extract_component_names(ai_client, lite_model: str, enum_text: str) -> list[str]:
    res = _safe_chat_create(
        ai_client, model=lite_model,
        messages=[{"role": "user", "content": f"提取以下文本中的建筑零件名称，仅输出JSON数组格式，例如 [\"烟囱\", \"正门\"]，不要其他文字：\n{enum_text}"}],
        temperature=0.1
    )
    content = res.choices[0].message.content.strip()
    try:
        if "```json" in content: content = content.split("```json")[1].split("```")[0]
        elif "```" in content: content = content.split("```")[1].split("```")[0]
        return json.loads(content)
    except Exception:
        return ["主屋体", "屋顶"]

def generate_fused_blueprint(ai_client: OpenAI, heavy_model: str, lite_model: str, image_bytes: bytes, image_mime: str, user_prompt: str) -> Tuple[str, str]:
    """生成 JSON 和 DAG 规划"""
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    # 1. 并发执行感知层 (Stage 1) - 控制并发数为 5，避免 503 错误
    reports = []
    
    # --- 首先串行执行枚举，获取零件清单 ---
    enum_report = _call_vision_subagent(ai_client, heavy_model, b64_image, image_mime, PROMPT_COMPONENT_ENUMERATOR, "零件枚举AI")
    reports.append(enum_report)
    components = _extract_component_names(ai_client, lite_model, enum_report)
    
    # --- 准备所有需要并发的任务 ---
    tasks = []
    
    # 基础感知任务
    tasks.append((PROMPT_SPATIAL_RELATION, "空间关系AI"))
    tasks.append((PROMPT_GEOMETRY, "几何结构AI"))
    tasks.append((PROMPT_MATERIAL, "材质光影AI"))
    tasks.append((PROMPT_SCALE, "尺度基准AI"))
    
    # 深度零件感知任务
    for comp in components[:8]:
        prompt = PROMPT_COMPONENT_DESCRIBER + f"\n当前要求描述的零件是：【{comp}】。请只关注此零件。"
        tasks.append((prompt, f"零件深描述AI-{comp}"))
        
    logger.info(f"[Stage 1] 启动 ThreadPoolExecutor 并发执行 {len(tasks)} 个视觉感知任务 (并发限制: 5)...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_role = {
            executor.submit(_call_vision_subagent, ai_client, heavy_model, b64_image, image_mime, prompt, role): role 
            for prompt, role in tasks
        }
        for future in concurrent.futures.as_completed(future_to_role):
            try:
                reports.append(future.result())
            except Exception as e:
                logger.error(f"并发任务异常: {e}")
            
    combined_report = "\n\n".join(reports) + f"\n\n【用户补充要求】\n{user_prompt}"
    
    # 2. 参数融合 (Stage 3)
    logger.info("[Stage 3] Fusion Agent 正在融合参数...")
    res_fusion = _safe_chat_create(
        ai_client,
        model=heavy_model,
        messages=[{"role": "system", "content": PROMPT_FUSION}, {"role": "user", "content": combined_report}],
        temperature=0.1
    )
    raw_fusion_output = res_fusion.choices[0].message.content.strip()
    
    # 提取人类可读总结
    summary_match = re.search(r'<human_summary>(.*?)</human_summary>', raw_fusion_output, re.DOTALL)
    if summary_match:
        human_summary = summary_match.group(1).strip()
        logger.info(f"\n========== [感知引擎分析结果] ==========\n{human_summary}\n=======================================\n")
    else:
        logger.warning("未能提取到 human_summary")
        
    # 提取 JSON
    json_match = re.search(r'<output>(.*?)</output>', raw_fusion_output, re.DOTALL)
    if json_match:
        json_blueprint = json_match.group(1).strip()
    else:
        json_blueprint = raw_fusion_output
        
    if json_blueprint.startswith("```json"): json_blueprint = json_blueprint[7:]
    if json_blueprint.endswith("```"): json_blueprint = json_blueprint[:-3]
    
    # 3. 编排规划 (Stage 4)
    logger.info("[Stage 4] Planner Agent 正在生成施工 DAG...")
    res_planner = _safe_chat_create(
        ai_client,
        model=heavy_model,
        messages=[{"role": "system", "content": PROMPT_PLANNER}, {"role": "user", "content": json_blueprint}],
        temperature=0.2
    )
    raw_planner_output = res_planner.choices[0].message.content.strip()
    
    # 提取人类可读计划
    plan_match = re.search(r'<human_plan>(.*?)</human_plan>', raw_planner_output, re.DOTALL)
    if plan_match:
        human_plan = plan_match.group(1).strip()
        logger.info(f"\n========== [施工规划与风险评估] ==========\n{human_plan}\n=========================================\n")
    else:
        logger.warning("未能提取到 human_plan")
        
    # 提取 DAG
    dag_match = re.search(r'<output>(.*?)</output>', raw_planner_output, re.DOTALL)
    if dag_match:
        dag_plan = dag_match.group(1).strip()
    else:
        dag_plan = raw_planner_output
    
    return json_blueprint, dag_plan


def review_ruby_code(ai_client: OpenAI, heavy_model: str, code: str, json_blueprint: str) -> tuple[float, str]:
    res = _safe_chat_create(
        ai_client,
        model=heavy_model,
        messages=[{"role": "system", "content": CRITIC_SYSTEM_PROMPT}, {"role": "user", "content": f"参数:\n{json_blueprint}\n代码:\n{code}"}],
        temperature=0.1
    )
    content = res.choices[0].message.content.strip()
    score, feedback = 0.0, content
    try:
        for line in content.split("\n"):
            if line.startswith("SCORE:"): score = float(line.replace("SCORE:", "").strip())
            elif line.startswith("FEEDBACK:"): feedback = line.replace("FEEDBACK:", "").strip()
    except Exception: pass
    return score, feedback

def take_sketchup_screenshot(mcp_client: RawMcpClient) -> Optional[bytes]:
    logger.info("[Execute] 正在截取 SketchUp 实况...")
    filepath = os.path.abspath("temp_screenshot.png").replace("\\", "/")
    mcp_client.call_tool("execute_ruby", {"code": f"Sketchup.active_model.active_view.write_image('{filepath}')"})
    for _ in range(15):
        if os.path.exists(filepath):
            try:
                with open(filepath, "rb") as f:
                    data = f.read()
                os.remove(filepath)
                return data
            except Exception: pass
        time.sleep(0.5)
    return None

def _call_visual_critic(ai_client: OpenAI, model_name: str, orig_b64: str, mime: str, screen_b64: str, sys_prompt: str, role_name: str) -> tuple[bool, str]:
    logger.info(f"[Stage 5] 启动 {role_name}...")
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{orig_b64}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screen_b64}"}}
        ]}
    ]
    res = _safe_chat_create(ai_client, model=model_name, messages=messages, temperature=0.1)
    content = res.choices[0].message.content.strip()
    passed = False
    for line in content.split("\n"):
        if line.startswith("PASS:"):
            if "YES" in line.replace("PASS:", "").strip().upper(): passed = True
    return passed, f"【{role_name}评议】\n{content}"

def visual_review_parallel(ai_client: OpenAI, heavy_model: str, original_bytes: bytes, original_mime: str, screenshot_bytes: bytes) -> tuple[bool, str]:
    orig_b64 = base64.b64encode(original_bytes).decode("utf-8")
    screen_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    
    results = []
    results.append(_call_visual_critic(ai_client, heavy_model, orig_b64, original_mime, screen_b64, PROMPT_SILHOUETTE_CRITIC, "大轮廓审查官"))
    results.append(_call_visual_critic(ai_client, heavy_model, orig_b64, original_mime, screen_b64, PROMPT_DETAIL_CHECKER, "零件细节审查官"))
            
    all_passed = all(p for p, _ in results)
    combined_feedback = "\n".join(fb for _, fb in results)
    return all_passed, combined_feedback



def _map_mcp_tool_to_genai(mcp_tool: dict) -> dict:
    return {
        "type": "function",
        "name": mcp_tool["name"],
        "description": mcp_tool.get("description", ""),
        "parameters": mcp_tool.get("inputSchema", {})
    }


def _safe_genai_interactions_create(client_g, model, **kwargs):
    for attempt in range(8):
        try:
            return client_g.interactions.create(model=model, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "too many requests" in err_str or "quota" in err_str:
                wait_t = 5 + attempt * 5
                logger.warning(f"谷歌 Interactions API 频率限制/通道耗尽 (429)，退避 {wait_t} 秒后重试 (第{attempt+1}次)...")
                time.sleep(wait_t)
            else:
                raise e
    raise RuntimeError("谷歌 API 连续被拒绝 (429)，请检查并发频率或账号额度。")

def _run_mcp_loop_internal_genai(client_g, ai_client, heavy_model, lite_model, coder_model, messages, json_blueprint, orig_img_bytes, orig_img_mime, interaction_id, mcp_client, raw_tools):
    genai_tools = [_map_mcp_tool_to_genai(t) for t in raw_tools]
    max_steps = 100 
    rejection_count = 0
    
    if interaction_id is None:
        input_parts = []
        for m in messages:
            if m["role"] in ["system", "user"]:
                input_parts.append({"type": "text", "text": f"{m['role']}: {m['content']}"})
            elif m["role"] == "assistant" and m.get("content"):
                input_parts.append({"type": "text", "text": f"assistant: {m['content']}"})
        input_text = "\n\n".join([p["text"] for p in input_parts])
        
        interaction = _safe_genai_interactions_create(
            client_g, model=coder_model,
            input=input_text,
            tools=genai_tools
        )
    else:
        user_prompt = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else "继续执行"
        interaction = _safe_genai_interactions_create(
            client_g, model=coder_model,
            previous_interaction_id=interaction_id,
            input=user_prompt,
            tools=genai_tools
        )
        
    for step in range(1, max_steps + 1):
        interaction_id = interaction.id
        logger.info(f"[MCP Agent (Interactions) - {coder_model}] 第 {step} 步思考中...")
        
        last_step = interaction.steps[-1]
        
        if last_step.type == "model_output":
            logger.info(f"[MCP Agent] 尝试交卷。触发双重并发视觉审查...")
            final_text = ""
            if last_step.content:
                for item in last_step.content:
                    if item.type == "text": final_text += item.text
            messages.append({"role": "assistant", "content": final_text})
            
            if orig_img_bytes:
                screenshot = take_sketchup_screenshot(mcp_client)
                if screenshot:
                    passed, visual_fb = visual_review_parallel(ai_client, heavy_model, orig_img_bytes, orig_img_mime, screenshot)
                    if not passed:
                        logger.warning(f"[!] 视觉委员会驳回交付！")
                        fb_msg = f"【双重视觉评审打回】\n{visual_fb}\n请立即修复缺失组件或轮廓差异！不要停！"
                        messages.append({"role": "user", "content": fb_msg})
                        interaction = client_g.interactions.create(
                            model=coder_model,
                            previous_interaction_id=interaction_id,
                            input=fb_msg,
                            tools=genai_tools
                        )
                        continue
            return final_text or "完工", messages, interaction_id
            
        elif last_step.type == "function_call":
            # For each function call in this step
            function_results = []
            
            # Since interaction.steps contains ALL steps from the beginning of the interaction request, 
            # we need to find the latest function calls. Wait, interaction.steps is the TIMELINE of the request.
            # When we call interactions.create, it runs until it stops (e.g. at function_call or model_output).
            # The last step(s) are what it just generated.
            # But wait! If a tool call triggers a visual check, we inject a NEW interactions.create().
            
            tool_name = last_step.name
            try: tool_args = last_step.arguments
            except: tool_args = {}
            
            messages.append({"role": "assistant", "tool_calls": [{"id": last_step.id, "type": "function", "function": {"name": tool_name, "arguments": json.dumps(tool_args)}}]})
            
            if tool_name == "execute_ruby":
                score, feedback = review_ruby_code(ai_client, heavy_model, tool_args.get("code", ""), json_blueprint)
                if score < 0.5:
                    rejection_count += 1
                    logger.warning(f"   [!] 代码逻辑打回: {rejection_count} 次")
                    if rejection_count < 3:
                        err_payload = json.dumps({"isError": True, "error": f"【高优拦截】代码不合规！\n审查意见：{feedback}"}, ensure_ascii=False)
                        function_results.append({"type": "function_result", "call_id": last_step.id, "name": tool_name, "result": [{"type": "text", "text": err_payload}]})
                        messages.append({"role": "tool", "tool_call_id": last_step.id, "name": tool_name, "content": err_payload})
                        interaction = _safe_genai_interactions_create(client_g, model=coder_model, previous_interaction_id=interaction_id, input=function_results, tools=genai_tools)
                        continue
                    else:
                        rejection_count = 0
                else:
                    rejection_count = 0
            
            result = mcp_client.call_tool(tool_name, tool_args)
            raw_result_str = json.dumps(result, ensure_ascii=False) if result else "Success"
            
            if tool_name in ["execute_ruby", "create_geometry", "delete_entities", "transform_entities", "set_material"] and orig_img_bytes:
                screenshot = take_sketchup_screenshot(mcp_client)
                if screenshot:
                    try:
                        passed, step_fb = _call_visual_critic(ai_client, heavy_model, base64.b64encode(orig_img_bytes).decode("utf-8"), orig_img_mime, base64.b64encode(screenshot).decode("utf-8"), PROMPT_STEP_REVIEWER, "阶段视觉验收AI")
                        raw_result_str += f"\n\n【阶段视觉反馈 (场景感知)】\n{step_fb}"
                    except: pass
            
            function_results.append({"type": "function_result", "call_id": last_step.id, "name": tool_name, "result": [{"type": "text", "text": raw_result_str}]})
            messages.append({"role": "tool", "tool_call_id": last_step.id, "name": tool_name, "content": compress_tool_output(ai_client, lite_model, tool_name, raw_result_str)})
            
            interaction = client_g.interactions.create(
                model=coder_model,
                previous_interaction_id=interaction_id,
                input=function_results,
                tools=genai_tools
            )
            
    return f"循环到达上限 ({max_steps})", messages, interaction_id

def _run_mcp_loop_internal(ai_client: list, coder_client: list, heavy_model: str, lite_model: str, coder_model: str, messages: List[Dict], json_blueprint: str, orig_img_bytes: bytes, orig_img_mime: str, interaction_id: str = None) -> Tuple[str, List[Dict], Optional[str]]:
    with RawMcpClient(host="127.0.0.1", port=9876) as mcp_client:
        try: raw_tools = mcp_client.list_tools()
        except Exception as e: raise RuntimeError(f"MCP 异常: {e}")
        
        is_genai = False
        try:
            from google import genai
            if coder_client and isinstance(coder_client[0], genai.Client):
                is_genai = True
        except: pass
        
        if is_genai:
            client_g = random.choice(coder_client)
            return _run_mcp_loop_internal_genai(client_g, ai_client, heavy_model, lite_model, coder_model, messages, json_blueprint, orig_img_bytes, orig_img_mime, interaction_id, mcp_client, raw_tools)
            
        openai_tools = [_map_mcp_tool_to_openai(t) for t in raw_tools]
        max_steps = 100 
        rejection_count = 0
        
        for step in range(1, max_steps + 1):
            logger.info(f"[MCP Agent - {coder_model}] 第 {step} 步思考中...")
            response = _safe_chat_create(coder_client, model=coder_model, messages=messages, temperature=0.2, tools=openai_tools)
            response_message = response.choices[0].message
            
            message_dict = {"role": "assistant"}
            if response_message.content: message_dict["content"] = response_message.content
            if response_message.tool_calls:
                message_dict["tool_calls"] = [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in response_message.tool_calls]
            messages.append(message_dict)
            
            if not response_message.tool_calls:
                logger.info(f"[MCP Agent] 尝试交卷。触发双重并发视觉审查...")
                if orig_img_bytes:
                    screenshot = take_sketchup_screenshot(mcp_client)
                    if screenshot:
                        passed, visual_fb = visual_review_parallel(ai_client, heavy_model, orig_img_bytes, orig_img_mime, screenshot)
                        if not passed:
                            logger.warning(f"[!] 视觉委员会驳回交付！")
                            messages.append({"role": "user", "content": f"【双重视觉评审打回】\n{visual_fb}\n请对照上述意见，立即使用 execute_ruby 修复缺失组件或轮廓差异！不要停！"})
                            continue
                return response_message.content or "完工", messages, None
                
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                try: tool_args = json.loads(tool_call.function.arguments)
                except: tool_args = {}
                
                if tool_name == "execute_ruby":
                    score, feedback = review_ruby_code(ai_client, heavy_model, tool_args.get("code", ""), json_blueprint)
                    if score < 0.5:
                        rejection_count += 1
                        logger.warning(f"   [!] 代码底层逻辑被打回！当前连续打回: {rejection_count} 次")
                        if rejection_count >= 3:
                            logger.warning("   [!] 连续打回达3次，启动降级机制，强制放行给 SketchUp 执行并交由视觉委员会兜底！")
                            rejection_count = 0
                        else:
                            error_payload = {
                                "isError": True, 
                                "error": f"【高优拦截 (得分{score}/0.5)】代码不合规！请立刻参考系统指令中的【Ruby 合规代码范例库】进行重写！\n审查详细意见：{feedback}"
                            }
                            messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": json.dumps(error_payload, ensure_ascii=False)})
                            continue 
                    else:
                        rejection_count = 0
                
                result = mcp_client.call_tool(tool_name, tool_args)
                raw_result_str = json.dumps(result, ensure_ascii=False) if result else "Success"
                
                if tool_name in ["execute_ruby", "create_geometry", "delete_entities", "transform_entities", "set_material"] and orig_img_bytes:
                    screenshot = take_sketchup_screenshot(mcp_client)
                    if screenshot:
                        logger.info("   [Stage 5 - Interstep] 获取当前步骤实况，进行视觉比对...")
                        try:
                            passed, step_fb = _call_visual_critic(
                                ai_client, heavy_model, 
                                base64.b64encode(orig_img_bytes).decode("utf-8"), 
                                orig_img_mime, 
                                base64.b64encode(screenshot).decode("utf-8"), 
                                PROMPT_STEP_REVIEWER, 
                                "阶段视觉验收AI"
                            )
                            raw_result_str += f"\n\n【阶段视觉反馈 (场景感知)】\n{step_fb}"
                        except Exception as e:
                            logger.error(f"视觉感知失败: {e}")
                            
                compressed_str = compress_tool_output(ai_client, lite_model, tool_name, raw_result_str)
                logger.info(f"   <= 工具执行完成。")
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": compressed_str})

    return f"循环到达上限 ({max_steps})", messages, None

def start_session(ai_client: list, coder_client: list, heavy_model: str, lite_model: str, coder_model: str, image_bytes: bytes, image_mime: str, user_prompt: str) -> dict:
    session_id = str(uuid.uuid4())
    logger.info("========== [Stage 1-4] 触发分布式微型智能体军团 ==========")
    json_blueprint, dag_plan = generate_fused_blueprint(ai_client, heavy_model, lite_model, image_bytes, image_mime, user_prompt)
    
    system_prompt = MCP_SYSTEM_PROMPT_TEMPLATE.format(json_blueprint=json_blueprint, dag_plan=dag_plan)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "参数和施工规划 (DAG) 已下达。请开始敲代码执行第一步。"}
    ]
    
    logger.info("========== [Stage 5+] 进入 MCP 编码循环 ==========")
    final_text, new_messages, interaction_id = _run_mcp_loop_internal(ai_client, coder_client, heavy_model, lite_model, coder_model, messages, json_blueprint, image_bytes, image_mime)
    
    SESSION_STORE[session_id] = {
        "messages": new_messages,
        "blueprint": json_blueprint,
        "orig_img_bytes": image_bytes,
        "orig_img_mime": image_mime,
        "interaction_id": interaction_id
    }
    _save_sessions()
    return {"session_id": session_id, "message": final_text}

def continue_session(ai_client: list, coder_client: list, heavy_model: str, lite_model: str, coder_model: str, session_id: str, user_prompt: str) -> dict:
    if session_id not in SESSION_STORE: raise ValueError("会话已过期。")
    session_data = SESSION_STORE[session_id]
    messages, blueprint = session_data["messages"], session_data["blueprint"]
    orig_img_bytes, orig_img_mime = session_data.get("orig_img_bytes"), session_data.get("orig_img_mime", "image/jpeg")
    interaction_id = session_data.get("interaction_id")
    
    messages.append({"role": "user", "content": user_prompt})
    final_text, new_messages, new_iid = _run_mcp_loop_internal(ai_client, coder_client, heavy_model, lite_model, coder_model, messages, blueprint, orig_img_bytes, orig_img_mime, interaction_id)
    
    SESSION_STORE[session_id]["messages"] = new_messages
    SESSION_STORE[session_id]["interaction_id"] = new_iid
    _save_sessions()
    return {"session_id": session_id, "message": final_text}
