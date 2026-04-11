import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AutoApply Pro — AI Job Application Engine",
  description: "Autonomous AI-powered job application platform. Apply to hundreds of jobs and send cold emails on autopilot.",
  keywords: ["job automation", "AI job search", "auto apply", "LinkedIn automation"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en" className={inter.variable}>
        <body className="bg-[#080B14] text-white antialiased">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
