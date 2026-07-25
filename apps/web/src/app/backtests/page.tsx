import type { Metadata } from "next";

import { BacktestExplorer } from "@/components/backtests/backtest-explorer";

export const metadata: Metadata = {
  title: "Model Backtests",
};

export default function BacktestsPage() {
  return <BacktestExplorer />;
}
