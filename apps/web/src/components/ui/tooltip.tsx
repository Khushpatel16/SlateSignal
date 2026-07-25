"use client";

import * as TooltipPrimitive from "@radix-ui/react-tooltip";

export function Tooltip({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          sideOffset={8}
          className="z-50 rounded-[4px] border border-[var(--line)] bg-[var(--surface-strong)] px-2.5 py-1.5 text-xs text-[var(--ink)] shadow-xl"
        >
          {label}
          <TooltipPrimitive.Arrow className="fill-[var(--surface-strong)]" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
