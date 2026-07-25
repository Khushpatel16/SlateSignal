export function formatMoney(value: number, digits = 0): string {
  const sign = value < 0 ? "-" : "";
  const absolute = Math.abs(value);

  if (absolute >= 1_000_000_000) {
    return `${sign}$${(absolute / 1_000_000_000).toFixed(digits + 1)}B`;
  }
  if (absolute >= 1_000_000) {
    return `${sign}$${(absolute / 1_000_000).toFixed(digits)}M`;
  }
  if (absolute >= 1_000) {
    return `${sign}$${(absolute / 1_000).toFixed(0)}K`;
  }
  return `${sign}$${absolute.toFixed(0)}`;
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T12:00:00Z`));
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function classNames(
  ...values: Array<string | false | null | undefined>
): string {
  return values.filter(Boolean).join(" ");
}
