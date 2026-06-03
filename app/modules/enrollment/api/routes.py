from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from app.core.db import SessionDep
from app.modules.enrollment.application.assign_complementary import (
    AssignComplementary,
)
from app.modules.enrollment.application.create_complementary import (
    CreateComplementary,
)
from app.modules.enrollment.application.get_enrollment_balance import (
    GetEnrollmentBalance,
)
from app.modules.enrollment.application.mass_enrollment import MassEnrollment
from app.modules.enrollment.application.modify_enrollment import ModifyEnrollment
from app.modules.enrollment.application.process_payment import ProcessDirectedPayment
from app.modules.enrollment.application.register_enrollment import (
    RegisterEnrollment,
)
from app.modules.enrollment.application.search_students import SearchStudents
from app.modules.enrollment.schemas.request import (
    DirectedPaymentRequest,
    RegisterEnrollmentRequest,
    ModifyEnrollmentRequest,
    ComplementaryCreateRequest,
    AssignComplementaryRequest,
)
from app.modules.enrollment.schemas.response import (
    ComplementaryItemResponse,
    EnrollmentBalanceResponse,
    EnrollmentCreatedResponse,
    PaymentDistributionResponse,
    PaymentHistoryItemResponse,
    PaymentReceiptResponse,
    PaymentResultResponse,
    ReceiptDistributionResponse,
    ReceiptGuardianResponse,
    ReceiptStudentResponse,
    StudentInfoResponse,
    StudentSearchItemResponse,
    StudentSearchListResponse,
    StudentGeneralInfoResponse,
    GradeInfoResponse,
    ComplementaryConceptResponse,
)
from app.modules.enrollment.infrastructure.models import (
    Acudiente,
    Estudiante,
    Grado,
    Matricula,
    Pago,
    PagoDetalle,
)
from app.modules.enrollment.domain.service import StudentService
from app.modules.enrollment.infrastructure.repository import SQLEnrollmentRepository

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
    session: SessionDep,
    student_id: int,
    year: int | None = Query(
        default=None,
        description="Año a consultar. Si no se envía, se usa el año actual.",
    ),
) -> EnrollmentBalanceResponse:
    if year is None:
        year = datetime.now().year

    use_case = GetEnrollmentBalance(session=session)

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
                detalle_id=item.detalle_id,
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
        costo_total=balance.total_cost,
        total_pagado=balance.total_paid,
        total_pendiente=balance.total_pending,
        estado_matricula=balance.enrollment_status,
        matricula_registrada=balance.enrollment_exists,
        pendiente_base=balance.pending_base,
        pagos_realizados=balance.payments_count,
        matricula_id=balance.matricula_id,
    )


@router.get(
    "/students",
    response_model=StudentSearchListResponse,
    summary="Buscar estudiantes con su estado de matrícula y balance",
    description="Retorna una lista de estudiantes que coinciden con los filtros, con su balance consolidado.",
)
async def search_students(
    session: SessionDep,
    documento: str | None = Query(
        default=None,
        description="Coincidencia parcial del documento/código",
    ),
    nombre: str | None = Query(
        default=None,
        description="Coincidencia parcial del nombre",
    ),
    year: int | None = Query(
        default=None,
        description="Año a consultar. Si no se envía, se usa el año actual.",
    ),
) -> StudentSearchListResponse:
    if year is None:
        year = datetime.now().year

    use_case = SearchStudents(session=session)
    balances = use_case.execute(documento, nombre, year)

    items = []
    for b in balances:
        items.append(
            StudentSearchItemResponse(
                estudiante_id=b.student.id,
                documento=b.student.documento,
                nombre=b.student.nombre,
                grado_id=b.student.grado_id,
                grado_nombre=b.student.grado_nombre,
                anio=b.year,
                matricula_registrada=b.enrollment_exists,
                estado_matricula=(
                    b.enrollment_status if b.enrollment_exists else "sin_matricula"
                ),
                pagos_realizados=b.payments_count,
                saldo_pendiente=b.total_pending,
                costo_total=b.total_cost,
                total_pagado=b.total_paid,
            )
        )

    return StudentSearchListResponse(
        estudiantes=items,
        total_resultados=len(items),
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
    session: SessionDep,
    request: RegisterEnrollmentRequest,
) -> EnrollmentCreatedResponse:
    use_case = RegisterEnrollment(session=session)

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
        complementarios=[
            ComplementaryItemResponse(
                detalle_id=c.detalle_id,
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
            f"Matrícula registrada exitosamente. Total a pagar: ${result.valor_total:,}"
        ),
    )


@router.put(
    "/students/{matricula_id}/matricula",
    status_code=200,
    summary="Modificar matrícula en tiempo real",
    description=(
        "Permite al administrador sobrescribir o aplicar descuentos al costo base, "
        "pensión o complementarios de una matrícula en tiempo real."
    ),
)
async def modify_enrollment(
    session: SessionDep,
    matricula_id: int,
    request: ModifyEnrollmentRequest,
) -> dict:
    use_case = ModifyEnrollment(session=session)

    try:
        result = use_case.execute(matricula_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return result


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
    session: SessionDep,
    request: DirectedPaymentRequest,
) -> PaymentResultResponse:
    use_case = ProcessDirectedPayment(session=session)

    asignaciones = [
        (a.concepto, a.complementario_id, a.monto) for a in request.asignaciones
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


@router.post(
    "/register/massive/csv",
    status_code=201,
    summary="Registrar matrículas masivamente vía CSV",
)
async def register_massive_csv(
    session: SessionDep,
    periodo_id: int,
    anio: int,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Archivo inválido. Solo se admiten archivos con extensión .csv",
        )
    use_case = MassEnrollment(session=session)

    content = await file.read()
    return use_case.execute(content, periodo_id, anio)


@router.post(
    "/register/massive/txt",
    status_code=201,
    summary="Registrar matrículas masivamente vía TXT",
)
async def register_massive_txt(
    session: SessionDep,
    periodo_id: int,
    anio: int,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Archivo inválido. Solo se admiten archivos con extensión .txt",
        )
    use_case = MassEnrollment(session=session)

    content = await file.read()
    return use_case.execute(content, periodo_id, anio)


@router.post(
    "/complementary",
    status_code=201,
    summary="Crear un concepto complementario nuevo",
)
async def create_complementary(
    session: SessionDep,
    request: ComplementaryCreateRequest,
):
    use_case = CreateComplementary(session=session)
    comp_id = use_case.execute(
        tipo_complementario=request.tipo_complementario,
        anio=request.anio,
        valor=request.valor,
        estado=request.estado_complemento,
        uso_matricula=request.uso_matricula,
    )
    return {
        "mensaje": "Complementario creado exitosamente",
        "complementario_id": comp_id,
    }


@router.post(
    "/{matricula_id}/complementary/assign",
    status_code=201,
    summary="Asignar un complementario a una matrícula existente",
)
async def assign_complementary(
    session: SessionDep,
    matricula_id: int,
    request: AssignComplementaryRequest,
):
    use_case = AssignComplementary(session=session)

    try:
        detalle_id = use_case.execute(
            matricula_id=matricula_id,
            complementary_id=request.complementario_id,
            descuento=request.descuento,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "mensaje": "Complementario asignado exitosamente a la matrícula",
        "detalle_id": detalle_id,
    }


@router.get(
    "/students/active",
    response_model=list[StudentGeneralInfoResponse],
    summary="Buscar estudiantes activos",
    description="Retorna una lista paginada de estudiantes activos filtrados opcionalmente por nombre/documento o grado.",
)
async def search_active_students(
    session: SessionDep,
    query: str | None = Query(default=None, description="Búsqueda por nombre o documento"),
    grado_id: int | None = Query(default=None, description="Filtrar por grado académico"),
    limit: int = Query(default=10, description="Límite de paginación"),
    offset: int = Query(default=0, description="Offset de paginación"),
) -> list[StudentGeneralInfoResponse]:
    service = StudentService(SQLEnrollmentRepository(session))
    results = service.search_active_students(query=query, grado_id=grado_id, limit=limit, offset=offset)
    return [
        StudentGeneralInfoResponse(
            id=s.id,
            nombre=s.nombre,
            documento=s.documento,
            grado_nombre=s.grado_nombre,
        )
        for s in results
    ]


@router.post(
    "/students/bulk",
    response_model=list[StudentGeneralInfoResponse],
    summary="Obtener información de estudiantes por lote",
    description="Recibe una lista de IDs de estudiantes y retorna su información básica.",
)
async def get_students_bulk(
    session: SessionDep,
    student_ids: list[int],
) -> list[StudentGeneralInfoResponse]:
    service = StudentService(SQLEnrollmentRepository(session))
    results = service.get_students_bulk(student_ids)
    return [
        StudentGeneralInfoResponse(
            id=s.id,
            nombre=s.nombre,
            documento=s.documento,
            grado_nombre=s.grado_nombre,
        )
        for s in results
    ]


@router.get(
    "/grades",
    response_model=list[GradeInfoResponse],
    summary="Obtener listado de grados disponibles",
    description="Retorna la lista de todos los grados académicos registrados.",
)
async def get_all_grades(
    session: SessionDep,
) -> list[GradeInfoResponse]:
    service = StudentService(SQLEnrollmentRepository(session))
    results = service.get_all_grades()
    return [
        GradeInfoResponse(
            id=g.id,
            nombre=g.nombre,
        )
        for g in results
    ]


@router.get(
    "/complementary",
    response_model=list[ComplementaryConceptResponse],
    summary="Obtener todos los conceptos complementarios activos por año",
)
async def get_complementaries(
    session: SessionDep,
    year: int | None = Query(
        default=None,
        description="Año a consultar. Si no se envía, se usa el año actual.",
    ),
) -> list[ComplementaryConceptResponse]:
    if year is None:
        year = datetime.now().year
    repo = SQLEnrollmentRepository(session)
    results = repo.get_all_complementaries_by_year(year)
    return [
        ComplementaryConceptResponse(
            id=c.id,  # type: ignore
            tipo_complementario=c.tipo_complementario,
            anio=c.anio,
            valor=c.valor,
            estado_complemento=c.estado_complemento,
            uso_matricula=c.uso_matricula,
        )
        for c in results
        if c.id is not None
    ]


@router.get(
    "/students/{student_id}/payments",
    response_model=list[PaymentHistoryItemResponse],
    summary="Obtener historial de pagos de un estudiante",
    description=(
        "Retorna la lista de pagos realizados por un estudiante "
        "para un año determinado. Si no se envía año, se usa el actual."
    ),
)
async def get_student_payments(
    session: SessionDep,
    student_id: int,
    year: int | None = Query(
        default=None,
        description="Año a consultar. Si no se envía, se usa el año actual.",
    ),
) -> list[PaymentHistoryItemResponse]:
    if year is None:
        year = datetime.now().year

    repo = SQLEnrollmentRepository(session)

    # Obtener la matrícula del estudiante para el año dado
    mat_id, _estado, _comps, _pend, _total = repo.get_enrollment_details(
        student_id, year
    )

    if mat_id is None:
        return []

    pagos = repo.get_payments(mat_id)

    return [
        PaymentHistoryItemResponse(
            id=p.id,  # type: ignore
            fecha_pago=p.fecha_pago.isoformat(),
            codigo_talonario=p.codigo_talonario,
            monto_total=p.monto_total,
            observacion=p.observacion,
        )
        for p in pagos
        if p.id is not None
    ]


@router.get(
    "/payments/{pago_id}/receipt",
    response_model=PaymentReceiptResponse,
    summary="Obtener comprobante/recibo de un pago",
    description=(
        "Retorna los datos completos del comprobante de pago, incluyendo "
        "información del estudiante, acudiente y distribución del pago."
    ),
)
async def get_payment_receipt(
    session: SessionDep,
    pago_id: int,
) -> PaymentReceiptResponse:
    from sqlmodel import select

    # 1. Obtener el pago
    pago = session.exec(select(Pago).where(Pago.id == pago_id)).first()
    if pago is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    # 2. Obtener matrícula → estudiante → grado + acudiente
    matricula = session.exec(
        select(Matricula).where(Matricula.id == pago.matricula_id)
    ).first()
    if matricula is None:
        raise HTTPException(status_code=404, detail="Matrícula asociada no encontrada")

    estudiante = session.exec(
        select(Estudiante).where(Estudiante.id == matricula.estudiante_id)
    ).first()
    if estudiante is None:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    grado = session.exec(
        select(Grado).where(Grado.id == estudiante.grado_id)
    ).first()

    acudiente = session.exec(
        select(Acudiente).where(Acudiente.id == estudiante.acudiente_id)
    ).first()

    # 3. Obtener distribuciones del pago
    detalles = session.exec(
        select(PagoDetalle).where(PagoDetalle.pago_id == pago_id)
    ).all()

    return PaymentReceiptResponse(
        pago_id=pago_id,
        codigo_talonario=pago.codigo_talonario,
        fecha_pago=pago.fecha_pago.isoformat(),
        monto_total=pago.monto_total,
        observacion=pago.observacion,
        estudiante=ReceiptStudentResponse(
            nombre=estudiante.nombre,
            documento=estudiante.documento,
            grado=grado.nombre if grado else "Sin grado",
        ),
        acudiente=ReceiptGuardianResponse(
            nombre=acudiente.nombre if acudiente else "Sin acudiente",
        ),
        distribuciones=[
            ReceiptDistributionResponse(
                concepto=d.concepto,
                monto_aplicado=d.monto_aplicado,
            )
            for d in detalles
        ],
    )

