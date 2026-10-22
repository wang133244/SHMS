import httpx

from app.core.config import get_settings


def exchange_phone_and_openid(login_code: str, phone_code: str) -> tuple[str, str]:
    settings = get_settings()
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise RuntimeError("微信 AppID/Secret 尚未配置")
    timeout = httpx.Timeout(8.0)
    with httpx.Client(timeout=timeout) as client:
        session_response = client.get("https://api.weixin.qq.com/sns/jscode2session", params={
            "appid": settings.wechat_app_id,
            "secret": settings.wechat_app_secret,
            "js_code": login_code,
            "grant_type": "authorization_code",
        })
        session_data = session_response.json()
        if session_response.status_code != 200 or session_data.get("errcode") or not session_data.get("openid"):
            raise ValueError("微信登录凭证无效")

        token_response = client.get("https://api.weixin.qq.com/cgi-bin/token", params={
            "grant_type": "client_credential",
            "appid": settings.wechat_app_id,
            "secret": settings.wechat_app_secret,
        })
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if token_response.status_code != 200 or not access_token:
            raise RuntimeError("获取微信手机号授权凭证失败")

        phone_response = client.post(
            "https://api.weixin.qq.com/wxa/business/getuserphonenumber",
            params={"access_token": access_token},
            json={"code": phone_code},
        )
        phone_data = phone_response.json()
        phone_info = phone_data.get("phone_info") or {}
        phone = phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber")
        if phone_response.status_code != 200 or phone_data.get("errcode") or not phone:
            raise ValueError("微信手机号授权失败")
    phone = phone.replace("+86", "").replace(" ", "")
    return session_data["openid"], phone
