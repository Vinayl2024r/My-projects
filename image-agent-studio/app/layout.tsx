import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cinematic Multi-Agent Image Studio",
  description:
    "Upload a reference asset, describe your idea, and let cooperating AI agents generate and self-critique a cinematic creative until it scores well.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
