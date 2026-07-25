import type { Metadata } from "next";

import { SavedWorkspace } from "@/components/saved/saved-workspace";

export const metadata: Metadata = {
  title: "Saved work",
};

export default function SavedPage() {
  return <SavedWorkspace />;
}
