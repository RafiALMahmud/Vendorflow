export type ApplicationStatus = 'draft' | 'submitted' | 'needs_correction' | 'resubmitted' | 'approved' | 'rejected';
export type Application = {
  id: string;
  company_name: string;
  status: ApplicationStatus;
  version: number;
  submitted_at: string | null;
  correction_note?: string;
};
export type ReviewDecision = 'approved' | 'rejected' | 'needs_correction';
export type Assessment = {
  score: number;
  level: string;
  rules_version: string;
  findings: {
    code: string;
    severity: 'warning' | 'error';
    description: string;
    evidence: { document_id: string | null; document_type: string; field_name: string | null }[];
  }[];
};
export type CaseDetail = {
  application: Application;
  assessment: Assessment | null;
  documents: { document_id: string; document_type: string; processing_status: string;
    fields?: Record<string, { raw_value: string | null; confirmed_value: string | null; review_status: string }> }[];
  audit_events: { id: string; action: string; actor_user_id: string; created_at: string; note: string }[];
};
export type QueueQuery = { status: string; search: string; page: number };
export type QueuePage = { items: Application[]; total: number; page: number; page_size: number };
export type Dashboard = { total: number; awaiting_review: number; approved: number; rejected: number; needs_correction: number };
export interface ReviewApi {
  downloadEvidence?(applicationId: string, documentId: string): Promise<Blob>;
  dashboard(signal?: AbortSignal): Promise<Dashboard>;
  queue(query: QueueQuery, signal?: AbortSignal): Promise<QueuePage>;
  detail(id: string, signal?: AbortSignal): Promise<CaseDetail>;
  review(id: string, decision: ReviewDecision, note: string, expectedVersion: number): Promise<CaseDetail>;
}
