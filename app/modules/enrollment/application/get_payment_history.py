from app.core.db import SessionDep
from app.modules.enrollment.infrastructure.repository import (
    SQLEnrollmentRepository,
)


class GetPaymentHistory:
    """Caso de uso: obtener el historial de pagos de un estudiante para auditoría."""

    def __init__(self, session: SessionDep) -> None:
        self.repo = SQLEnrollmentRepository(session)

    def execute(self, student_id: int, year: int) -> list:
        student = self.repo.get_student_by_id(student_id)
        if student is None:
            raise ValueError(f"Estudiante con ID {student_id} no encontrado")

        matricula_id, _, _, _, _ = self.repo.get_enrollment_details(student_id, year)
        if matricula_id is None:
            return []

        return self.repo.get_payments_by_matricula(matricula_id)
