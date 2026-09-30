import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Temporal Trust Graph",
  description: "Make knowledge reliability visible and explainable.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
