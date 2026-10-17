import pytest
from pydantic import ValidationError

from src.web.validators.personal import PersonalBaseValidator


def datos_personal(**sobrescrituras):
    datos = {
        "dni": "12345678",
        "nombre": "Ana",
        "apellido": "Perez",
        "tipo_personal_id": 1,
        "menu_id": 1,
        "activo": True,
    }
    datos.update(sobrescrituras)
    return datos


def test_validador_acepta_los_limites_maximos_del_modelo():
    personal = PersonalBaseValidator(
        **datos_personal(
            dni="1" * 12,
            nombre="A" * 50,
            apellido="B" * 50,
        )
    )

    assert len(personal.dni) == 12
    assert len(personal.nombre) == 50
    assert len(personal.apellido) == 50


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("dni", "1" * 13),
        ("nombre", "A" * 51),
        ("apellido", "B" * 51),
    ],
)
def test_validador_rechaza_valores_mayores_que_el_limite(campo, valor):
    with pytest.raises(ValidationError):
        PersonalBaseValidator(**datos_personal(**{campo: valor}))
