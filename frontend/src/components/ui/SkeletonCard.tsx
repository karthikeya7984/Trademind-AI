"use client";
import { cn } from "@/lib/utils";

interface Props {
  className?: string;
  lines?: number;
}

export default function SkeletonCard({ className, lines = 3 }: Props) {
  return (
    <div className={cn("glass rounded-xl p-4 animate-pulse", className)}>
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className={cn("bg-muted rounded-lg h-4", i === 0 ? "w-3/4" : i === lines - 1 ? "w-1/2" : "w-full")} />
        ))}
      </div>
    </div>
  );
}
