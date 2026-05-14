from app.modules.enrollment.domain.entities import (
    ComplementaryDetail,
    EnrollmentBalance,
    EnrollmentCreated,
    PaymentAllocation,
    PaymentResult,
)
from app.modules.enrollment.domain.repositories import EnrollmentRepository


class EnrollmentService:
    """Servicio de dominio que calcula el balance de matrícula."""

    def __init__(self, repository: EnrollmentRepository) -> None:
        self._repo = repository

    def get_balance(self, student_id: int, year: int) -> EnrollmentBalance:
        """
        Calcula el balance completo de matrícula de un estudiante.

        Incluye:
        - Costo base de matrícula (según grado y año)
        - Complementarios asignados (con descuentos)
        - Primer mes de pensión
        - Totales: costo, pagado y pendiente
        """
        student = self._repo.get_student_by_id(student_id)
        if student is None:
            msg = f"Estudiante con id {student_id} no encontrado"
            raise ValueError(msg)

        # Costo base de matrícula según grado y año
        base_cost = self._repo.get_enrollment_base_cost(student.grado_id, year) or 0

        # Detalles de matrícula (complementarios asignados)
        (
            matricula_id,
            enrollment_status,
            complementary_items,
            pending_base,
            pending_pension,
        ) = self._repo.get_enrollment_details(student_id, year)
        enrollment_exists = matricula_id is not None

        complementary_total = sum(item.valor_completo for item in complementary_items)

        # Primer mes de pensión
        first_month_pension = (
            self._repo.get_first_month_pension_cost(student.grado_id, year) or 0
        )

        # Cálculos totales
        total_cost = base_cost + complementary_total + first_month_pension

        if enrollment_exists:
            # Pendiente = base pendiente + complementarios pendientes + pensión pendiente
            total_pending = (
                pending_base
                + sum(item.valor_pendiente for item in complementary_items)
                + pending_pension
            )
        else:
            # Sin matrícula: todo está pendiente
            total_pending = total_cost

        total_paid = total_cost - total_pending

        return EnrollmentBalance(
            student=student,
            year=year,
            enrollment_base_cost=base_cost,
            complementary_items=complementary_items,
            complementary_total=complementary_total,
            first_month_pension=first_month_pension,
            total_cost=total_cost,
            total_paid=total_paid,
            total_pending=total_pending,
            enrollment_status=enrollment_status,
            enrollment_exists=enrollment_exists,
            pending_base=pending_base,
            pending_pension=pending_pension,
        )

    def register_enrollment(
        self, student_id: int, period_id: int, year: int
    ) -> EnrollmentCreated:
        """
        Genera la matrícula automáticamente para un estudiante.

        1. Busca costo base por grado del estudiante
        2. Asigna complementarios activos con uso_matricula=True
        3. Suma 1er mes de pensión
        4. Crea registro Matricula + DetalleMatricula
        """
        student = self._repo.get_student_by_id(student_id)
        if student is None:
            msg = f"Estudiante con id {student_id} no encontrado"
            raise ValueError(msg)

        if self._repo.student_has_enrollment(student_id, year):
            msg = f"El estudiante {student_id} ya tiene matrícula registrada para {year}"
            raise ValueError(msg)

        # Costo base
        base_cost = self._repo.get_enrollment_base_cost(student.grado_id, year)
        if base_cost is None:
            msg = (
                f"No hay costo de matrícula parametrizado para "
                f"grado '{student.grado_nombre}' en {year}"
            )
            raise ValueError(msg)

        param_id = self._repo.get_param_matricula_id(student.grado_id, year)
        if param_id is None:
            msg = "No se encontró parametrización de matrícula"
            raise ValueError(msg)

        # Complementarios activos
        active_comps = self._repo.get_active_complementaries(year)
        comp_details: list[tuple[int, int]] = []
        comp_entities: list[ComplementaryDetail] = []

        for comp_id, tipo, valor in active_comps:
            comp_details.append((comp_id, valor))
            comp_entities.append(
                ComplementaryDetail(
                    complementario_id=comp_id,
                    tipo_complementario=tipo,
                    valor=valor,
                    descuento=0,
                    valor_completo=valor,
                    valor_pendiente=valor,
                )
            )

        total_complementarios = sum(v for _, v in comp_details)

        # Primer mes de pensión
        pension = (
            self._repo.get_first_month_pension_cost(student.grado_id, year) or 0
        )

        valor_total = base_cost + total_complementarios + pension

        # Crear en BD
        matricula_id = self._repo.create_enrollment(
            para_matricula_id=param_id,
            student_id=student_id,
            period_id=period_id,
            valor_total=valor_total,
            base_cost=base_cost,
            pension_cost=pension,
            complementary_details=comp_details,
        )

        return EnrollmentCreated(
            matricula_id=matricula_id,
            estudiante_id=student_id,
            valor_total=valor_total,
            costo_base=base_cost,
            total_complementarios=total_complementarios,
            primer_mes_pension=pension,
            complementarios=comp_entities,
        )

    def process_auto_payment(
        self,
        matricula_id: int,
        monto: int,
        codigo_talonario: str,
        observacion: str | None = None,
    ) -> PaymentResult:
        """
        Procesa un pago con auto-distribución.

        Distribuye el monto en orden de prioridad:
        1. Costo base de matrícula
        2. Complementarios asignados (en orden)
        3. Primer mes de pensión

        Si el monto sobra después de pagar un concepto, automáticamente
        se aplica al siguiente.
        """
        if monto <= 0:
            msg = "El monto del pago debe ser mayor a 0"
            raise ValueError(msg)

        enrollment = self._repo.get_enrollment_by_id(matricula_id)
        if enrollment is None:
            msg = f"Matrícula con id {matricula_id} no encontrada"
            raise ValueError(msg)

        if not self._repo.validate_talonario_unique(codigo_talonario):
            msg = f"El código de talonario '{codigo_talonario}' ya está registrado"
            raise ValueError(msg)

        (
            _mat_id,
            _est_id,
            _valor_total,
            _estado,
            pending_base,
            pending_pension,
            _param_id,
        ) = enrollment

        # Obtener complementarios con pendientes
        comp_details = self._repo.get_enrollment_complementary_details(matricula_id)

        remaining = monto
        distribuciones: list[PaymentAllocation] = []

        # 1. Aplicar a costo base
        if remaining > 0 and pending_base > 0:
            aplicar = min(remaining, pending_base)
            new_pending = pending_base - aplicar
            self._repo.update_pending_base(matricula_id, new_pending)
            distribuciones.append(
                PaymentAllocation(
                    concepto="matricula_base",
                    complementario_id=None,
                    monto_aplicado=aplicar,
                )
            )
            remaining -= aplicar

        # 2. Aplicar a complementarios (en orden)
        for _det_id, comp_id, tipo, comp_pending in comp_details:
            if remaining <= 0:
                break
            if comp_pending <= 0:
                continue
            aplicar = min(remaining, comp_pending)
            new_pending = comp_pending - aplicar
            self._repo.update_complementary_pending(
                matricula_id, comp_id, new_pending
            )
            distribuciones.append(
                PaymentAllocation(
                    concepto=f"complementario:{tipo}",
                    complementario_id=comp_id,
                    monto_aplicado=aplicar,
                )
            )
            remaining -= aplicar

        # 3. Aplicar a pensión
        if remaining > 0 and pending_pension > 0:
            aplicar = min(remaining, pending_pension)
            new_pending = pending_pension - aplicar
            self._repo.update_pending_pension(matricula_id, new_pending)
            distribuciones.append(
                PaymentAllocation(
                    concepto="pension",
                    complementario_id=None,
                    monto_aplicado=aplicar,
                )
            )
            remaining -= aplicar

        monto_aplicado = monto - remaining

        # Registrar pago
        pago_id = self._repo.create_payment(
            matricula_id=matricula_id,
            codigo_talonario=codigo_talonario,
            monto_total=monto,
            modo_pago="auto",
            observacion=observacion,
            distribuciones=[
                (d.concepto, d.complementario_id, d.monto_aplicado)
                for d in distribuciones
            ],
        )

        # Verificar si la matrícula quedó completamente pagada
        saldo = self._calculate_total_pending(matricula_id)
        if saldo == 0:
            self._repo.update_enrollment_status(matricula_id, True)

        return PaymentResult(
            pago_id=pago_id,
            codigo_talonario=codigo_talonario,
            monto_total=monto,
            monto_aplicado=monto_aplicado,
            distribuciones=distribuciones,
            saldo_restante_matricula=saldo,
            matricula_pagada=saldo == 0,
        )

    def process_directed_payment(
        self,
        matricula_id: int,
        asignaciones: list[tuple[str, int | None, int]],
        codigo_talonario: str,
        observacion: str | None = None,
    ) -> PaymentResult:
        """
        Procesa un pago con asignación dirigida.

        El usuario especifica exactamente cuánto va a cada concepto.
        Valida que no se pague más de lo pendiente por concepto.

        Args:
            asignaciones: Lista de (concepto, complementario_id, monto).
        """
        enrollment = self._repo.get_enrollment_by_id(matricula_id)
        if enrollment is None:
            msg = f"Matrícula con id {matricula_id} no encontrada"
            raise ValueError(msg)

        if not self._repo.validate_talonario_unique(codigo_talonario):
            msg = f"El código de talonario '{codigo_talonario}' ya está registrado"
            raise ValueError(msg)

        (
            _mat_id,
            _est_id,
            _valor_total,
            _estado,
            pending_base,
            pending_pension,
            _param_id,
        ) = enrollment

        comp_details = self._repo.get_enrollment_complementary_details(matricula_id)
        comp_pending_map = {comp_id: pend for _, comp_id, _, pend in comp_details}

        monto_total = 0
        distribuciones: list[PaymentAllocation] = []

        for concepto, comp_id, monto in asignaciones:
            if monto <= 0:
                msg = f"El monto para '{concepto}' debe ser mayor a 0"
                raise ValueError(msg)

            if concepto == "matricula_base":
                if monto > pending_base:
                    msg = (
                        f"Monto ${monto:,} excede el pendiente de matrícula base "
                        f"(${pending_base:,})"
                    )
                    raise ValueError(msg)
                new_pending = pending_base - monto
                self._repo.update_pending_base(matricula_id, new_pending)
                pending_base = new_pending

            elif concepto == "pension":
                if monto > pending_pension:
                    msg = (
                        f"Monto ${monto:,} excede el pendiente de pensión "
                        f"(${pending_pension:,})"
                    )
                    raise ValueError(msg)
                new_pending = pending_pension - monto
                self._repo.update_pending_pension(matricula_id, new_pending)
                pending_pension = new_pending

            elif concepto.startswith("complementario") and comp_id is not None:
                current_pending = comp_pending_map.get(comp_id, 0)
                if monto > current_pending:
                    msg = (
                        f"Monto ${monto:,} excede el pendiente del "
                        f"complementario ID {comp_id} (${current_pending:,})"
                    )
                    raise ValueError(msg)
                new_pending = current_pending - monto
                self._repo.update_complementary_pending(
                    matricula_id, comp_id, new_pending
                )
                comp_pending_map[comp_id] = new_pending
            else:
                msg = f"Concepto '{concepto}' no reconocido"
                raise ValueError(msg)

            distribuciones.append(
                PaymentAllocation(
                    concepto=concepto,
                    complementario_id=comp_id,
                    monto_aplicado=monto,
                )
            )
            monto_total += monto

        # Registrar pago
        pago_id = self._repo.create_payment(
            matricula_id=matricula_id,
            codigo_talonario=codigo_talonario,
            monto_total=monto_total,
            modo_pago="dirigido",
            observacion=observacion,
            distribuciones=[
                (d.concepto, d.complementario_id, d.monto_aplicado)
                for d in distribuciones
            ],
        )

        # Verificar si la matrícula quedó completamente pagada
        saldo = self._calculate_total_pending(matricula_id)
        if saldo == 0:
            self._repo.update_enrollment_status(matricula_id, True)

        return PaymentResult(
            pago_id=pago_id,
            codigo_talonario=codigo_talonario,
            monto_total=monto_total,
            monto_aplicado=monto_total,
            distribuciones=distribuciones,
            saldo_restante_matricula=saldo,
            matricula_pagada=saldo == 0,
        )

    def _calculate_total_pending(self, matricula_id: int) -> int:
        """Calcula el total pendiente recargando datos frescos de la BD."""
        enrollment = self._repo.get_enrollment_by_id(matricula_id)
        if enrollment is None:
            return 0

        _, _, _, _, pending_base, pending_pension, _ = enrollment
        comp_details = self._repo.get_enrollment_complementary_details(matricula_id)
        comp_pending = sum(pend for _, _, _, pend in comp_details)

        return pending_base + comp_pending + pending_pension
