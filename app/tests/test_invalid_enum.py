def test_invalid_enum_returns_422(client):
    payload = {
        "estudiante_id": 3,
        "complementario_id": 1,
        "tipo_prueba": "matematicas",  # <-- fuera del Enum
        "estado": "pendiente",
        "periodo_id": 1,
    }
    response = client.post("/api/v1/tests/details", json=payload)
    assert response.status_code in [400, 422]
    assert "tipo_prueba must be one of" in response.text or "enum" in response.text
