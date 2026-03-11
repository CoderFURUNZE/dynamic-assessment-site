from fastapi import APIRouter, Depends

from app.api.deps import get_current_user

router = APIRouter(prefix="/extensions", tags=["extensions"])


@router.get("/overview")
def extension_overview(_user=Depends(get_current_user)):
    return {
        "features": [
            {
                "key": "multiple_intelligence",
                "title": "多元智能问卷",
                "status": "planned",
                "owner": "管理员/教师",
                "summary": "作为学习者画像的扩展模块，后续通过问卷补充语言、逻辑、协作等维度。",
                "scope": "当前版本仅预留入口，不进入主评价模型。",
            },
            {
                "key": "peer_review",
                "title": "自评与互评",
                "status": "planned",
                "owner": "教师/学生",
                "summary": "用于补充学生自我认知和同伴评价差异，服务于阶段总结和反思。",
                "scope": "当前版本仅保留扩展位，不影响主线展示与计算。",
            },
            {
                "key": "graph_ocr",
                "title": "知识图谱截图识别",
                "status": "planned",
                "owner": "教师",
                "summary": "后续支持从其他平台截图识别图谱节点与边，减少重复建图成本。",
                "scope": "当前版本以教师手建和目录导入为主，截图识别只做占位。",
            },
        ]
    }


@router.get("/methodology")
def methodology_overview(_user=Depends(get_current_user)):
    return {
        "method_cards": [
            {
                "key": "dynamic_evaluation",
                "title": "动态评价说明",
                "summary": "教师按学期或阶段导入过程数据后，系统重算阶段评价和总画像，不依赖学生每一次点击实时重算。",
                "focus": ["阶段数据导入", "阶段对比", "风险提示", "教师补充评价"],
            },
            {
                "key": "persona",
                "title": "学习者画像说明",
                "summary": "当前画像以学习投入、学习成效、学习习惯、学习特征四类维度为主，由教师配置权重后自动生成。",
                "focus": ["画像分型", "维度权重", "人工覆盖", "结论性文字说明"],
            },
            {
                "key": "graph",
                "title": "知识图谱说明",
                "summary": "知识图谱负责组织课程知识结构，并把资源、任务、练习和小测绑定到知识点节点上。",
                "focus": ["前置关系", "关联关系", "节点资源", "节点任务"],
            },
            {
                "key": "recommendation",
                "title": "推荐说明",
                "summary": "推荐先根据知识图谱和掌握状态决定推什么，再根据画像类型决定怎么推，并给出推荐依据。",
                "focus": ["推荐目标", "推荐依据", "补救路径", "解锁状态"],
            },
        ],
        "demo_flow": [
            "管理员或教师准备课程、知识点和知识图谱基础数据。",
            "教师创建课程阶段，并导入某阶段的学习数据。",
            "系统自动生成阶段画像、阶段评价和趋势结果。",
            "教师查看班级分析和单学生成长轨迹，并补充阶段评语。",
            "学生查看课程总览、知识图谱、阶段报告和推荐建议。",
        ],
        "empty_states": [
            {
                "scenario": "暂无课程或知识点",
                "advice": "先在管理员端或教师端完成课程与知识点建设，再进入学生端演示。",
            },
            {
                "scenario": "暂无阶段数据",
                "advice": "先在教师端创建阶段并导入样例数据，系统才会生成阶段画像和动态评价。",
            },
            {
                "scenario": "节点暂无资源/任务",
                "advice": "在教师图谱工作台中绑定资源、任务、练习或小测，学生节点详情才会展示教学内容。",
            },
            {
                "scenario": "暂无推荐结果",
                "advice": "先选择当前知识点并生成学习建议，系统会返回推荐依据和补救路径。",
            },
        ],
    }
