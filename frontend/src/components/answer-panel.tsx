"use client";

import { useState } from "react";
import { api, type AnswerResponse } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, ExternalLink } from "lucide-react";

export function AnswerPanel() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnswerResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await api.answer({ query: query.trim() });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Answer request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="answer-query" className="text-sm font-medium">
            Question
          </label>
          <Input
            id="answer-query"
            placeholder="e.g. What is the Florida appraisal clause dispute process?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
        </div>
        <Button type="submit" disabled={loading || !query.trim()}>
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Get Answer
        </Button>
      </form>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3 text-sm">
            <span className="rounded bg-muted px-2 py-1">
              run: <span className="font-mono">{data.run_id}</span>
            </span>
            <span className="rounded bg-muted px-2 py-1">
              {data.citation_count} citations
            </span>
            {data.cache_hit && (
              <span className="rounded bg-blue-100 px-2 py-1 text-blue-800">
                cache hit
              </span>
            )}
          </div>

          {data.answer && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Answer</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm">{data.answer}</p>
              </CardContent>
            </Card>
          )}

          {data.citations && data.citations.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Citations</h3>
              {data.citations.map((c, i) => (
                <div key={i} className="rounded border p-3 text-sm">
                  <div className="font-medium">
                    {c.url ? (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 hover:underline"
                      >
                        {c.title || c.url}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      c.title || "Untitled"
                    )}
                  </div>
                  {c.snippet && (
                    <p className="mt-1 text-muted-foreground">{c.snippet}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
