import type { Metadata } from "next";

import { ResearchDashboard } from "@/components/research/research-dashboard";

export const metadata: Metadata = {
  title: "Research",
};

export default function ResearchPage() {
  return <ResearchDashboard />;
}
