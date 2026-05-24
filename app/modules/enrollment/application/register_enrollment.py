from sqlmodel import Session

from app.modules.enrollment.domain.entities import EnrollmentCreated
from app.modules.enrollment.domain.service import EnrollmentService
from app.modules.enrollment.infrastructure.repository import (
    SQLEnrollmentRepository,
)


class RegisterEnrollment:
    """Caso de uso: registrar matrícula automáticamente para un estudiante."""

    def __init__(self, session: Session) -> None:
        repository = SQLEnrollmentRepository(session)
        self._service = EnrollmentService(repository)

    def execute(
        self, student_id: int, period_id: int, year: int
    ) -> EnrollmentCreated:
        return self._service.register_enrollment(student_id, period_id, year)
