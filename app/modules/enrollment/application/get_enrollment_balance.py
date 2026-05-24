from sqlmodel import Session

from app.modules.enrollment.domain.entities import EnrollmentBalance
from app.modules.enrollment.domain.service import EnrollmentService
from app.modules.enrollment.infrastructure.repository import (
    SQLEnrollmentRepository,
)


class GetEnrollmentBalance:
    """Caso de uso: obtener el balance de matrícula de un estudiante."""

    def __init__(self, session: Session) -> None:
        repository = SQLEnrollmentRepository(session)
        self._service = EnrollmentService(repository)

    def execute(self, student_id: int, year: int) -> EnrollmentBalance:
        return self._service.get_balance(student_id, year)
