from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.db import get_session
from app.modules.enrollment.application.get_enrollment_balance import (
    GetEnrollmentBalance,
)
from app.modules.enrollment.application.process_payment import (
    ProcessAutoPayment,
    ProcessDirectedPayment,
)
from app.modules.enrollment.application.register_enrollment import (
    RegisterEnrollment,
)
from app.modules.enrollment.infrastructure.repository_impl import (
    SQLEnrollmentRepository,
)
from app.modules.enrollment.schemas.request import (
    AutoPaymentRequest,
    DirectedPaymentRequest,
    RegisterEnrollmentRequest,
)
from app.modules.enrollment.schemas.response import (
    ComplementaryItemResponse,
    EnrollmentBalanceResponse,
    EnrollmentCreatedResponse,
    PaymentDistributionResponse,
    PaymentResultResponse,
    StudentInfoResponse,
)

router = APIRouter(
    responses={
        200: {"description": "OK"},
        404: {"description": "Recurso no encontrado"},
    },
)


@router.get(
    "/students/{student_id}/balance",
    response_model=EnrollmentBalanceResponse,
    summary="Obtener balance de matrícula de un estudiante",
    description=(
        "Retorna el desglose completo de lo que un estudiante debe en su "
        "matrícula, incluyendo el costo base, complementarios asignados "
        "y el primer mes de pensión."
    ),
)
async def get_enrollment_balance(
    student_id: int,
    year: int = Query(
        default=None,
        description="Año a consultar. Si no se envía, se usa el año actual.",
    ),
    session: Session = Depends(get_session),
) -> EnrollmentBalanceResponse:
    if year is None:
        year = datetime.now().year

    repository = SQLEnrollmentRepository(session)
    use_case = GetEnrollmentBalance(repository)

    try:
        balance = use_case.execute(student_id, year)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return EnrollmentBalanceResponse(
        estudiante=StudentInfoResponse(
            id=balance.student.id,
            nombre=balance.student.nombre,
            documento=balance.student.documento,
            grado_id=balance.student.grado_id,
            grado_nombre=balance.student.grado_nombre,
            activo=balance.student.activo,
        ),
        anio=balance.year,
        costo_base_matricula=balance.enrollment_base_cost,
        complementarios=[
            ComplementaryItemResponse(
                complementario_id=item.complementario_id,
                tipo_complementario=item.tipo_complementario,
                valor=item.valor,
                descuento=item.descuento,
                valor_completo=item.valor_completo,
                valor_pendiente=item.valor_pendiente,
            )
            for item in balance.complementary_items
        ],
        total_complementarios=balance.complementary_total,
        primer_mes_pension=balance.first_month_pension,
        costo_total=balance.total_cost,
        total_pagado=balance.total_paid,
        total_pendiente=balance.total_pending,
        estado_matricula=balance.enrollment_status,
        matricula_registrada=balance.enrollment_exists,
        pendiente_base=balance.pending_base,
        pendiente_pension=balance.pending_pension,
    )


@router.post(
    "/register",
    response_model=EnrollmentCreatedResponse,
    status_code=201,
    summary="Registrar matrícula para un estudiante",
    description=(
        "Genera automáticamente la matrícula para un estudiante. "
        "Calcula el costo base según su grado, asigna los complementarios "
        "activos con uso_matricula=True, y suma el primer mes de pensión."
    ),
)
async def register_enrollment(
    request: RegisterEnrollmentRequest,
    session: Session = Depends(get_session),
) -> EnrollmentCreatedResponse:
    repository = SQLEnrollmentRepository(session)
    use_case = RegisterEnrollment(repository)

    try:
        result = use_case.execute(
            request.estudiante_id, request.periodo_id, request.anio
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return EnrollmentCreatedResponse(
        matricula_id=result.matricula_id,
        estudiante_id=result.estudiante_id,
        valor_total=result.valor_total,
        costo_base=result.costo_base,
        total_complementarios=result.total_complementarios,
        primer_mes_pension=result.primer_mes_pension,
        complementarios=[
            ComplementaryItemResponse(
                complementario_id=c.complementario_id,
                tipo_complementario=c.tipo_complementario,
                valor=c.valor,
                descuento=c.descuento,
                valor_completo=c.valor_completo,
                valor_pendiente=c.valor_pendiente,
            )
            for c in result.complementarios
        ],
        mensaje=(
            f"Matrícula registrada exitosamente. "
            f"Total a pagar: ${result.valor_total:,}"
        ),
    )


@router.post(
    "/payments/auto",
    response_model=PaymentResultResponse,
    status_code=201,
    summary="Pago con auto-distribución",
    description=(
        "Registra un pago y distribuye el monto automáticamente en orden "
        "de prioridad: matrícula base → complementarios → pensión. "
        "Si el monto sobra después de completar un concepto, se aplica "
        "automáticamente al siguiente. Requiere código de talonario físico."
    ),
)
async def auto_payment(
    request: AutoPaymentRequest,
    session: Session = Depends(get_session),
) -> PaymentResultResponse:
    repository = SQLEnrollmentRepository(session)
    use_case = ProcessAutoPayment(repository)

    try:
        result = use_case.execute(
            request.matricula_id,
            request.monto,
            request.codigo_talonario,
            request.observacion,
        )
    except ValueError as e:
        error_msg = str(e)
        if "talonario" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg) from e
        raise HTTPException(status_code=400, detail=error_msg) from e

    if result.matricula_pagada:
        mensaje = "Matrícula completamente pagada!"
    elif result.monto_aplicado < result.monto_total:
        mensaje = (
            f"Pago registrado. Se aplicaron ${result.monto_aplicado:,} de "
            f"${result.monto_total:,}. El excedente de "
            f"${result.monto_total - result.monto_aplicado:,} no se aplicó "
            f"porque no hay más conceptos pendientes."
        )
    else:
        mensaje = (
            f"Pago parcial registrado. Saldo pendiente: "
            f"${result.saldo_restante_matricula:,}"
        )

    return PaymentResultResponse(
        pago_id=result.pago_id,
        codigo_talonario=result.codigo_talonario,
        monto_total=result.monto_total,
        monto_aplicado=result.monto_aplicado,
        distribuciones=[
            PaymentDistributionResponse(
                concepto=d.concepto,
                complementario_id=d.complementario_id,
                monto_aplicado=d.monto_aplicado,
            )
            for d in result.distribuciones
        ],
        saldo_restante=result.saldo_restante_matricula,
        matricula_pagada=result.matricula_pagada,
        mensaje=mensaje,
    )


@router.post(
    "/payments/directed",
    response_model=PaymentResultResponse,
    status_code=201,
    summary="Pago con asignación dirigida",
    description=(
        "Registra un pago donde el padre especifica exactamente cuánto "
        "va a cada concepto (matrícula base, complementarios específicos, "
        "pensión). Valida que no se pague más de lo pendiente por concepto. "
        "Requiere código de talonario físico."
    ),
)
async def directed_payment(
    request: DirectedPaymentRequest,
    session: Session = Depends(get_session),
) -> PaymentResultResponse:
    repository = SQLEnrollmentRepository(session)
    use_case = ProcessDirectedPayment(repository)

    asignaciones = [
        (a.concepto, a.complementario_id, a.monto)
        for a in request.asignaciones
    ]

    try:
        result = use_case.execute(
            request.matricula_id,
            asignaciones,
            request.codigo_talonario,
            request.observacion,
        )
    except ValueError as e:
        error_msg = str(e)
        if "talonario" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg) from e
        if "excede" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg) from e
        raise HTTPException(status_code=400, detail=error_msg) from e

    if result.matricula_pagada:
        mensaje = "Matrícula completamente pagada!"
    else:
        mensaje = (
            f"Pago dirigido registrado. Saldo pendiente: "
            f"${result.saldo_restante_matricula:,}"
        )

    return PaymentResultResponse(
        pago_id=result.pago_id,
        codigo_talonario=result.codigo_talonario,
        monto_total=result.monto_total,
        monto_aplicado=result.monto_aplicado,
        distribuciones=[
            PaymentDistributionResponse(
                concepto=d.concepto,
                complementario_id=d.complementario_id,
                monto_aplicado=d.monto_aplicado,
            )
            for d in result.distribuciones
        ],
        saldo_restante=result.saldo_restante_matricula,
        matricula_pagada=result.matricula_pagada,
        mensaje=mensaje,
    )
