import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Route } from "../types";
import { colors } from "./route-colors";
export default function RouteMap({
  routes,
  hub,
  selected,
  onSelect,
}: {
  routes: Route[];
  hub: [number, number];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const host = useRef<HTMLDivElement>(null),
    map = useRef<L.Map | null>(null);
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    if (!host.current) return;
    const m = L.map(host.current, {
      zoomControl: true,
      zoomAnimation: false,
      fadeAnimation: false,
      markerZoomAnimation: false,
    }).setView(hub, 11);
    map.current = m;
    const tiles = L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { attribution: "© OpenStreetMap contributors", maxZoom: 19 },
    );
    tiles.on("tileerror", () => setOffline(true));
    tiles.addTo(m);
    return () => {
      m.stop();
      m.remove();
      map.current = null;
    };
  }, []);
  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const layer = L.layerGroup().addTo(m);
    const points: L.LatLngTuple[] = [hub];
    L.marker(hub, {
      icon: L.divIcon({
        className: "hub-marker",
        html: "H",
        iconSize: [28, 28],
      }),
    })
      .bindTooltip("Al Quoz hub")
      .addTo(layer);
    routes.forEach((r, i) => {
      const color = colors[i % colors.length];
      const path: L.LatLngTuple[] = [
        hub,
        ...r.stops.map((s) => [s.lat, s.lng] as L.LatLngTuple),
        hub,
      ];
      points.push(...path);
      L.polyline(path, {
        color,
        weight: selected === r.route_id ? 5 : 3,
        opacity: !selected || selected === r.route_id ? 0.9 : 0.25,
        dashArray: "7 5",
      })
        .on("click", () => onSelect(r.route_id))
        .addTo(layer);
      r.stops.forEach((s) => {
        const label = document.createElement("div");
        label.textContent = `${r.route_id} · ${s.seq} · ${s.eta} · ${s.consignment_ids.join(", ")} · ${s.address}`;
        L.circleMarker([s.lat, s.lng], {
          radius: selected === r.route_id ? 7 : 4,
          color,
          fillColor: color,
          fillOpacity: 1,
          weight: 2,
        })
          .bindPopup(label)
          .on("click", () => onSelect(r.route_id))
          .addTo(layer);
      });
    });
    if (points.length > 1)
      m.fitBounds(L.latLngBounds(points), {
        padding: [30, 30],
        maxZoom: 12,
        animate: false,
      });
    m.invalidateSize();
    return () => {
      if (map.current === m) layer.remove();
    };
  }, [routes, selected, hub[0], hub[1]]);
  return (
    <div className="map-wrap">
      <div
        ref={host}
        className="route-map"
        aria-label="Interactive routes map"
      />
      <div className="map-note">
        {offline
          ? "Map tiles unavailable. Cached coordinates and route paths remain visible."
          : "Approximate connections · 1.4 × straight-line distance"}
      </div>
    </div>
  );
}
