"use client";

import { useState } from "react";
import { CalendarRange, Check, Megaphone, UsersRound } from "lucide-react";

import { SliderField } from "@/components/lab/slider-field";
import { classNames } from "@/lib/format";
import {
  GENRES,
  PREMIUM_FORMATS,
  type AudienceRating,
  type ForecastRequest,
  type Genre,
  type PremiumFormat,
  type SourceMaterial,
} from "@/types/domain";

const SOURCE_OPTIONS: SourceMaterial[] = [
  "Original",
  "Book",
  "Comic / graphic novel",
  "Video game",
  "True story",
  "Sequel",
  "Remake",
  "Toy / brand",
];

const RATING_OPTIONS: AudienceRating[] = [
  "G",
  "PG",
  "PG-13",
  "R",
  "NC-17",
  "Not rated",
];

type Section = "package" | "release" | "demand";

export function ForecastForm({
  value,
  onChange,
}: {
  value: ForecastRequest;
  onChange: (value: ForecastRequest) => void;
}) {
  const [section, setSection] = useState<Section>("package");

  function update<K extends keyof ForecastRequest>(
    key: K,
    next: ForecastRequest[K],
  ) {
    onChange({ ...value, [key]: next });
  }

  function toggleGenre(genre: Genre) {
    const hasGenre = value.genres.includes(genre);
    if (hasGenre && value.genres.length > 1) {
      update(
        "genres",
        value.genres.filter((item) => item !== genre),
      );
      return;
    }
    if (!hasGenre && value.genres.length < 4) {
      update("genres", [...value.genres, genre]);
    }
  }

  function toggleFormat(format: PremiumFormat) {
    const hasFormat = value.premium_formats.includes(format);
    if (hasFormat && value.premium_formats.length > 1) {
      update(
        "premium_formats",
        value.premium_formats.filter((item) => item !== format),
      );
      return;
    }
    if (!hasFormat) {
      update("premium_formats", [...value.premium_formats, format]);
    }
  }

  return (
    <div>
      <section className="border-b border-[var(--line)] p-5">
        <label className="block">
          <span className="text-[10px] font-bold text-[var(--muted)] uppercase">
            Working title
          </span>
          <input
            value={value.title}
            onChange={(event) => update("title", event.target.value)}
            maxLength={160}
            placeholder="Untitled project"
            className="mt-2 h-11 w-full border border-[var(--line)] bg-[var(--canvas-raised)] px-3 text-sm font-bold text-white placeholder:text-[#666] focus:border-[var(--signal)] focus:outline-none"
          />
        </label>

        <label className="mt-5 block">
          <span className="flex justify-between gap-3">
            <span className="text-[10px] font-bold text-[var(--muted)] uppercase">
              Synopsis
            </span>
            <span className="tabular text-[10px] text-[var(--muted)]">
              {value.synopsis.length}/5,000
            </span>
          </span>
          <textarea
            value={value.synopsis}
            onChange={(event) => update("synopsis", event.target.value)}
            minLength={40}
            maxLength={5000}
            rows={7}
            placeholder="Who wants what, what stands in their way, and what happens if they fail?"
            className="mt-2 w-full resize-y border border-[var(--line)] bg-[var(--canvas-raised)] p-3 text-sm leading-6 text-white placeholder:text-[#666] focus:border-[var(--signal)] focus:outline-none"
          />
        </label>

        <div className="mt-5">
          <div className="flex justify-between gap-3">
            <p className="text-[10px] font-bold text-[var(--muted)] uppercase">
              Genre mix
            </p>
            <p className="text-[10px] text-[var(--muted)]">Choose 1–4</p>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {GENRES.map((genre) => {
              const selected = value.genres.includes(genre);
              return (
                <button
                  key={genre}
                  type="button"
                  onClick={() => toggleGenre(genre)}
                  aria-pressed={selected}
                  className={classNames(
                    "h-8 border px-2.5 text-[11px] font-bold transition-colors",
                    selected
                      ? "border-[var(--signal)] bg-[rgba(240,201,76,0.12)] text-[var(--signal)]"
                      : "border-[var(--line)] text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white",
                  )}
                >
                  {genre}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-3 border-b border-[var(--line)]">
        <SectionButton
          label="Package"
          icon={<UsersRound size={14} />}
          active={section === "package"}
          onClick={() => setSection("package")}
        />
        <SectionButton
          label="Release"
          icon={<CalendarRange size={14} />}
          active={section === "release"}
          onClick={() => setSection("release")}
        />
        <SectionButton
          label="Demand"
          icon={<Megaphone size={14} />}
          active={section === "demand"}
          onClick={() => setSection("demand")}
        />
      </div>

      <section className="space-y-6 p-5">
        {section === "package" && (
          <>
            <SliderField
              label="Production budget"
              value={value.budget}
              min={500_000}
              max={350_000_000}
              step={500_000}
              format="money"
              onChange={(next) => update("budget", next)}
            />
            <SliderField
              label="Marketing budget"
              value={value.marketing_budget}
              min={0}
              max={250_000_000}
              step={500_000}
              format="money"
              onChange={(next) => update("marketing_budget", next)}
            />

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
              <TextField
                label="Director"
                value={value.director ?? ""}
                placeholder="Search or enter name"
                onChange={(next) => update("director", next || null)}
              />
              <TextField
                label="Studio"
                value={value.studio ?? ""}
                placeholder="Studio or distributor"
                onChange={(next) => update("studio", next || null)}
              />
            </div>

            <TextField
              label="Top-billed cast"
              value={value.cast.join(", ")}
              placeholder="Separate names with commas"
              onChange={(next) =>
                update(
                  "cast",
                  next
                    .split(",")
                    .map((name) => name.trim())
                    .filter(Boolean)
                    .slice(0, 8),
                )
              }
            />

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
              <SelectField
                label="Source material"
                value={value.source_material}
                options={SOURCE_OPTIONS}
                onChange={(next) =>
                  update("source_material", next as SourceMaterial)
                }
              />
              <SelectField
                label="Audience rating"
                value={value.audience_rating}
                options={RATING_OPTIONS}
                onChange={(next) =>
                  update("audience_rating", next as AudienceRating)
                }
              />
            </div>

            <SliderField
              label="Franchise / IP strength"
              value={value.franchise_strength}
              min={0}
              max={100}
              step={1}
              format="score"
              onChange={(next) => update("franchise_strength", next)}
              description="Use 0 for an unknown original and reserve 80+ for globally established IP."
            />
            <SliderField
              label="Runtime"
              value={value.runtime_minutes}
              min={70}
              max={210}
              step={1}
              onChange={(next) => update("runtime_minutes", next)}
            />
          </>
        )}

        {section === "release" && (
          <>
            <label className="block">
              <span className="text-xs font-bold text-[var(--muted-strong)]">
                Release date
              </span>
              <input
                type="date"
                value={value.release_date}
                onChange={(event) => update("release_date", event.target.value)}
                className="mt-2 h-11 w-full border border-[var(--line)] bg-[var(--canvas-raised)] px-3 text-sm text-white focus:border-[var(--signal)] focus:outline-none"
              />
            </label>

            <div>
              <p className="text-xs font-bold text-[var(--muted-strong)]">
                Release formats
              </p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {PREMIUM_FORMATS.map((format) => {
                  const selected = value.premium_formats.includes(format);
                  return (
                    <button
                      key={format}
                      type="button"
                      onClick={() => toggleFormat(format)}
                      aria-pressed={selected}
                      className={classNames(
                        "flex h-10 items-center gap-2 border px-3 text-left text-xs font-bold",
                        selected
                          ? "border-[var(--signal)] bg-[rgba(240,201,76,0.09)] text-white"
                          : "border-[var(--line)] text-[var(--muted)] hover:bg-[var(--surface)]",
                      )}
                    >
                      <span
                        className={classNames(
                          "grid size-4 place-items-center border",
                          selected
                            ? "border-[var(--signal)] bg-[var(--signal)] text-black"
                            : "border-[var(--line)]",
                        )}
                      >
                        {selected && <Check size={11} strokeWidth={3} />}
                      </span>
                      {format}
                    </button>
                  );
                })}
              </div>
            </div>

            <SliderField
              label="Opening theater count"
              value={value.theater_count}
              min={50}
              max={5500}
              step={50}
              onChange={(next) => update("theater_count", next)}
            />
            <SliderField
              label="Competition pressure"
              value={value.competition_score}
              min={0}
              max={100}
              step={1}
              format="score"
              onChange={(next) => update("competition_score", next)}
              description="Higher values mean more direct audience and screen competition."
            />
          </>
        )}

        {section === "demand" && (
          <>
            <SliderField
              label="Social awareness"
              value={value.social_buzz}
              min={0}
              max={100}
              step={1}
              format="score"
              onChange={(next) => update("social_buzz", next)}
            />
            <SliderField
              label="Trailer engagement"
              value={value.trailer_engagement}
              min={0}
              max={100}
              step={1}
              format="score"
              onChange={(next) => update("trailer_engagement", next)}
              description="Quality of response, separated from total reach."
            />
            <SliderField
              label="International appeal"
              value={value.international_appeal}
              min={0}
              max={100}
              step={1}
              format="score"
              onChange={(next) => update("international_appeal", next)}
            />
            <SliderField
              label="Production readiness"
              value={value.production_readiness}
              min={0}
              max={100}
              step={1}
              format="score"
              onChange={(next) => update("production_readiness", next)}
              description="Package confidence, schedule health, and execution risk."
            />
          </>
        )}
      </section>
    </div>
  );
}

function SectionButton({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={classNames(
        "flex h-11 items-center justify-center gap-2 border-r border-[var(--line)] text-[11px] font-bold last:border-r-0",
        active
          ? "bg-[var(--surface)] text-white"
          : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function TextField({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs font-bold text-[var(--muted-strong)]">
        {label}
      </span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-2 h-10 w-full border border-[var(--line)] bg-[var(--canvas-raised)] px-3 text-xs text-white placeholder:text-[#666] focus:border-[var(--signal)] focus:outline-none"
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-xs font-bold text-[var(--muted-strong)]">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 h-10 w-full border border-[var(--line)] bg-[var(--canvas-raised)] px-3 text-xs text-white focus:border-[var(--signal)] focus:outline-none"
      >
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}
