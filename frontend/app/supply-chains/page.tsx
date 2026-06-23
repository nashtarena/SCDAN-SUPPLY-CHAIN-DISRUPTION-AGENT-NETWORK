"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// /supply-chains without an id just bounces to the dashboard
// which already lists supply chains.
export default function SupplyChainsRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard"); }, [router]);
  return null;
}
