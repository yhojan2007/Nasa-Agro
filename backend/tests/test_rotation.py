"""Reglas de rotación con candidatos ya puntuados, sin clima de red."""

from app.rotation import RotationCandidate, plan_rotation


def _candidate(
    crop_id: str,
    nombre: str,
    familia: str,
    puntaje: int,
    mes: int,
    fertilidad: str | None = None,
    fija_nitrogeno: bool = False,
    profundidad_raiz: str | None = "media",
    ciclo_meses: int = 4,
) -> RotationCandidate:
    return RotationCandidate(
        id=crop_id,
        nombre=nombre,
        familia=familia,
        puntaje=puntaje,
        mes=mes,
        ciclo_meses=ciclo_meses,
        fertilidad=fertilidad,
        fija_nitrogeno=fija_nitrogeno,
        profundidad_raiz=profundidad_raiz,
    )


def test_rotation_changes_family_and_prefers_a_legume() -> None:
    options = {
        10: [_candidate("maiz", "Maíz", "gramineas", 80, 10, fertilidad="alta")],
        2: [
            _candidate("frijol", "Frijol", "fabaceas", 70, 2, fija_nitrogeno=True),
            _candidate("papa", "Papa", "solanaceas", 78, 2, profundidad_raiz="superficial"),
        ],
        6: [_candidate("quinua", "Quinua", "quenopodiaceas", 80, 6)],
    }
    steps, _notes, _message = plan_rotation(options, 10, None)
    assert [step.id for step in steps] == ["maiz", "frijol", "quinua"]
    assert steps[0].familia != steps[1].familia
    assert "nitrógeno" in steps[1].motivo


def test_same_family_is_not_planted_next() -> None:
    options = {
        1: [
            _candidate("maiz", "Maíz", "gramineas", 90, 1),
            _candidate("arroz", "Arroz", "gramineas", 80, 1),
        ]
    }
    steps, _notes, message = plan_rotation(options, 1, None)
    assert [step.id for step in steps] == ["maiz"]
    assert "No hay tres cultivos" in message


def test_low_organic_matter_adds_a_green_manure_note() -> None:
    options = {1: [_candidate("quinua", "Quinua", "quenopodiaceas", 80, 1)]}
    _steps, notes, _message = plan_rotation(options, 1, 1.2)
    assert any("abono verde" in note for note in notes)


def test_score_below_minimum_is_left_out() -> None:
    options = {1: [_candidate("maiz", "Maíz", "gramineas", 40, 1)]}
    steps, _notes, message = plan_rotation(options, 1, None)
    assert steps == []
    assert "50" in message
