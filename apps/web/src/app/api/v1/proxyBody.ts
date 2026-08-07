export class ProxyPayloadTooLargeError extends Error {
  constructor() {
    super("proxy_payload_too_large");
    this.name = "ProxyPayloadTooLargeError";
  }
}

export function allowlistedHeaders(source: Headers, names: readonly string[]): Headers {
  const headers = new Headers();
  for (const name of names) {
    const value = source.get(name);
    if (value) headers.set(name, value);
  }
  return headers;
}

/** 流式转发时逐块计数，避免 Next.js 为上传件额外分配完整 arrayBuffer。 */
export function limitRequestBody(
  body: ReadableStream<Uint8Array>,
  maxBytes: number
): ReadableStream<Uint8Array> {
  const reader = body.getReader();
  let received = 0;

  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      const result = await reader.read();
      if (result.done) {
        controller.close();
        return;
      }
      received += result.value.byteLength;
      if (received > maxBytes) {
        await reader.cancel();
        controller.error(new ProxyPayloadTooLargeError());
        return;
      }
      controller.enqueue(result.value);
    },
    cancel(reason) {
      return reader.cancel(reason);
    }
  });
}
