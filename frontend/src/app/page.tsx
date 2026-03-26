"use client";

import { useEffect, useMemo, useState } from "react";
import { HealthIndicator } from "@/components/health-indicator";
import { SearchPanel } from "@/components/search-panel";
import { AnswerPanel } from "@/components/answer-panel";
import { ResearchPanel } from "@/components/research-panel";
import OpsPanel from "@/components/ops-panel";
import { MyWorkPanel } from "@/components/my-work-panel";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const BASE_TABS = [
  { id: "search", label: "Search" },
  { id: "answer", label: "Answer" },
  { id: "research", label: "Research" },
  { id: "my-work", label: "My Work" },
] as const;

const OPS_TAB = { id: "ops", label: "Ops" } as const;

type TabId = (typeof BASE_TABS)[number]["id"] | typeof OPS_TAB.id;

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("search");
  const [canAccessOps, setCanAccessOps] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((data) => {
        if (!cancelled) {
          setCanAccessOps(data.can_access_ops);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCanAccessOps(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!canAccessOps && activeTab === "ops") {
      setActiveTab("my-work");
    }
  }, [activeTab, canAccessOps]);

  const tabs = useMemo(
    () => (canAccessOps ? [...BASE_TABS, OPS_TAB] : BASE_TABS),
    [canAccessOps]
  );

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold">exai-insurance-intel</h1>
            <p className="text-sm text-muted-foreground">
              Insurance intelligence pilot
            </p>
          </div>
          <HealthIndicator />
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-4xl px-6 py-8">
        {/* Tab navigation */}
        <div className="mb-8 flex gap-1 rounded-lg bg-muted p-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors",
                activeTab === tab.id
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "search" && <SearchPanel />}
        {activeTab === "answer" && <AnswerPanel />}
        {activeTab === "research" && <ResearchPanel />}
        {activeTab === "my-work" && <MyWorkPanel />}
        {activeTab === "ops" && canAccessOps && <OpsPanel />}
      </main>
    </div>
  );
}
