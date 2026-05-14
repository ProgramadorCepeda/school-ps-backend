from pydantic import BaseModel, Field


class RegisterEnrollmentRequest(BaseModel):
    """Solicitud para registrar matrícula a un estudiante."""

    estudiante_id: int = Field(description="ID del estudiante")
    periodo_id: int = Field(description="ID del periodo electivo")
    anio: int = Field(description="Año de la matrícula")


class AutoPaymentRequest(BaseModel):
    """Pago con auto-distribución (cascada automática)."""

    matricula_id: int = Field(description="ID de la matrícula a pagar")
    monto: int = Field(
        gt=0,
        description=(
            "Monto total a pagar. Se distribuye automáticamente: "
            "primero matrícula base, luego complementarios, luego pensión."
        ),
    )
    codigo_talonario: str = Field(
        min_length=1,
        description="Código del talonario físico (planilla del colegio)",
    )
    observacion: str | None = Field(
        default=None, description="Observación opcional del pago"
    )


class ConceptoAsignacion(BaseModel):
    """Cuánto asignar a un concepto específico."""

    concepto: str = Field(
        description=(
            "Tipo de concepto: 'matricula_base', 'complementario', o 'pension'"
        ),
    )
    complementario_id: int | None = Field(
        default=None,
        description="ID del complementario (obligatorio si concepto='complementario')",
    )
    monto: int = Field(
        gt=0, description="Monto a aplicar a este concepto"
    )


class DirectedPaymentRequest(BaseModel):
    """Pago con asignación dirigida (el padre elige a dónde va cada monto)."""

    matricula_id: int = Field(description="ID de la matrícula a pagar")
    asignaciones: list[ConceptoAsignacion] = Field(
        min_length=1,
        description="Lista de conceptos con sus montos a pagar",
    )
    codigo_talonario: str = Field(
        min_length=1,
        description="Código del talonario físico",
    )
    observacion: str | None = Field(
        default=None, description="Observación opcional del pago"
    )
