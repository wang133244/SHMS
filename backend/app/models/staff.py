from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CalendarKind, EmploymentStatus, PositionCode, Role


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[PositionCode] = mapped_column(Enum(PositionCode), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)


class Staff(Base):
    __tablename__ = "staff"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    employee_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256))
    openid: Mapped[str | None] = mapped_column(String(128), unique=True)
    position_id: Mapped[int | None] = mapped_column(ForeignKey("positions.id"))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.EMPLOYEE, nullable=False)
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        Enum(EmploymentStatus), default=EmploymentStatus.ACTIVE, nullable=False
    )
    position: Mapped[Position | None] = relationship()


class WorkCalendar(Base):
    __tablename__ = "work_calendars"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    kind: Mapped[CalendarKind] = mapped_column(Enum(CalendarKind), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(240))
