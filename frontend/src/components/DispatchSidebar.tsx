import {
  BoxIcon,
  CheckCheckIcon,
  ClipboardCheckIcon,
  FileWarningIcon,
  LayoutDashboardIcon,
  MapPinIcon,
  RouteIcon,
  ShieldCheckIcon,
  SlidersHorizontalIcon,
  TriangleAlertIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { EvidenceDialog } from "./dispatch-ui";
const icons = [
  LayoutDashboardIcon,
  FileWarningIcon,
  MapPinIcon,
  RouteIcon,
  SlidersHorizontalIcon,
  ClipboardCheckIcon,
  TriangleAlertIcon,
];
export default function DispatchSidebar({
  pages,
  page,
  onNavigate,
  reviewCount,
  hub,
  hubName,
}: {
  pages: string[];
  page: number;
  onNavigate: (page: number) => void;
  reviewCount: number;
  hub: string;
  hubName: string;
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-icon">
          <BoxIcon aria-hidden="true" />
        </span>
        <div>
          Sahra Express<small>Dispatch workspace</small>
        </div>
      </div>
      <div className="workspace-switch">
        <span className="hub-symbol">
          <RouteIcon aria-hidden="true" />
        </span>
        <div>
          <strong>{hub}</strong>
          <small>{hubName}</small>
        </div>
        <ShieldCheckIcon
          aria-hidden="true"
          className="size-4 text-muted-foreground"
        />
      </div>
      <nav aria-label="Main navigation">
        {pages.map((name, i) => {
          const Icon = icons[i];
          return (
            <div key={name}>
              {[0, 3, 6].includes(i) && (
                <span className="nav-label">
                  {i === 0 ? "Workspace" : i === 3 ? "Dispatch" : "Operations"}
                </span>
              )}
              <Button
                type="button"
                variant="ghost"
                className={page === i ? "nav-item active" : "nav-item"}
                aria-current={page === i ? "page" : undefined}
                onClick={() => onNavigate(i)}
              >
                <Icon aria-hidden="true" />
                <span>{name}</span>
                {i === 2 && (
                  <Badge variant="secondary" size="sm" className="nav-count">
                    {reviewCount}
                  </Badge>
                )}
              </Button>
            </div>
          );
        })}
      </nav>
      <div className="side-footer">
        <div className="local-status">
          <span className="live-dot" />
          <span>Local workspace</span>
        </div>
        <p>Customer records stay on this machine.</p>
        <Separator />
        <EvidenceDialog title="Planning guide">
          <div className="guide">
            <h3>Start with input and address review</h3>
            <p>
              Routes need valid parcel details and a supported destination.
              Confirm the building when only an area centre is available.
            </p>
            <h3>Review routes and held parcels</h3>
            <p>
              Check held rows, driver workload, cash and route timing. Every
              manual change creates a new version and runs independent
              validation.
            </p>
            <h3>Approve and export</h3>
            <p>
              Resolve all hard violations before approval. Download the JSON and
              printable driver sheets. Dispatched plans are frozen.
            </p>
            <p className="text-muted-foreground">
              Road distances are estimates. The app has no delivery completion records.
            </p>
          </div>
        </EvidenceDialog>
      </div>
      <div className="sidebar-profile">
        <div className="avatar">HM</div>
        <div>
          <strong>Hub manager</strong>
          <small>Local operator</small>
        </div>
        <CheckCheckIcon
          className="size-4 text-muted-foreground"
          aria-hidden="true"
        />
      </div>
    </aside>
  );
}
