"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/predictions", label: "Scenario Analysis" },
  { href: "/timeline", label: "Generation Timeline" },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-60 bg-gray-900 text-white min-h-screen p-5 flex flex-col">
      <div className="mb-8">
        <div className="text-xl font-bold text-yellow-400">Suryagrid AI</div>
        <div className="text-xs text-gray-400 mt-1">Solar DSM Monitoring</div>
      </div>
      <nav className="flex flex-col gap-1">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={`px-3 py-2 rounded text-sm ${pathname === l.href ? "bg-blue-600 font-medium" : "hover:bg-gray-700 text-gray-300"}`}
          >
            {l.label}
          </Link>
        ))}
      </nav>
      <div className="mt-auto text-xs text-gray-500 pt-6 border-t border-gray-700">
        Phase 1 &middot; Synthetic Data Mode
      </div>
    </aside>
  );
}
