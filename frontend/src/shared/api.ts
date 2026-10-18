export type HealthResponse = {
  status: "ok";
  service: string;
  environment: string;
};

export type UserRole = "vendor" | "admin";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  created_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
};

export type RegisterInput = {
  email: string;
  full_name: string;
  password: string;
};

export type VendorProfileInput = {
  company_name: string;
  registration_number: string;
  contact_email: string;
  phone: string;
  address: string;
};

export type VendorProfile = VendorProfileInput & {
  id: string;
  owner_user_id: string;
  created_at: string;
  updated_at: string;
};

export type DocumentType =
  | "trade_license"
  | "business_registration"
  | "tax_certificate"
  | "other";

export type ProcessingStatus = "uploaded" | "processing" | "processed" | "failed";

export type VendorDocument = {
  id: string;
  vendor_id: string;
  document_type: DocumentType;
  original_filename: string;
  mime_type: string;
  file_size: number;
  processing_status: ProcessingStatus;
  processing_error: string | null;
  created_at: string;
  updated_at: string;
};

export type ExtractedFieldName =
  | "company_name"
  | "registration_number"
  | "license_number"
  | "certificate_number"
  | "issue_date"
  | "expiry_date"
  | "tax_identifier";

export type ReviewStatus = "unreviewed" | "confirmed" | "corrected";

export type ExtractedField = {
  id: string;
  document_id: string;
  field_name: ExtractedFieldName;
  raw_value: string | null;
  normalized_value: string | null;
  confirmed_value: string | null;
  review_status: ReviewStatus;
  extraction_method: string | null;
  review_note: string | null;
  created_at: string;
  updated_at: string;
};

export type ExtractedFieldReviewUpdate = {
  field_name: ExtractedFieldName;
  confirmed_value: string;
  review_status: "confirmed" | "corrected";
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
  }
}

export const SESSION_EXPIRED_EVENT = 'vendorflow:session-expired';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type UploadProgress = {
  loaded: number;
  total: number | null;
  percent: number | null;
};

type ApiOptions = Omit<RequestInit, "body"> & {
  token?: string;
  body?: unknown;
  formData?: FormData;
  responseType?: "json" | "blob";
};

export async function apiRequest<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const {
    token,
    body,
    formData,
    responseType = "json",
    headers: suppliedHeaders,
    ...requestOptions
  } = options;
  const headers = new Headers(suppliedHeaders);

  headers.set("Accept", "application/json");
  if (body !== undefined) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers,
    body: formData ?? (body === undefined ? undefined : JSON.stringify(body)),
  });

  if (!response.ok) {
    if (response.status === 401 && token) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    let detail = "Request failed. Please try again.";
    try {
      const errorBody = (await response.json()) as { detail?: unknown };
      if (typeof errorBody.detail === "string") {
        detail = errorBody.detail;
      } else if (Array.isArray(errorBody.detail)) {
        const firstIssue = errorBody.detail[0] as
          | { loc?: unknown; msg?: unknown }
          | undefined;
        if (firstIssue && typeof firstIssue.msg === "string") {
          const location = Array.isArray(firstIssue.loc)
            ? firstIssue.loc.at(-1)
            : undefined;
          detail =
            typeof location === "string"
              ? `${location.replaceAll("_", " ")}: ${firstIssue.msg}`
              : firstIssue.msg;
        }
      }
    } catch {
      // Keep the safe generic message for non-JSON failures.
    }
    throw new ApiError(response.status, detail);
  }

  if (responseType === "blob") return response.blob() as Promise<T>;
  return response.json() as Promise<T>;
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { signal });
}

export function registerVendor(payload: RegisterInput): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/register", {
    method: "POST",
    body: payload,
  });
}

export function loginVendor(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function getCurrentUser(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me", { token });
}

export function getVendorProfile(token: string): Promise<VendorProfile> {
  return apiRequest<VendorProfile>("/vendors/me", { token });
}

export function createVendorProfile(
  token: string,
  payload: VendorProfileInput,
): Promise<VendorProfile> {
  return apiRequest<VendorProfile>("/vendors/me", {
    method: "POST",
    token,
    body: payload,
  });
}

export function updateVendorProfile(
  token: string,
  payload: VendorProfileInput,
): Promise<VendorProfile> {
  return apiRequest<VendorProfile>("/vendors/me", {
    method: "PATCH",
    token,
    body: payload,
  });
}

export function listDocuments(token: string): Promise<VendorDocument[]> {
  return apiRequest<VendorDocument[]>("/documents", { token });
}

export function getDocument(
  token: string,
  documentId: string,
): Promise<VendorDocument> {
  return apiRequest<VendorDocument>(`/documents/${documentId}`, { token });
}

export function getExtractedFields(
  token: string,
  documentId: string,
): Promise<ExtractedField[]> {
  return apiRequest<ExtractedField[]>(
    `/documents/${documentId}/extracted-fields`,
    { token },
  );
}

export function updateExtractedFields(
  token: string,
  documentId: string,
  fields: ExtractedFieldReviewUpdate[],
): Promise<ExtractedField[]> {
  return apiRequest<ExtractedField[]>(
    `/documents/${documentId}/extracted-fields`,
    { method: "PATCH", token, body: { fields } },
  );
}

export function uploadDocument(
  token: string,
  documentType: DocumentType,
  file: File,
  onProgress?: (progress: UploadProgress) => void,
): Promise<VendorDocument> {
  const formData = new FormData();
  formData.set("document_type", documentType);
  formData.set("file", file);
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE_URL}/documents/upload`);
    request.setRequestHeader("Accept", "application/json");
    request.setRequestHeader("Authorization", `Bearer ${token}`);
    request.upload.addEventListener("progress", (event) => {
      const total = event.lengthComputable ? event.total : null;
      onProgress?.({
        loaded: event.loaded,
        total,
        percent: total ? Math.round((event.loaded / total) * 100) : null,
      });
    });
    request.addEventListener("load", () => {
      let payload: unknown;
      try {
        payload = JSON.parse(request.responseText);
      } catch {
        reject(new ApiError(request.status, "The server returned an invalid response."));
        return;
      }
      if (request.status >= 200 && request.status < 300) {
        onProgress?.({ loaded: file.size, total: file.size, percent: 100 });
        resolve(payload as VendorDocument);
        return;
      }
      const detail =
        typeof payload === "object" &&
        payload !== null &&
        "detail" in payload &&
        typeof payload.detail === "string"
          ? payload.detail
          : "Unable to upload this document.";
      if (request.status === 401) window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
      reject(new ApiError(request.status, detail));
    });
    request.addEventListener("error", () => {
      reject(new ApiError(0, "Network error. Check the backend connection and retry."));
    });
    request.addEventListener("abort", () => {
      reject(new ApiError(0, "Document upload was cancelled."));
    });
    request.send(formData);
  });
}

export function downloadDocument(token: string, documentId: string): Promise<Blob> {
  return apiRequest<Blob>(`/documents/${documentId}/file`, {
    token,
    responseType: "blob",
  });
}

export function retryDocument(token: string, documentId: string): Promise<VendorDocument> {
  return apiRequest(`/documents/${encodeURIComponent(documentId)}/retry`, { token, method: 'POST' });
}

