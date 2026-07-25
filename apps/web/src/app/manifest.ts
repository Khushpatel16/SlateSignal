import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SlateSignal",
    short_name: "SlateSignal",
    description:
      "Box-office forecasting, package optimization, and release intelligence.",
    start_url: "/",
    display: "standalone",
    background_color: "#0c0c0d",
    theme_color: "#f0c94c",
    icons: [
      {
        src: "/favicon.ico",
        sizes: "any",
        type: "image/x-icon",
      },
    ],
  };
}
