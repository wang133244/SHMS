from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.core.config import get_settings
from app.db.session import get_db
from app.models.enums import EmploymentStatus
from app.models.staff import Staff
from app.services.auth import DEMO_ACCOUNT_ALIASES, bind_wechat_identity, resolve_demo_employee_no, resolve_demo_login
from app.services.wechat import exchange_phone_and_openid

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    employee_no: str


class PasswordLoginRequest(BaseModel):
    employee_no: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class WeChatLoginRequest(BaseModel):
    login_code: str = Field(min_length=1, max_length=128)
    phone_code: str = Field(min_length=1, max_length=128)


@router.post("/wechat/login")
def wechat_login(payload: WeChatLoginRequest, db: Session = Depends(get_db)):
    try:
        openid, phone = exchange_phone_and_openid(payload.login_code, payload.phone_code)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(401, "微信登录校验失败") from error
    result = bind_wechat_identity(db, openid, phone)
    if result.status == "binding_conflict":
        raise HTTPException(409, "微信账号或手机号已绑定其他员工")
    if result.staff is None:
        return {"status": result.status}
    return {"status": "pending_assignment" if result.staff.role.value == "employee" and result.staff.position is None else "active", "access_token": create_access_token(result.staff.id), "token_type": "bearer", "role": result.staff.role, "position": result.staff.position.code if result.staff.position else None, "employee_no": result.staff.employee_no}


@router.post("/password-login")
def password_login(payload: PasswordLoginRequest, db: Session = Depends(get_db)):
    submitted_employee_no = payload.employee_no.strip()
    employee_no, demo_password_valid = resolve_demo_login(submitted_employee_no, payload.password)
    staff = db.scalar(select(Staff).where(Staff.employee_no == employee_no))
    password_valid = demo_password_valid if submitted_employee_no in DEMO_ACCOUNT_ALIASES else verify_password(payload.password, staff.password_hash if staff else None)
    if staff is None or staff.employment_status is not EmploymentStatus.ACTIVE or not password_valid:
        raise HTTPException(status_code=401, detail="工号或密码错误")
    status = "pending_assignment" if staff.role.value == "employee" and staff.position is None else "active"
    return {"status": status, "access_token": create_access_token(staff.id), "token_type": "bearer", "role": staff.role, "position": staff.position.code if staff.position else None, "employee_no": staff.employee_no, "login_employee_no": submitted_employee_no}


@router.post("/dev-login")
def dev_login(payload: DevLoginRequest, db: Session = Depends(get_db)):
    if get_settings().app_env != "development":
        raise HTTPException(404, "not found")
    employee_no, is_demo_alias = resolve_demo_employee_no(payload.employee_no)
    staff = db.scalar(select(Staff).where(Staff.employee_no == employee_no))
    if staff is None or staff.employment_status is not EmploymentStatus.ACTIVE:
        raise HTTPException(status_code=401, detail="pending_binding")
    return {"access_token": create_access_token(staff.id), "token_type": "bearer", "role": staff.role, "position": staff.position.code if staff.position else None, "employee_no": staff.employee_no, "login_employee_no": payload.employee_no.strip() if is_demo_alias else staff.employee_no}
