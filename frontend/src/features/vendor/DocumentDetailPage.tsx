import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  downloadDocument,
  getDocument,
  getExtractedFields,
  retryDocument,
  type ExtractedField,
  type VendorDocument,
} from "../../shared/api";
import { useAuth } from "../auth/useAuth";
import {
  documentTypeLabels,
  processingStatusLabels,
  readableDate,
  readableSize,
} from "./documentUi";

type DetailState =
  | { kind: "loading" }
  | { kind: "ready"; document: VendorDocument; fields: ExtractedField[] }
  | { kind: "error"; message: string; forbidden: boolean; missing: boolean };

function detailError(error: unknown) {
  if (error instanceof ApiError) {
    return {
      message: error.detail,
      forbidden: error.status === 403,
      missing: error.status === 404,
    };
  }
  return {
    message: "Network error. Check the backend connection and retry.",
    forbidden: false,
    missing: false,
  };
}

export function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { token } = useAuth();
  const [state, setState] = useState<DetailState>({ kind: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (!token || !documentId) return;
    let active = true;
    setState({ kind: "loading" });
    Promise.all([
      getDocument(token, documentId),
      getExtractedFields(token, documentId),
    ])
      .then(([document, fields]) => {
        if (active) setState({ kind: "ready", document, fields });
      })
      .catch((error: unknown) => {
        if (active) setState({ kind: "error", ...detailError(error) });
      });
    return () => {
      active = false;
    };
  }, [documentId, reloadKey, token]);

  async function handleDownload(document: VendorDocument) {
    if (!token) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const blob = await downloadDocument(token, document.id);
      const objectUrl = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = objectUrl;
      link.download = document.original_filename;
      link.click();
      URL.revokeObjectURL(objectUrl);
    } catch (error) {
      setDownloadError(
        error instanceof ApiError
          ? error.detail
          : "Network error. Unable to download this document.",
      );
    } finally {
      setDownloading(false);
    }
  }

  if (!documentId) {
    return <main className="mx-auto max-w-5xl px-6 py-14">Invalid document.</main>;
  }

  if (state.kind === "loading") {
    return (
      <main className="mx-auto max-w-5xl px-6 py-14" aria-live="polite">
        <p className="text-slate-300">Loading document details…</p>
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <section className="rounded-3xl border border-rose-900/70 bg-slate-900 p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-300">
            {state.forbidden ? "Forbidden" : state.missing ? "Not found" : "Connection problem"}
          </p>
          <h1 className="mt-3 text-3xl font-bold">Unable to load document</h1>
          <p className="mt-3 text-slate-300" role="alert">{state.message}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            {!state.forbidden && !state.missing && (
              <button className="primary-button" type="button" onClick={() => setReloadKey((key) => key + 1)}>
                Retry
              </button>
            )}
            <Link className="secondary-button" to="/documents">Back to documents</Link>
          </div>
        </section>
      </main>
    );
  }

  const reviewed = state.fields.filter(
    (field) => field.review_status !== "unreviewed",
  ).length;

  return (
    <main className="mx-auto max-w-5xl px-6 py-14">
      <Link className="text-sm text-cyan-300 hover:text-cyan-200" to="/documents">
        &larr; Back to documents
      </Link>
      <section className="mt-5 rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-2xl sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
              {documentTypeLabels[state.document.document_type]}
            </p>
            <h1 className="mt-3 break-all text-3xl font-bold">
              {state.document.original_filename}
            </h1>
          </div>
          <span className="rounded-full bg-slate-800 px-3 py-1 text-sm font-medium">
            {processingStatusLabels[state.document.processing_status]}
          </span>
        </div>

        <dl className="mt-8 grid gap-4 rounded-2xl bg-slate-950 p-5 sm:grid-cols-2 lg:grid-cols-4">
          <Metadata label="File type" value={state.document.mime_type} />
          <Metadata label="Size" value={readableSize(state.document.file_size)} />
          <Metadata label="Uploaded" value={readableDate(state.document.created_at)} />
          <Metadata label="Fields reviewed" value={`${reviewed} of ${state.fields.length}`} />
        </dl>

        {state.document.processing_error && (
          <p className="mt-6 rounded-xl bg-amber-950/50 p-4 text-sm text-amber-200" role="alert">
            {state.document.processing_error}
          </p>
        )}
        {state.document.processing_status === "processing" && (
          <p className="mt-6 text-sm text-slate-300" role="status">
            Extraction is still processing. Reload this page to check for updates.
          </p>
        )}
        {state.document.processing_status === "processed" && state.fields.length === 0 && (
          <p className="mt-6 rounded-xl bg-slate-950 p-4 text-sm text-amber-200">
            Processing finished, but no readable supported fields were found.
          </p>
        )}

        <div className="mt-8 flex flex-wrap gap-3">
          {state.document.processing_status === 'failed' && <button className="primary-button" disabled={retrying} onClick={async () => {
            if (!token) return;
            setRetrying(true); setDownloadError(null);
            try { await retryDocument(token, state.document.id); setReloadKey(key => key + 1); }
            catch (error) { setDownloadError(error instanceof Error ? error.message : 'Unable to retry extraction.'); }
            finally { setRetrying(false); }
          }}>{retrying ? 'Retrying extraction…' : 'Retry extraction'}</button>}
          {state.document.processing_status === "processed" && state.fields.length > 0 && (
            <Link className="primary-button" to={`/documents/${state.document.id}/review`}>
              Review extracted fields
            </Link>
          )}
          <button
            className="secondary-button"
            disabled={downloading}
            type="button"
            onClick={() => handleDownload(state.document)}
          >
            {downloading ? "Downloading…" : "Download original"}
          </button>
        </div>
        {downloadError && <p className="mt-4 text-sm text-rose-300" role="alert">{downloadError}</p>}
      </section>
    </main>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-slate-200">{value}</dd>
    </div>
  );
}
