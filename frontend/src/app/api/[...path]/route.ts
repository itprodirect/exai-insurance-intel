import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";
const BACKEND_API_KEY = process.env.BACKEND_API_KEY || "";

async function handler(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const backendPath = `/api/${path.join("/")}`;
  const url = `${BACKEND_URL}${backendPath}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (BACKEND_API_KEY) {
    headers["Authorization"] = `Bearer ${BACKEND_API_KEY}`;
  }

  const init: RequestInit = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  try {
    const resp = await fetch(url, init);
    if (resp.status === 204) {
      return new NextResponse(null, { status: 204 });
    }
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
export const DELETE = handler;
