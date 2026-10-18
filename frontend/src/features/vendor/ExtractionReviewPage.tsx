import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  getDocument,
  getExtractedFields,
  updateExtractedFields,
  type ExtractedField,
  type ExtractedFieldName,
  type VendorDocument,
} from "../../shared/api";
import { useAuth } from "../auth/useAuth";

const fieldLabels: Record<ExtractedFieldName, string> = {
  company_name: "Company name",
  registration_number: "Registration number",
  license_number: "License number",
  issue_date: "Issue date",
  expiry_date: "Expiry date",
  tax_identifier: "Tax identifier",
};

const dateFields = new Set<ExtractedFieldName>(["issue_date", "expiry_date"]);

function messageFrom(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.detail : fallback;
}

function initialValue(field: ExtractedField) {
  if (field.confirmed_value) return field.confirmed_value;
  if (field.normalized_value) return field.normalized_value;
  if (dateFields.has(field.field_name)) return "";
  return field.raw_value ?? "";
}

export function ExtractionReviewPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { token } = useAuth();
  const [document, setDocument] = useState<VendorDocument | null>(null);
  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [savingField, setSavingField] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loadErrorStatus, setLoadErrorStatus] = useState<number | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loadFields = useCallback(async () => {
    if (!token || !documentId) return;
    const loaded = await getExtractedFields(token, documentId);
    setFields(loaded);
    setValues(
      Object.fromEntries(loaded.map((field) => [field.field_name, initialValue(field)])),
    );
  }, [documentId, token]);

  useEffect(() => {
    if (!token || !documentId) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    setLoadErrorStatus(null);
    Promise.all([getDocument(token, documentId), getExtractedFields(token, documentId)])
      .then(([loadedDocument, loadedFields]) => {
        if (!active) return;
        setDocument(loadedDocument);
        setFields(loadedFields);
        setValues(
          Object.fromEntries(
            loadedFields.map((field) => [field.field_name, initialValue(field)]),
          ),
        );
      })
      .catch((caughtError: unknown) => {
        if (active) {
          setError(messageFrom(caughtError, "Unable to load extracted fields."));
          setLoadErrorStatus(caughtError instanceof ApiError ? caughtError.status : 0);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [documentId, reloadKey, token]);

  async function saveField(
    field: ExtractedField,
    reviewStatus: "confirmed" | "corrected",
  ) {
    if (!token || !documentId) return;
    const confirmedValue = values[field.field_name]?.trim() ?? "";
    if (!confirmedValue) {
      setError(
        dateFields.has(field.field_name)
          ? "Enter a valid date in YYYY-MM-DD format."
          : "Enter a value before saving your review.",
      );
      return;
    }
    setSavingField(field.field_name);
    setError(null);
    setSuccess(null);
    try {
      await updateExtractedFields(token, documentId, [
        {
          field_name: field.field_name,
          confirmed_value: confirmedValue,
          review_status: reviewStatus,
        },
      ]);
      await loadFields();
      setSuccess(`${fieldLabels[field.field_name]} review saved and reloaded.`);
    } catch (caughtError) {
      setError(messageFrom(caughtError, "Unable to save this field review."));
    } finally {
      setSavingField(null);
    }
  }

  if (!documentId) {
    return <main className="mx-auto max-w-5xl px-6 py-14">Invalid document.</main>;
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-14">
      <Link className="text-sm text-cyan-300 hover:text-cyan-200" to={`/documents/${documentId}`}>
        &larr; Back to document details
      </Link>
      <section className="mt-5 rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Human verification
        </p>
        <h1 className="mt-3 text-3xl font-bold">Review extracted fields</h1>
        <p className="mt-2 text-slate-400">
          {document?.original_filename ?? "Document"}. OCR and parsing results are
          suggestions only. Confirm each correct value or save an explicit correction.
        </p>

        <div className="mt-5" aria-live="polite">
          {error && <p className="text-sm text-rose-300" role="alert">{error}</p>}
          {success && <p className="text-sm text-emerald-300" role="status">{success}</p>}
        </div>

        {loading ? (
          <p className="mt-8 text-slate-400">Loading extracted fields...</p>
        ) : loadErrorStatus !== null ? (
          <div className="mt-8 rounded-2xl border border-rose-900/70 bg-slate-950 p-5">
            <p className="text-sm font-semibold text-rose-300">
              {loadErrorStatus === 403
                ? "Access forbidden"
                : loadErrorStatus === 404
                  ? "Document not found"
                  : "Unable to load extraction results"}
            </p>
            {loadErrorStatus !== 403 && loadErrorStatus !== 404 && (
              <button
                className="secondary-button mt-4 text-sm"
                type="button"
                onClick={() => setReloadKey((key) => key + 1)}
              >
                Retry
              </button>
            )}
          </div>
        ) : fields.length === 0 ? (
          <p className="mt-8 rounded-2xl bg-slate-950 p-5 text-amber-200">
            No readable fields were extracted. Check the document quality or re-upload it.
          </p>
        ) : (
          <ul className="mt-8 space-y-5">
            {fields.map((field) => {
              const candidate = field.normalized_value ?? field.raw_value;
              const enteredValue = values[field.field_name] ?? "";
              const isSaving = savingField === field.field_name;
              const matchesCandidate = Boolean(
                candidate && enteredValue.trim() === candidate.trim(),
              );
              return (
                <li className="rounded-2xl border border-slate-800 bg-slate-950 p-5" key={field.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="font-semibold">{fieldLabels[field.field_name]}</h2>
                      <p className="mt-1 text-sm text-slate-400">
                        Original: <span className="text-slate-200">{field.raw_value ?? "Unknown or unreadable"}</span>
                      </p>
                      {field.normalized_value && field.normalized_value !== field.raw_value && (
                        <p className="mt-1 text-sm text-slate-400">
                          Normalized candidate: <span className="text-slate-200">{field.normalized_value}</span>
                        </p>
                      )}
                      {field.confirmed_value && (
                        <p className="mt-1 text-sm text-slate-400">
                          Vendor-confirmed: <span className="font-medium text-emerald-200">{field.confirmed_value}</span>
                        </p>
                      )}
                    </div>
                    <span className="rounded-full bg-slate-800 px-3 py-1 text-xs capitalize text-slate-300">
                      {field.review_status}
                    </span>
                  </div>
                  {field.review_note && (
                    <p className="mt-3 rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-amber-200">
                      {field.review_note}
                    </p>
                  )}
                  {dateFields.has(field.field_name) && !field.normalized_value && (
                    <p className="mt-3 text-sm text-amber-200">
                      This date could not be normalized. Enter an unambiguous date before saving.
                    </p>
                  )}
                  <label className="mt-4 block" htmlFor={`field-${field.field_name}`}>
                    <span className="mb-2 block text-sm font-medium text-slate-300">
                      Verified value{dateFields.has(field.field_name) ? " (YYYY-MM-DD)" : ""}
                    </span>
                    <input
                      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3"
                      id={`field-${field.field_name}`}
                      type={dateFields.has(field.field_name) ? "date" : "text"}
                      value={enteredValue}
                      onChange={(event) =>
                        setValues((current) => ({
                          ...current,
                          [field.field_name]: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      className="primary-button text-sm"
                      disabled={isSaving || !matchesCandidate}
                      type="button"
                      onClick={() => saveField(field, "confirmed")}
                    >
                      {isSaving ? "Saving..." : "Confirm extracted value"}
                    </button>
                    <button
                      className="secondary-button text-sm"
                      disabled={isSaving || matchesCandidate}
                      type="button"
                      onClick={() => saveField(field, "corrected")}
                    >
                      {isSaving ? "Saving..." : "Save correction"}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
