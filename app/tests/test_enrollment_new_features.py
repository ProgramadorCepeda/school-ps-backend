import pytest
from datetime import datetime
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import event
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import get_session
from app.modules.enrollment.infrastructure.models import (
    Grado,
    Acudiente,
    Estudiante,
    Periodo,
    ParametrizarMatricula,
    Complementario,
    Matricula,
)
from sqlalchemy.pool import StaticPool

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine, expire_on_commit=False) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session):
    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_manual_enrollment_success(session, client):
    # 1. Seed necessary parametrization
    grado = Grado(nombre="Quinto")
    session.add(grado)
    session.commit()
    session.refresh(grado)

    periodo = Periodo(
        periodo_electivo=datetime.now(), estado=True, fecha=datetime.now()
    )
    session.add(periodo)
    session.commit()
    session.refresh(periodo)

    param = ParametrizarMatricula(grado_id=grado.id, anio=2026, valor=850000)
    session.add(param)

    comp = Complementario(
        tipo_complementario="Seguro",
        anio=2026,
        valor=100000,
        estado_complemento="Activo",
        uso_matricula=True,
    )
    session.add(comp)
    session.commit()

    # 2. Make manual enrollment request
    payload = {
        "documento": "1005777888",
        "nombre": "Estudiante Manual",
        "grado": "Quinto",
        "nombre_acudiente": "Padre Manual",
        "periodo_id": periodo.id,
        "anio": 2026,
    }
    response = client.post("/api/v1/enrollment/students/manual", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "matricula_id" in data
    assert "exitosa" in data["mensaje"]

    # Verify database
    db_student = (
        session.query(Estudiante).filter(Estudiante.documento == "1005777888").first()
    )
    assert db_student is not None
    assert db_student.nombre == "Estudiante Manual"
    assert db_student.grado_id == grado.id

    db_acudiente = (
        session.query(Acudiente).filter(Acudiente.id == db_student.acudiente_id).first()
    )
    assert db_acudiente is not None
    assert db_acudiente.nombre == "Padre Manual"
    assert db_acudiente.parentesco == "Representante"


def test_manual_enrollment_invalid_grade(session, client):
    periodo = Periodo(
        periodo_electivo=datetime.now(), estado=True, fecha=datetime.now()
    )
    session.add(periodo)
    session.commit()

    payload = {
        "documento": "1005777888",
        "nombre": "Estudiante Manual",
        "grado": "Grado Inexistente",
        "nombre_acudiente": "Padre Manual",
        "periodo_id": 1,
        "anio": 2026,
    }
    response = client.post("/api/v1/enrollment/students/manual", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "no existe" in response.json()["detail"]


def test_mass_enrollment_with_names(session, client):
    # Seed parameters
    grado = Grado(nombre="Tercero")
    session.add(grado)
    session.commit()
    session.refresh(grado)

    periodo = Periodo(
        periodo_electivo=datetime.now(), estado=True, fecha=datetime.now()
    )
    session.add(periodo)
    session.commit()
    session.refresh(periodo)

    param = ParametrizarMatricula(grado_id=grado.id, anio=2026, valor=600000)
    session.add(param)
    session.commit()

    csv_data = (
        "documento,nombre,grado,acudiente\n10051111,Juan Perez,Tercero,Maria Perez"
    )
    files = {"file": ("students.csv", csv_data.encode("utf-8"), "text/csv")}
    params = {"periodo_id": periodo.id, "anio": 2026}
    response = client.post(
        "/api/v1/enrollment/register/massive/csv", files=files, params=params
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["success"] == 1
    assert data["errors"] == 0

    # Verify db
    student = (
        session.query(Estudiante).filter(Estudiante.documento == "10051111").first()
    )
    assert student is not None
    assert student.nombre == "Juan Perez"


def test_payment_history_and_receipt(session, client):
    # Seed student, acudiente, grado, parametrización
    grado = Grado(nombre="Primero")
    acudiente = Acudiente(
        nombre="Andres", parentesco="Padre", telefono="123", correo="a@a.com"
    )
    session.add(grado)
    session.add(acudiente)
    session.commit()
    session.refresh(grado)
    session.refresh(acudiente)

    periodo = Periodo(
        periodo_electivo=datetime.now(), estado=True, fecha=datetime.now()
    )
    session.add(periodo)
    session.commit()
    session.refresh(periodo)

    param = ParametrizarMatricula(grado_id=grado.id, anio=2026, valor=500000)
    session.add(param)

    estudiante = Estudiante(
        grado_id=grado.id,
        acudiente_id=acudiente.id,
        nombre="Felipe",
        documento="123456",
        activo=True,
        fecha_activo=datetime.now(),
    )
    session.add(estudiante)
    session.commit()
    session.refresh(estudiante)

    # Register enrollment
    client.post(
        "/api/v1/enrollment/register",
        json={"estudiante_id": estudiante.id, "periodo_id": periodo.id, "anio": 2026},
    )

    matricula = (
        session.query(Matricula)
        .filter(Matricula.estudiante_id == estudiante.id)
        .first()
    )
    assert matricula is not None

    # Perform directed payment
    payment_payload = {
        "matricula_id": matricula.id,
        "codigo_talonario": "TAL-AUDIT-1",
        "observacion": "Pago auditoria",
        "asignaciones": [{"concepto": "matricula_base", "monto": 200000}],
    }
    response_pay = client.post(
        "/api/v1/enrollment/payments/directed", json=payment_payload
    )
    assert response_pay.status_code == status.HTTP_201_CREATED
    pago_id = response_pay.json()["pago_id"]

    # Test audit trail/payment history GET
    response_history = client.get(
        f"/api/v1/enrollment/students/{estudiante.id}/payments", params={"year": 2026}
    )
    assert response_history.status_code == status.HTTP_200_OK
    history = response_history.json()
    assert len(history) == 1
    assert history[0]["codigo_talonario"] == "TAL-AUDIT-1"
    assert history[0]["monto_total"] == 200000

    # Test receipt/comprobante GET
    response_receipt = client.get(f"/api/v1/enrollment/payments/{pago_id}/receipt")
    assert response_receipt.status_code == status.HTTP_200_OK
    receipt = response_receipt.json()
    assert receipt["pago_id"] == pago_id
    assert receipt["codigo_talonario"] == "TAL-AUDIT-1"
    assert receipt["monto_total"] == 200000
    assert receipt["estudiante"]["nombre"] == "Felipe"
    assert receipt["estudiante"]["grado"] == "Primero"
    assert receipt["acudiente"]["nombre"] == "Andres"
    assert receipt["distribuciones"][0]["concepto"] == "matricula_base"
    assert receipt["distribuciones"][0]["monto_aplicado"] == 200000


def test_manual_enrollment_validators(session, client):
    # Test letters in documento
    payload_letters_doc = {
        "documento": "1005ABC777",
        "nombre": "Estudiante Manual",
        "grado": "Quinto",
        "nombre_acudiente": "Padre Manual",
        "periodo_id": 1,
        "anio": 2026,
    }
    response = client.post("/api/v1/enrollment/students/manual", json=payload_letters_doc)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "únicamente números" in response.text

    # Test numbers in student name
    payload_num_name = {
        "documento": "1005777888",
        "nombre": "Estudiante 123",
        "grado": "Quinto",
        "nombre_acudiente": "Padre Manual",
        "periodo_id": 1,
        "anio": 2026,
    }
    response = client.post("/api/v1/enrollment/students/manual", json=payload_num_name)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "no pueden contener números" in response.text

    # Test numbers in acudiente name
    payload_num_acudiente = {
        "documento": "1005777888",
        "nombre": "Estudiante Manual",
        "grado": "Quinto",
        "nombre_acudiente": "Padre 456",
        "periodo_id": 1,
        "anio": 2026,
    }
    response = client.post("/api/v1/enrollment/students/manual", json=payload_num_acudiente)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "no pueden contener números" in response.text

