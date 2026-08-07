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
      query: ({ idempotencyKey, ...body }) => ({
        url: "/matters",
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body
      }),
      invalidatesTags: ["MatterList"]
    }),
    getMatter: builder.query<Matter, string>({
      query: (matterId) => `/matters/${matterId}`,
      providesTags: (_result, _error, matterId) => [{ type: "Matter", id: matterId }]
    }),
    uploadDocument: builder.mutation<
      UploadResult,
      { matterId: string; kind: DocumentKind; expectedRevision: number; file: File }
    >({
      query: ({ matterId, kind, expectedRevision, file }) => {
        const body = new FormData();
        body.append("kind", kind);
        body.append("expected_revision", String(expectedRevision));
        body.append("file", file);
        return { url: `/matters/${matterId}/documents`, method: "POST", body };
      },
      invalidatesTags: (_result, _error, { matterId }) => [{ type: "Matter", id: matterId }]
    }),
    saveFacts: builder.mutation<
      Matter,
      {
        matterId: string;
        expected_revision: number;
        fields: Record<string, string>;
        confirm_fields: string[];
      }
    >({
      query: ({ matterId, ...body }) => ({
        url: `/matters/${matterId}/facts`, method: "PUT", body
      }),
      invalidatesTags: (_result, _error, { matterId }) => [{ type: "Matter", id: matterId }]
    }),
    validateMatter: builder.mutation<ValidationResult, { matterId: string; expected_revision: number }>({
      query: ({ matterId, ...body }) => ({
        url: `/matters/${matterId}/validate`, method: "POST", body
      }),
      invalidatesTags: (_result, _error, { matterId }) => [{ type: "Matter", id: matterId }]
    }),
    startGeneration: builder.mutation<
      GenerationStartResult,
      { matterId: string; expected_revision: number }
    >({
      query: ({ matterId, ...body }) => ({
        url: `/matters/${matterId}/generations`, method: "POST", body
      }),
      invalidatesTags: (_result, _error, { matterId }) => [{ type: "Matter", id: matterId }]
    }),
    getJob: builder.query<Job, string>({ query: (jobId) => `/jobs/${jobId}` }),
    getGeneration: builder.query<Generation, string>({
      query: (generationId) => `/generations/${generationId}`,
      providesTags: (_result, _error, generationId) => [{ type: "Generation", id: generationId }]
    }),
    confirmGeneration: builder.mutation<
      Generation,
      { generationId: string; expected_revision: number }
    >({
      query: ({ generationId, ...body }) => ({
        url: `/generations/${generationId}/confirm`, method: "POST", body
      }),
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
  useGetGenerationQuery,
  useConfirmGenerationMutation
} = caseApi;
