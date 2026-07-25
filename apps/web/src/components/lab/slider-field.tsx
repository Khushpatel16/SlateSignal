"use client";

import * as Slider from "@radix-ui/react-slider";

import { formatMoney } from "@/lib/format";

export function SliderField({
  label,
  value,
  min,
  max,
  step,
  onChange,
  format = "number",
  description,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  format?: "number" | "money" | "score";
  description?: string;
}) {
  const display =
    format === "money"
      ? formatMoney(value)
      : format === "score"
        ? `${value}/100`
        : value.toLocaleString();

  return (
    <label className="block">
      <span className="flex items-center justify-between gap-3">
        <span className="text-xs font-bold text-[var(--muted-strong)]">
          {label}
        </span>
        <span className="tabular text-xs font-extrabold text-white">
          {display}
        </span>
      </span>
      <Slider.Root
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([next]) => onChange(next)}
        className="relative mt-3 flex h-5 w-full touch-none items-center"
      >
        <Slider.Track className="relative h-1 grow bg-[var(--surface-soft)]">
          <Slider.Range className="absolute h-full bg-[var(--signal)]" />
        </Slider.Track>
        <Slider.Thumb
          aria-label={label}
          className="block size-4 border-2 border-[var(--signal)] bg-[var(--canvas)] shadow-sm transition-transform hover:scale-110"
        />
      </Slider.Root>
      {description && (
        <span className="mt-1 block text-[10px] leading-4 text-[var(--muted)]">
          {description}
        </span>
      )}
    </label>
  );
}
