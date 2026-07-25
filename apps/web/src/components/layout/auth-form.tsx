"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { CircleAlert, Clapperboard, LoaderCircle } from "lucide-react";

import { api, ApiError } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (mode === "signup") {
        await api.register({
          display_name: name,
          email,
          password,
        });
      } else {
        await api.login({ email, password });
      }
      router.push("/");
      router.refresh();
    } catch (submissionError) {
      setError(
        submissionError instanceof ApiError
          ? submissionError.message
          : "The request could not be completed.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-var(--topbar)-64px)] place-items-center px-5 py-12 lg:min-h-[calc(100vh-var(--topbar))]">
      <div className="w-full max-w-[400px]">
        <span className="grid size-10 place-items-center bg-[var(--signal)] text-black">
          <Clapperboard size={20} />
        </span>
        <p className="mt-6 text-[10px] font-bold text-[var(--signal)] uppercase">
          SlateSignal account
        </p>
        <h1 className="font-editorial mt-2 text-4xl font-semibold text-white">
          {mode === "login" ? "Return to your slate." : "Start a decision log."}
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
          {mode === "login"
            ? "Sign in to access saved forecasts and package comparisons."
            : "Create an account to save forecasts, optimizer plans, and release scenarios."}
        </p>

        <form onSubmit={submit} className="mt-8 space-y-4">
          {mode === "signup" && (
            <Field
              label="Display name"
              type="text"
              value={name}
              onChange={setName}
              autoComplete="name"
            />
          )}
          <Field
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            autoComplete="email"
          />
          <Field
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            autoComplete={
              mode === "login" ? "current-password" : "new-password"
            }
          />
          {mode === "signup" && (
            <p className="text-[10px] leading-4 text-[var(--muted)]">
              Use at least 10 characters. Passwords are hashed with Argon2 and
              never stored in plain text.
            </p>
          )}

          {error && (
            <p className="flex items-start gap-2 border-l-2 border-[var(--negative)] bg-[var(--surface)] p-3 text-xs leading-5 text-[var(--negative)]">
              <CircleAlert size={15} className="mt-0.5 shrink-0" />
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={pending}
            className="flex h-11 w-full items-center justify-center gap-2 bg-[var(--signal)] text-sm font-extrabold text-black hover:bg-[var(--signal-strong)] disabled:cursor-wait disabled:opacity-70"
          >
            {pending && <LoaderCircle size={16} className="animate-spin" />}
            {mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-xs text-[var(--muted)]">
          {mode === "login"
            ? "New to SlateSignal?"
            : "Already have an account?"}{" "}
          <Link
            href={mode === "login" ? "/signup" : "/login"}
            className="font-bold text-[var(--signal)] hover:text-[var(--signal-strong)]"
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </Link>
        </p>
      </div>
    </div>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  autoComplete,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-bold text-[var(--muted-strong)]">
        {label}
      </span>
      <input
        required
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        minLength={type === "password" ? 10 : undefined}
        className="mt-2 h-11 w-full border border-[var(--line)] bg-[var(--canvas-raised)] px-3 text-sm text-white focus:border-[var(--signal)] focus:outline-none"
      />
    </label>
  );
}
