from app.modules.enrollment.domain.entities import EnrollmentCreated
from app.modules.enrollment.domain.repositories import EnrollmentRepository
from app.modules.enrollment.domain.service import EnrollmentService


class RegisterEnrollment:
    """Caso de uso: registrar matrícula automáticamente para un estudiante."""

    def __init__(self, repository: EnrollmentRepository) -> None:
        self._service = EnrollmentService(repository)

    def execute(
        self, student_id: int, period_id: int, year: int
    ) -> EnrollmentCreated:
        return self._service.register_enrollment(student_id, period_id, year)
