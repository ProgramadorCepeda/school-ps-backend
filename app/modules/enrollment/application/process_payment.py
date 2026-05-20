from app.modules.enrollment.domain.entities import PaymentResult
from app.modules.enrollment.domain.repositories import EnrollmentRepository
from app.modules.enrollment.domain.service import EnrollmentService



class ProcessDirectedPayment:
    """Caso de uso: pago con asignación dirigida."""

    def __init__(self, repository: EnrollmentRepository) -> None:
        self._service = EnrollmentService(repository)

    def execute(
        self,
        matricula_id: int,
        asignaciones: list[tuple[str, int | None, int]],
        codigo_talonario: str,
        observacion: str | None = None,
    ) -> PaymentResult:
        return self._service.process_directed_payment(
            matricula_id, asignaciones, codigo_talonario, observacion
        )
