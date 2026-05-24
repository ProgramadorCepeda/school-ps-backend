from app.core.db import SessionDep
from app.modules.enrollment.infrastructure.repository import (
    SQLEnrollmentRepository,
)


class CreateComplementary:
    """Caso de uso: crear un concepto complementario nuevo."""

    def __init__(self, session: SessionDep) -> None:
        self._repository = SQLEnrollmentRepository(session)

    def execute(
        self,
        tipo_complementario: str,
        anio: int,
        valor: int,
        estado: str,
        uso_matricula: bool,
    ) -> int:
        return self._repository.create_complementary(
            tipo_complementario=tipo_complementario,
            anio=anio,
            valor=valor,
            estado=estado,
            uso_matricula=uso_matricula,
        )
