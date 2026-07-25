"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Bookmark,
  CalendarDays,
  ChevronDown,
  Clapperboard,
  FlaskConical,
  GitCompareArrows,
  LayoutDashboard,
  LineChart,
  LockKeyhole,
  LogOut,
  Microscope,
  Search,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { CommandMenu } from "@/components/layout/command-menu";
import { Tooltip } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import { classNames } from "@/lib/format";
import type { User } from "@/types/domain";

const navigation = [
  {
    href: "/",
    label: "Forecast desk",
    mobileLabel: "Forecast",
    icon: LayoutDashboard,
  },
  {
    href: "/calendar",
    label: "Release calendar",
    mobileLabel: "Calendar",
    icon: CalendarDays,
  },
  {
    href: "/compare",
    label: "Collision compare",
    mobileLabel: "Compare",
    icon: GitCompareArrows,
  },
  {
    href: "/backtests",
    label: "Locked backtests",
    mobileLabel: "Backtests",
    icon: LineChart,
  },
  {
    href: "/research",
    label: "Research",
    mobileLabel: "Research",
    icon: Microscope,
  },
  {
    href: "/lab",
    label: "Scenario lab",
    mobileLabel: "Lab",
    icon: FlaskConical,
  },
];

const mobileNavigation = navigation.filter((item) =>
  ["/", "/calendar", "/compare", "/backtests", "/lab"].includes(item.href),
);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [engineOnline, setEngineOnline] = useState<boolean | null>(null);
  const [previewJoined, setPreviewJoined] = useState(false);
  const active =
    navigation.find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
    ) ?? navigation[0];

  useEffect(() => {
    let activeRequest = true;
    api
      .health()
      .then((health) => {
        if (activeRequest) setEngineOnline(health.status === "ok");
      })
      .catch(() => {
        if (activeRequest) setEngineOnline(false);
      });
    api
      .session()
      .then((account) => {
        if (activeRequest) setUser(account);
      })
      .catch(() => {
        if (activeRequest) setUser(null);
      });
    const joined =
      window.localStorage.getItem("slatesignal:preview") === "joined";
    queueMicrotask(() => {
      if (activeRequest) setPreviewJoined(joined);
    });
    return () => {
      activeRequest = false;
    };
  }, [pathname]);

  async function logout() {
    try {
      await api.logout();
      setUser(null);
      toast.success("Signed out");
      router.push("/");
      router.refresh();
    } catch {
      toast.error("Could not sign out");
    }
  }

  function joinPreview() {
    window.localStorage.setItem("slatesignal:preview", "joined");
    setPreviewJoined(true);
    toast.success("Preview access noted for this browser");
  }

  return (
    <div className="min-h-screen bg-[var(--canvas)]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[var(--sidebar)] border-r border-[var(--line-soft)] bg-[var(--canvas-raised)] lg:flex lg:flex-col">
        <div className="flex h-[var(--topbar)] items-center border-b border-[var(--line-soft)] px-5">
          <Link href="/" className="flex items-center gap-3">
            <span className="grid size-8 place-items-center bg-[var(--signal)] text-black">
              <Clapperboard size={18} strokeWidth={2.2} />
            </span>
            <span>
              <span className="block text-sm font-extrabold text-white">
                SlateSignal
              </span>
              <span className="block text-[10px] font-semibold text-[var(--muted)] uppercase">
                Decision intelligence
              </span>
            </span>
          </Link>
        </div>

        <nav aria-label="Primary" className="flex-1 px-3 py-4">
          <p className="px-3 pb-2 text-[10px] font-bold text-[#77756f] uppercase">
            Workspace
          </p>
          <div className="space-y-1">
            {navigation.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={classNames(
                    "flex h-10 items-center gap-3 border-l-2 px-3 text-sm transition-colors",
                    isActive
                      ? "border-[var(--signal)] bg-[var(--surface)] font-semibold text-white"
                      : "border-transparent text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white",
                  )}
                >
                  <Icon size={17} />
                  {item.label}
                </Link>
              );
            })}
          </div>

          <p className="mt-7 px-3 pb-2 text-[10px] font-bold text-[#77756f] uppercase">
            Operations
          </p>
          <Link
            href="/admin"
            className={classNames(
              "flex h-10 items-center gap-3 border-l-2 px-3 text-sm transition-colors",
              pathname.startsWith("/admin")
                ? "border-[var(--signal)] bg-[var(--surface)] font-semibold text-white"
                : "border-transparent text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white",
            )}
          >
            <BarChart3 size={17} />
            Admin
          </Link>
        </nav>

        <div className="m-3 border border-[var(--line)] bg-[var(--surface)] p-3">
          <div className="flex items-center gap-2 text-xs font-bold text-white">
            <LockKeyhole size={14} className="text-[var(--signal)]" />
            Pro preview
          </div>
          <p className="mt-2 text-[11px] leading-4 text-[var(--muted)]">
            PDF exports, team slates, and live market feeds are staged for the
            paid tier.
          </p>
          <button
            type="button"
            onClick={joinPreview}
            disabled={previewJoined}
            className="mt-3 h-8 w-full border border-[var(--line)] text-[11px] font-bold text-[var(--muted-strong)] hover:bg-[var(--surface-soft)]"
          >
            {previewJoined ? "Preview joined" : "Join preview"}
          </button>
        </div>

        <div className="flex h-14 items-center gap-3 border-t border-[var(--line-soft)] px-5">
          <span
            className={classNames(
              "size-2",
              engineOnline === null
                ? "bg-[var(--muted)]"
                : engineOnline
                  ? "bg-[var(--positive)]"
                  : "bg-[var(--negative)]",
            )}
            aria-hidden="true"
          />
          <span className="text-[11px] text-[var(--muted)]">
            {engineOnline === null
              ? "Checking decision engine"
              : engineOnline
                ? "Decision engine online"
                : "Decision engine offline"}
          </span>
        </div>
      </aside>

      <header className="fixed inset-x-0 top-0 z-30 flex h-[var(--topbar)] items-center border-b border-[var(--line-soft)] bg-[rgba(12,12,13,0.92)] px-4 backdrop-blur-xl lg:left-[var(--sidebar)] lg:px-6">
        <Link href="/" className="mr-3 flex items-center gap-2 lg:hidden">
          <span className="grid size-8 place-items-center bg-[var(--signal)] text-black">
            <Clapperboard size={18} />
          </span>
          <span className="text-sm font-extrabold text-white">SlateSignal</span>
        </Link>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-white">
            {active.label}
          </p>
          <p className="hidden text-[11px] text-[var(--muted)] sm:block">
            Worldwide theatrical forecast
          </p>
        </div>

        <div className="ml-auto flex items-center gap-1.5">
          <Tooltip label="Search projects and titles">
            <button
              type="button"
              aria-label="Search"
              onClick={() => setSearchOpen(true)}
              className="grid size-9 place-items-center border border-transparent text-[var(--muted)] hover:border-[var(--line)] hover:bg-[var(--surface)] hover:text-white"
            >
              <Search size={17} />
            </button>
          </Tooltip>
          {user ? (
            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button
                  type="button"
                  aria-label="Open account menu"
                  className="ml-1 flex h-9 items-center gap-2 border border-[var(--line)] bg-[var(--surface)] px-2 text-[var(--muted)] hover:text-white"
                >
                  <span className="grid size-5 place-items-center bg-[var(--signal)] text-[9px] font-extrabold text-black">
                    {user.display_name.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="hidden max-w-28 truncate text-xs font-bold sm:block">
                    {user.display_name}
                  </span>
                  <ChevronDown size={13} />
                </button>
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  align="end"
                  sideOffset={8}
                  className="z-50 min-w-56 border border-[var(--line)] bg-[var(--canvas-raised)] p-1 shadow-2xl"
                >
                  <div className="border-b border-[var(--line)] px-3 py-2.5">
                    <p className="truncate text-xs font-bold text-white">
                      {user.display_name}
                    </p>
                    <p className="mt-0.5 truncate text-[10px] text-[var(--muted)]">
                      {user.email}
                    </p>
                  </div>
                  <DropdownMenu.Item asChild>
                    <Link
                      href="/saved"
                      className="flex h-9 cursor-pointer items-center gap-2 px-3 text-xs text-[var(--muted)] outline-none hover:bg-[var(--surface)] hover:text-white"
                    >
                      <Bookmark size={14} />
                      Saved work
                    </Link>
                  </DropdownMenu.Item>
                  {user.role === "admin" && (
                    <DropdownMenu.Item asChild>
                      <Link
                        href="/admin"
                        className="flex h-9 cursor-pointer items-center gap-2 px-3 text-xs text-[var(--muted)] outline-none hover:bg-[var(--surface)] hover:text-white"
                      >
                        <BarChart3 size={14} />
                        Admin
                      </Link>
                    </DropdownMenu.Item>
                  )}
                  <DropdownMenu.Item
                    onSelect={logout}
                    className="flex h-9 cursor-pointer items-center gap-2 px-3 text-xs text-[var(--muted)] outline-none hover:bg-[var(--surface)] hover:text-white"
                  >
                    <LogOut size={14} />
                    Sign out
                  </DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          ) : (
            <Tooltip label="Sign in">
              <Link
                href="/login"
                aria-label="Sign in"
                className="ml-1 grid size-9 place-items-center border border-[var(--line)] bg-[var(--surface)] text-[var(--muted)] hover:text-white"
              >
                <UserRound size={17} />
              </Link>
            </Tooltip>
          )}
        </div>
      </header>

      <main className="min-h-screen pt-[var(--topbar)] pb-20 lg:ml-[var(--sidebar)] lg:pb-0">
        {children}
      </main>

      <nav
        aria-label="Mobile navigation"
        className="fixed inset-x-0 bottom-0 z-40 grid h-16 grid-cols-5 border-t border-[var(--line)] bg-[rgba(12,12,13,0.96)] backdrop-blur-xl lg:hidden"
      >
        {mobileNavigation.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-label={item.label}
              className={classNames(
                "flex flex-col items-center justify-center gap-1 text-[9px]",
                isActive ? "text-[var(--signal)]" : "text-[var(--muted)]",
              )}
            >
              <Icon size={18} />
              <span className="px-1">{item.mobileLabel}</span>
            </Link>
          );
        })}
      </nav>

      <CommandMenu open={searchOpen} onOpenChange={setSearchOpen} />
    </div>
  );
}
