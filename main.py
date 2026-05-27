from fastapi import FastAPI
from pydantic import BaseModel
from kerykeion import AstrologicalSubject, SynastryAspects

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
            result.append({
                "name": p.name,
                "sign": p.sign,
                "degree": round(p.position, 2),
                "house": p.house_name,
                "retrograde": p.retrograde,
                # stationary: Kerykeion no lo calcula nativamente.
                # MVP default: False. Para precisión real, comparar efemérides ±3 días
                # y detectar velocidad < 0.1°/día.
                "stationary": False,
            })
    return result


def extract_houses(subject: AstrologicalSubject) -> list:
    return [
        {"number": i + 1, "sign": h.sign, "degree": round(h.position, 2)}
        for i, h in enumerate(subject.houses_list)
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/natal")
def natal(data: BirthData):
    subject = make_subject(data)
    aspects_obj = subject.aspects_list if hasattr(subject, "aspects_list") else []
    aspects = [
        {"p1": a.p1_name, "p2": a.p2_name, "type": a.aspect, "orb": round(a.orbit, 2)}
        for a in aspects_obj
    ]
    return {
        "planets": extract_planets(subject),
        "houses": extract_houses(subject),
        "aspects": aspects,
    }


@app.post("/synastry")
def synastry(data: SynastryRequest):
    subject_a = make_subject(data.person_a)
    subject_b = make_subject(data.person_b)
    syn = SynastryAspects(subject_a, subject_b)
    return {
        "aspects": [
            {"p1": a.p1_name, "p2": a.p2_name, "type": a.aspect, "orb": round(a.orbit, 2)}
            for a in syn.all_aspects
        ]
    }
