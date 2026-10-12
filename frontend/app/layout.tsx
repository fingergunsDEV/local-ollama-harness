import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Local Agent Harness",
  description: "A local-only, approval-gated Ollama workspace agent",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
