import { describe, expect, it } from "vitest";

import {
  classNames,
  formatDate,
  formatDateTime,
  formatMoney,
  formatPercent,
} from "@/lib/format";

describe("format helpers", () => {
  it.each([
    [2_450_000_000, "$2.5B"],
    [185_000_000, "$185M"],
    [42_000, "$42K"],
    [640, "$640"],
    [-3_400_000, "-$3M"],
  ])("formats %s dollars as %s", (value, expected) => {
    expect(formatMoney(value)).toBe(expected);
  });

  it("formats probability values as percentages", () => {
    expect(formatPercent(0.638)).toBe("64%");
    expect(formatPercent(0.638, 1)).toBe("63.8%");
  });

  it("keeps release dates stable across local time zones", () => {
    expect(formatDate("2027-05-21")).toBe("May 21, 2027");
  });

  it("formats saved-work timestamps for the activity log", () => {
    expect(formatDateTime("2027-05-21T19:30:00Z")).toContain("May 21, 2027");
  });

  it("joins only active class names", () => {
    expect(classNames("base", false, null, "active", undefined)).toBe(
      "base active",
    );
  });
});
