import type { Metadata } from "next";

import { MovieReport } from "@/components/movies/movie-report";

export const metadata: Metadata = {
  title: "Film Forecast Report",
  description:
    "A source-backed, ledger-locked box-office forecast with uncertainty, evidence, and model limitations.",
};

export default async function MoviePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <MovieReport slug={slug} />;
}
