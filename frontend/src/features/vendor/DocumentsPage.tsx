import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import {
  ApiError,
  downloadDocument,
  listDocuments,
  uploadDocument,
  type DocumentType,
  type VendorDocument,
} from "../../shared/api";
import { useAuth } from "../auth/useAuth";

const documentTypeLabels: Record<DocumentType, string> = {
  trade_license: "Trade license",
  business_registration: "Business registration",
  tax_certificate: "Tax certificate",
  other: "Other",
};

function readableSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function messageFrom(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.detail : fallback;
}

export function DocumentsPage() {
  const { token } = useAuth();
  const fileInput = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<VendorDocument[]>([]);
  const [documentType, setDocumentType] = useState<DocumentType>("trade_license");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let active = true;
    listDocuments(token)
      .then((data) => {
        if (active) setDocuments(data);
      })
      .catch((caughtError: unknown) => {
        if (active) {
          setError(messageFrom(caughtError, "Unable to load your documents."));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !file) {
      setError("Choose a PDF, JPG, JPEG, or PNG file first.");
      return;
    }
    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await uploadDocument(token, documentType, file);
      setDocuments((current) => [
        created,
        ...current.filter((document) => document.id !== created.id),
      ]);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      setSuccess(`${created.original_filename} uploaded securely.`);
    } catch (caughtError) {
      setError(messageFrom(caughtError, "Unable to upload this document."));
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(document: VendorDocument) {
    if (!token) return;
    setDownloadingId(document.id);
    setError(null);
    try {
      const blob = await downloadDocument(token, document.id);
      const objectUrl = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = objectUrl;
      link.download = document.original_filename;
      link.click();
      URL.revokeObjectURL(objectUrl);
    } catch (caughtError) {
      setError(messageFrom(caughtError, "Unable to download this document."));
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-14">
      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Private document storage
        </p>
        <h1 className="mt-3 text-3xl font-bold">Vendor documents</h1>
        <p className="mt-2 text-slate-400">
          Upload PDF, JPG, JPEG, or PNG files. Files are private to your vendor account.
        </p>

        <form className="mt-8 grid gap-5 md:grid-cols-[1fr_1.5fr_auto] md:items-end" onSubmit={handleUpload}>
          <label className="block" htmlFor="document-type">
            <span className="mb-2 block text-sm font-medium text-slate-300">Document type</span>
            <select
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3"
              id="document-type"
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value as DocumentType)}
            >
              {Object.entries(documentTypeLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label className="block" htmlFor="document-file">
            <span className="mb-2 block text-sm font-medium text-slate-300">File</span>
            <input
              ref={fileInput}
              accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              className="block w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm"
              id="document-file"
              required
              type="file"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button className="primary-button" disabled={uploading} type="submit">
            {uploading ? "Uploading…" : "Upload document"}
          </button>
        </form>

        <div className="mt-4" aria-live="polite">
          {error && <p className="text-sm text-rose-300" role="alert">{error}</p>}
          {success && <p className="text-sm text-emerald-300" role="status">{success}</p>}
        </div>
      </section>

      <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-900 p-8">
        <h2 className="text-xl font-semibold">Uploaded documents</h2>
        {loading ? (
          <p className="mt-5 text-slate-400">Loading documents…</p>
        ) : documents.length === 0 ? (
          <p className="mt-5 rounded-2xl bg-slate-950 p-5 text-slate-400">
            No documents uploaded yet.
          </p>
        ) : (
          <ul className="mt-5 divide-y divide-slate-800">
            {documents.map((document) => (
              <li className="flex flex-wrap items-center justify-between gap-4 py-5" key={document.id}>
                <div>
                  <p className="font-medium text-slate-100">{document.original_filename}</p>
                  <p className="mt-1 text-sm text-slate-400">
                    {documentTypeLabels[document.document_type]} · {readableSize(document.file_size)} ·{" "}
                    <span className="capitalize">{document.processing_status}</span>
                  </p>
                  {document.processing_error && (
                    <p className="mt-2 max-w-2xl text-sm text-amber-300">
                      {document.processing_error}
                    </p>
                  )}
                </div>
                <div className="flex gap-3">
                  {document.processing_status === "processed" && (
                    <Link
                      className="primary-button text-sm"
                      to={`/documents/${document.id}/review`}
                    >
                      Review extraction
                    </Link>
                  )}
                  <button
                    className="secondary-button text-sm"
                    disabled={downloadingId === document.id}
                    type="button"
                    onClick={() => handleDownload(document)}
                  >
                    {downloadingId === document.id ? "Downloading…" : "Download"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
