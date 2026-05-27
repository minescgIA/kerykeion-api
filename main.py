from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kerykeion import AstrologicalSubject, SynastryAspects, NatalAspects
import traceback

app = FastAPI(title="Mapa Vincular — Astrological Engine")


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


def extract_planets(subject: AstrologicalSubject) -> list:
    planet_names = [
        "sun", "moon", "mercury", "venus", "mars",
        "jupiter", "saturn", "uranus", "neptune", "pluto",
        "true_node", "chiron",
    ]
    result = []
    for name in planet_names:
        if hasattr(subject, name):
            p = getattr(subject, name)
            # Kerykeion v4: house puede ser int o string según la versión
            house_val = getattr(p, "house", None) or getattr(p, "house_name", None)
            result.append({
                "name": str(p.name),
                "sign": str(p.sign),
                "degree": round(float(p.position), 2),
                "house": house_val,
                "retrograde": bool(getattr(p, "retrograde", False)),
                "stationary": False,
            })
    return result


def extract_houses(subject: AstrologicalSubject) -> list:
    houses = []
    for i, h in enumerate(subject.houses_list):
        houses.append({
            "number": i + 1,
            "sign": str(h.sign),
            "degree": round(float(h.position), 2),
        })
    return houses


def extract_natal_aspects(subject: AstrologicalSubject) -> list:
    try:
        # Kerykeion v4+: usar NatalAspects
        natal = NatalAspects(subject)
        aspects_list = natal.aspects_list
        return [
            {
                "p1": str(a.p1_name),
                "p2": str(a.p2_name),
                "type": str(a.aspect),
                "orb": round(float(a.orbit), 2),
            }
            for a in aspects_list
        ]
    except Exception:
        # Fallback: intentar acceder directamente en versiones anteriores
        try:
            aspects_list = subject.aspects_list
            return [
                {
                    "p1": str(a.p1_name),
                    "p2": str(a.p2_name),
                    "type": str(a.aspect),
                    "orb": round(float(a.orbit), 2),
                }
                for a in aspects_list
            ]
        except Exception:
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


@app.post("/synastry")
def synastry(data: SynastryRequest):
    try:
        subject_a = make_subject(data.person_a)
        subject_b = make_subject(data.person_b)
        syn = SynastryAspects(subject_a, subject_b)

        # Kerykeion v4: puede ser all_aspects o aspects
        aspects_list = getattr(syn, "all_aspects", None) or getattr(syn, "aspects", [])

        return {
            "aspects": [
                {
                    "p1": str(a.p1_name),
                    "p2": str(a.p2_name),
                    "type": str(a.aspect),
                    "orb": round(float(a.orbit), 2),
                }
                for a in aspects_list
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "traceback": traceback.format_exc(),
        })
