"""Rotación por reglas: familia, nitrógeno, raíz y puntaje climático."""

from dataclasses import dataclass

from app.constants import (
    AVISO_ROTACION,
    MATERIA_ORGANICA_BAJA,
    MAX_FALLOW_MONTHS,
    MIN_ROTATION_SCORE,
    NITROGEN_BONUS,
    ROOT_BONUS,
)
from app.schemas import PasoRotacion


@dataclass
class RotationCandidate:
    """Cultivo ya puntuado en un mes concreto."""

    id: str
    nombre: str
    familia: str
    puntaje: int
    mes: int
    ciclo_meses: int
    fertilidad: str | None
    fija_nitrogeno: bool
    profundidad_raiz: str | None


def _shift_month(month: int, steps: int) -> int:
    return ((month - 1 + steps) % 12) + 1


def _pick(
    pool: list[RotationCandidate],
    previous: RotationCandidate | None,
    used_ids: set[str],
) -> RotationCandidate | None:
    available = [
        item
        for item in pool
        if item.puntaje >= MIN_ROTATION_SCORE
        and item.id not in used_ids
        and (previous is None or item.familia != previous.familia)
    ]
    if not available:
        return None

    def sort_key(item: RotationCandidate) -> tuple[int, int, str]:
        bonus = 0
        if previous and previous.fertilidad == "alta" and item.fija_nitrogeno:
            bonus += NITROGEN_BONUS
        if (
            previous
            and previous.profundidad_raiz
            and item.profundidad_raiz
            and {previous.profundidad_raiz, item.profundidad_raiz} == {"superficial", "profunda"}
        ):
            bonus += ROOT_BONUS
        return (item.puntaje + bonus, item.puntaje, item.nombre)

    return max(available, key=sort_key)


def _motivo(item: RotationCandidate, previous: RotationCandidate | None, fallow: int) -> str:
    reasons: list[str] = []
    if fallow:
        reasons.append(f"tras {fallow} mes(es) de espera porque el mes inmediato no alcanzaba")
    if previous is None:
        reasons.append("mejor puntaje climático para abrir el ciclo")
    else:
        reasons.append(f"cambia de familia respecto de {previous.nombre}")
        if previous.fertilidad == "alta" and item.fija_nitrogeno:
            reasons.append("aporta nitrógeno después de un cultivo de fertilidad alta")
        if {previous.profundidad_raiz, item.profundidad_raiz} == {"superficial", "profunda"}:
            reasons.append("alterna profundidad de raíz")
    return "; ".join(reasons)


def plan_rotation(
    options_by_month: dict[int, list[RotationCandidate]],
    start_month: int | None,
    materia_organica: float | None,
) -> tuple[list[PasoRotacion], list[str], str]:
    """Arma hasta tres pasos sin repetir familia de un eslabón al siguiente.

    Args:
        options_by_month: Candidatos ya puntuados, agrupados por mes de siembra.
        start_month: Mes pedido para el primer cultivo. None busca el mejor.
        materia_organica: Porcentaje, si el usuario lo indicó.

    Returns:
        Pasos, observaciones y un mensaje resumen.
    """
    notes: list[str] = []
    if materia_organica is not None and materia_organica < MATERIA_ORGANICA_BAJA:
        notes.append(
            "Materia orgánica baja: incluye un abono verde o un descanso entre ciclos."
        )
    steps: list[PasoRotacion] = []
    used: set[str] = set()
    previous: RotationCandidate | None = None
    cursor = start_month
    for _ in range(3):
        chosen: RotationCandidate | None = None
        fallow = 0
        if cursor is None:
            flat = [item for group in options_by_month.values() for item in group]
            chosen = _pick(flat, previous, used)
            if chosen is not None:
                cursor = chosen.mes
        else:
            for wait in range(MAX_FALLOW_MONTHS + 1):
                month = _shift_month(cursor, wait)
                chosen = _pick(options_by_month.get(month, []), previous, used)
                if chosen is not None:
                    fallow = wait
                    cursor = month
                    break
        if chosen is None:
            break
        steps.append(
            PasoRotacion(
                orden=len(steps) + 1,
                cultivo=chosen.nombre,
                id=chosen.id,
                mes_siembra=chosen.mes,
                puntaje=chosen.puntaje,
                familia=chosen.familia,
                descanso_meses=fallow,
                motivo=_motivo(chosen, previous, fallow),
            )
        )
        used.add(chosen.id)
        previous = chosen
        cursor = _shift_month(chosen.mes, chosen.ciclo_meses)
    if not steps:
        message = (
            "Ningún cultivo llega al puntaje mínimo "
            f"({MIN_ROTATION_SCORE}) para abrir un ciclo en este punto."
        )
    elif len(steps) < 3:
        message = (
            "No hay tres cultivos de familias distintas con puntaje de al menos "
            f"{MIN_ROTATION_SCORE} encadenados a este calendario."
        )
    else:
        message = "Ciclo de tres pasos con las reglas de familia, nitrógeno y raíz."
    return steps, notes, message


def aviso_rotacion() -> str:
    """Texto fijo que acompaña cualquier ciclo.

    Returns:
        El aviso de la especificación, en una sola frase.
    """
    return AVISO_ROTACION
