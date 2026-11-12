import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IPL Intelligence | Cricket, decoded.",
  description: "A modern IPL analytics and player intelligence platform.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
