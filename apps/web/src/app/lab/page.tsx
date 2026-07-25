import type { Metadata } from "next";

import { GreenlightLab } from "@/components/lab/greenlight-lab";

export const metadata: Metadata = {
  title: "Greenlight Lab",
  description:
    "Build, forecast, and optimize a film package through live counterfactual simulation.",
};

export default function LabPage() {
  return <GreenlightLab />;
}
