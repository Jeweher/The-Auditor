// Types reflecting the backend API responses.

export interface User {
  id: string;
  email: string;
  full_name: string;
  company_name?: string | null;
  sector?: string | null;
 profile_photo?: string | null;
  is_active: boolean;
  role: string;
  job_title?: string | null;
  company_size?: string | null;
  audit_reason?: string | null;
  email_verified: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Assessment {
  id: string;
  name: string;
  kb_collection: string;
  assessment_level: string;
  target_maturity_level: number;
  evidence_mode: string;
  response_scale: string;
  sample_percent: number | null;
  kb_source_filename: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  total_controls: number;
  completed_controls: number;
  skipped_controls: number;
  progress_percent: number;
}

export interface FollowupQuestion {
  id: string;
  question_text: string;
  order_index: number;
  evidence_expected: boolean;
  expected_documents: string[];
  response: string | null;
  raw_text: string | null;
  llm_justification: string | null;
  answer_id: string | null;
  evidence_id: string | null;
  evidence_filename: string | null;
}

export interface ControlWithQuestions {
  id: string;
  control_number: string;
  domain: string;
  title: string;
  order_index: number;
  state: string;
  maturity_score: number | null;
  followup_questions: FollowupQuestion[];
}

export interface EvidenceAnalysis {
  verdict: string;
  relevance: number;
  coverage: Record<string, string> | null;
  summary: string | null;
  missing_elements: string[];
}

export interface Evidence {
  id: string;
  answer_id: string;
  filename: string;
  file_type: string;
  size: number;
  created_at: string;
  analysis: EvidenceAnalysis | null;
}

export interface ReportSummary {
  overall_maturity: number | null;
  compliance_percent: number;
  total_controls: number;
  assessed_controls: number;
  skipped_controls: number;
  controls_at_target: number;
  controls_below_target: number;
  assessment_completeness: number;
  verified_controls: number;
  declared_controls: number;
  verified_percent: number;
  declared_percent: number;
}

export interface AggregateRow {
  key: string;
  average_maturity: number | null;
  target: number;
  gap: number | null;
  assessed_controls: number;
}

export interface ControlRow {
  control_number: string;
  domain: string;
  title: string;
  state: string;
  maturity_level: number | null;
  cutback_level: number | null;
  target_level: number | null;
  gap: number | null;
  confidence: string | null;
  assessment_mode: string | null;
  evidence_status: string | null;
  finding: string | null;
  recommendation: string | null;
  missing_for_next_level: string | null;
}

export interface Report {
  assessment_id: string;
  name: string;
  assessment_level: string;
  target_maturity_level: number;
  status: string;
  summary: ReportSummary;
  maturity_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
  evidence_distribution: Record<string, number>;
  by_domain: AggregateRow[];
  by_subchapter: AggregateRow[];
  controls: ControlRow[];
}