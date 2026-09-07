import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Hiring Assistant",
  description: "Voice-AI powered candidate screening, built on Hunar.AI Voice Agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">{children}</div>
      </body>
    </html>
  );
}
