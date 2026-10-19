import {
  ArrowRightIcon,
  ArrowUpRightIcon,
  CheckCheckIcon,
  Clock3Icon,
  FileWarningIcon,
  MapPinIcon,
  PackageIcon,
  RouteIcon,
  ShieldCheckIcon,
} from "lucide-react";
import type { Address, Inputs, Overview, Plan } from "../types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardPanel,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Meter } from "@/components/ui/meter";
import { Separator } from "@/components/ui/separator";
import { Metric, StatusBadge } from "./dispatch-ui";
const amount = (v: number) =>
  v.toLocaleString("en-AE", { maximumFractionDigits: 2 });
export default function MorningOverview({
  overview,
  inputs,
  addresses,
  plan,
  onNavigate,
  onReview,
}: {
  overview: Overview;
  inputs: Inputs;
  addresses: Address[];
  plan: Plan | null;
  onNavigate: (page: number) => void;
  onReview: (quality: string) => void;
}) {
  const supported = addresses.filter((a) =>
    ["AUTO_ROUTE", "MANUAL_OVERRIDE"].includes(a.action),
  ).length;
  const qualities = ["GOOD", "AMBIGUOUS", "INCOMPLETE", "INVALID"];
  const counts = Object.fromEntries(
    qualities.map((q) => [q, addresses.filter((a) => a.quality === q).length]),
  );
  return (
    <div className="overview-content">
      <div className="metrics four">
        <Metric
          label="Imported rows"
          value={overview.counts.consignments}
          detail={`${overview.dispositions.QUARANTINED} quarantined at import`}
        />
        <Metric
          label="Available drivers"
          value={overview.available_drivers}
          detail={`${inputs.drivers.length} in the source roster`}
        />
        <Metric
          label="Available vehicles"
          value={overview.available_vehicles}
          detail={`${inputs.vehicles.length} vehicles in the fleet`}
        />
        <Metric
          label="Fleet weight capacity"
          value={amount(overview.fleet_weight_capacity_kg) + " kg"}
          detail={`${amount(overview.fleet_volume_capacity_m3)} m³ before licence pairing`}
        />
      </div>
      <Card className="readiness-banner">
        <CardPanel>
          <div className="readiness-icon">
            <ShieldCheckIcon aria-hidden="true" />
          </div>
          <div className="readiness-copy">
            <div className="readiness-title">
              <h2>Review the plan before dispatch</h2>
              <StatusBadge
                text={plan?.validation.valid ? "VALIDATED" : "REVIEW REQUIRED"}
              />
            </div>
            <p>
              <strong>
                {supported} of {addresses.length}
              </strong>{" "}
              records have supported locations. Parcel and fleet checks still
              apply. Unresolved records stay held.
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => onReview("ALL")}
          >
            Open address review
            <ArrowRightIcon aria-hidden="true" />
          </Button>
        </CardPanel>
      </Card>
      <div className="overview-grid">
        <Card>
          <CardHeader>
            <CardTitle render={<h2 />}>Address readiness</CardTitle>
            <CardDescription>
              Locations supported by history or confirmed by a reviewer.
            </CardDescription>
            <CardAction>
              <MapPinIcon
                className="size-4 text-muted-foreground"
                aria-hidden="true"
              />
            </CardAction>
          </CardHeader>
          <CardPanel>
            <div className="readiness-total">
              <strong>
                {supported}
                <span> / {addresses.length}</span>
              </strong>
              <span className="text-muted-foreground">supported locations</span>
            </div>
            <div
              className="distribution"
              role="img"
              aria-label={qualities.map((q) => `${q}: ${counts[q]}`).join(", ")}
            >
              {qualities.map((q) => (
                <span
                  key={q}
                  className={"segment segment-" + q.toLowerCase()}
                  style={{ width: `${(counts[q] / addresses.length) * 100}%` }}
                />
              ))}
            </div>
            <div className="quality-grid">
              {qualities.map((q) => (
                <Button
                  key={q}
                  type="button"
                  variant="ghost"
                  className="quality-row"
                  onClick={() => onReview(q)}
                >
                  <span
                    className={"quality-dot " + q.toLowerCase()}
                    aria-hidden="true"
                  />
                  <span>{q.charAt(0) + q.slice(1).toLowerCase()}</span>
                  <strong>{counts[q]}</strong>
                  <ArrowUpRightIcon aria-hidden="true" />
                </Button>
              ))}
            </div>
          </CardPanel>
          <CardFooter className="card-note">
            <ShieldCheckIcon aria-hidden="true" />
            Scores measure location evidence. They do not predict delivery success.
          </CardFooter>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle render={<h2 />}>Needs attention</CardTitle>
            <CardDescription>
              Review these before the {overview.config.planning_deadline}{" "}
              deadline.
            </CardDescription>
            <CardAction>
              <StatusBadge text="REVIEW REQUIRED" />
            </CardAction>
          </CardHeader>
          <CardPanel className="attention-list">
            <Button
              type="button"
              variant="ghost"
              className="attention-item"
              onClick={() => onNavigate(1)}
            >
              <span className="attention-icon">
                <FileWarningIcon aria-hidden="true" />
              </span>
              <span>
                <strong>
                  {overview.dispositions.QUARANTINED} input rows need correction
                </strong>
                <small>
                  Duplicate IDs, package values or unsupported slots.
                </small>
              </span>
              <ArrowRightIcon aria-hidden="true" />
            </Button>
            <Separator />
            <Button
              type="button"
              variant="ghost"
              className="attention-item"
              onClick={() => onReview("AMBIGUOUS")}
            >
              <span className="attention-icon">
                <MapPinIcon aria-hidden="true" />
              </span>
              <span>
                <strong>{counts.AMBIGUOUS} ambiguous destinations</strong>
                <small>
                  Confirm the building and location with the customer.
                </small>
              </span>
              <ArrowRightIcon aria-hidden="true" />
            </Button>
            <Separator />
            <div className="deadline-note">
              <Clock3Icon aria-hidden="true" />
              <p>
                At the deadline, approve the valid routes. Keep unresolved parcels
                held for follow-up.
              </p>
            </div>
          </CardPanel>
        </Card>
      </div>
      <Card className="overview-routes">
        <CardHeader>
          <CardTitle render={<h2 />}>Dispatch plan</CardTitle>
          <CardDescription>
            {plan
              ? `${plan.routes.length} active routes · ${plan.metrics.planned_consignments} planned consignments · ${plan.unassigned.length} rows held or unassigned`
              : "Generate a plan to see routes, assignments and timing."}
          </CardDescription>
          <CardAction>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onNavigate(3)}
            >
              View route planner
              <ArrowUpRightIcon aria-hidden="true" />
            </Button>
          </CardAction>
        </CardHeader>
        {plan && plan.routes.length ? (
          <>
            <CardPanel>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Route / driver</TableHead>
                    <TableHead>Vehicle</TableHead>
                    <TableHead>Stops</TableHead>
                    <TableHead>Weight used</TableHead>
                    <TableHead>Return to hub</TableHead>
                    <TableHead className="text-end">Route cost</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {plan.routes.slice(0, 4).map((r) => (
                    <TableRow key={r.route_id}>
                      <TableCell>
                        <div className="route-name">
                          <span className="route-symbol">
                            <RouteIcon aria-hidden="true" />
                          </span>
                          <div>
                            <strong>{r.route_id}</strong>
                            <small>
                              {r.driver_id} ·{" "}
                              {inputs.drivers.find(
                                (d) => d.driver_id === r.driver_id,
                              )?.name || "Assigned driver"}
                            </small>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <strong className="table-value">{r.vehicle_id}</strong>
                        <small>
                          {r.vehicle_type.replaceAll("_", " ").toLowerCase()}
                        </small>
                      </TableCell>
                      <TableCell>{r.stops.length}</TableCell>
                      <TableCell>
                        <div className="table-meter">
                          <Meter
                            aria-label={`${r.route_id} weight utilization`}
                            value={Math.min(100, r.weight_utilization * 100)}
                          />
                          <span>{Math.round(r.weight_utilization * 100)}%</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="time-cell">
                          <Clock3Icon aria-hidden="true" />
                          {r.return_hub}
                        </span>
                      </TableCell>
                      <TableCell className="text-end">
                        AED {amount(r.cost_aed)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardPanel>
            <CardFooter className="route-table-footer">
              <span>
                <CheckCheckIcon aria-hidden="true" />
                {plan.validation.valid
                  ? "No hard violations"
                  : "Hard violations require correction"}
              </span>
              <span>
                Showing {Math.min(4, plan.routes.length)} of{" "}
                {plan.routes.length} routes
              </span>
            </CardFooter>
          </>
        ) : (
          <CardPanel>
            <div className="empty-route">
              <PackageIcon aria-hidden="true" />
              <h3>No routes to show yet</h3>
              <p>
                Select Generate plan to assign eligible parcels to routes.
              </p>
            </div>
          </CardPanel>
        )}
      </Card>
      <div className="overview-footnote">
        <ShieldCheckIcon aria-hidden="true" />
        <span>{overview.backend_note}</span>
      </div>
    </div>
  );
}
