// SIH26018 Intelligent Land Record Digitization and Validation System
// TypeScript definitions matching FastAPI backend Pydantic models

export type UserRole = 'ADMIN' | 'OPERATOR' | 'REVIEWER' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Document {
  id: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  doc_type: string;
  status: 'UPLOADED' | 'PROCESSING' | 'EXTRACTED' | 'NORMALIZED' | 'VALIDATED' | 'FLAGGED' | 'FAILED';
  storage_key?: string;
  created_by?: string;
  metadata_json?: Record<string, any>;
  uploaded_at: string;
  processed_at?: string;
}

export interface DocumentPaginatedList {
  total: number;
  page: number;
  limit: number;
  data: Document[];
}

export type ConfidenceCategory = 'HIGH' | 'MEDIUM' | 'LOW';

export interface FieldExtractionEvidence {
  field: string;
  value: any;
  normalized_value?: any;
  confidence: number;
  category: ConfidenceCategory;
  source: string;
  evidence?: string;
}

export interface ExtractionResult {
  id: string;
  document_id: string;
  provider: string;
  raw_text?: string;
  extracted_fields: Record<string, any>;
  field_confidences?: Record<string, number>;
  structured_fields?: Record<string, FieldExtractionEvidence>;
  confidence_score: number;
  confidence_category: ConfidenceCategory;
  low_confidence_fields: string[];
  status: string;
  extracted_at: string;
}

export interface RuleValidationResult {
  rule_name: string;
  passed: boolean;
  message: string;
  severity: 'ERROR' | 'WARNING' | 'INFO';
}

export interface ValidationCheck {
  record_id: string;
  is_valid: boolean;
  status: string;
  rule_results: RuleValidationResult[];
  discrepancy_summary?: string;
  validated_at?: string;
}

export type DiscrepancyType =
  | 'OWNER_MISMATCH'
  | 'CO_OWNER_MISMATCH'
  | 'AREA_MISMATCH'
  | 'SURVEY_CONFLICT'
  | 'LOCATION_MISMATCH'
  | 'IDENTIFIER_CONFLICT'
  | 'DUPLICATE_DOCUMENT'
  | 'SUSPICIOUS_DATE_SEQUENCE'
  | 'MISSING_RELATED_RECORD'
  | 'LOW_CONFIDENCE_CRITICAL_FIELD';

export type DiscrepancySeverity = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type DiscrepancyStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';

export interface Discrepancy {
  id: string;
  record_id: string;
  compared_record_id?: string;
  comparison_id?: string;
  discrepancy_type: DiscrepancyType | string;
  severity: DiscrepancySeverity | string;
  description: string;
  field_name?: string;
  source_value?: string;
  conflicting_value?: string;
  confidence: number;
  status: DiscrepancyStatus | string;
  created_at: string;
  updated_at: string;
}

export interface DiscrepancyPaginatedList {
  total: number;
  page: number;
  limit: number;
  data: Discrepancy[];
}

export interface ComparisonSummary {
  record_id: string;
  matched_records_count: number;
  total_discrepancies: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  highest_severity?: string;
  discrepancies: Discrepancy[];
}

export interface RecordComparison {
  id: string;
  record_id: string;
  compared_record_id: string;
  match_type: string;
  discrepancy_count: number;
  highest_severity?: string;
  status: string;
  compared_at: string;
  discrepancies: Discrepancy[];
}

export type RecordStatus = 'EXTRACTED' | 'NORMALIZED' | 'VALIDATED' | 'FLAGGED' | 'REJECTED';

export type ReviewStatus =
  | 'NOT_REQUIRED'
  | 'PENDING_REVIEW'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'CHANGES_REQUESTED';

export interface LandRecord {
  id: string;
  document_id?: string;
  created_by?: string;
  state: string;
  district: string;
  tehsil: string;
  village: string;
  khasra_number: string;
  khata_number: string;
  area_in_hectares: number;
  land_classification?: string;
  owner_name?: string;
  co_owners?: string[];
  patta_number?: string;
  registration_number?: string;
  mutation_number?: string;
  document_date?: string;
  confidence_score: number;
  status: RecordStatus | string;
  review_status: ReviewStatus | string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface LandRecordDetail extends LandRecord {
  latest_validation?: ValidationCheck;
  discrepancies?: Discrepancy[];
}

export interface LandRecordPaginatedList {
  total: number;
  page: number;
  limit: number;
  total_pages?: number;
  data: LandRecord[];
}

export interface ReviewDetail {
  record_id: string;
  review_status: ReviewStatus;
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
  rejection_reason?: string;
  land_record_status: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  actor_user_id?: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  previous_state?: Record<string, any>;
  new_state?: Record<string, any>;
  metadata_json?: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface AuditLogList {
  total: number;
  page: number;
  limit: number;
  items: AuditLog[];
}

export interface OCRStatus {
  selected_engine: string;
  available: boolean;
  provider_name: string;
  engine_version?: string;
  supported_languages: string[];
  offline_operational: boolean;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  environment: string;
  services: {
    backend: string;
    database: string;
  };
}

export interface DashboardStats {
  total_records: number;
  documents_processed: number;
  records_awaiting_review: number;
  validated_records: number;
  flagged_records: number;
  open_discrepancies: number;
  low_confidence_records: number;
  approved_records: number;
  rejected_records: number;
}

export interface DigitizationPipelineResult {
  document: Document;
  extraction: ExtractionResult;
  records: LandRecord[];
  validations: ValidationCheck[];
  discrepancies?: ComparisonSummary;
  summary: string;
}

export type ViewName =
  | 'dashboard'
  | 'records'
  | 'record-detail'
  | 'upload'
  | 'discrepancies'
  | 'review'
  | 'audit'
  | 'system'
  | 'cadastral-map';

export interface CadastralMapRecord {
  record_id: string;
  khasra_number: string;
  khata_number: string;
  state: string;
  district: string;
  tehsil: string;
  village: string;
  area_in_hectares: number;
  land_classification?: string;
  status: string;
  review_status: string;
  confidence_score: number;
  has_discrepancies: boolean;
  discrepancy_count: number;
  latitude?: number;
  longitude?: number;
  boundary_geojson?: Record<string, any>;
  geometry_validation_status: string;
  map_source: string;
}

export interface CadastralMapResponse {
  total_parcels: number;
  parcels: CadastralMapRecord[];
}

export interface GeometryValidationResponse {
  is_valid: boolean;
  geometry_type?: string;
  vertex_count?: number;
  coordinate_reference_system: string;
  errors: string[];
  warnings: string[];
}


export type JobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'RETRYING';

export interface Job {
  id: string;
  document_id: string;
  created_by?: string;
  status: JobStatus;
  current_stage: string;
  progress_percentage: number;
  error_category?: string;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  result_summary?: Record<string, any>;
  metadata_json?: Record<string, any>;
}

export interface JobPaginatedList {
  total: number;
  page: number;
  limit: number;
  data: Job[];
}

