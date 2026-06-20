import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

export const metadata = { title: "SuryaGrid AI - Solar DSM Intelligence", description: "Solar Nowcasting & DSM Penalty Prediction System" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen flex">
        <Sidebar />
        <main className="flex-1 p-8 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
