"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";

const NAV_LINKS = [
  { href: "/dashboard",  label: "Supply Chains" },
  { href: "/analytics",  label: "Analytics" },
];

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <nav className="flex items-center justify-between border-b border-border bg-surface px-6 py-3">
      <div className="flex items-center gap-6">
        <Link href="/dashboard" className="text-sm font-semibold text-white">
          SCDAN
        </Link>
        <div className="flex gap-1">
          {NAV_LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-md px-3 py-1.5 text-sm transition ${
                  active
                    ? "bg-white/10 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>
      <button
        onClick={() => { clearToken(); router.push("/login"); }}
        className="rounded-md border border-border px-3 py-1.5 text-sm text-gray-400 transition hover:text-white"
      >
        Log out
      </button>
    </nav>
  );
}
