from abc import ABC, abstractmethod

from app.modules.enrollment.domain.entities import (
    ComplementaryDetail,
    StudentInfo,
)


class EnrollmentRepository(ABC):
    """Interfaz abstracta para el acceso a datos de matrícula."""

    # === Consulta ===

    @abstractmethod
    def get_student_by_id(self, student_id: int) -> StudentInfo | None:
        """Obtiene la información del estudiante con su grado."""
        ...

    @abstractmethod
    def get_enrollment_base_cost(self, grade_id: int, year: int) -> int | None:
        """Obtiene el costo base de matrícula para un grado y año."""
        ...

    @abstractmethod
    def get_enrollment_details(
        self, student_id: int, year: int
    ) -> tuple[int | None, bool, list[ComplementaryDetail], int, int]:
        """
        Obtiene los detalles de matrícula de un estudiante para un año.

        Returns:
            Tuple de (matricula_id, estado_matricula, lista_complementarios,
                       pendiente_base, pendiente_pension).
            Si no existe matrícula, retorna (None, False, [], 0, 0).
        """
        ...

    @abstractmethod
    def get_first_month_pension_cost(self, grade_id: int, year: int) -> int | None:
        """Obtiene el costo de pensión mensual para un grado y año."""
        ...

    # === Registro de matrícula ===

    @abstractmethod
    def get_param_matricula_id(self, grade_id: int, year: int) -> int | None:
        """Obtiene el ID del registro ParametrizarMatricula para un grado y año."""
        ...

    @abstractmethod
    def student_has_enrollment(self, student_id: int, year: int) -> bool:
        """Verifica si el estudiante ya tiene matrícula para el año dado."""
        ...

    @abstractmethod
    def get_active_complementaries(self, year: int) -> list[tuple[int, str, int]]:
        """
        Obtiene los complementarios activos con uso_matricula=True para un año.

        Returns:
            Lista de (complementario_id, tipo_complementario, valor).
        """
        ...

    @abstractmethod
    def create_enrollment(
        self,
        para_matricula_id: int,
        student_id: int,
        period_id: int,
        valor_total: int,
        base_cost: int,
        pension_cost: int,
        complementary_details: list[tuple[int, int]],
    ) -> int:
        """
        Crea el registro de matrícula con sus detalles.

        Args:
            para_matricula_id: ID del ParametrizarMatricula.
            student_id: ID del estudiante.
            period_id: ID del periodo.
            valor_total: Valor total de la matrícula.
            base_cost: Costo base pendiente.
            pension_cost: Costo pensión pendiente.
            complementary_details: Lista de (complementario_id, valor).

        Returns:
            ID de la matrícula creada.
        """
        ...

    # === Pagos ===

    @abstractmethod
    def get_enrollment_by_id(
        self, matricula_id: int
    ) -> tuple | None:
        """
        Obtiene matrícula por ID con sus pendientes.

        Returns:
            Tuple (id, estudiante_id, valor_total, estado_matricula,
                   pendiente_base, pendiente_pension, para_matricula_id)
            o None si no existe.
        """
        ...

    @abstractmethod
    def get_enrollment_complementary_details(
        self, matricula_id: int
    ) -> list[tuple[int, int, str, int]]:
        """
        Obtiene los detalles de complementarios de una matrícula con pendientes > 0.

        Returns:
            Lista de (detalle_id, complementario_id, tipo, valor_pendiente).
        """
        ...

    @abstractmethod
    def validate_talonario_unique(self, codigo: str) -> bool:
        """Verifica que el código de talonario no esté ya registrado."""
        ...

    @abstractmethod
    def create_payment(
        self,
        matricula_id: int,
        codigo_talonario: str,
        monto_total: int,
        modo_pago: str,
        observacion: str | None,
        distribuciones: list[tuple[str, int | None, int]],
    ) -> int:
        """
        Crea el registro de pago con su desglose.

        Args:
            distribuciones: Lista de (concepto, complementario_id, monto_aplicado).

        Returns:
            ID del pago creado.
        """
        ...

    @abstractmethod
    def update_pending_base(self, matricula_id: int, new_pending: int) -> None:
        """Actualiza el valor_pendiente_base de una matrícula."""
        ...

    @abstractmethod
    def update_pending_pension(self, matricula_id: int, new_pending: int) -> None:
        """Actualiza el valor_pendiente_pension de una matrícula."""
        ...

    @abstractmethod
    def update_complementary_pending(
        self, matricula_id: int, complementario_id: int, new_pending: int
    ) -> None:
        """Actualiza el valor_pendiente de un detalle_matricula."""
        ...

    @abstractmethod
    def update_enrollment_status(
        self, matricula_id: int, status: bool
    ) -> None:
        """Actualiza el estado_matricula."""
        ...
