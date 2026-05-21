import csv
import io
from datetime import datetime

from sqlmodel import Session, select

from app.modules.enrollment.domain.service import EnrollmentService
from app.modules.enrollment.infrastructure.models import Estudiante


class MassEnrollmentService:
    """Caso de uso para registrar matrículas masivamente a partir de archivos."""

    def __init__(self, db_session: Session, enrollment_service: EnrollmentService):
        self._session = db_session
        self._enrollment_service = enrollment_service

    def process_csv_file(self, content: bytes, period_id: int, year: int) -> dict:
        """
        Procesa un archivo CSV y crea/actualiza los estudiantes y los matricula.
        Formato esperado: documento,nombre,grado_id,acudiente_id
        """
        decoded_content = content.decode("utf-8")
        reader = csv.reader(io.StringIO(decoded_content), delimiter=",")  # type: ignore[abstract]
        
        return self._process_rows(reader, period_id, year)
    
    def process_txt_file(self, content: bytes, period_id: int, year: int) -> dict:
        """
        Procesa un archivo TXT separado por comas.
        """
        return self.process_csv_file(content, period_id, year)

    def _process_rows(self, reader, period_id: int, year: int) -> dict:
        success_count = 0
        error_count = 0
        errors = []

        # Saltar cabecera si existe
        header = next(reader, None)
        if not header:
            return {"status": "error", "message": "El archivo está vacío"}
            
        # Si la cabecera no parece ser cabecera (es decir, el grado_id es un número), la procesamos.
        # De lo contrario la ignoramos.
        try:
            int(header[2])
            # Fue un dato, rebobinamos
            rows = [header] + list(reader)
        except (ValueError, IndexError):
            rows = list(reader)

        for line_idx, row in enumerate(rows, start=2): # +1 por header y +1 por ser 1-indexed
            if not row or len(row) < 4:
                continue
                
            try:
                documento = row[0].strip()
                nombre = row[1].strip()
                grado_id = int(row[2].strip())
                acudiente_id = int(row[3].strip())
                
                # Buscar si el estudiante existe
                statement = select(Estudiante).where(Estudiante.documento == documento)
                estudiante = self._session.exec(statement).first()
                
                if not estudiante:
                    # Crear nuevo estudiante
                    estudiante = Estudiante(
                        documento=documento,
                        nombre=nombre,
                        grado_id=grado_id,
                        acudiente_id=acudiente_id,
                        activo=True,
                        fecha_activo=datetime.now()
                    )
                    self._session.add(estudiante)
                    self._session.commit()
                    self._session.refresh(estudiante)
                else:
                    # Actualizar si cambió grado o acudiente
                    if estudiante.grado_id != grado_id or estudiante.acudiente_id != acudiente_id:
                        estudiante.grado_id = grado_id
                        estudiante.acudiente_id = acudiente_id
                        self._session.add(estudiante)
                        self._session.commit()
                
                # Intentar matricular
                try:
                    if estudiante.id is None:
                        raise ValueError("Estudiante ID no generado")
                    self._enrollment_service.register_enrollment(
                        student_id=estudiante.id,
                        period_id=period_id,
                        year=year
                    )
                    success_count += 1
                except ValueError as ve:
                    if "ya tiene una matrícula" in str(ve):
                        pass # Ignorar si ya está matriculado
                    else:
                        raise ve

            except Exception as e:
                error_count += 1
                errors.append(f"Fila {line_idx} ({row}): {str(e)}")

        return {
            "status": "success" if error_count == 0 else "partial",
            "processed": success_count + error_count,
            "success": success_count,
            "errors": error_count,
            "error_details": errors[:10] # Solo mostrar los primeros 10 errores
        }
