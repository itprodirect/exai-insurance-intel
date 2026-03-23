"use client";

import { useState } from "react";
import { api, type SearchResponse } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, ExternalLink } from "lucide-react";

export function SearchPanel() {
  const [query, setQuery] = useState("");
  const [numResults, setNumResults] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await api.search({
        query: query.trim(),
        num_results: numResults,
      });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="search-query" className="text-sm font-medium">
            Search query
          </label>
          <Input
            id="search-query"
            placeholder="e.g. forensic engineer insurance expert witness"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
        </div>
        <div className="flex items-end gap-4">
          <div className="space-y-2">
            <label htmlFor="num-results" className="text-sm font-medium">
              Results
            </label>
            <Input
              id="num-results"
              type="number"
              min={1}
              max={100}
              value={numResults}
              onChange={(e) => setNumResults(Number(e.target.value))}
              className="w-20"
              disabled={loading}
            />
          </div>
          <Button type="submit" disabled={loading || !query.trim()}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Search
          </Button>
        </div>
      </form>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      {data && <SearchResults data={data} />}
    </div>
  );
}

function SearchResults({ data }: { data: SearchResponse }) {
  const { record, recommendation } = data;

  return (
    <div className="space-y-4">
      {/* Metadata bar */}
      <div className="flex flex-wrap gap-3 text-sm">
        <span className="rounded bg-muted px-2 py-1">
          run: <span className="font-mono">{data.run_id}</span>
        </span>
        <span className="rounded bg-muted px-2 py-1">
          {record.result_count} results
        </span>
        <span className="rounded bg-muted px-2 py-1">
          cost: ${record.estimated_cost_usd.toFixed(4)}
        </span>
        {record.cache_hit && (
          <span className="rounded bg-blue-100 px-2 py-1 text-blue-800">
            cache hit
          </span>
        )}
      </div>

      {/* Scores */}
      <div className="flex flex-wrap gap-2">
        <ScoreBadge label="Relevance" value={record.relevance_score} />
        <ScoreBadge label="Credibility" value={record.credibility_score} />
        <ScoreBadge label="Actionability" value={record.actionability_score} />
        <ScoreBadge label="Confidence" value={record.confidence_score} />
      </div>

      {/* Recommendation */}
      {recommendation?.headline_recommendation && (
        <p className="text-sm text-muted-foreground italic">
          {recommendation.headline_recommendation}
        </p>
      )}

      {/* Failure reasons */}
      {record.failure_reasons.length > 0 && (
        <div className="text-sm text-orange-700">
          Issues: {record.failure_reasons.join(", ")}
        </div>
      )}

      {/* Results list */}
      {record.results.length === 0 ? (
        <p className="text-sm text-muted-foreground">No results returned.</p>
      ) : (
        <div className="space-y-3">
          {record.results.map((result, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  {result.url ? (
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 hover:underline"
                    >
                      {result.title || "Untitled"}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    result.title || "Untitled"
                  )}
                </CardTitle>
                {result.url && (
                  <p className="text-xs text-muted-foreground truncate">
                    {result.url}
                  </p>
                )}
              </CardHeader>
              <CardContent>
                {result.highlights.length > 0 ? (
                  <ul className="space-y-1 text-sm">
                    {result.highlights.map((h, j) => (
                      <li key={j} className="text-muted-foreground">
                        {h}
                      </li>
                    ))}
                  </ul>
                ) : result.summary ? (
                  <p className="text-sm text-muted-foreground">
                    {result.summary}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    No preview available
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ScoreBadge({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 70
      ? "bg-green-100 text-green-800"
      : pct >= 40
        ? "bg-yellow-100 text-yellow-800"
        : "bg-red-100 text-red-800";

  return (
    <span className={`rounded px-2 py-1 text-xs font-medium ${color}`}>
      {label}: {pct}%
    </span>
  );
}
