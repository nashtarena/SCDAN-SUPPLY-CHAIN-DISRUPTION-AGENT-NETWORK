"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";

export default function Navbar() {
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <nav className="flex items-center justify-between border-b border-border bg-surface px-6 py-4">
      <Link href="/dashboard" className="text-base font-semibold text-white">
        SCDAN
      </Link>
      <button
        onClick={handleLogout}
        className="rounded-md border border-border px-3 py-1.5 text-sm text-gray-300 transition hover:bg-background"
      >
        Log out
      </button>
    </nav>
  );
}
