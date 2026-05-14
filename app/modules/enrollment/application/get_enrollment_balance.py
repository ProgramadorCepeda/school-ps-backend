from app.modules.enrollment.domain.entities import EnrollmentBalance
from app.modules.enrollment.domain.repositories import EnrollmentRepository
from app.modules.enrollment.domain.service import EnrollmentService


class GetEnrollmentBalance:
    """Caso de uso: obtener el balance de matrícula de un estudiante."""

    def __init__(self, repository: EnrollmentRepository) -> None:
        self._service = EnrollmentService(repository)

    def execute(self, student_id: int, year: int) -> EnrollmentBalance:
        return self._service.get_balance(student_id, year)
