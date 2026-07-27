import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adaptive Assessment",
  description: "Adaptive competency assessment platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white dark:bg-neutral-950 text-gray-900 dark:text-gray-100 min-h-screen">
  {children}
</body>
    </html>
  );
}