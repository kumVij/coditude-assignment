import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "People Search & Reachout",
  description: "Paste a JD, source candidates, and reach out via Hunar.AI Voice Agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 antialiased">
        <div className="mx-auto max-w-5xl px-4 py-8">{children}</div>
      </body>
    </html>
  );
}
