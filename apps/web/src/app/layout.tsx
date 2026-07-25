import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "@/components/providers";

import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "SlateSignal | Film decision intelligence",
    template: "%s | SlateSignal",
  },
  description:
    "Bias-aware box-office forecasting, counterfactual greenlight simulation, and release-window intelligence.",
  applicationName: "SlateSignal",
  icons: {
    icon: "/slatesignal-mark.svg",
    shortcut: "/slatesignal-mark.svg",
    apple: "/slatesignal-mark.svg",
  },
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    title: "SlateSignal | Film decision intelligence",
    description:
      "Uncertainty-aware box-office forecasting, package optimization, and release-window intelligence.",
    type: "website",
    images: ["/films/dune-part-three-wide.jpg"],
  },
  twitter: {
    card: "summary_large_image",
    title: "SlateSignal | Film decision intelligence",
    description:
      "Uncertainty-aware box-office forecasting and greenlight simulation.",
    images: ["/films/dune-part-three-wide.jpg"],
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#0c0c0d",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning data-scroll-behavior="smooth">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
