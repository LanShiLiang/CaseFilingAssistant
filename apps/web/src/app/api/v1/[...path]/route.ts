import type { NextRequest } from "next/server";

import {
  allowlistedHeaders,
  limitRequestBody,
  ProxyPayloadTooLargeError
} from "../proxyBody";

export const dynamic = "force-dynamic";

const REQUEST_HEADERS = ["content-type", "idempotency-key", "x-request-id"] as const;
const RESPONSE_HEADERS = [
  "content-type",
  "content-disposition",
  "cache-control",
  "x-request-id"
] as const;
const MAX_PROXY_BODY_BYTES = 22 * 1024 * 1024;

function payloadTooLargeResponse() {
  return Response.json(
    { error: { code: "file_too_large", message: "上传内容超过本地代理限制。" } },
    { status: 413, headers: { "Cache-Control": "no-store" } }
  );
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const internalApi = process.env.CFA_INTERNAL_API_URL ?? "http://127.0.0.1:8000";
  const target = new URL(`/api/v1/${path.map(encodeURIComponent).join("/")}`, internalApi);
  target.search = request.nextUrl.search;
  const headers = allowlistedHeaders(request.headers, REQUEST_HEADERS);

  const declaredLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_PROXY_BODY_BYTES) {
    return payloadTooLargeResponse();
  }

  try {
    const upstreamSignal = AbortSignal.any([
      request.signal,
      AbortSignal.timeout(120_000)
    ]);
    const init: RequestInit & { duplex?: "half" } = {
      method: request.method,
      headers,
      cache: "no-store",
      redirect: "manual",
      signal: upstreamSignal
    };
    if (request.method !== "GET" && request.method !== "HEAD" && request.body) {
      init.body = limitRequestBody(request.body, MAX_PROXY_BODY_BYTES);
      init.duplex = "half";
    }
    const response = await fetch(target, init);
    const responseHeaders = allowlistedHeaders(response.headers, RESPONSE_HEADERS);
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders
    });
  } catch (reason) {
    if (reason instanceof ProxyPayloadTooLargeError) return payloadTooLargeResponse();
    return Response.json(
      { error: { code: "api_unavailable", message: "本地服务暂不可用，请稍后重试。" } },
      { status: 502, headers: { "Cache-Control": "no-store" } }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
