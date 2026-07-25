import type { Metadata } from "next";

import { CompareWorkspace } from "@/components/compare/compare-workspace";

export const metadata: Metadata = {
  title: "Compare Film Forecasts",
};

export default function ComparePage() {
  return <CompareWorkspace />;
}
