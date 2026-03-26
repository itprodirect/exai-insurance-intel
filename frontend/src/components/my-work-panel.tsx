"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type MeResponse,
  type RunRecord,
  type SavedQueryRecord,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Trash2, Play } from "lucide-react";
import { cn } from "@/lib/utils";

interface MyWorkPanelProps {
  onReplayQuery?: (workflow: string, query: string) => void;
}

export function MyWorkPanel({ onReplayQuery }: MyWorkPanelProps) {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [savedQueries, setSavedQueries] = useState<SavedQueryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Save query form state.
  const [newWorkflow, setNewWorkflow] = useState("search");
  const [newQuery, setNewQuery] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [meData, runsData, sqData] = await Promise.all([
        api.me(),
        api.myRuns({ limit: 20 }),
        api.listSavedQueries(),
      ]);
      setMe(meData);
      setRuns(runsData.runs);
      setSavedQueries(sqData.queries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleSaveQuery(e: React.FormEvent) {
    e.preventDefault();
    if (!newQuery.trim()) return;
    setSaving(true);
    try {
      await api.saveQuery({
        workflow: newWorkflow,
        query: newQuery.trim(),
        label: newLabel.trim() || undefined,
      });
      setNewQuery("");
      setNewLabel("");
      await refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save query"
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteQuery(id: string) {
    try {
      await api.deleteSavedQuery(id);
      setSavedQueries((prev) => prev.filter((q) => q.id !== id));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete query"
      );
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
        <Button variant="outline" size="sm" onClick={refresh}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* User identity + usage summary */}
      {me && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-sm font-medium">
              {me.user_id.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-sm font-medium">{me.user_id}</p>
              <p className="text-xs text-muted-foreground">Pilot user</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="My runs" value={me.usage.total_runs} />
            <StatCard label="Completed" value={me.usage.completed} />
            <StatCard label="Cache hits" value={me.usage.cache_hits} />
            <StatCard
              label="Avg latency"
              value={
                me.usage.avg_duration_ms != null
                  ? `${me.usage.avg_duration_ms.toFixed(0)} ms`
                  : "—"
              }
            />
          </div>

          {me.usage.by_workflow.length > 0 && (
            <div className="text-xs text-muted-foreground">
              Workflows:{" "}
              {me.usage.by_workflow
                .map((w) => `${w.workflow} (${w.count})`)
                .join(", ")}
            </div>
          )}
        </div>
      )}

      {/* Saved queries */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Saved Queries</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Save query form */}
          <form onSubmit={handleSaveQuery} className="space-y-2">
            <div className="flex gap-2">
              <select
                value={newWorkflow}
                onChange={(e) => setNewWorkflow(e.target.value)}
                className="rounded-md border px-2 py-1.5 text-sm"
              >
                <option value="search">Search</option>
                <option value="answer">Answer</option>
                <option value="research">Research</option>
              </select>
              <Input
                placeholder="Query text..."
                value={newQuery}
                onChange={(e) => setNewQuery(e.target.value)}
                className="flex-1"
                disabled={saving}
              />
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Label (optional)"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                className="flex-1"
                disabled={saving}
              />
              <Button
                type="submit"
                size="sm"
                disabled={saving || !newQuery.trim()}
              >
                {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                Save
              </Button>
            </div>
          </form>

          {/* Saved query list */}
          {savedQueries.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No saved queries yet.
            </p>
          ) : (
            <div className="space-y-2">
              {savedQueries.map((sq) => (
                <div
                  key={sq.id}
                  className="flex items-center gap-2 rounded border p-2 text-sm"
                >
                  <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-medium">
                    {sq.workflow}
                  </span>
                  <span className="flex-1 truncate">
                    {sq.label ? (
                      <>
                        <span className="font-medium">{sq.label}</span>
                        <span className="text-muted-foreground">
                          {" "}
                          — {sq.query}
                        </span>
                      </>
                    ) : (
                      sq.query
                    )}
                  </span>
                  {onReplayQuery && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      title="Replay query"
                      onClick={() => onReplayQuery(sq.workflow, sq.query)}
                    >
                      <Play className="h-3 w-3" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-red-600"
                    title="Delete saved query"
                    onClick={() => handleDeleteQuery(sq.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent runs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">My Recent Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No runs yet.</p>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center gap-2 rounded border p-2 text-sm"
                >
                  <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-medium">
                    {run.workflow}
                  </span>
                  <StatusBadge status={run.status} />
                  <span className="flex-1 truncate text-muted-foreground">
                    {run.query_preview || "—"}
                  </span>
                  {run.duration_ms != null && (
                    <span className="text-xs text-muted-foreground">
                      {run.duration_ms.toFixed(0)} ms
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    running: "bg-blue-100 text-blue-800",
    queued: "bg-yellow-100 text-yellow-800",
    pending: "bg-gray-100 text-gray-800",
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
