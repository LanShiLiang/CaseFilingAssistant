import { describe, expect, it } from "vitest";

import { limitRequestBody, ProxyPayloadTooLargeError } from "./proxyBody";

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
