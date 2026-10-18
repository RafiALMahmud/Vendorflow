import type { DocumentType, ProcessingStatus } from "../../shared/api";

export const documentTypeLabels: Record<DocumentType, string> = {
  trade_license: "Trade license",
  business_registration: "Business registration",
  tax_certificate: "Tax certificate",
  other: "Other",
};

export const processingStatusLabels: Record<ProcessingStatus, string> = {
  uploaded: "Uploaded",
  processing: "Processing",
  processed: "Processed",
  failed: "Failed",
};

export function readableSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function readableDate(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(parsed);
}
