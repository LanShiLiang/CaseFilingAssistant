import type { components } from "./generated";

type Schemas = components["schemas"];

/** 运行时代码只从 OpenAPI 生成 schema 派生协议类型，禁止维护平行手写响应结构。 */
export type Matter = Schemas["MatterResponse"];
export type MatterDocument = Schemas["MatterDocumentResponse"];
export type DocumentKind = MatterDocument["kind"];
export type ConfirmationState = Matter["confirmations"][string];
export type SourceReference = Schemas["SourceReferenceResponse"];
export type StepGate = Schemas["StepGateResponse"];
export type Job = Schemas["JobResponse"];
export type JobStatus = Job["status"];
export type ValidationIssue = Schemas["ValidationIssueResponse"];
export type ValidationResult = Schemas["ValidationResponse"];
export type Generation = Schemas["GenerationResponse"];
export type GenerationStartResult = Schemas["GenerationStartResponse"];
export type UploadResult = Schemas["UploadResponse"];
export type CreateMatterRequest = Schemas["CreateMatterRequest"];
export type SaveFactsRequest = Schemas["SaveFactsRequest"];

// FastAPI 的统一异常处理器不进入具体 endpoint response schema；错误 envelope 保持窄而稳定。
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Record<string, unknown>;
  };
}

export type { components, operations, paths } from "./generated";
