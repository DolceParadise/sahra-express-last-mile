"""Offline evaluator only. Predictions must already exist on disk before reading truth."""

import csv, statistics, math
from .core import ROOT, hav


def evaluate(predictions):
    truth = list(csv.DictReader((ROOT / "data/ground_truth_sample.csv").open()))
    index = {}
    for p in predictions:
        index.setdefault(p["consignment_id"], []).append(p)
    rows = []
    for t in truth:
        candidates = index.get(t["consignment_id"], [])
        p = candidates[0] if len(candidates) == 1 else {}
        error = (
            hav([p["lat"], p["lng"]], [float(t["true_lat"]), float(t["true_lng"])])
            * 1000
            if p.get("lat") is not None
            else None
        )
        rows.append(
            {
                "consignment_id": t["consignment_id"],
                "quality": p.get("quality", "INVALID"),
                "confidence": p.get("confidence", 0),
                "error_m": error,
                "area_centroid_error_m": (
                    hav(
                        [
                            p["area_candidates"][0]["lat"],
                            p["area_candidates"][0]["lng"],
                        ],
                        [float(t["true_lat"]), float(t["true_lng"])],
                    )
                    * 1000
                    if len(p.get("area_candidates", [])) == 1
                    else None
                ),
            }
        )

    def summary(rs):
        errors = sorted(r["error_m"] for r in rs if r["error_m"] is not None)
        n = len(errors)
        total = len(rs)
        return {
            "samples": total,
            "predicted": n,
            "abstained": total - n,
            "coverage": n / total if total else 0,
            "median_error_m": statistics.median(errors) if n else None,
            "mean_error_m": statistics.mean(errors) if n else None,
            "p90_error_m": errors[math.ceil(0.9 * n) - 1] if n else None,
            **{
                f"within_{m}m_among_predictions": (
                    sum(e <= m for e in errors) / n if n else None
                )
                for m in [50, 100, 500]
            },
            **{
                f"within_{m}m_all_samples": (
                    sum(e <= m for e in errors) / total if total else None
                )
                for m in [50, 100, 500]
            },
        }

    return {
        **summary(rows),
        "denominators": "Coverage uses all evaluation rows; error metrics and *_among_predictions use predictions only; *_all_samples includes abstentions as not successful. P90 uses nearest rank.",
        "by_quality": {
            q: summary([r for r in rows if r["quality"] == q])
            for q in sorted({r["quality"] for r in rows})
        },
        "thresholds": {
            str(t): summary(
                [
                    {**r, "error_m": r["error_m"] if r["confidence"] >= t else None}
                    for r in rows
                ]
            )
            for t in [0, 0.85, 0.9, 0.95, 0.98]
        },
        "rows": rows,
    }
