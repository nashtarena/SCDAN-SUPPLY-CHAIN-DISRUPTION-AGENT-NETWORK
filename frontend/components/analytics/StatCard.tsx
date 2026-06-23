"use client";

interface Props {
  label: string;
  value: number | string;
  color?: string;
}

export default function StatCard({ label, value, color = "text-white" }: Props) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${color}`}>{value}</p>
    </div>
  );
}
