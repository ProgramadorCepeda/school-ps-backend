from pydantic import BaseModel


class ComplementaryItemResponse(BaseModel):
    """DTO para un ítem complementario dentro de la matrícula."""

    complementario_id: int
    tipo_complementario: str
    valor: int
    descuento: int
    valor_completo: int
    valor_pendiente: int


class StudentInfoResponse(BaseModel):
    """DTO con información básica del estudiante."""

    id: int
    nombre: str
    documento: str
    grado_id: int
    grado_nombre: str
    activo: bool


class EnrollmentBalanceResponse(BaseModel):
    """DTO de respuesta con el balance completo de matrícula."""

    estudiante: StudentInfoResponse
    anio: int
    costo_base_matricula: int
    complementarios: list[ComplementaryItemResponse]
    total_complementarios: int
    primer_mes_pension: int
    costo_total: int
    total_pagado: int
    total_pendiente: int
    estado_matricula: bool
    matricula_registrada: bool
    pendiente_base: int
    pendiente_pension: int


class EnrollmentCreatedResponse(BaseModel):
    """Respuesta al crear una matrícula."""

    matricula_id: int
    estudiante_id: int
    valor_total: int
    costo_base: int
    total_complementarios: int
    primer_mes_pension: int
    complementarios: list[ComplementaryItemResponse]
    mensaje: str


class PaymentDistributionResponse(BaseModel):
    """Detalle de cómo se distribuyó un pago a un concepto."""

    concepto: str
    complementario_id: int | None = None
    monto_aplicado: int


class PaymentResultResponse(BaseModel):
    """Respuesta al registrar un pago."""

    pago_id: int
    codigo_talonario: str
    monto_total: int
    monto_aplicado: int
    distribuciones: list[PaymentDistributionResponse]
    saldo_restante: int
    matricula_pagada: bool
    mensaje: str
