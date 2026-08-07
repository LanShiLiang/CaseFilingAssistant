import { describe, expect, it } from "vitest";

import {
  allowlistedHeaders,
  limitRequestBody,
  ProxyPayloadTooLargeError
} from "./proxyBody";

function byteStream(...chunks: number[][]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(Uint8Array.from(chunk)));
      controller.close();
    }
  });
}

describe("limitRequestBody", () => {
  it("不缓冲地透传限制内的数据", async () => {
    const response = new Response(limitRequestBody(byteStream([1, 2], [3]), 3));
    expect([...new Uint8Array(await response.arrayBuffer())]).toEqual([1, 2, 3]);
  });

  it("累计大小超限时终止流", async () => {
    const response = new Response(limitRequestBody(byteStream([1, 2], [3, 4]), 3));
    await expect(response.arrayBuffer()).rejects.toBeInstanceOf(ProxyPayloadTooLargeError);
  });
});

describe("allowlistedHeaders", () => {
  it("只复制显式允许的代理头", () => {
    const source = new Headers({
      "content-type": "application/json",
      "x-request-id": "request-1",
      authorization: "not-forwarded"
    });

    const result = allowlistedHeaders(source, ["content-type", "x-request-id"]);

    expect(Object.fromEntries(result.entries())).toEqual({
      "content-type": "application/json",
      "x-request-id": "request-1"
    });
  });
});
