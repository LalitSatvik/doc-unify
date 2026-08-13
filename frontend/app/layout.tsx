import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "doc-unify",
  description: "Unify messy documents into one structured, provenance-backed table.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
