"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";

type Status = "checking" | "ok" | "error";

export function HealthIndicator() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    let mounted = true;
    api
      .health()
      .then(() => mounted && setStatus("ok"))
      .catch(() => mounted && setStatus("error"));
    return () => {
      mounted = false;
    };
  }, []);

  const colors: Record<Status, string> = {
    checking: "bg-yellow-400",
    ok: "bg-green-500",
    error: "bg-red-500",
  };

  const labels: Record<Status, string> = {
    checking: "Checking backend...",
    ok: "Backend connected",
    error: "Backend unavailable",
  };

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className={`inline-block h-2 w-2 rounded-full ${colors[status]}`} />
      {labels[status]}
    </div>
  );
}
