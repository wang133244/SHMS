from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class PositionCode(StrEnum):
    LOGISTICS = "logistics"
    SECURITY = "security"
    HEALTH = "health"
    CARE = "care"
    KITCHEN = "kitchen"
    BUSINESS = "business"


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CalendarKind(StrEnum):
    WORKDAY = "workday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"
    SCHOOL_BREAK = "school_break"
    MAKEUP_WORKDAY = "makeup_workday"


class Frequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEMESTER = "semester"
    SECURITY_WEEKEND = "security_weekend"


class TaskStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CHANGE_PENDING = "change_pending"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PublicationStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DISABLED = "disabled"
