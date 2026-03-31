import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WareFlow — Warehouse Management",
  description: "Self-hosted warehouse management system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
