import { api } from "./client";
import type { Assessment, ControlWithQuestions, Report, Evidence } from "../types";

export interface CreateAssessmentPayload {
  name: string;
  assessment_level: string; // AL1 | AL2 | AL3
  target_maturity_level: number; // 3 | 4 | 5
  domain?: string | null; // IS | PP | DP
  kb_collection?: string | null;
}

export async function listAssessments(): Promise<Assessment[]> {
  const { data } = await api.get<Assessment[]>("/api/v1/assessments");
  return data;
}

export async function createAssessment(payload: CreateAssessmentPayload): Promise<Assessment> {
  const { data } = await api.post<Assessment>("/api/v1/assessments", payload);
  return data;
}

export async function getAssessment(id: string): Promise<Assessment> {
  const { data } = await api.get<Assessment>(`/api/v1/assessments/${id}`);
  return data;
}

export async function deleteAssessment(id: string): Promise<void> {
  await api.delete(`/api/v1/assessments/${id}`);
}

export async function getCurrentControl(assessmentId: string): Promise<ControlWithQuestions | null> {
  const { data } = await api.get<ControlWithQuestions | null>(
    `/api/v1/assessments/${assessmentId}/current`
  );
  return data;
}

export async function getReport(assessmentId: string): Promise<Report> {
  const { data } = await api.get<Report>(`/api/v1/assessments/${assessmentId}/report`);
  return data;
}

// --- Control lifecycle ---

export async function startControl(controlId: string): Promise<ControlWithQuestions> {
  const { data } = await api.post<ControlWithQuestions>(
    `/api/v1/assessments/controls/${controlId}/start`
  );
  return data;
}

export async function skipControl(controlId: string): Promise<ControlWithQuestions> {
  const { data } = await api.post<ControlWithQuestions>(
    `/api/v1/assessments/controls/${controlId}/skip`
  );
  return data;
}

export interface AssessControlResult {
  control_id: string;
  control_number: string;
  maturity_level: number;
  confidence: string;
  assessment_mode: string;
  evidence_status: string;
  finding: string;
  missing_for_next_level: string;
  recommendation: string;
  llm_used: boolean;
}

export async function assessControl(controlId: string): Promise<AssessControlResult> {
  const { data } = await api.post<AssessControlResult>(
    `/api/v1/assessments/controls/${controlId}/assess`
  );
  return data;
}

// --- Answers ---

export interface AnswerPayload {
  response?: string | null; // yes | no | partial | skipped
  raw_text?: string | null;
}

export interface AnswerResult {
  id: string;
  followup_question_id: string;
  response: string;
  raw_text: string | null;
  llm_justification: string | null;
}

export async function answerQuestion(questionId: string, payload: AnswerPayload): Promise<AnswerResult> {
  const { data } = await api.post<AnswerResult>(
    `/api/v1/assessments/questions/${questionId}/answer`,
    payload
  );
  return data;
}

// --- Evidence ---

export async function uploadEvidence(answerId: string, file: File): Promise<Evidence> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<Evidence>(
    `/api/v1/assessments/answers/${answerId}/evidence`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function analyzeEvidence(evidenceId: string): Promise<Evidence> {
  const { data } = await api.post<Evidence>(
    `/api/v1/assessments/evidence/${evidenceId}/analyze`
  );
  return data;
}

export async function listControls(assessmentId: string): Promise<ControlWithQuestions[]> {
  const { data } = await api.get<ControlWithQuestions[]>(`/api/v1/assessments/${assessmentId}/controls`);
  return data;
}

export async function editAnswer(answerId: string, payload: AnswerPayload): Promise<AnswerResult> {
  const { data } = await api.patch<AnswerResult>(`/api/v1/assessments/answers/${answerId}`, payload);
  return data;
}

export interface UploadQuestionnaireResult {
  collection: string;
  chunks_ingested: number;
  filename: string;
}

export async function uploadQuestionnaire(file: File): Promise<UploadQuestionnaireResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post<UploadQuestionnaireResult>(
    "/api/v1/knowledge-base/upload",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}