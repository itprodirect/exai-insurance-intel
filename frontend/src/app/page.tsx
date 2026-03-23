"use client";

import { useState } from "react";
import { HealthIndicator } from "@/components/health-indicator";
import { SearchPanel } from "@/components/search-panel";
import { AnswerPanel } from "@/components/answer-panel";
import { ResearchPanel } from "@/components/research-panel";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "search", label: "Search" },
  { id: "answer", label: "Answer" },
  { id: "research", label: "Research" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabId>("search");

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
          {TABS.map((tab) => (
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
      </main>
    </div>
  );
}
