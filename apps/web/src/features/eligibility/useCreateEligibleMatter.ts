"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { parseApiError } from "@/lib/domain";
import { useCreateMatterMutation } from "@/store/caseApi";

const ELIGIBILITY_VERSION = "self_single_v1.0.0";

/**
 * 封装首页新建事项的协议细节，页面只负责展示适用条件和触发操作。
 * 幂等键在每次人工确认后重新生成，重复提交由服务端保证不会创建两份事项。
 */
export function useCreateEligibleMatter() {
  const router = useRouter();
  const [createMatter, { isLoading }] = useCreateMatterMutation();
  const [error, setError] = useState("");
  const idempotencyKey = useRef<string | null>(null);

  async function create() {
    setError("");
    try {
      const matter = await createMatter({
        eligibility_confirmed: true,
        eligibility_version: ELIGIBILITY_VERSION,
        idempotencyKey: (idempotencyKey.current ??= crypto.randomUUID())
      }).unwrap();
      idempotencyKey.current = null;
      router.push(`/matters/${matter.id}`);
    } catch (reason) {
      setError(parseApiError(reason));
    }
  }

  return { create, creating: isLoading, error };
}
