from app.core.db import SessionDep
from app.modules.enrollment.infrastructure.repository import (
    SQLEnrollmentRepository,
)


class GetPaymentReceipt:
    """Caso de uso: obtener los datos completos de un recibo/comprobante de pago."""

    def __init__(self, session: SessionDep) -> None:
        self.repo = SQLEnrollmentRepository(session)

    def execute(self, pago_id: int) -> dict:
        receipt_data = self.repo.get_payment_receipt_data(pago_id)
        if receipt_data is None:
            raise ValueError(f"Pago con ID {pago_id} no encontrado")
        return receipt_data
