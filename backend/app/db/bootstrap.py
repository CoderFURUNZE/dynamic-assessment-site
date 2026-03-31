from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import EvalConfig, PortraitDimension, PortraitIndicator, PortraitIndicatorSourceType, User, UserRole
from app.db.session import engine


def bootstrap_defaults() -> None:
    with Session(engine) as session:
        any_user = session.exec(select(User.id)).first()
        allow_default_users = settings.app_env.strip().lower() != "production"
        if not any_user and allow_default_users:
            session.add(User(username="admin", password_hash=hash_password("admin123"), role=UserRole.admin))
            session.add(User(username="teacher1", password_hash=hash_password("teacher123"), role=UserRole.teacher))
            session.add(User(username="student1", password_hash=hash_password("student123"), role=UserRole.student))
            session.commit()

        cfg = session.exec(
            select(EvalConfig).where(EvalConfig.subject == "数学", EvalConfig.grade == "高二")
        ).first()
        if cfg is None:
            session.add(EvalConfig(subject="数学", grade="高二"))
            session.commit()

        _bootstrap_portrait_dimensions(session)


def _bootstrap_portrait_dimensions(session: Session) -> None:
    defaults = [
        {
            "code": "potential_trait",
            "title": "潜能与特质倾向",
            "description": "用于描述学习者在创造性、迁移能力和价值判断方面的潜在特征。",
            "sort_order": 1,
            "indicators": [
                ("creative_thinking", "创造性思维倾向", "主要依据教师对开放性任务、项目作品和综合创新表现的阶段评价。", PortraitIndicatorSourceType.teacher, 1, 1.0),
                ("cross_context_transfer", "跨情境迁移能力", "主要依据阶段导入的综合任务、迁移题和跨知识点应用结果。", PortraitIndicatorSourceType.imported, 2, 1.0),
                ("value_judgement", "存在思考与价值判断", "主要依据教师补充评价、反思作业和高层次判断记录。", PortraitIndicatorSourceType.teacher, 3, 1.0),
            ],
        },
        {
            "code": "social_emotional",
            "title": "情感与社会性发展",
            "description": "用于描述协作、动机、自我调节和社会性表现。",
            "sort_order": 2,
            "indicators": [
                ("collaboration", "协作能力与社交网络", "关注协作参与和同伴互动。", PortraitIndicatorSourceType.teacher, 1, 1.0),
                ("motivation", "学习动机与态度", "主要依据阶段导入的出勤、投入、任务完成连续性，并允许教师补充修正。", PortraitIndicatorSourceType.imported, 2, 1.0),
                ("self_regulation", "自我调节与元认知", "关注反馈吸收和学习调整。", PortraitIndicatorSourceType.teacher, 3, 1.0),
            ],
        },
        {
            "code": "knowledge_cognition",
            "title": "知识与认知状态",
            "description": "用于描述知识掌握、认知层级和跨学科关联能力。",
            "sort_order": 3,
            "indicators": [
                ("cross_discipline_link", "跨学科知识关联能力", "关注知识之间的关联和整合。", PortraitIndicatorSourceType.auto, 1, 1.0),
                ("discipline_level", "学科能力层级与认知路径", "关注认知层级和能力进阶。", PortraitIndicatorSourceType.auto, 2, 1.0),
                ("language_mastery", "语言类知识掌握度", "主要依据阶段导入的表达类作业、小测和文本型任务结果。", PortraitIndicatorSourceType.imported, 3, 1.0),
                ("logic_mastery", "逻辑类知识掌握度", "主要依据阶段导入的小测、练习和推理型任务结果。", PortraitIndicatorSourceType.imported, 4, 1.0),
            ],
        },
        {
            "code": "learning_behavior",
            "title": "学习行为与过程",
            "description": "用于描述资源偏好、策略偏好和交互方式。",
            "sort_order": 4,
            "indicators": [
                ("resource_preference", "资源偏好", "关注视频、图像、文本等资源偏好。", PortraitIndicatorSourceType.auto, 1, 1.0),
                ("strategy_preference", "辅助学习策略", "主要依据阶段导入的补救学习、学习路径调整和老师补充观察。", PortraitIndicatorSourceType.imported, 2, 1.0),
                ("text_discussion_interaction", "文本/讨论型交互偏好", "关注讨论、文本表达类交互。", PortraitIndicatorSourceType.auto, 3, 1.0),
                ("practice_experience_interaction", "实践/体验型交互偏好", "关注实验、练习、体验类交互。", PortraitIndicatorSourceType.auto, 4, 1.0),
            ],
        },
        {
            "code": "individual_background",
            "title": "个体基础特征",
            "description": "用于描述基础背景、兴趣类型和智能优势方向。",
            "sort_order": 5,
            "indicators": [
                ("academic_background", "人口学背景与学业经历", "关注基本背景信息和学业经历。", PortraitIndicatorSourceType.questionnaire, 1, 1.0),
                ("interest_type", "探究兴趣类型", "关注学习兴趣和问题探究倾向。", PortraitIndicatorSourceType.questionnaire, 2, 1.0),
                ("intelligence_advantage", "智能优势倾向标签", "关注多元智能优势标签。", PortraitIndicatorSourceType.questionnaire, 3, 1.0),
            ],
        },
    ]

    existing_dimensions = session.exec(select(PortraitDimension)).all()
    dimension_map = {item.code: item for item in existing_dimensions}

    for item in defaults:
        dimension = dimension_map.get(item["code"]) or PortraitDimension(code=item["code"])
        dimension.title = item["title"]
        dimension.description = item["description"]
        dimension.sort_order = item["sort_order"]
        dimension.active = True
        session.add(dimension)
        session.flush()

        existing_indicators = session.exec(
            select(PortraitIndicator).where(PortraitIndicator.dimension_id == dimension.id)
        ).all()
        indicator_map = {indicator.code: indicator for indicator in existing_indicators}

        for code, title, description, source_type, sort_order, weight in item["indicators"]:
            indicator = indicator_map.get(code) or PortraitIndicator(
                dimension_id=dimension.id,
                code=code,
            )
            indicator.dimension_id = dimension.id
            indicator.title = title
            indicator.description = description
            indicator.source_type = source_type
            indicator.sort_order = sort_order
            indicator.default_weight = weight
            indicator.active = True
            session.add(indicator)
    session.commit()
