"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import { Toaster } from "sonner";

import { CookieBanner } from "@/components/layout/cookie-banner";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Tooltip.Provider delayDuration={350}>
      {children}
      <CookieBanner />
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#1e1e21",
            border: "1px solid #303034",
            color: "#f4f2ec",
            borderRadius: "6px",
          },
        }}
      />
    </Tooltip.Provider>
  );
}
