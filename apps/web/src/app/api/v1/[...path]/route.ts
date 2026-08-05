import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const REQUEST_HEADERS = ["content-type", "idempotency-key", "x-request-id"] as const;
const RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "cache-control",
  "x-request-id"
] as const;

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const internalApi = process.env.CFA_INTERNAL_API_URL ?? "http://127.0.0.1:8000";
  const target = new URL(`/api/v1/${path.map(encodeURIComponent).join("/")}`, internalApi);
  target.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  try {
    const init: RequestInit = {
      method: request.method,
      headers,
      cache: "no-store",
      redirect: "manual"
    };
    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.arrayBuffer();
    }
    const response = await fetch(target, init);
    const responseHeaders = new Headers();
    for (const name of RESPONSE_HEADERS) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });
  } catch {
    return Response.json(
      { error: { code: "api_unavailable", message: "本地服务暂不可用，请稍后重试。" } },
      { status: 502, headers: { "Cache-Control": "no-store" } }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
