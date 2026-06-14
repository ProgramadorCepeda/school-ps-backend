from app.core.db import SessionDep
from app.modules.training_schools.domain.entities import TipoComplementarioInfo
from app.modules.training_schools.domain.service import TrainingSchoolService
from app.modules.training_schools.infrastructure.enrollment_adapter import (
    EnrollmentAdapter,
)
from app.modules.training_schools.infrastructure.repository import (
    TrainingSchoolRepository,
)


class ListTiposComplementario:
    def __init__(self, session: SessionDep) -> None:
        self.service = TrainingSchoolService(
            repository=TrainingSchoolRepository(session=session),
            enrollment=EnrollmentAdapter(session),
        )

    async def execute(self) -> list[TipoComplementarioInfo]:
        return await self.service.list_tipos_complementario()


class CreateTipoComplementario:
    def __init__(self, session: SessionDep) -> None:
        self.service = TrainingSchoolService(
            repository=TrainingSchoolRepository(session=session),
            enrollment=EnrollmentAdapter(session),
        )

    async def execute(
        self, nombre: str, sub_tipo_complementario: int | None
    ) -> TipoComplementarioInfo:
        return await self.service.create_tipo_complementario(
            nombre=nombre, sub_tipo_complementario=sub_tipo_complementario
        )


class UpdateTipoComplementario:
    def __init__(self, session: SessionDep) -> None:
        self.service = TrainingSchoolService(
            repository=TrainingSchoolRepository(session=session),
            enrollment=EnrollmentAdapter(session),
        )

    async def execute(
        self,
        tipo_id: int,
        nombre: str | None,
        estado: bool | None,
        sub_tipo_complementario: int | None,
    ) -> TipoComplementarioInfo:
        return await self.service.update_tipo_complementario(
            tipo_id=tipo_id,
            nombre=nombre,
            estado=estado,
            sub_tipo_complementario=sub_tipo_complementario,
        )


class DeleteTipoComplementario:
    def __init__(self, session: SessionDep) -> None:
        self.service = TrainingSchoolService(
            repository=TrainingSchoolRepository(session=session),
            enrollment=EnrollmentAdapter(session),
        )

    async def execute(self, tipo_id: int) -> None:
        await self.service.delete_tipo_complementario(tipo_id)
