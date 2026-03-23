import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

async function handler(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const backendPath = `/api/${path.join("/")}`;
  const url = `${BACKEND_URL}${backendPath}`;

  const init: RequestInit = {
    method: request.method,
    headers: { "Content-Type": "application/json" },
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  try {
    const resp = await fetch(url, init);
    const data = await resp.json();
    return NextResponse.json(data, { status: resp.status });
  } catch {
    return NextResponse.json(
      { error: "Backend unavailable", detail: `Could not reach ${BACKEND_URL}` },
      { status: 502 }
    );
  }
}

export const GET = handler;
export const POST = handler;
