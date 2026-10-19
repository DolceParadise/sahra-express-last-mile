import copy
import pytest
from backend.app.core import config
from backend.app.ingestion import ingest
from backend.app.addresses import resolve_all
from backend.app.routing import plan


@pytest.fixture(scope="session")
def real():
    cfg = config()
    data = ingest(cfg)
    addresses, _ = resolve_all(data, cfg)
    return cfg, data, addresses


@pytest.fixture
def small(real):
    cfg, data, addresses = copy.deepcopy(real)
    c = copy.deepcopy(next(c for c in data["consignments"] if not c["problems"]))
    c.update(
        consignment_id="TEST1",
        row_key="consignments:2",
        weight_kg=2,
        length_cm=20,
        width_cm=10,
        height_cm=10,
        pieces=1,
        volume_m3=0.002,
        payment_type="PREPAID",
        cod_amount_aed=0,
        handling="NONE",
        window=[540, 1260],
        normalized_address="flat 1 test tower dubai",
        notes="",
        attempt_number=1,
    )
    d = copy.deepcopy(next(d for d in data["drivers"] if d["status"] == "AVAILABLE"))
    d.update(
        driver_id="TD1",
        status="AVAILABLE",
        licence_type="BOTH",
        start=540,
        end=1080,
        problems=[],
    )
    v = copy.deepcopy(next(v for v in data["vehicles"] if v["type"] == "SMALL_VAN"))
    v.update(
        vehicle_id="TV1",
        status="AVAILABLE",
        problems=[],
        max_weight_kg=600,
        max_volume_m3=3,
        type="SMALL_VAN",
        refrigerated=False,
    )
    a = copy.deepcopy(addresses[0])
    a.update(
        consignment_id="TEST1",
        row_key=c["row_key"],
        lat=25.13,
        lng=55.25,
        quality="GOOD",
        action="AUTO_ROUTE",
        source="HISTORICAL_CLUSTER",
        candidates=[{"key": ["Dubai Marina", "test tower", "building"]}],
    )
    data.update(consignments=[c], drivers=[d], vehicles=[v])
    p = plan(data, [a], cfg, solver_seconds=0)
    return cfg, data, [a], p
