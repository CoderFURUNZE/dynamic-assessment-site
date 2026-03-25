from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


class WechatLoginRequest(BaseModel):
    openid: str
    phone: str | None = None


class WechatBindRequest(BaseModel):
    openid: str
    phone: str
