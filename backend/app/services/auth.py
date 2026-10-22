from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EmploymentStatus
from app.models.staff import Staff


DEMO_PASSWORD = "123456"
DEMO_ACCOUNT_ALIASES = {
    "0001": "ADMIN-001",
    "1001": "EMP-LOGISTICS",
    "2001": "EMP-HEALTH",
    "3001": "EMP-CARE",
    "4001": "EMP-KITCHEN",
    "5001": "EMP-BUSINESS",
}


def resolve_demo_employee_no(employee_no: str) -> tuple[str, bool]:
    normalized = employee_no.strip()
    canonical = DEMO_ACCOUNT_ALIASES.get(normalized)
    return canonical or normalized, canonical is not None


def resolve_demo_login(employee_no: str, password: str) -> tuple[str, bool]:
    canonical, is_alias = resolve_demo_employee_no(employee_no)
    return canonical, is_alias and password == DEMO_PASSWORD


@dataclass(frozen=True)
class BindingResult:
    status: str
    staff: Staff | None = None


def bind_wechat_identity(db: Session, openid: str, phone: str) -> BindingResult:
    normalized_phone = phone.strip()
    by_openid = db.scalar(select(Staff).where(Staff.openid == openid))
    by_phone = db.scalar(select(Staff).where(Staff.phone == normalized_phone, Staff.employment_status == EmploymentStatus.ACTIVE))
    if by_phone is None:
        return BindingResult("pending_binding")
    if by_openid is not None and by_openid.id != by_phone.id:
        return BindingResult("binding_conflict")
    if by_phone.openid is not None and by_phone.openid != openid:
        return BindingResult("binding_conflict")
    by_phone.openid = openid
    db.commit(); db.refresh(by_phone)
    return BindingResult("bound", by_phone)
