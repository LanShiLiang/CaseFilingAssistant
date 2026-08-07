import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type {
  Generation,
  GenerationStartResult,
  Job,
  Matter,
  UploadResult,
  ValidationResult,
  DocumentKind
} from "@case-filing/contracts";

function idempotentJsonRequest(
  url: string,
  method: "POST" | "PUT",
  idempotencyKey: string,
  body: unknown
) {
  return {
    url,
    method,
    headers: { "Idempotency-Key": idempotencyKey },
    body
  };
}

function changedMatterTags(matterId: string, includeList = false) {
  return [
    { type: "Matter" as const, id: matterId },
    ...(includeList ? (["MatterList"] as const) : [])
  ];
}

export const caseApi = createApi({
  reducerPath: "caseApi",
  baseQuery: fetchBaseQuery({ baseUrl: "/api/v1" }),
  tagTypes: ["Matter", "MatterList", "Generation"],
  endpoints: (builder) => ({
    listMatters: builder.query<Matter[], void>({
      query: () => "/matters",
      providesTags: ["MatterList"]
    }),
    createMatter: builder.mutation<
      Matter,
      { eligibility_confirmed: boolean; eligibility_version: string; idempotencyKey: string }
    >({
      query: ({ idempotencyKey, ...body }) =>
        idempotentJsonRequest("/matters", "POST", idempotencyKey, body),
      invalidatesTags: ["MatterList"]
    }),
    getMatter: builder.query<Matter, string>({
      query: (matterId) => `/matters/${matterId}`,
      providesTags: (_result, _error, matterId) => [{ type: "Matter", id: matterId }]
    }),
    uploadDocument: builder.mutation<
      UploadResult,
      {
        matterId: string;
        kind: DocumentKind;
        expectedRevision: number;
        file: File;
        idempotencyKey: string;
      }
    >({
      query: ({ matterId, kind, expectedRevision, file, idempotencyKey }) => {
        const body = new FormData();
        body.append("kind", kind);
        body.append("expected_revision", String(expectedRevision));
        body.append("file", file);
        return {
          url: `/matters/${matterId}/documents`,
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKey },
          body
        };
      },
      invalidatesTags: (result, _error, { matterId }) =>
        result ? changedMatterTags(matterId, true) : []
    }),
    saveFacts: builder.mutation<
      Matter,
      {
        matterId: string;
        expected_revision: number;
        fields: Record<string, string>;
        confirm_fields: string[];
        dismissed_scope_signal_ids: string[];
        idempotencyKey: string;
      }
    >({
      query: ({ matterId, idempotencyKey, ...body }) =>
        idempotentJsonRequest(`/matters/${matterId}/facts`, "PUT", idempotencyKey, body),
      invalidatesTags: (result, _error, { matterId }) =>
        result ? changedMatterTags(matterId, true) : []
    }),
    validateMatter: builder.mutation<
      ValidationResult,
      { matterId: string; expected_revision: number; idempotencyKey: string }
    >({
      query: ({ matterId, idempotencyKey, ...body }) =>
        idempotentJsonRequest(`/matters/${matterId}/validate`, "POST", idempotencyKey, body),
      invalidatesTags: (result, _error, { matterId }) =>
        result ? changedMatterTags(matterId) : []
    }),
    startGeneration: builder.mutation<
      GenerationStartResult,
      { matterId: string; expected_revision: number; idempotencyKey: string }
    >({
      query: ({ matterId, idempotencyKey, ...body }) =>
        idempotentJsonRequest(`/matters/${matterId}/generations`, "POST", idempotencyKey, body),
      invalidatesTags: (result, _error, { matterId }) =>
        result ? changedMatterTags(matterId) : []
    }),
    getJob: builder.query<Job, string>({ query: (jobId) => `/jobs/${jobId}` }),
    retryJob: builder.mutation<
      Job,
      { jobId: string; expected_revision: number; idempotencyKey: string }
    >({
      query: ({ jobId, idempotencyKey, ...body }) =>
        idempotentJsonRequest(`/jobs/${jobId}/retry`, "POST", idempotencyKey, body)
    }),
    getGeneration: builder.query<Generation, string>({
      query: (generationId) => `/generations/${generationId}`,
      providesTags: (_result, _error, generationId) => [{ type: "Generation", id: generationId }]
    }),
    confirmGeneration: builder.mutation<
      Generation,
      {
        generationId: string;
        expected_revision: number;
        critical_fields_reviewed: true;
        manual_review_understood: true;
        local_requirements_reviewed: true;
        idempotencyKey: string;
      }
    >({
      query: ({ generationId, idempotencyKey, ...body }) =>
        idempotentJsonRequest(
          `/generations/${generationId}/export-attestation`,
          "PUT",
          idempotencyKey,
          body
        ),
      invalidatesTags: (_result, _error, { generationId }) => [
        { type: "Generation", id: generationId }
      ]
    })
  })
});

export const {
  useListMattersQuery,
  useCreateMatterMutation,
  useGetMatterQuery,
  useUploadDocumentMutation,
  useSaveFactsMutation,
  useValidateMatterMutation,
  useStartGenerationMutation,
  useGetJobQuery,
  useRetryJobMutation,
  useGetGenerationQuery,
  useConfirmGenerationMutation
} = caseApi;
