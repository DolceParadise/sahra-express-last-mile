export interface Address {
  row_key: string;
  consignment_id: string;
  original_address: string;
  normalized_address: string;
  lat: number | null;
  lng: number | null;
  quality: string;
  confidence: number;
  confidence_kind: string;
  source: string;
  action: string;
  explanation: string;
  evidence: string[];
  candidates: unknown[];
  area_candidates: unknown[];
  components: Record<string, string | null>;
}
export interface Stop {
  stop_id: string;
  seq: number;
  consignment_ids: string[];
  lat: number;
  lng: number;
  eta: string;
  service_min: number;
  address: string;
  weight_kg: number;
  volume_m3: number;
  cash_aed: number;
  completed: boolean;
  window: number[];
}
export interface Route {
  route_id: string;
  driver_id: string;
  vehicle_id: string;
  vehicle_type: string;
  licence: string;
  depart_hub: string;
  return_hub: string;
  distance_km: number;
  duration_min: number;
  cost_aed: number;
  cash_aed: number;
  weight_kg: number;
  volume_m3: number;
  weight_utilization: number;
  volume_utilization: number;
  stops: Stop[];
  breaks: { start: string; end: string }[];
}
export interface Finding {
  code: string;
  severity: string;
  route: string;
  driver: string;
  vehicle: string;
  consignment_ids: string[];
  explanation: string;
  recommended_correction: string;
}
export interface Plan {
  version: number;
  plan_date: string;
  state: string;
  engine: string;
  runtime_seconds: number;
  fallback_reason: string | null;
  routes: Route[];
  unassigned: { consignment_id: string; row_key: string; reason: string }[];
  addresses: Address[];
  validation: {
    valid: boolean;
    hard_count: number;
    soft_count: number;
    findings: Finding[];
  };
  metrics: Record<string, number | string | number[] | null>;
  change_summary?: {
    operation: string;
    previous_metrics: Record<string, number>;
    reason?: string;
    affected_routes?: string[];
    next_action?: string;
  };
}
export interface Resource {
  driver_id?: string;
  vehicle_id?: string;
  name?: string;
  licence_type?: string;
  type?: string;
  status: string;
  problems: string[];
  max_weight_kg?: number;
  max_volume_m3?: number;
  refrigerated?: boolean;
}
export interface InputRow {
  row_key: string;
  consignment_id: string;
  disposition: string;
  problems: string[];
  raw: Record<string, string>;
  [key: string]: unknown;
}
export interface Issue {
  dataset: string;
  row_key: string;
  record_id: string;
  code: string;
  severity: string;
  explanation: string;
  action: string;
}
export interface Inputs {
  consignments: InputRow[];
  drivers: Resource[];
  vehicles: Resource[];
  issues: Issue[];
  raw_counts: Record<string, number>;
}
export interface Overview {
  config: {
    client_id: string;
    hub_id: string;
    hub_name: string;
    hub: [number, number];
    planning_deadline: string;
    plan_date: string;
    timezone: string;
  };
  counts: Record<string, number>;
  dispositions: Record<string, number>;
  address_quality: Record<string, number>;
  available_drivers: number;
  available_vehicles: number;
  fleet_weight_capacity_kg: number;
  fleet_volume_capacity_m3: number;
  backend_note: string;
}
export async function request<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(
    "/api" + path,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  return data as T;
}
