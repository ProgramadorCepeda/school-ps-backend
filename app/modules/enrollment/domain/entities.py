from dataclasses import dataclass, field


@dataclass
class StudentInfo:
    """Información básica del estudiante."""

    id: int
    nombre: str
    documento: str
    grado_id: int
    grado_nombre: str
    activo: bool


@dataclass
class ComplementaryDetail:
    """Detalle de un complementario dentro de la matrícula."""

    complementario_id: int
    tipo_complementario: str
    valor: int
    descuento: int
    valor_completo: int
    valor_pendiente: int


@dataclass
class EnrollmentBalance:
    """Resultado consolidado del balance de matrícula de un estudiante."""

    student: StudentInfo
    year: int
    enrollment_base_cost: int
    complementary_items: list[ComplementaryDetail] = field(default_factory=list)
    complementary_total: int = 0
    first_month_pension: int = 0
    total_cost: int = 0
    total_paid: int = 0
    total_pending: int = 0
    enrollment_status: bool = False
    enrollment_exists: bool = False
    pending_base: int = 0
    pending_pension: int = 0


@dataclass
class PaymentAllocation:
    """Cómo se distribuyó una parte del pago a un concepto."""

    concepto: str
    complementario_id: int | None
    monto_aplicado: int


@dataclass
class PaymentResult:
    """Resultado de procesar un pago."""

    pago_id: int
    codigo_talonario: str
    monto_total: int
    monto_aplicado: int
    distribuciones: list[PaymentAllocation]
    saldo_restante_matricula: int
    matricula_pagada: bool


@dataclass
class EnrollmentCreated:
    """Resultado de registrar una matrícula."""

    matricula_id: int
    estudiante_id: int
    valor_total: int
    costo_base: int
    total_complementarios: int
    primer_mes_pension: int
    complementarios: list[ComplementaryDetail]
