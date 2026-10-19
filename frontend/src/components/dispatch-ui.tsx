import { Children, isValidElement, type ReactNode } from "react";
import {
  ArrowUpRightIcon,
  BoxIcon,
  CheckCheckIcon,
  ClipboardListIcon,
  CoinsIcon,
  FileTextIcon,
  MapPinIcon,
  PackageCheckIcon,
  RouteIcon,
  TruckIcon,
  UsersIcon,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardPanel, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectItem,
  SelectPopup,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPanel,
  DialogPopup,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** The application status vocabulary maps to coss's semantic variants. */
export function StatusBadge({ text }: { text: string }) {
  const positive = [
    "GOOD",
    "VALIDATED",
    "APPROVED",
    "ACCEPTED",
    "AUTO_ROUTE",
    "READY",
    "AVAILABLE",
    "DISPATCHED",
  ].includes(text);
  const negative = ["INVALID", "HARD", "QUARANTINED"].includes(text);
  const review = [
    "AMBIGUOUS",
    "INCOMPLETE",
    "WARNING",
    "REVIEW REQUIRED",
    "ON_LEAVE",
    "IN_MAINTENANCE",
  ].includes(text);
  return (
    <Badge
      variant={
        positive
          ? "success"
          : negative
            ? "error"
            : review
              ? "warning"
              : "secondary"
      }
      className="status-badge"
    >
      <span className="status-dot" aria-hidden="true" />
      {text.replaceAll("_", " ")}
    </Badge>
  );
}

/** Keep application sections on the same coss Card spacing and surface. */
export function Panel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const content = Children.toArray(children);
  const first = content[0];
  const heading =
    isValidElement<{ className?: string; children?: ReactNode }>(first) &&
    (first.type === "h2" || first.props.className?.includes("panel-head"));
  return (
    <Card className={cn("panel", className)} render={<section />}>
      {heading && (
        <CardHeader className="section-heading">
          {isValidElement(first) && first.type === "h2" ? (
            <CardTitle render={<h2 />}>
              {first.props.children as ReactNode}
            </CardTitle>
          ) : (
            first
          )}
        </CardHeader>
      )}
      <CardPanel>{heading ? content.slice(1) : content}</CardPanel>
    </Card>
  );
}

export interface ChoiceItem {
  value: string;
  label: string;
}
/** An items-first Select composition. Form labels come from the surrounding Field. */
export function Choice({
  items,
  value,
  onValueChange,
  required,
  disabled,
  className,
  "aria-label": ariaLabel,
}: {
  items: ChoiceItem[];
  value: string | number;
  onValueChange: (value: string) => void;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
}) {
  const options = items.filter((item) => item.value !== "");
  const placeholder =
    items.find((item) => item.value === "")?.label ?? "Choose an option";
  const selected = options.find((item) => item.value === String(value)) ?? null;
  return (
    <Select
      items={options}
      value={selected}
      onValueChange={(item) => onValueChange(item?.value ?? "")}
      itemToStringValue={(item) => item.value}
      required={required}
      disabled={disabled}
    >
      <SelectTrigger
        aria-label={ariaLabel}
        className={cn("choice-trigger", className)}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectPopup alignItemWithTrigger={false} className="choice-popup">
        {options.map((item) => (
          <SelectItem value={item} key={item.value} data-value={item.value}>
            {item.label}
          </SelectItem>
        ))}
      </SelectPopup>
    </Select>
  );
}

export function EvidenceDialog({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="evidence-trigger"
          />
        }
      >
        <FileTextIcon aria-hidden="true" />
        {title}
        <ArrowUpRightIcon aria-hidden="true" />
      </DialogTrigger>
      <DialogPopup className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Source records and details for this view.
          </DialogDescription>
        </DialogHeader>
        <DialogPanel className="evidence-panel">{children}</DialogPanel>
        <DialogFooter>
          <DialogClose render={<Button type="button" variant="ghost" />}>
            Close
          </DialogClose>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

export function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  const name = label.toLowerCase();
  const Icon = name.includes("driver")
    ? UsersIcon
    : name.includes("vehicle")
      ? TruckIcon
      : name.includes("capacity")
        ? BoxIcon
        : name.includes("route")
          ? RouteIcon
          : name.includes("slot")
            ? CheckCheckIcon
            : name.includes("cost") ||
                name.includes("aed") ||
                name.includes("overtime")
              ? CoinsIcon
              : name.includes("planned")
                ? PackageCheckIcon
                : name.includes("address")
                  ? MapPinIcon
                  : ClipboardListIcon;
  return (
    <Card className="metric">
      <CardPanel>
        <div className="metric-label">
          <span>{label}</span>
          <Icon aria-hidden="true" className="size-4" />
        </div>
        <strong>{value}</strong>
        {detail && <small>{detail}</small>}
      </CardPanel>
    </Card>
  );
}

export function DispatchLoading({ error }: { error: string }) {
  return (
    <div className="loading" role="status">
      <div className="loading-brand">
        <BoxIcon aria-hidden="true" />
        Sahra Express
      </div>
      <p>{error || "Loading source files and historical locations..."}</p>
      {!error && (
        <div className="loading-skeletons">
          <Skeleton className="h-12 w-56" />
          <Skeleton className="h-3 w-72" />
          <Skeleton className="h-3 w-48" />
        </div>
      )}
    </div>
  );
}
