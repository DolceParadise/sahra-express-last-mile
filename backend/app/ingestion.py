"""Raw values, normalized canonical records and explicit row dispositions."""

import collections, math
from .core import read_csv, minute, norm


def ingest(cfg, data_dir=None):
    raw = {
        n: read_csv(n, cfg, data_dir)
        for n in ["consignments", "drivers", "vehicles", "areas", "delivery_history"]
    }
    issues = []
    out = {}

    def issue(dataset, row, code, msg, severity="HARD"):
        issues.append(
            dict(
                dataset=dataset,
                row_key=row["row_key"],
                record_id=row.get(
                    "consignment_id", row.get("driver_id", row.get("vehicle_id"))
                ),
                code=code,
                severity=severity,
                explanation=msg,
                action=(
                    "Correct source and reimport"
                    if severity == "HARD"
                    else "Review normalized value"
                ),
            )
        )
        if severity == "HARD":
            row["problems"].append(code)

    def number(r, key, default=None, positive=False, integer=False):
        try:
            val = float(r["raw"].get(key, ""))
            if (
                not math.isfinite(val)
                or val < 0
                or (positive and val <= 0)
                or (integer and val != int(val))
            ):
                raise ValueError()
            return val
        except (ValueError, TypeError):
            if default is not None and not r["raw"].get(key, ""):
                return default
            issue(
                r["dataset"],
                r,
                "INVALID_" + key.upper(),
                f"{key} must be a finite "
                + ("positive" if positive else "nonnegative")
                + " number",
            )
            return 0

    for dataset, idkey in [
        ("consignments", "consignment_id"),
        ("drivers", "driver_id"),
        ("vehicles", "vehicle_id"),
    ]:
        counts = collections.Counter(x.get(idkey, "") for x in raw[dataset])
        records = []
        for i, source in enumerate(raw[dataset], 2):
            r = {
                **source,
                "raw": source.copy(),
                "dataset": dataset,
                "row_key": f"{dataset}:{i}",
                "problems": [],
            }
            if not source.get(idkey):
                issue(dataset, r, "MISSING_ID", "Identifier is required")
            if counts[source.get(idkey, "")] > 1:
                issue(
                    dataset,
                    r,
                    "DUPLICATE_ID",
                    "Every row sharing this ID is quarantined until identity is corrected",
                )
            if dataset == "consignments":
                for key in [
                    "weight_kg",
                    "length_cm",
                    "width_cm",
                    "height_cm",
                    "pieces",
                    "attempt_number",
                ]:
                    r[key] = number(
                        r,
                        key,
                        positive=True,
                        integer=key in ["pieces", "attempt_number"],
                    )
                r["volume_m3"] = (
                    r["length_cm"] * r["width_cm"] * r["height_cm"] * r["pieces"] / 1e6
                )
                r["cod_amount_aed"] = number(
                    r,
                    "cod_amount_aed",
                    default=0 if source["payment_type"] == "PREPAID" else None,
                )
                if source["payment_type"] not in ["COD", "PREPAID"]:
                    issue(dataset, r, "PAYMENT", "Unknown payment type")
                if source["payment_type"] == "PREPAID" and r["cod_amount_aed"] > 0:
                    issue(
                        dataset,
                        r,
                        "PAYMENT_CONFLICT",
                        "Prepaid parcel has positive COD",
                    )
                if r["handling"] not in ["NONE", "FRAGILE", "CHILLED", "BULKY"]:
                    issue(dataset, r, "HANDLING", "Unknown handling")
                if r["attempt_number"] > 3:
                    issue(
                        dataset,
                        r,
                        "RTO",
                        "More than three attempts needs shop decision",
                    )
                try:
                    a, b = source["slot_start"], source["slot_end"]
                    r["window"] = (
                        list(cfg["delivery_hours"])
                        if not a and not b
                        else [minute(a), minute(b)]
                    )
                    if (
                        r["window"] != cfg["delivery_hours"]
                        and r["window"] not in cfg["slots"]
                    ):
                        raise ValueError()
                except ValueError:
                    r["window"] = list(cfg["delivery_hours"])
                    issue(
                        dataset,
                        r,
                        "INVALID_SLOT",
                        "Slot is reversed, incomplete, outside hours or not a supported commitment",
                    )
                r["normalized_address"] = norm(
                    " ".join(
                        source.get(k, "")
                        for k in [
                            "address_line_1",
                            "address_line_2",
                            "area",
                            "city",
                            "landmark",
                        ]
                    )
                )
            elif dataset == "drivers":
                r["licence_type"] = cfg["licence_aliases"].get(
                    norm(source["licence_type"]), source["licence_type"].upper()
                )
                if r["licence_type"] not in {"MOTORCYCLE", "LIGHT_VEHICLE", "BOTH"}:
                    issue(dataset, r, "LICENCE", "Unknown licence")
                r["experience_months"] = number(r, "experience_months")
                try:
                    r["start"], r["end"] = minute(source["shift_start"]), minute(
                        source["shift_end"]
                    )
                    if r["start"] >= r["end"]:
                        raise ValueError()
                except ValueError:
                    r["start"] = r["end"] = 0
                    issue(dataset, r, "SHIFT", "Invalid shift")
                if r["status"] not in ["AVAILABLE", "ON_LEAVE"]:
                    issue(dataset, r, "STATUS", "Unknown driver status")
            else:
                r["type"] = cfg["vehicle_aliases"].get(
                    norm(source["type"]), source["type"].upper()
                )
                if r["type"] not in cfg["vehicle_types"]:
                    issue(dataset, r, "VEHICLE_TYPE", "Unknown vehicle type")
                for key in [
                    "max_weight_kg",
                    "max_volume_m3",
                    "fixed_cost_aed_day",
                    "cost_per_km_aed",
                ]:
                    r[key] = number(r, key, positive=key.startswith("max_"))
                r["refrigerated"] = source["refrigerated"].upper() == "TRUE"
                if source["refrigerated"].upper() not in ["TRUE", "FALSE"]:
                    issue(dataset, r, "REFRIGERATION", "Invalid boolean")
                if r["refrigerated"] and r["type"] != "CHILLED_VAN":
                    issue(
                        dataset,
                        r,
                        "REFRIGERATION_CONFLICT",
                        "Refrigerated flag contradicts vehicle type; no chilled eligibility",
                        severity="WARNING",
                    )
                if r["status"] not in ["AVAILABLE", "IN_MAINTENANCE"]:
                    issue(dataset, r, "STATUS", "Unknown vehicle status")
            if any(str(r.get(k, "")) != str(source[k]) for k in source):
                issue(
                    dataset,
                    r,
                    "NORMALIZED",
                    "Safe type/alias/time normalization applied; original preserved",
                    severity="INFO",
                )
            r["disposition"] = (
                "QUARANTINED"
                if r["problems"]
                else (
                    "UNAVAILABLE"
                    if dataset != "consignments" and r["status"] != "AVAILABLE"
                    else "ACCEPTED"
                )
            )
            records.append(r)
        out[dataset] = records
    return {
        **out,
        "areas": raw["areas"],
        "history": raw["delivery_history"],
        "issues": issues,
        "raw_counts": {k: len(v) for k, v in raw.items()},
    }
