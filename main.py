from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kerykeion import AstrologicalSubject, SynastryAspects, NatalAspects
import traceback

app = FastAPI(title="Mapa Vincular — Astrological Engine")

PLANET_ATTRS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
    "true_node", "chiron",
]

HOUSE_ATTRS = [
    "first_house", "second_house", "third_house", "fourth_house",
    "fifth_house", "sixth_house", "seventh_house", "eighth_house",
    "ninth_house", "tenth_house", "eleventh_house", "twelfth_house",
]

SIGN_ES = {
    "Ari": "Aries", "Tau": "Tauro", "Gem": "Géminis", "Can": "Cáncer",
    "Leo": "Leo", "Vir": "Virgo", "Lib": "Libra", "Sco": "Escorpio",
    "Sag": "Sagitario", "Cap": "Capricornio", "Aqu": "Acuario", "Pis": "Piscis",
    # Por si devuelve el nombre completo en inglés
    "Aries": "Aries", "Taurus": "Tauro", "Gemini": "Géminis", "Cancer": "Cáncer",
    "Virgo": "Virgo", "Libra": "Libra", "Scorpio": "Escorpio",
    "Sagittarius": "Sagitario", "Capricorn": "Capricornio",
    "Aquarius": "Acuario", "Pisces": "Piscis",
}

ASPECT_ES = {
    "conjunction": "Conjunción", "Conjunction": "Conjunción",
    "opposition": "Oposición", "Opposition": "Oposición",
    "trine": "Trígono", "Trine": "Trígono",
    "square": "Cuadratura", "Square": "Cuadratura",
    "sextile": "Sextil", "Sextile": "Sextil",
    "quincunx": "Quincuncio", "Quincunx": "Quincuncio",
    "semi-sextile": "Semi-sextil", "Semi-sextile": "Semi-sextil",
    "semi-square": "Semi-cuadratura", "Semi-square": "Semi-cuadratura",
    "sesqui-quadrate": "Sesqui-cuadratura", "Sesqui-quadrate": "Sesqui-cuadratura",
}


class BirthData(BaseModel):
    name: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    lat: float
    lon: float
    tz: str


class SynastryRequest(BaseModel):
    person_a: BirthData
    person_b: BirthData


def make_subject(d: BirthData) -> AstrologicalSubject:
    return AstrologicalSubject(
        d.name, d.year, d.month, d.day,
        d.hour, d.minute,
        lng=d.lon, lat=d.lat, tz_str=d.tz
    )


def sign_es(raw: str) -> str:
    return SIGN_ES.get(str(raw), str(raw))


def aspect_es(raw: str) -> str:
    return ASPECT_ES.get(str(raw), str(raw))


def get_attr_safe(obj, *attrs, default=None):
    for attr in attrs:
        try:
            val = getattr(obj, attr, None)
            if val is not None:
                return val
        except Exception:
            continue
    return default


def extract_planets(subject: AstrologicalSubject) -> list:
    result = []
    for name in PLANET_ATTRS:
        if not hasattr(subject, name):
            continue
        try:
            p = getattr(subject, name)
            house_val = get_attr_safe(p, "house", "house_name", default=None)
            result.append({
                "name": str(p.name),
                "sign": sign_es(p.sign),
                "degree": round(float(p.position), 2),
                "house": house_val,
                "retrograde": bool(get_attr_safe(p, "retrograde", default=False)),
                "stationary": False,
            })
        except Exception:
            continue
    return result


def extract_houses(subject: AstrologicalSubject) -> list:
    houses = []
    for i, house_attr in enumerate(HOUSE_ATTRS):
        try:
            h = getattr(subject, house_attr, None)
            if h is None:
                continue
            houses.append({
                "number": i + 1,
                "sign": sign_es(h.sign),
                "degree": round(float(h.position), 2),
            })
        except Exception:
            continue
    return houses


def format_aspects(aspects_list) -> list:
    result = []
    for a in aspects_list:
        try:
            result.append({
                "p1": str(a.p1_name),
                "p2": str(a.p2_name),
                "type": aspect_es(a.aspect),
                "orb": round(float(a.orbit), 2),
            })
        except Exception:
            continue
    return result


def extract_natal_aspects(subject: AstrologicalSubject) -> list:
    # Intento 1: NatalAspects (Kerykeion v4+)
    for attr in ["aspects_list", "relevant_aspects", "all_aspects"]:
        try:
            natal = NatalAspects(subject)
            aspects_list = getattr(natal, attr, None)
            if aspects_list:
                return format_aspects(aspects_list)
        except Exception:
            continue

    # Intento 2: acceso directo al subject
    for attr in ["aspects_list", "relevant_aspects", "all_aspects"]:
        try:
            aspects_list = getattr(subject, attr, None)
            if aspects_list:
                return format_aspects(aspects_list)
        except Exception:
            continue

    return []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/natal")
def natal(data: BirthData):
    try:
        subject = make_subject(data)
        return {
            "planets": extract_planets(subject),
            "houses": extract_houses(subject),
            "aspects": extract_natal_aspects(subject),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "traceback": traceback.format_exc(),
        })


@app.get("/debug/aspects")
def debug_aspects():
    """Endpoint temporal para ver los atributos disponibles en NatalAspects."""
    try:
        subject = AstrologicalSubject(
            "Test", 1985, 7, 22, 8, 15,
            lng=-58.38, lat=-34.60, tz_str="America/Argentina/Buenos_Aires"
        )
        natal = NatalAspects(subject)
        attrs = [a for a in dir(natal) if not a.startswith("_")]
        return {"natal_aspects_attrs": attrs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synastry")
def synastry(data: SynastryRequest):
    try:
        subject_a = make_subject(data.person_a)
        subject_b = make_subject(data.person_b)
        syn = SynastryAspects(subject_a, subject_b)
        aspects_list = get_attr_safe(syn, "all_aspects", "aspects", "relevant_aspects", default=[])
        return {
            "aspects": format_aspects(aspects_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "traceback": traceback.format_exc(),
        })
