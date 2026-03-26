"use client";

import { useCallback, useEffect, useState } from "react";
import { api, OpsSummary, RunRecord } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Summary cards
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold tabular-nums">{value}</p>
        {sub && <p className="text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

function SummaryCards({ summary }: { summary: OpsSummary }) {
  const cacheRate =
    summary.total_runs > 0
      ? ((summary.cache_hits / summary.total_runs) * 100).toFixed(0)
      : "—";

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatCard
        label="Total runs"
        value={summary.total_runs}
        sub={`${summary.completed} ok / ${summary.failed} failed`}
      />
      <StatCard label="Cache hit rate" value={`${cacheRate}%`} />
      <StatCard
        label="Avg latency"
        value={
          summary.avg_duration_ms != null
            ? `${summary.avg_duration_ms.toFixed(0)} ms`
            : "—"
        }
        sub={
          summary.max_duration_ms != null
            ? `max ${summary.max_duration_ms.toFixed(0)} ms`
            : undefined
        }
      />
      <StatCard
        label="Total spend"
        value={`$${summary.total_spent_usd.toFixed(4)}`}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workflow breakdown table
// ---------------------------------------------------------------------------

function WorkflowTable({ summary }: { summary: OpsSummary }) {
  if (summary.by_workflow.length === 0) return null;
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">By workflow</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="px-4 py-2">Workflow</th>
              <th className="px-4 py-2 text-right">Runs</th>
              <th className="px-4 py-2 text-right">Avg latency</th>
            </tr>
          </thead>
          <tbody>
            {summary.by_workflow.map((wf) => (
              <tr key={wf.workflow} className="border-b last:border-0">
                <td className="px-4 py-2 font-mono text-xs">{wf.workflow}</td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {wf.count}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {wf.avg_duration_ms != null
                    ? `${Number(wf.avg_duration_ms).toFixed(0)} ms`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Filter bar
// ---------------------------------------------------------------------------

const WORKFLOW_OPTIONS = [
  "",
  "search",
  "answer",
  "research",
  "find-similar",
  "structured-search",
];
const MODE_OPTIONS = ["", "smoke", "live", "auto"];
const STATUS_OPTIONS = ["", "completed", "failed", "pending"];

function FilterBar({
  filters,
  onChange,
}: {
  filters: { workflow: string; mode: string; status: string };
  onChange: (f: { workflow: string; mode: string; status: string }) => void;
}) {
  return (
    <div className="flex flex-wrap gap-3 text-sm">
      <label className="flex items-center gap-1.5">
        <span className="text-xs text-muted-foreground">Workflow</span>
        <select
          className="rounded border bg-background px-2 py-1 text-sm"
          value={filters.workflow}
          onChange={(e) => onChange({ ...filters, workflow: e.target.value })}
        >
          {WORKFLOW_OPTIONS.map((w) => (
            <option key={w} value={w}>
              {w || "All"}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-1.5">
        <span className="text-xs text-muted-foreground">Mode</span>
        <select
          className="rounded border bg-background px-2 py-1 text-sm"
          value={filters.mode}
          onChange={(e) => onChange({ ...filters, mode: e.target.value })}
        >
          {MODE_OPTIONS.map((m) => (
            <option key={m} value={m}>
              {m || "All"}
            </option>
          ))}
        </select>
      </label>
      <label className="flex items-center gap-1.5">
        <span className="text-xs text-muted-foreground">Status</span>
        <select
          className="rounded border bg-background px-2 py-1 text-sm"
          value={filters.status}
          onChange={(e) => onChange({ ...filters, status: e.target.value })}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s || "All"}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Run detail drawer
// ---------------------------------------------------------------------------

function RunDetail({
  run,
  onClose,
}: {
  run: RunRecord;
  onClose: () => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">
            Run <span className="font-mono">{run.id}</span>
          </CardTitle>
          <button
            onClick={onClose}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            close
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-2 text-xs">
          <Field label="Workflow" value={run.workflow} />
          <Field label="Mode" value={run.mode} />
          <Field label="Status" value={run.status} />
          <Field
            label="Duration"
            value={
              run.duration_ms != null ? `${run.duration_ms.toFixed(0)} ms` : "—"
            }
          />
          <Field label="Run ID" value={run.run_id || "—"} mono />
          <Field label="Request ID" value={run.request_id || "—"} mono />
          <Field
            label="Cache hit"
            value={run.cache_hit != null ? String(run.cache_hit) : "—"}
          />
          <Field label="Artifacts" value={String(run.artifact_count)} />
          <Field
            label="Started"
            value={run.started_at ? formatTime(run.started_at) : "—"}
          />
          <Field
            label="Completed"
            value={run.completed_at ? formatTime(run.completed_at) : "—"}
          />
        </div>
        {run.query_preview && (
          <div>
            <p className="text-xs text-muted-foreground">Query</p>
            <p className="text-xs font-mono break-all">{run.query_preview}</p>
          </div>
        )}
        {run.error_message && (
          <div className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-800">
            {run.error_message}
          </div>
        )}
        {run.cost_summary && (
          <div>
            <p className="text-xs text-muted-foreground">Cost summary</p>
            <pre className="text-xs font-mono bg-muted rounded p-2 overflow-x-auto">
              {JSON.stringify(run.cost_summary, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <p className="text-muted-foreground">{label}</p>
      <p className={cn(mono && "font-mono")}>{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Runs table
// ---------------------------------------------------------------------------

function RunsTable({
  runs,
  selectedId,
  onSelect,
}: {
  runs: RunRecord[];
  selectedId: string | null;
  onSelect: (run: RunRecord) => void;
}) {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        No runs found.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-xs text-muted-foreground">
            <th className="px-3 py-2">Time</th>
            <th className="px-3 py-2">Workflow</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2 text-right">Latency</th>
            <th className="px-3 py-2">Query</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr
              key={run.id}
              onClick={() => onSelect(run)}
              className={cn(
                "border-b last:border-0 cursor-pointer transition-colors",
                selectedId === run.id
                  ? "bg-muted"
                  : "hover:bg-muted/50"
              )}
            >
              <td className="px-3 py-2 text-xs tabular-nums whitespace-nowrap">
                {run.started_at ? formatTime(run.started_at) : "—"}
              </td>
              <td className="px-3 py-2 font-mono text-xs">{run.workflow}</td>
              <td className="px-3 py-2">
                <StatusBadge status={run.status} />
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-xs">
                {run.duration_ms != null
                  ? `${run.duration_ms.toFixed(0)} ms`
                  : "—"}
              </td>
              <td className="px-3 py-2 text-xs truncate max-w-[200px]">
                {run.query_preview || "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    pending: "bg-yellow-100 text-yellow-800",
  };
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-xs font-medium",
        styles[status] || "bg-muted text-muted-foreground"
      )}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function OpsPanel() {
  const [summary, setSummary] = useState<OpsSummary | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunRecord | null>(null);
  const [filters, setFilters] = useState({
    workflow: "",
    mode: "",
    status: "",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, runsData] = await Promise.all([
        api.opsSummary(),
        api.listRuns({
          limit: 50,
          workflow: filters.workflow || undefined,
          mode: filters.mode || undefined,
          status: filters.status || undefined,
        }),
      ]);
      setSummary(summaryData);
      setRuns(runsData.runs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ops data");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="space-y-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Internal observability for pilot workflow runs.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchData}
          disabled={loading}
        >
          {loading ? "Loading..." : "Refresh"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Summary cards */}
      {summary && <SummaryCards summary={summary} />}

      {/* Workflow breakdown */}
      {summary && <WorkflowTable summary={summary} />}

      {/* Filter + runs table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Recent runs</h3>
          <FilterBar filters={filters} onChange={setFilters} />
        </div>
        <Card>
          <CardContent className="p-0">
            <RunsTable
              runs={runs}
              selectedId={selectedRun?.id ?? null}
              onSelect={setSelectedRun}
            />
          </CardContent>
        </Card>
      </div>

      {/* Run detail */}
      {selectedRun && (
        <RunDetail
          run={selectedRun}
          onClose={() => setSelectedRun(null)}
        />
      )}
    </div>
  );
}
