"""Reproducible offline run. Invoke as python -m scripts.run."""

from backend.app.core import config, dump, ROOT
from backend.app.ingestion import ingest
from backend.app.addresses import resolve_all
from backend.app.routing import plan
from backend.app.validation import validate
from backend.app.metrics import metrics
from backend.app.evaluation import evaluate


def main():
    cfg = config()
    data = ingest(cfg)
    addresses, rejected = resolve_all(data, cfg)
    dump(
        ROOT / "outputs/addresses.json", addresses
    )  # Predictions written before evaluator reads truth.
    dump(
        ROOT / "outputs/validation.json",
        {
            "issues": data["issues"],
            "resource_dispositions": {
                name: [
                    {k: r[k] for k in ["row_key", idkey, "disposition", "problems"]}
                    for r in data[name]
                ]
                for name, idkey in [
                    ("drivers", "driver_id"),
                    ("vehicles", "vehicle_id"),
                ]
            },
            "dispositions": [
                {
                    k: r[k]
                    for k in ["row_key", "consignment_id", "disposition", "problems"]
                }
                for r in data["consignments"]
            ],
        },
    )
    dump(
        ROOT / "outputs/canonical_inputs.json",
        {k: data[k] for k in ["consignments", "drivers", "vehicles", "areas"]},
    )
    results = {}
    for method in ["baseline", "optimized"]:
        p = plan(data, addresses, cfg, method=method)
        p["validation"] = validate(p, data, addresses, cfg)
        p["metrics"] = metrics(p, data, cfg)
        if p["validation"]["valid"]:
            p["state"] = "VALIDATED"
        dump(ROOT / f"outputs/{method}_plan.json", p)
        results[method] = {
            "metrics": p["metrics"],
            "validation": p["validation"],
            "runtime_seconds": p["runtime_seconds"],
            "engine": p["engine"],
        }
        print(method, p["engine"], p["runtime_seconds"], p["metrics"], p["validation"])
        assert p["validation"]["valid"], "Generated plan contains hard violations"
    dump(ROOT / "outputs/comparison.json", results)
    dump(ROOT / "outputs/evaluation.json", evaluate(addresses))
    dump(ROOT / "outputs/history_rejections.json", rejected)


if __name__ == "__main__":
    main()
