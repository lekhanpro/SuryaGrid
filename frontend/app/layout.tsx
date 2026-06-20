import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

export const metadata = { title: "Suryagrid AI - Solar DSM Monitoring", description: "Solar Nowcasting & DSM Penalty Prediction System" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen flex">
        <Sidebar />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </body>
    </html>
  );
}
