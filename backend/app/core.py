"""Canonical time, configuration and geometry primitives. No evaluation data access."""

import csv, json, math, re, unicodedata
from pathlib import Path
from datetime import datetime
import yaml

ROOT = Path(__file__).resolve().parents[2]


def config(name="sahra_express"):
    if not re.fullmatch(r"[a-z_]+", name):
        raise ValueError("Invalid client config name")
    return yaml.safe_load((ROOT / "config/clients" / f"{name}.yaml").read_text())


def read_csv(name, cfg=None, data_dir=None):
    path = (Path(data_dir) if data_dir else ROOT / "data") / f"{name}.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    mapping = (cfg or {}).get("field_mappings", {}).get(name, {})
    return [{mapping.get(k, k): v for k, v in r.items()} for r in rows]


def norm(s):
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFKC", str(s)).casefold()),
    ).strip()


def minute(s):
    for fmt in ["%H:%M", "%I:%M %p"]:
        try:
            d = datetime.strptime(s.strip().upper(), fmt)
            return d.hour * 60 + d.minute
        except ValueError:
            pass
    raise ValueError(f"Unparseable time {s!r}")


def hhmm(t):
    t = math.ceil(t - 1e-8)
    return f"{t//60:02d}:{t%60:02d}"


def hav(a, b):
    a1, o1, a2, o2 = map(math.radians, [*a, *b])
    x = (
        math.sin((a2 - a1) / 2) ** 2
        + math.cos(a1) * math.cos(a2) * math.sin((o2 - o1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(min(1, math.sqrt(x)))


def road(a, b, cfg):
    return hav(a, b) * cfg["road_factor"]


def travel(km, t, kind, cfg):
    """Integrate speed over every peak boundary; result in minutes."""
    start = t
    remaining = km
    while remaining > 1e-9:
        peak = any(a <= t < b for a, b in cfg["peak_periods"])
        speed = cfg["peak_speed_kmh"] if peak else cfg["speed_kmh"]
        if kind == "MOTORBIKE":
            speed *= cfg["bike_speed_factor"]
        boundaries = [
            x for pair in cfg["peak_periods"] for x in pair if x > t + 1e-7
        ] + [2880]
        boundary = min(boundaries)
        possible = (boundary - t) * speed / 60
        if possible >= remaining:
            t += remaining / speed * 60
            break
        t = boundary
        remaining -= possible
    return t - start


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False))
