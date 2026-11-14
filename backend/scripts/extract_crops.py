"""Construye crops.json a partir de la copia local de EcoCrop.

No inventa rangos: copia columnas numéricas y traduce categorías con un
diccionario fijo. La lluvia RMIN/ROPMN/ROPMX/RMAX se guarda como requisito
de la ventana de ciclo, que es el uso del modelo de aptitud EcoCrop.

Uso, desde backend/:
    python scripts/extract_crops.py
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FULL_CSV = DATA_DIR / "ecocrop_db.csv"
SUBSET_CSV = DATA_DIR / "ecocrop_subset.csv"
OUTPUT = DATA_DIR / "crops.json"

SOURCE = (
    "FAO EcoCrop, copia OpenCLIM/EcoCrop EcoCrop_DB.csv "
    "(descarga de la rama master el 2026-11-13; CGIAR cita el commit ea43ecd "
    "como instantánea de referencia). Números copiados sin ajuste."
)

TEXTURES = {
    "heavy": "arcilloso",
    "medium": "franco",
    "light": "arenoso",
    "organic": "organico",
}
FERTILITY = {"high": "alta", "moderate": "media", "low": "baja"}
FAMILIES = {
    "Gramineae": "gramineas",
    "Leguminosae": "fabaceas",
    "Solanaceae": "solanaceas",
    "Euphorbiaceae": "euforbiaceas",
    "Chenopodiaceae": "quenopodiaceas",
    "Alliaceae": "aliaceas",
}

# categoria es la clasificación de la app. El CAT original queda en las notas.
TARGETS = [
    {
        "id": "maiz",
        "nombre": "Maíz",
        "scientific": "Zea mays ssp. mays",
        "categoria": "cereales",
    },
    {
        "id": "papa",
        "nombre": "Papa",
        "scientific": "Solanum tuberosum",
        "categoria": "tuberculos_raices",
    },
    {
        "id": "quinua",
        "nombre": "Quinua",
        "scientific": "Chenopodium quinoa",
        "categoria": "cereales",
    },
    {
        "id": "haba",
        "nombre": "Haba",
        "scientific": "Vicia faba",
        "categoria": "legumbres",
    },
    {
        "id": "frijol",
        "nombre": "Frijol",
        "scientific": "Phaseolus vulgaris",
        "categoria": "legumbres",
    },
    {
        "id": "soya",
        "nombre": "Soya",
        "scientific": "Glycine max",
        "categoria": "oleaginosas",
    },
    {
        "id": "arroz",
        "nombre": "Arroz",
        "scientific": "Oryza sativa",
        "categoria": "cereales",
    },
    {
        "id": "tomate",
        "nombre": "Tomate",
        "scientific": "Lycopersicon esculentum",
        "categoria": "hortalizas",
    },
    {
        "id": "cebolla",
        "nombre": "Cebolla",
        "scientific": "Allium cepa",
        "categoria": "hortalizas",
    },
    {
        "id": "yuca",
        "nombre": "Yuca",
        "scientific": "Manihot esculenta",
        "categoria": "tuberculos_raices",
    },
]


def blank(value: str | None) -> bool:
    """True si EcoCrop dejó la celda vacía o en NA."""
    return value is None or value.strip() in {"", "NA"}


def number(value: str, label: str) -> float:
    """Convierte una celda numérica. Falla si falta: no se rellena a mano."""
    if blank(value):
        raise ValueError(f"Falta {label}")
    return float(value)


def optional_number(value: str) -> float | None:
    """Celda numérica que EcoCrop puede dejar vacía, como KTMP."""
    if blank(value):
        return None
    return float(value)


def map_textures(text: str) -> list[str]:
    """Traduce heavy/medium/light/organic. 'wide' cubre las tres texturas minerales."""
    if blank(text):
        return []
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if "wide" in parts:
        return ["arcilloso", "franco", "arenoso"]
    found: list[str] = []
    for part in parts:
        mapped = TEXTURES.get(part)
        if mapped and mapped not in found:
            found.append(mapped)
    return found


def map_drainage(text: str) -> list[str]:
    """Traduce las clases de drenaje que aparecen en la celda DRA."""
    if blank(text):
        return []
    found: list[str] = []
    if "poorly" in text and "pobre" not in found:
        found.append("pobre")
    if "well" in text and "bueno" not in found:
        found.append("bueno")
    if "excessive" in text and "excesivo" not in found:
        found.append("excesivo")
    return found


def map_depth(text: str) -> str | None:
    """Traduce la profundidad óptima DEP."""
    if blank(text):
        return None
    if text.startswith("shallow"):
        return "superficial"
    if text.startswith("medium"):
        return "media"
    if text.startswith("deep"):
        return "profunda"
    return None


def family_slug(famname: str) -> str:
    """Último tramo de FAMNAME, pasado a un identificador corto."""
    token = famname.split(":")[-1].strip()
    return FAMILIES.get(token, token.lower())


def build_crop(target: dict[str, str], row: dict[str, str]) -> dict:
    """Arma un objeto de crops.json desde una fila exacta."""
    killing = optional_number(row["KTMP"])
    family = family_slug(row["FAMNAME"])
    fertility = None if blank(row["FER"]) else FERTILITY.get(row["FER"].strip())
    notes = (
        "Temperaturas (TMIN, TOPMN, TOPMX, TMAX), lluvia (RMIN, ROPMN, ROPMX, RMAX), "
        "pH, duración (GMIN, GMAX) y KTMP se copiaron de EcoCrop. La lluvia se compara "
        "con la suma de la ventana de ciclo, convención del modelo de aptitud EcoCrop; "
        "la ficha no rotula ese milimetraje con una sola palabra. "
        f"TEXT={row['TEXT'] or 'vacío'}; DRA={row['DRA'] or 'vacío'}; "
        f"DEP={row['DEP'] or 'vacío'}; FER={row['FER'] or 'vacío'}; "
        f"CAT original={row['CAT'] or 'vacío'}. "
        "sensible_helada es una regla del proyecto: true solo si KTMP es mayor o igual que 0. "
        "fija_nitrogeno es true solo para la familia Leguminosae de esta ficha. "
        "tolerancia_sequia no está en EcoCrop y queda en null."
    )
    return {
        "id": target["id"],
        "nombre": target["nombre"],
        "nombre_cientifico": target["scientific"],
        "ecoport": row["EcoPortCode"].strip(),
        "categoria": target["categoria"],
        "familia": family,
        "ciclo_dias": [int(number(row["GMIN"], "GMIN")), int(number(row["GMAX"], "GMAX"))],
        "temp": {
            "abs_min": number(row["TMIN"], "TMIN"),
            "opt_min": number(row["TOPMN"], "TOPMN"),
            "opt_max": number(row["TOPMX"], "TOPMX"),
            "abs_max": number(row["TMAX"], "TMAX"),
        },
        "temp_min_helada": killing,
        "sensible_helada": killing is not None and killing >= 0,
        "precip_ciclo_mm": {
            "abs_min": number(row["RMIN"], "RMIN"),
            "opt_min": number(row["ROPMN"], "ROPMN"),
            "opt_max": number(row["ROPMX"], "ROPMX"),
            "abs_max": number(row["RMAX"], "RMAX"),
        },
        "suelo": {
            "ph": {
                "abs_min": number(row["PHMIN"], "PHMIN"),
                "opt_min": number(row["PHOPMN"], "PHOPMN"),
                "opt_max": number(row["PHOPMX"], "PHOPMX"),
                "abs_max": number(row["PHMAX"], "PHMAX"),
            },
            "texturas": map_textures(row["TEXT"]),
            "drenaje": map_drainage(row["DRA"]),
        },
        "fertilidad": fertility,
        "fija_nitrogeno": family == "fabaceas",
        "profundidad_raiz": map_depth(row["DEP"]),
        "tolerancia_sequia": None,
        "fuente": (
            f"{SOURCE} ScientificName={target['scientific']}; "
            f"EcoPort={row['EcoPortCode'].strip()}."
        ),
        "validado": True,
        "notas": notes,
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    """Lee el CSV en UTF-8."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    """Escribe el subconjunto y crops.json. No descarga nada."""
    source = FULL_CSV if FULL_CSV.exists() else SUBSET_CSV
    if not source.exists():
        raise SystemExit(f"No está el CSV de EcoCrop en {DATA_DIR}")
    rows = read_rows(source)
    by_name = {row["ScientificName"].strip(): row for row in rows}
    selected: list[dict[str, str]] = []
    crops: list[dict] = []
    for target in TARGETS:
        row = by_name.get(target["scientific"])
        if row is None:
            raise SystemExit(f"No está en EcoCrop: {target['scientific']}")
        selected.append(row)
        crops.append(build_crop(target, row))
    with SUBSET_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0].keys()))
        writer.writeheader()
        writer.writerows(selected)
    OUTPUT.write_text(json.dumps(crops, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Escribí {len(crops)} cultivos en {OUTPUT}")


if __name__ == "__main__":
    main()
