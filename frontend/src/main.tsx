import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field, FieldLabel, FieldError } from "@/components/ui/field";
import { Meter } from "@/components/ui/meter";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Panel,
  Choice,
  EvidenceDialog,
  StatusBadge,
  Metric,
} from "./components/dispatch-ui";
import React, { lazy, Suspense, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { colors } from "./components/route-colors";
const RouteMap = lazy(() => import("./components/RouteMap"));
import { request } from "./types";
import type { Address, Plan, Overview, Inputs, Resource, Issue } from "./types";
import DispatchSidebar from "./components/DispatchSidebar";
import MorningOverview from "./components/MorningOverview";
import { DispatchLoading } from "./components/dispatch-ui";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Tooltip,
  TooltipPopup,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  BoxIcon,
  InfoIcon,
  ChevronRightIcon,
  CheckCheckIcon,
  PlayIcon,
  TriangleAlertIcon,
} from "lucide-react";
import "./style.css";
const pages = [
  "Morning overview",
  "Input audit",
  "Address review",
  "Route planning",
  "Edit & validate",
  "Approval & export",
  "Operational exceptions",
];
const money = (x: unknown) =>
  Number(x ?? 0).toLocaleString("en-AE", { maximumFractionDigits: 2 });
const identity = {
  reviewer: "Hub manager",
  reason: "Reviewed in dispatch desk",
};
const Badge = StatusBadge;
function App() {
  const [page, setPage] = useState(0),
    [overview, setOverview] = useState<Overview | null>(null),
    [inputs, setInputs] = useState<Inputs | null>(null),
    [addresses, setAddresses] = useState<Address[]>([]),
    [p, setPlan] = useState<Plan | null>(null),
    [versions, setVersions] = useState<{ version: number; created: string }[]>(
      [],
    ),
    [events, setEvents] = useState<unknown[]>([]),
    [evidence, setEvidence] = useState<Record<string, unknown>>({}),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [selected, setSelected] = useState(""),
    [search, setSearch] = useState(""),
    [quality, setQuality] = useState("ALL"),
    [row, setRow] = useState(""),
    [date, setDate] = useState("2026-10-14"),
    [drivers, setDrivers] = useState<Resource[]>([]),
    [vehicles, setVehicles] = useState<Resource[]>([]),
    [reviewer, setReviewer] = useState("Hub manager"),
    [reason, setReason] = useState(""),
    [lat, setLat] = useState(""),
    [lng, setLng] = useState(""),
    [operation, setOperation] = useState("vehicle"),
    [resource, setResource] = useState(""),
    [stopIndex, setStopIndex] = useState(0),
    [targetRoute, setTargetRoute] = useState(""),
    [targetIndex, setTargetIndex] = useState(0),
    [exceptionKind, setExceptionKind] = useState("driver_absence"),
    [exceptionResource, setExceptionResource] = useState(""),
    [urgent, setUrgent] = useState('{\n  "consignment_id": "URGENT-001"\n}'),
    [cid, setCid] = useState(""),
    [slot, setSlot] = useState("13:00,17:00"),
    [issueFilter, setIssueFilter] = useState("HARD");
  const refresh = () =>
    Promise.all([
      request<{ version: number; created: string }[]>("/versions").then(
        setVersions,
      ),
      request<unknown[]>("/events").then(setEvents),
    ]);
  useEffect(() => {
    Promise.all([
      request<Overview>("/overview").then((x) => {
        setOverview(x);
        setDate(x.config.plan_date);
      }),
      request<Inputs>("/inputs").then((x) => {
        setInputs(x);
        setDrivers(x.drivers);
        setVehicles(x.vehicles);
      }),
      request<Address[]>("/addresses").then(setAddresses),
      request<Record<string, unknown>>("/evidence").then(setEvidence),
      request<{ version: number; created: string }[]>("/versions").then(
        async (x) => {
          setVersions(x);
          if (x[0]) setPlan(await request<Plan>("/plans/" + x[0].version));
        },
      ),
    ]).catch((e) => setError(String(e)));
  }, []);
  useEffect(() => {
    if (!p) return;
    setAddresses(p.addresses);
    if (!p.routes.some((r) => r.route_id === selected))
      setSelected(p.routes[0]?.route_id ?? "");
    request<{ drivers: Resource[]; vehicles: Resource[] }>(
      "/plans/" + p.version + "/context",
    )
      .then((x) => {
        setDrivers(x.drivers);
        setVehicles(x.vehicles);
      })
      .catch((e) => setError(String(e)));
    refresh().catch((e) => setError(String(e)));
  }, [p?.version]);
  const act = async (path: string, body: unknown) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await request<Plan>(path, body);
      setPlan(result);
      setNotice(
        `Version ${result.version} saved. ${result.validation.valid ? "No hard violations." : result.validation.hard_count + " hard violations need correction."}`,
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const route = p?.routes.find((r) => r.route_id === selected);
  const selectedAddress = addresses.find((a) => a.row_key === row);
  const list = addresses.filter(
    (a) =>
      (quality === "ALL" || a.quality === quality) &&
      `${a.consignment_id} ${a.original_address}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const routeSelector = (
    <Choice
      aria-label="Route"
      value={selected}
      onValueChange={(value) => {
        setSelected(value);
        setResource("");
      }}
      items={[
        ...(p?.routes.map((r) => ({
          value: String(r.route_id),
          label: `${r.route_id} · ${r.driver_id} · ${r.vehicle_id}`,
        })) ?? []),
      ]}
    />
  );
  const generate = () =>
    act("/plans", { plan_date: date, method: "optimized", solver_seconds: 5 });
  const stats = p && (
    <div className="metrics four">
      <Metric
        label="Planned consignments"
        value={p.metrics.planned_consignments}
        detail={`${p.metrics.unassigned_rows} input rows held / unassigned`}
      />
      <Metric
        label="Active routes"
        value={p.routes.length}
        detail={`${p.metrics.total_km} approximate km`}
      />
      <Metric
        label="Scenario cost"
        value={"AED " + money(p.metrics.total_cost_scenario_aed)}
        detail="Uses the historical failure rate"
      />
      <Metric
        label="Within booked slots"
        value={
          Math.round(Number(p.metrics.planned_on_time_fraction) * 100) + "%"
        }
        detail="Share of planned arrivals within booked slots"
      />
    </div>
  );
  const validation = p && (
    <Panel className="panel">
      <div className="panel-head">
        <h2>Independent validation</h2>
        <Badge text={p.validation.valid ? "VALIDATED" : "HARD"} />
        <span>
          {p.validation.hard_count} hard · {p.validation.soft_count} soft
        </span>
      </div>
      {!p.validation.findings.length ? (
        <p className="positive">No constraint findings.</p>
      ) : (
        p.validation.findings.map((f, i) => (
          <div
            key={i}
            className={"finding " + (f.severity === "HARD" ? "hard" : "")}
          >
            <Badge text={f.severity} />
            <div>
              <strong>
                {f.route} · {f.code}
              </strong>
              <p>{f.explanation}</p>
              <small>
                {f.recommended_correction} {f.consignment_ids.join(", ")}
              </small>
            </div>
          </div>
        ))
      )}
    </Panel>
  );
  if (!overview || !inputs) return <DispatchLoading error={error} />;
  return (
    <div className="app">
      <DispatchSidebar
        pages={pages}
        page={page}
        onNavigate={(next) => {
          setPage(next);
          setSearch("");
        }}
        reviewCount={addresses.filter((a) => a.quality !== "GOOD").length}
        hub={overview.config.hub_id}
        hubName={overview.config.hub_name}
      />

      <main>
        <div className="workspace-bar">
          <div>
            <BoxIcon aria-hidden="true" />
            <span>Operations</span>
            <ChevronRightIcon aria-hidden="true" />
            <span>
              {overview.config.hub_id} · {overview.config.hub_name}
            </span>
          </div>
          <span className="workspace-live">
            <span className="live-dot" />
            Local workspace
          </span>
        </div>
        <header>
          <div>
            <span className="eyebrow">DAILY DISPATCH</span>
            <h1>{pages[page]}</h1>
            <p>
              {overview.config.hub_name} · Plan ready by{" "}
              {overview.config.planning_deadline} · {overview.config.timezone}
            </p>
          </div>
          <div className="header-controls">
            <Field>
              <FieldLabel>Shift date</FieldLabel>
              <Input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
              <FieldError />
            </Field>
            {p && <Badge text={p.state} />}
            <Button
              type="button"
              variant="default"
              loading={busy}
              disabled={busy}
              onClick={generate}
            >
              <PlayIcon aria-hidden="true" />
              {busy ? "Working..." : "Generate plan"}
            </Button>
          </div>
        </header>
        {error && (
          <Alert variant="error" className="feedback">
            <TriangleAlertIcon aria-hidden="true" />
            <AlertTitle>Action could not complete</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {notice && (
          <Alert variant="success" role="status" className="feedback">
            <CheckCheckIcon aria-hidden="true" />
            <AlertTitle>{notice}</AlertTitle>
          </Alert>
        )}
        <div className="context-strip">
          <span>{overview.config.client_id}</span>
          <span>
            {p ? `Plan v${p.version} · ${p.plan_date}` : "No plan generated"}
          </span>
          {p ? (
            <div className="planner-status">
              <CheckCheckIcon aria-hidden="true" />
              <span>
                {p.fallback_reason
                  ? "Fallback plan generated"
                  : "Plan generated"}{" "}
                in {p.runtime_seconds}s
              </span>
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Button
                      type="button"
                      size="icon-xs"
                      variant="ghost"
                      aria-label="Planning method details"
                    />
                  }
                >
                  <InfoIcon aria-hidden="true" />
                </TooltipTrigger>
                <TooltipPopup>
                  {p.engine}.{" "}
                  {p.fallback_reason ||
                    "Road distances use the configured straight-line approximation."}
                </TooltipPopup>
              </Tooltip>
            </div>
          ) : (
            <span>Import complete · review exceptions before dispatch</span>
          )}
          {p && (
            <Choice
              aria-label="Load saved version"
              value={p.version}
              onValueChange={(value) => {
                setBusy(true);
                request<Plan>("/plans/" + value)
                  .then(setPlan)
                  .catch((e) => setError(String(e)))
                  .finally(() => setBusy(false));
              }}
              items={[
                ...(versions.map((v) => ({
                  value: String(v.version),
                  label: `Version ${v.version} · ${new Date(v.created).toLocaleTimeString()}`,
                })) ?? []),
              ]}
            />
          )}
        </div>
        {page === 0 && (
          <MorningOverview
            overview={overview}
            inputs={inputs}
            addresses={addresses}
            plan={p}
            onNavigate={setPage}
            onReview={(q) => {
              setQuality(q);
              setPage(2);
            }}
          />
        )}
        {page === 1 && (
          <>
            <div className="metrics four">
              {Object.entries(overview.counts).map(([name, n]) => (
                <Metric
                  key={name}
                  label={name.replaceAll("_", " ")}
                  value={n}
                  detail="Source CSV imported"
                />
              ))}
            </div>
            <Panel className="panel">
              <div className="panel-head">
                <h2>Import problems and normalization</h2>
                <Choice
                  aria-label="Issue severity"
                  value={issueFilter}
                  onValueChange={(value) => setIssueFilter(value)}
                  items={[
                    ...(["HARD", "WARNING", "INFO", "ALL"].map((x) => ({
                      value: String(x),
                      label: x,
                    })) ?? []),
                  ]}
                />
              </div>
              <p>
                All rows sharing a duplicate ID stay held. Correct the source file
                and reimport it. Address confirmation cannot fix parcel details.
              </p>
              <div className="table-scroll">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Input row</TableHead>
                      <TableHead>Record / problem</TableHead>
                      <TableHead>Explanation</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {inputs.issues
                      .filter(
                        (i) =>
                          issueFilter === "ALL" || i.severity === issueFilter,
                      )
                      .map((i: Issue, n) => (
                        <TableRow key={n}>
                          <TableCell>
                            {i.row_key}
                            <br />
                            <Badge text={i.severity} />
                          </TableCell>
                          <TableCell>
                            <strong>{i.record_id}</strong>
                            <small>{i.code}</small>
                          </TableCell>
                          <TableCell>{i.explanation}</TableCell>
                          <TableCell>{i.action}</TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              </div>
            </Panel>
            <EvidenceDialog title={"Raw input values and row dispositions"}>
              <pre>
                {JSON.stringify(
                  inputs.consignments.filter((c) => c.problems.length),
                  null,
                  2,
                )}
              </pre>
            </EvidenceDialog>
          </>
        )}
        {page === 2 && (
          <>
            <div className="toolbar">
              <Input
                type="text"
                aria-label="Search addresses"
                placeholder="Search ID, building, area..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Choice
                aria-label="Address quality"
                value={quality}
                onValueChange={(value) => setQuality(value)}
                items={[
                  ...(["ALL", "GOOD", "AMBIGUOUS", "INCOMPLETE", "INVALID"].map(
                    (x) => ({
                      value: String(x),
                      label: x,
                    }),
                  ) ?? []),
                ]}
              />
              <span>{list.length} records</span>
            </div>
            <div className="review-layout">
              <Panel className="panel address-list">
                {list.map((a) => (
                  <Button
                    type="button"
                    variant="outline"
                    key={a.row_key}
                    className={row === a.row_key ? "selected" : ""}
                    onClick={() => {
                      setRow(a.row_key);
                      setLat("");
                      setLng("");
                      setReason("");
                    }}
                  >
                    <div>
                      <strong>{a.consignment_id}</strong>
                      <Badge text={a.quality} />
                    </div>
                    <p>{a.original_address || "Missing address"}</p>
                    <small>
                      {a.action.replaceAll("_", " ")} · {a.source}
                    </small>
                  </Button>
                ))}
              </Panel>
              <Panel className="panel review-detail">
                {selectedAddress ? (
                  <>
                    <div className="panel-head">
                      <h2>{selectedAddress.consignment_id}</h2>
                      <Badge text={selectedAddress.quality} />
                    </div>
                    <div className="data-label">
                      Original address<p>{selectedAddress.original_address}</p>
                    </div>
                    <div className="data-label">
                      Normalized address
                      <p>{selectedAddress.normalized_address}</p>
                    </div>
                    <div className="callout">
                      <strong>{selectedAddress.explanation}</strong>
                      <p>
                        Next action:{" "}
                        {selectedAddress.action.replaceAll("_", " ")}
                      </p>
                    </div>
                    <dl>
                      <dt>Evidence source</dt>
                      <dd>{selectedAddress.source}</dd>
                      <dt>Evidence strength</dt>
                      <dd>
                        {selectedAddress.confidence.toFixed(2)} ·{" "}
                        {selectedAddress.confidence_kind}
                      </dd>
                      <dt>Supported coordinate</dt>
                      <dd>
                        {selectedAddress.lat === null
                          ? "Needs confirmation"
                          : `${selectedAddress.lat}, ${selectedAddress.lng}`}
                      </dd>
                      <dt>Source records</dt>
                      <dd>
                        {selectedAddress.evidence.join(", ") ||
                          "No matching historical locations"}
                      </dd>
                    </dl>
                    <EvidenceDialog
                      title={
                        " Parsed components, candidates and rejected outliers "
                      }
                    >
                      <pre>
                        {JSON.stringify(
                          {
                            components: selectedAddress.components,
                            candidates: selectedAddress.candidates,
                            area_centres: selectedAddress.area_candidates,
                          },
                          null,
                          2,
                        )}
                      </pre>
                    </EvidenceDialog>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (p)
                          act(`/plans/${p.version}/address-review`, {
                            row_key: row,
                            action: "MANUAL_OVERRIDE",
                            lat: Number(lat),
                            lng: Number(lng),
                            reviewer,
                            reason,
                          });
                      }}
                    >
                      <h3>Record a verified correction</h3>
                      <p>
                        Enter coordinates confirmed by the customer. Record who
                        confirmed the location and how.
                      </p>
                      <div className="form-grid">
                        <Field>
                          <FieldLabel>Latitude</FieldLabel>
                          <Input
                            required
                            type="number"
                            step="any"
                            value={lat}
                            onChange={(e) => setLat(e.target.value)}
                          />
                          <FieldError />
                        </Field>
                        <Field>
                          <FieldLabel>Longitude</FieldLabel>
                          <Input
                            required
                            type="number"
                            step="any"
                            value={lng}
                            onChange={(e) => setLng(e.target.value)}
                          />
                          <FieldError />
                        </Field>
                        <Field>
                          <FieldLabel>Reviewer</FieldLabel>
                          <Input
                            type="text"
                            required
                            value={reviewer}
                            onChange={(e) => setReviewer(e.target.value)}
                          />
                          <FieldError />
                        </Field>
                        <Field>
                          <FieldLabel>Evidence / reason</FieldLabel>
                          <Input
                            type="text"
                            required
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                          />
                          <FieldError />
                        </Field>
                      </div>
                      <Button
                        type="submit"
                        variant="default"
                        disabled={!p || busy}
                      >
                        Confirm location
                      </Button>
                      <div className="actions">
                        {[
                          "VERIFY_WITH_CUSTOMER",
                          "VERIFY_WITH_SHOP",
                          "HOLD_FOR_CORRECTION",
                        ].map((action) => (
                          <Button
                            variant="outline"
                            key={action}
                            type="button"
                            disabled={!p || busy || !reason || !reviewer}
                            onClick={() =>
                              p &&
                              act(`/plans/${p.version}/address-review`, {
                                row_key: row,
                                action,
                                reviewer,
                                reason,
                              })
                            }
                          >
                            {action.replaceAll("_", " ")}
                          </Button>
                        ))}
                      </div>
                      {!p && (
                        <p>Generate a draft plan before saving a review.</p>
                      )}
                      <small>
                        Corrections carry forward when you reoptimize this draft.
                        Reoptimize to assign newly confirmed records.
                      </small>
                    </form>
                  </>
                ) : (
                  <div className="empty">
                    Select a consignment to inspect its evidence.
                  </div>
                )}
              </Panel>
            </div>
          </>
        )}
        {(page === 3 || page === 4) && (
          <>
            {!p ? (
              <Panel className="empty panel">
                <h2>Build the morning plan</h2>
                <p>
                  Generate a plan from the audited source files. Unresolved
                  destinations stay held.
                </p>
                <Button
                  type="button"
                  variant="default"
                  loading={busy}
                  disabled={busy}
                  onClick={generate}
                >
                  <PlayIcon aria-hidden="true" />
                  Generate plan
                </Button>
              </Panel>
            ) : (
              <>
                {stats}
                <div className="planning-layout">
                  <Panel className="panel map-panel">
                    <div className="panel-head">
                      <h2>Routes from Al Quoz</h2>
                      {routeSelector}
                    </div>
                    <Suspense
                      fallback={
                        <div className="map-loading" role="status">
                          Loading route map...
                        </div>
                      }
                    >
                      <RouteMap
                        routes={p.routes}
                        hub={overview.config.hub}
                        selected={selected}
                        onSelect={setSelected}
                      />
                    </Suspense>
                    <div className="legend">
                      {p.routes.map((r, i) => (
                        <Button
                          type="button"
                          variant="outline"
                          key={r.route_id}
                          onClick={() => setSelected(r.route_id)}
                        >
                          <i
                            style={{ background: colors[i % colors.length] }}
                          />
                          {r.route_id} · {r.stops.length} stops
                        </Button>
                      ))}
                    </div>
                  </Panel>
                  <Panel className="panel route-detail">
                    {route && (
                      <>
                        <div className="panel-head">
                          <h2>{route.route_id}</h2>
                          <Badge text={route.vehicle_type} />
                        </div>
                        <p>
                          {route.driver_id} · {route.vehicle_id} ·{" "}
                          {route.licence}
                        </p>
                        <div className="mini-stats">
                          <span>
                            AED <strong>{money(route.cost_aed)}</strong>
                          </span>
                          <span>
                            <strong>{route.distance_km}</strong> km
                          </span>
                          <span>
                            <strong>{route.duration_min}</strong> min
                          </span>
                          <span>
                            Cash <strong>{money(route.cash_aed)}</strong>
                          </span>
                        </div>
                        <p>
                          Depart {route.depart_hub} → return {route.return_hub}
                          <br />
                          Break{" "}
                          {route.breaks
                            .map((b) => b.start + " to " + b.end)
                            .join(", ") || "Not required"}
                        </p>
                        <div className="data-label">
                          Weight {route.weight_kg} kg ·{" "}
                          {Math.round(route.weight_utilization * 100)}%
                          <Meter
                            aria-label="Weight utilization"
                            value={Math.min(1, route.weight_utilization)}
                            max={1}
                          />
                        </div>
                        <div className="data-label">
                          Volume {route.volume_m3} m³ ·{" "}
                          {Math.round(route.volume_utilization * 100)}%
                          <Meter
                            aria-label="Volume utilization"
                            value={Math.min(1, route.volume_utilization)}
                            max={1}
                          />
                        </div>
                        <ol className="stops">
                          {route.stops.map((s) => (
                            <li key={s.stop_id}>
                              <time>{s.eta}</time>
                              <div>
                                <strong>{s.consignment_ids.join(", ")}</strong>
                                <p>{s.address}</p>
                                <small>
                                  {s.service_min} min service ·{" "}
                                  {s.weight_kg.toFixed(1)} kg · COD{" "}
                                  {money(s.cash_aed)}
                                </small>
                              </div>
                            </li>
                          ))}
                        </ol>
                      </>
                    )}
                  </Panel>
                </div>
                {page === 4 && (
                  <Panel className="panel">
                    <h2>Change an assignment</h2>
                    <p>
                      Edits create a new version, recompute the route and run
                      independent validation. An incompatible choice is saved as
                      a draft so you can inspect the violation.
                    </p>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        act(`/plans/${p.version}/edit`, {
                          operation,
                          route_id: selected,
                          resource_id: resource,
                          stop_index: stopIndex,
                          target_route_id: targetRoute,
                          target_index: targetIndex,
                          reviewer,
                          reason,
                        });
                      }}
                    >
                      <div className="form-grid">
                        <Field>
                          <FieldLabel>Route</FieldLabel>
                          {routeSelector}
                          <FieldError />
                        </Field>
                        <Field>
                          <FieldLabel>Change</FieldLabel>
                          <Choice
                            value={operation}
                            onValueChange={(value) => {
                              setOperation(value);
                              setResource("");
                            }}
                            items={[
                              ...([
                                "vehicle",
                                "driver",
                                "reorder",
                                "move",
                                "hold",
                              ].map((x) => ({
                                value: String(x),
                                label: x,
                              })) ?? []),
                            ]}
                          />
                          <FieldError />
                        </Field>
                        {["vehicle", "driver"].includes(operation) ? (
                          <Field>
                            <FieldLabel>Resource</FieldLabel>
                            <Choice
                              required
                              value={resource}
                              onValueChange={(value) => setResource(value)}
                              items={[
                                {
                                  value: String(""),
                                  label: "Choose resource",
                                },
                                ...((operation === "driver"
                                  ? drivers
                                  : vehicles
                                ).map((x) => ({
                                  value: String(x.driver_id || x.vehicle_id),
                                  label: `${x.driver_id || x.vehicle_id} · ${x.type || x.licence_type} · ${x.status}`,
                                })) ?? []),
                              ]}
                            />
                            <FieldError />
                          </Field>
                        ) : (
                          <>
                            <Field>
                              <FieldLabel>Stop</FieldLabel>
                              <Choice
                                value={stopIndex}
                                onValueChange={(value) =>
                                  setStopIndex(Number(value))
                                }
                                items={[
                                  ...(route?.stops.map((s, i) => ({
                                    value: String(i),
                                    label: `${i + 1} · ${s.consignment_ids.join(", ")}`,
                                  })) ?? []),
                                ]}
                              />
                              <FieldError />
                            </Field>
                            {operation === "move" && (
                              <Field>
                                <FieldLabel>Target route</FieldLabel>
                                <Choice
                                  required
                                  value={targetRoute}
                                  onValueChange={(value) =>
                                    setTargetRoute(value)
                                  }
                                  items={[
                                    {
                                      value: String(""),
                                      label: "Choose target",
                                    },
                                    ...(p.routes.map((r) => ({
                                      value: String(r.route_id),
                                      label: r.route_id,
                                    })) ?? []),
                                  ]}
                                />
                                <FieldError />
                              </Field>
                            )}
                            {operation !== "hold" && (
                              <Field>
                                <FieldLabel>
                                  New position, first is 1
                                </FieldLabel>
                                <Input
                                  type="number"
                                  min="1"
                                  max={(route?.stops.length || 0) + 1}
                                  value={targetIndex + 1}
                                  onChange={(e) =>
                                    setTargetIndex(Number(e.target.value) - 1)
                                  }
                                />
                                <FieldError />
                              </Field>
                            )}
                          </>
                        )}
                        <Field>
                          <FieldLabel>Reviewer</FieldLabel>
                          <Input
                            type="text"
                            required
                            value={reviewer}
                            onChange={(e) => setReviewer(e.target.value)}
                          />
                          <FieldError />
                        </Field>
                        <Field>
                          <FieldLabel>Reason</FieldLabel>
                          <Input
                            type="text"
                            required
                            value={reason}
                            onChange={(e) => setReason(e.target.value)}
                          />
                          <FieldError />
                        </Field>
                      </div>
                      <Button
                        type="submit"
                        variant="default"

                        disabled={busy || p.state === "DISPATCHED"}
                      >
                        Apply and validate
                      </Button>
                    </form>
                  </Panel>
                )}
                {p.change_summary && (
                  <Panel className="panel">
                    <h2>Latest change · {p.change_summary.operation}</h2>
                    <p>
                      Before:{" "}
                      {p.change_summary.previous_metrics.planned_consignments}{" "}
                      planned · AED{" "}
                      {money(
                        p.change_summary.previous_metrics
                          .total_cost_scenario_aed,
                      )}
                      . Now: {p.metrics.planned_consignments} planned · AED{" "}
                      {money(p.metrics.total_cost_scenario_aed)}.
                    </p>
                    <p>
                      {p.change_summary.reason || p.change_summary.next_action}
                    </p>
                  </Panel>
                )}
                {validation}
                <Panel className="panel">
                  <h2>Held and unassigned · {p.unassigned.length} rows</h2>
                  <div className="table-scroll">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Consignment</TableHead>
                          <TableHead>Source row</TableHead>
                          <TableHead>Reason / next action</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {p.unassigned.map((u) => (
                          <TableRow key={u.row_key}>
                            <TableCell>{u.consignment_id}</TableCell>
                            <TableCell>{u.row_key}</TableCell>
                            <TableCell>{u.reason}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </Panel>
              </>
            )}
          </>
        )}
        {page === 5 && (
          <>
            {p ? (
              <>
                <div className="workflow">
                  {["DRAFT", "VALIDATED", "APPROVED", "DISPATCHED"].map((s) => (
                    <span key={s} className={p.state === s ? "current" : ""}>
                      {s}
                    </span>
                  ))}
                </div>
                {stats}
                <Panel className="panel">
                  <h2>Manager sign-off</h2>
                  <p>
                    Approval covers the feasible partial plan.{" "}
                    {p.unassigned.length} input rows remain unassigned and
                    require follow-up.
                  </p>
                  <div className="form-grid">
                    <Field>
                      <FieldLabel>Reviewer</FieldLabel>
                      <Input
                        type="text"
                        value={reviewer}
                        onChange={(e) => setReviewer(e.target.value)}
                      />
                      <FieldError />
                    </Field>
                    <Field>
                      <FieldLabel>Review note</FieldLabel>
                      <Input
                        type="text"
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                      />
                      <FieldError />
                    </Field>
                  </div>
                  <div className="actions">
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy}
                      onClick={() => act(`/plans/${p.version}/validate`, {})}
                    >
                      Revalidate
                    </Button>
                    <Button
                      type="button"
                      variant="default"

                      disabled={
                        busy ||
                        !p.validation.valid ||
                        !reviewer ||
                        !reason ||
                        p.state === "DISPATCHED"
                      }
                      onClick={() =>
                        act(`/plans/${p.version}/approve`, { reviewer, reason })
                      }
                    >
                      Approve version
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={busy || p.state !== "APPROVED"}
                      onClick={() =>
                        act(`/plans/${p.version}/dispatch`, {
                          reviewer,
                          reason,
                        })
                      }
                    >
                      Mark dispatched
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      render={<a href={`/api/plans/${p.version}/export`} />}
                    >
                      Download Appendix B JSON ↓
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      render={
                        <a
                          target="_blank"
                          rel="noreferrer"
                          href={`/api/plans/${p.version}/sheets`}
                        />
                      }
                    >
                      Print driver route sheets ↗
                    </Button>
                  </div>
                </Panel>
                {validation}
                <Panel className="panel">
                  <h2>Costs and comparison</h2>
                  <div className="metrics four">
                    <Metric
                      label="Fixed fleet"
                      value={"AED " + money(p.metrics.fixed_cost_aed)}
                    />
                    <Metric
                      label="Distance cost"
                      value={"AED " + money(p.metrics.running_cost_aed)}
                    />
                    <Metric
                      label="Overtime"
                      value={"AED " + money(p.metrics.overtime_cost_aed)}
                    />
                    <Metric
                      label="Failure-cost scenario"
                      value={"AED " + money(p.metrics.risk_cost_scenario_aed)}
                    />
                  </div>
                  <p>{String(p.metrics.risk_note)}</p>
                  <p>
                    Scenario predicted successes:{" "}
                    {p.metrics.predicted_successes_scenario}. Actual completed:{" "}
                    {p.metrics.actual_completed}. Scenario cost per success: AED{" "}
                    {money(p.metrics.cost_per_success_scenario_aed)}.
                  </p>
                  <EvidenceDialog
                    title={
                      "Baseline comparison and address evaluation"
                    }
                  >
                    <pre>{JSON.stringify(evidence, null, 2)}</pre>
                  </EvidenceDialog>
                </Panel>
                <EvidenceDialog title={"Review history"}>
                  <pre>{JSON.stringify(events, null, 2)}</pre>
                </EvidenceDialog>
              </>
            ) : (
              <Panel className="empty panel">
                Generate a plan before approval and export.
              </Panel>
            )}
          </>
        )}
        {page === 6 && (
          <Panel className="panel">
            <Badge text="SIMULATION" />
            <h2>Handle a shift exception</h2>
            <p>
              Simulate an event before dispatch. An absence or breakdown holds
              parcels on the affected route and preserves other routes. Review
              the held parcels, then reoptimize if needed.
            </p>
            <p>
              Dispatch freezes the plan. Coordinate later changes manually;
              this app has no live driver location, parcel handover records or
              proof of delivery.
            </p>
            {p ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  let incoming;
                  try {
                    if (exceptionKind === "urgent")
                      incoming = JSON.parse(urgent);
                  } catch {
                    setError("Incoming record is not valid JSON");
                    return;
                  }
                  act(`/plans/${p.version}/exceptions`, {
                    kind: exceptionKind,
                    resource_id: exceptionResource,
                    consignment_id: cid,
                    consignment: incoming,
                    slot_start: slot.split(",")[0],
                    slot_end: slot.split(",")[1],
                    reviewer,
                    reason,
                  });
                }}
              >
                <div className="form-grid">
                  <Field>
                    <FieldLabel>Scenario</FieldLabel>
                    <Choice
                      value={exceptionKind}
                      onValueChange={(value) => setExceptionKind(value)}
                      items={[
                        ...([
                          "driver_absence",
                          "vehicle_breakdown",
                          "urgent",
                          "reschedule",
                        ].map((x) => ({
                          value: String(x),
                          label: x,
                        })) ?? []),
                      ]}
                    />
                    <FieldError />
                  </Field>
                  {["driver_absence", "vehicle_breakdown"].includes(
                    exceptionKind,
                  ) && (
                    <Field>
                      <FieldLabel>Resource</FieldLabel>
                      <Choice
                        required
                        value={exceptionResource}
                        onValueChange={(value) => setExceptionResource(value)}
                        items={[
                          {
                            value: String(""),
                            label: "Choose affected resource",
                          },
                          ...((exceptionKind === "driver_absence"
                            ? drivers
                            : vehicles
                          ).map((x) => ({
                            value: String(x.driver_id || x.vehicle_id),
                            label: `${x.driver_id || x.vehicle_id} · ${x.status}`,
                          })) ?? []),
                        ]}
                      />
                      <FieldError />
                    </Field>
                  )}
                  {exceptionKind === "reschedule" && (
                    <>
                      <Field>
                        <FieldLabel>Consignment ID</FieldLabel>
                        <Input
                          type="text"
                          required
                          value={cid}
                          onChange={(e) => setCid(e.target.value)}
                        />
                        <FieldError />
                      </Field>
                      <Field>
                        <FieldLabel>New booked slot</FieldLabel>
                        <Choice
                          value={slot}
                          onValueChange={(value) => setSlot(value)}
                          items={[
                            ...([
                              "09:00,13:00",
                              "13:00,17:00",
                              "17:00,21:00",
                            ].map((x) => ({
                              value: String(x),
                              label: x,
                            })) ?? []),
                          ]}
                        />
                        <FieldError />
                      </Field>
                    </>
                  )}
                  <Field>
                    <FieldLabel>Reviewer</FieldLabel>
                    <Input
                      type="text"
                      required
                      value={reviewer}
                      onChange={(e) => setReviewer(e.target.value)}
                    />
                    <FieldError />
                  </Field>
                  <Field>
                    <FieldLabel>Reason</FieldLabel>
                    <Input
                      type="text"
                      required
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                    />
                    <FieldError />
                  </Field>
                </div>
                {exceptionKind === "urgent" && (
                  <Field>
                    <FieldLabel>
                      Full incoming CSV-shaped record as JSON
                    </FieldLabel>
                    <Textarea
                      rows={12}
                      value={urgent}
                      onChange={(e) => setUrgent(e.target.value)}
                    />
                    <small>
                      Uses the same validation pipeline. Missing fields
                      quarantine the incoming row. No synthetic coordinates are
                      added.
                    </small>
                    <FieldError />
                  </Field>
                )}
                <div className="actions">
                  <Button type="submit" variant="default" disabled={busy}>
                    Apply simulated event
                  </Button>
                  <Button
                    variant="outline"
                    type="button"
                    disabled={busy || p.state === "DISPATCHED"}
                    onClick={() =>
                      act(`/plans/${p.version}/reoptimize`, {
                        reviewer,
                        reason: reason || identity.reason,
                      })
                    }
                  >
                    Reoptimize reviewed draft
                  </Button>
                  <Button
                    variant="outline"
                    type="button"
                    disabled={busy}
                    onClick={() =>
                      act("/plans", { plan_date: date, solver_seconds: 0 })
                    }
                  >
                    Simulate solver timeout
                  </Button>
                </div>
                {p.change_summary && (
                  <div className="callout">
                    <strong>Latest: {p.change_summary.operation}</strong>
                    <p>
                      Routes affected:{" "}
                      {p.change_summary.affected_routes?.join(", ") ||
                        "See validation"}
                      . Planned{" "}
                      {p.change_summary.previous_metrics.planned_consignments} →{" "}
                      {p.metrics.planned_consignments}.
                    </p>
                    <p>{p.change_summary.next_action}</p>
                  </div>
                )}
              </form>
            ) : (
              <p>Generate a plan to run an exception scenario.</p>
            )}
          </Panel>
        )}
        <footer>
          Local planning prototype · Source data is fictional and confidential ·
          Distances and arrival times are estimates. Actual completions remain zero.
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <TooltipProvider>
      <App />
    </TooltipProvider>
  </React.StrictMode>,
);
