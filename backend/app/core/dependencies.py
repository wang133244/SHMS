from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import EmploymentStatus, Role
from app.models.staff import Staff

bearer = HTTPBearer(auto_error=False)


def get_current_staff(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> Staff:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing access token")
    try:
        staff_id = decode_access_token(credentials.credentials)
    except (ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid access token")
    staff = db.get(Staff, staff_id)
    if staff is None or staff.employment_status is not EmploymentStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive account")
    return staff


def require_admin(current: Staff = Depends(get_current_staff)) -> Staff:
    if current.role is not Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="administrator role required")
    return current


def require_assigned_position(current: Staff = Depends(get_current_staff)) -> Staff:
    if current.position is None and current.role is Role.EMPLOYEE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="岗位待分配")
    return current
