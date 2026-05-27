from app.core.db import SessionDep
from app.modules.enrollment.domain.entities import EnrollmentBalance
from app.modules.enrollment.domain.service import EnrollmentService
from app.modules.enrollment.infrastructure.repository import (
    SQLEnrollmentRepository,
)


class SearchStudents:
    """Caso de uso: buscar estudiantes y obtener su balance consolidado."""

    def __init__(self, session: SessionDep) -> None:
        repository = SQLEnrollmentRepository(session)
        self.service = EnrollmentService(repository)

    def execute(
        self,
        documento: str | None,
        nombre: str | None,
        year: int,
    ) -> list[EnrollmentBalance]:
        students = self.service.repo.search_students(documento, nombre)
        balances = []
        for student in students:
            balance = self.service.get_balance(student.id, year)
            balances.append(balance)
        return balances
