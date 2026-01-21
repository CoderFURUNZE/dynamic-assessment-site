import json
from collections import deque

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.models import ExpressionEvent
from app.db.session import get_session
from app.schemas.vision import VisionAnalysisOut, VisionFrameIn
from app.services.vision import ExpressionEstimator, decode_base64_image_to_bgr

router = APIRouter(prefix="/vision", tags=["vision"])


@router.websocket("/ws")
async def vision_ws(
    ws: WebSocket,
    session: Session = Depends(get_session),
):
    await ws.accept()

    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=1008)
        return

    try:
        user = get_current_user(token=token, session=session)  # type: ignore
    except Exception:
        await ws.close(code=1008)
        return

    try:
        estimator = ExpressionEstimator()
    except Exception as e:
        await ws.send_text(json.dumps({"type": "error", "detail": str(e)}, ensure_ascii=False))
        await ws.close(code=1011)
        return

    smooth = deque(maxlen=8)

    try:
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            frame = VisionFrameIn(**data)
            img = decode_base64_image_to_bgr(frame.image_b64)
            res = estimator.analyze_bgr(img)
            smooth.append(res.difficulty)
            difficulty_s = sum(smooth) / len(smooth)

            session.add(
                ExpressionEvent(
                    user_id=user.id,
                    kp_id=frame.kp_id,
                    label=res.label,
                    confidence=float(res.confidence),
                    difficulty=float(difficulty_s),
                )
            )
            session.commit()

            out = VisionAnalysisOut(
                kp_id=frame.kp_id,
                label=res.label,
                confidence=float(res.confidence),
                difficulty=float(difficulty_s),
            )
            await ws.send_text(out.model_dump_json())
    except WebSocketDisconnect:
        return

