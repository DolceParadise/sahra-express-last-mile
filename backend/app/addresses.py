"""Evidence-based locations. This module never reads the evaluation file."""

import collections, re, statistics
from difflib import SequenceMatcher
from functools import lru_cache
from .core import norm, hav


class AreaAliasProvider:
    def __init__(self, areas):
        self.areas = areas
        self.aliases = collections.defaultdict(list)
        for a in areas:
            for v in [a["area_name"], *a["aliases"].split(";")]:
                if v:
                    self.aliases[norm(v)].append(a)

    @lru_cache(maxsize=4096)
    def lookup(self, text):
        key = norm(text)
        if not key:
            return []
        if key in self.aliases:
            return self.aliases[key]
        # Only a unique strong spelling correction is accepted.
        scores = sorted(
            ((SequenceMatcher(None, key, k).ratio(), k) for k in self.aliases),
            reverse=True,
        )
        if scores and scores[0][0] >= 0.86:
            best = self.aliases[scores[0][1]]
            other = next((s for s, k in scores[1:] if self.aliases[k] != best), 0)
            if scores[0][0] - other >= 0.04:
                return best
        return []


def building(text):
    s = norm(text)
    for short, long in [
        ("bldg", "building"),
        ("twr", "tower"),
        ("res", "residence"),
        ("apts", "apartments"),
    ]:
        s = re.sub(r"\b" + short + r"\b", long, s)
    return s


def components(r):
    a = norm(r.get("address_line_1", ""))
    b = building(r.get("address_line_2", ""))
    villa = re.search(r"\b(?:villa(?: no)?\s*|v\s*)(\d+)\b", a)
    street = re.search(r"\b(?:street|st)\s*(\d+)", a)
    apt = re.search(r"(?:flat(?: no)?|apt|apartment|f)\s*(\d+)", a)
    makani = re.search(
        r"(?<!\d)(\d{10})(?!\d)", r.get("address_line_1", "") + " " + r.get("notes", "")
    )
    return {
        "building": b,
        "apartment": apt.group(1) if apt else None,
        "villa": villa.group(1) if villa else None,
        "street": street.group(1) if street else None,
        "community": r.get("area", "") if villa else None,
        "sub_community": b if villa else None,
        "makani": makani.group(1) if makani else None,
        "landmark": r.get("landmark", ""),
        "notes": r.get("notes", ""),
    }


class ExternalGeocoderProvider:
    enabled = False

    def candidates(self, address):
        return []  # Deliberately unavailable. Never fabricates a point.


class HistoricalLocationProvider:
    def __init__(self, history, area_provider, cfg):
        self.index = collections.defaultdict(list)
        self.cfg = cfg
        self.rejected = collections.Counter()
        self.dispositions = []
        for line, h in enumerate(history, 2):
            ledger = {
                "row_key": f"delivery_history:{line}",
                "consignment_id": h["consignment_id"],
                "disposition": "EVIDENCE_CANDIDATE",
            }
            self.dispositions.append(ledger)
            if h.get("date", "") >= cfg["plan_date"]:
                ledger["disposition"] = "FUTURE_EVENT_EXCLUDED"
                continue
            if h["outcome"] != "DELIVERED":
                ledger["disposition"] = "NOT_SUCCESSFUL_EVIDENCE"
                continue
            try:
                point = [float(h["event_lat"]), float(h["event_lng"])]
                if not (-90 <= point[0] <= 90 and -180 <= point[1] <= 180):
                    raise ValueError()
            except ValueError:
                ledger["disposition"] = "INVALID_GPS"
                self.rejected["invalid_gps"] += 1
                continue
            areas = area_provider.lookup(h["area"]) or area_provider.lookup(h["city"])
            if len(areas) != 1:
                ledger["disposition"] = "UNRESOLVED_AREA"
                self.rejected["unresolved_area"] += 1
                continue
            area = areas[0]
            if (
                hav(point, [float(area["centroid_lat"]), float(area["centroid_lng"])])
                > cfg["address"]["area_max_radius_km"]
            ):
                ledger["disposition"] = "FAR_FROM_AREA"
                self.rejected["far_from_area"] += 1
                continue
            c = components(h)
            key = self.key(area["area_name"], c)
            if not key:
                ledger["disposition"] = "MISSING_IDENTITY"
                self.rejected["missing_identity"] += 1
                continue
            self.index[key].append(
                {
                    "point": point,
                    "id": h["consignment_id"],
                    "phone": h["customer_phone"],
                    "apartment": c["apartment"],
                }
            )

    @staticmethod
    def key(area, c):
        if c["villa"]:
            if not c["sub_community"] or not c["street"]:
                return None
            return (area, c["sub_community"], "villa", c["villa"], c["street"])
        if c["building"]:
            return (area, c["building"], "building")
        return None

    def candidates(self, areas, c, phone):
        matches = []
        for area in areas:
            key = self.key(area["area_name"], c)
            if key and key in self.index:
                matches.append((key, self.index[key], False))
            elif key:
                # Fuzzy building matches need independent matching phone AND same apartment.
                for other, obs in self.index.items():
                    if other[0] != key[0] or other[2:] != key[2:]:
                        continue
                    if SequenceMatcher(None, key[1], other[1]).ratio() < 0.9:
                        continue
                    if any(
                        o["phone"] == phone
                        and phone
                        and c["apartment"]
                        and o["apartment"] == c["apartment"]
                        for o in obs
                    ):
                        matches.append((other, obs, True))
        # Missing area may be recovered only by exact building plus supporting phone.
        if not areas and c["building"]:
            for key, obs in self.index.items():
                if key[1] == c["building"] and any(
                    o["phone"] == phone and phone for o in obs
                ):
                    matches.append((key, obs, False))
        return matches


def cluster(observations, cfg):
    if not observations:
        return None
    radius = cfg["address"]["cluster_radius_km"]
    # Maximum-support neighbourhood, then a medoid. No averaging across buildings.
    groups = [
        [o for o in observations if hav(o["point"], anchor["point"]) <= radius]
        for anchor in observations
    ]
    group = max(groups, key=len)
    medoid = min(group, key=lambda o: sum(hav(o["point"], p["point"]) for p in group))
    return {
        "point": medoid["point"],
        "support": len(group),
        "total": len(observations),
        "fraction": len(group) / len(observations),
        "evidence": [o["id"] for o in group],
        "outliers": [o["id"] for o in observations if o not in group],
    }


def resolve_all(data, cfg):
    area_provider = AreaAliasProvider(data["areas"])
    history = HistoricalLocationProvider(data["history"], area_provider, cfg)
    results = []
    for r in data["consignments"]:
        c = components(r)
        explicit_areas = area_provider.lookup(r["area"])
        city_areas = area_provider.lookup(r["city"])
        areas = explicit_areas or city_areas
        fields_conflict = bool(
            explicit_areas
            and city_areas
            and {a["area_name"] for a in explicit_areas}.isdisjoint(
                {a["area_name"] for a in city_areas}
            )
        )
        matches = history.candidates(areas, c, r["customer_phone"])
        clusters = []
        for key, obs, fuzzy in matches:
            g = cluster(obs, cfg)
            if g:
                clusters.append({**g, "key": list(key), "fuzzy": fuzzy})
        result = {
            "row_key": r["row_key"],
            "consignment_id": r["consignment_id"],
            "original_address": " | ".join(
                r[k] for k in ["address_line_1", "address_line_2", "area", "city"]
            ),
            "normalized_address": r["normalized_address"],
            "components": c,
            "lat": None,
            "lng": None,
            "confidence": 0,
            "confidence_kind": "heuristic evidence strength, not probability",
            "quality": "INCOMPLETE",
            "source": "NONE",
            "action": "VERIFY_WITH_CUSTOMER",
            "manual_review_required": True,
            "evidence": [],
            "candidates": clusters,
            "area_candidates": [
                {
                    "name": a["area_name"],
                    "emirate": a["emirate"],
                    "lat": float(a["centroid_lat"]),
                    "lng": float(a["centroid_lng"]),
                    "precision": "area centroid only",
                }
                for a in areas
            ],
        }
        text = norm(result["original_address"])
        city = norm(r["city"])
        permitted = {norm(x) for x in cfg["service_emirates"]}
        external_city = any(
            x in city and x not in permitted
            for x in [
                "dubai",
                "sharjah",
                "ajman",
                "abu dhabi",
                "fujairah",
                "ras al khaimah",
                "umm al quwain",
            ]
        )
        wrong_emirate = any(norm(a["emirate"]) not in permitted for a in areas)
        if re.search(r"\bp\s*o\s*box\b|\bpo box\b", text):
            result.update(
                quality="INVALID",
                action="HOLD_FOR_CORRECTION",
                explanation="PO Box is not a physical destination",
            )
        elif external_city or wrong_emirate or fields_conflict:
            result.update(
                quality="INVALID",
                action="HOLD_FOR_CORRECTION",
                explanation="Location is outside the configured service region or conflicts with the city field",
            )
        elif len(areas) > 1 or len(clusters) > 1:
            result.update(
                quality="AMBIGUOUS",
                action="MANAGER_REVIEW",
                explanation="Multiple areas or buildings match; confirm the building and emirate",
            )
        elif clusters:
            g = clusters[0]
            if (
                g["support"] >= cfg["address"]["min_observations"]
                and g["fraction"] >= cfg["address"]["min_cluster_fraction"]
            ):
                score = (
                    0.88
                    if g["fuzzy"]
                    else min(0.98, 0.88 + 0.01 * min(g["support"], 10))
                )
                if score >= cfg["address"]["auto_threshold"]:
                    result.update(
                        lat=g["point"][0],
                        lng=g["point"][1],
                        quality="GOOD",
                        source="HISTORICAL_CLUSTER",
                        confidence=score,
                        action="AUTO_ROUTE",
                        manual_review_required=False,
                        evidence=g["evidence"],
                        explanation=f"{g['support']}/{g['total']} successful GPS observations agree on one building location; {len(g['outliers'])} outliers excluded",
                    )
                else:
                    result.update(
                        explanation="History strength below configured auto-route threshold"
                    )
            else:
                result.update(
                    quality="AMBIGUOUS",
                    action="MANAGER_REVIEW",
                    explanation=f"History has {g['support']}/{g['total']} consistent observations; too few matching observations or conflicting GPS",
                )
        else:
            result.update(
                explanation="History does not identify a building location. Confirm the destination with the customer"
            )
        if not result.get("explanation"):
            result["explanation"] = "Insufficient evidence"
        results.append(result)
    return results, {
        "counts": dict(history.rejected),
        "dispositions": history.dispositions,
    }
