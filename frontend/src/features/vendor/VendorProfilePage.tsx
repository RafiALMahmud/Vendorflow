import { useEffect, useState, type FormEvent } from "react";

import {
  ApiError,
  createVendorProfile,
  getVendorProfile,
  updateVendorProfile,
  type VendorProfile,
  type VendorProfileInput,
} from "../../shared/api";
import { useAuth } from "../auth/useAuth";

const emptyProfile: VendorProfileInput = {
  company_name: "",
  registration_number: "",
  contact_email: "",
  phone: "",
  address: "",
};

type PageState = "loading" | "create" | "edit";

function errorMessage(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.detail : fallback;
}

export function VendorProfilePage() {
  const { token } = useAuth();
  const [pageState, setPageState] = useState<PageState>("loading");
  const [form, setForm] = useState<VendorProfileInput>(emptyProfile);
  const [savedProfile, setSavedProfile] = useState<VendorProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setError(null);
    getVendorProfile(token)
      .then((profile) => {
        if (controller.signal.aborted) return;
        setSavedProfile(profile);
        setForm({
          company_name: profile.company_name,
          registration_number: profile.registration_number,
          contact_email: profile.contact_email,
          phone: profile.phone,
          address: profile.address,
        });
        setPageState("edit");
      })
      .catch((caughtError: unknown) => {
        if (controller.signal.aborted) return;
        if (caughtError instanceof ApiError && caughtError.status === 404) {
          setPageState("create");
          return;
        }
        setError(errorMessage(caughtError, "Unable to load your vendor profile."));
        setPageState("create");
      });
    return () => controller.abort();
  }, [token]);

  function updateField(field: keyof VendorProfileInput, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setSaved(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      const profile =
        pageState === "edit"
          ? await updateVendorProfile(token, form)
          : await createVendorProfile(token, form);
      setSavedProfile(profile);
      setPageState("edit");
      setSaved(true);
    } catch (caughtError) {
      setError(errorMessage(caughtError, "Unable to save your vendor profile."));
    } finally {
      setSubmitting(false);
    }
  }

  if (pageState === "loading") {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14" aria-live="polite">
        <p className="text-slate-300">Loading vendor profile…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-14">
      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Vendor workspace
        </p>
        <h1 className="mt-3 text-3xl font-bold">
          {pageState === "create" ? "Set up company profile" : "Edit company profile"}
        </h1>
        <p className="mt-2 text-slate-400">
          This information identifies your company throughout onboarding.
        </p>

        <form className="mt-8 grid gap-5 sm:grid-cols-2" onSubmit={handleSubmit}>
          <ProfileField
            id="company-name"
            label="Company name"
            value={form.company_name}
            onChange={(value) => updateField("company_name", value)}
            maxLength={200}
          />
          <ProfileField
            id="registration-number"
            label="Registration number"
            value={form.registration_number}
            onChange={(value) => updateField("registration_number", value)}
            maxLength={100}
          />
          <ProfileField
            id="contact-email"
            label="Contact email"
            type="email"
            value={form.contact_email}
            onChange={(value) => updateField("contact_email", value)}
            maxLength={320}
          />
          <ProfileField
            id="phone"
            label="Phone"
            type="tel"
            value={form.phone}
            onChange={(value) => updateField("phone", value)}
            minLength={7}
            maxLength={40}
            pattern="[0-9+().\-\s]{7,40}"
          />
          <label className="block sm:col-span-2" htmlFor="address">
            <span className="mb-2 block text-sm font-medium text-slate-300">Address</span>
            <textarea
              className="min-h-28 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
              id="address"
              maxLength={500}
              required
              value={form.address}
              onChange={(event) => updateField("address", event.target.value)}
            />
          </label>

          <div className="sm:col-span-2" aria-live="polite">
            {error && <p className="mb-4 text-sm text-rose-300" role="alert">{error}</p>}
            {saved && (
              <p className="mb-4 text-sm text-emerald-300" role="status">
                Profile saved successfully.
              </p>
            )}
            <button className="primary-button" disabled={submitting} type="submit">
              {submitting
                ? "Saving…"
                : savedProfile
                  ? "Save changes"
                  : "Create profile"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

function ProfileField({
  id,
  label,
  value,
  onChange,
  type = "text",
  minLength = 1,
  maxLength,
  pattern,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  minLength?: number;
  maxLength: number;
  pattern?: string;
}) {
  return (
    <label className="block" htmlFor={id}>
      <span className="mb-2 block text-sm font-medium text-slate-300">{label}</span>
      <input
        className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20"
        id={id}
        maxLength={maxLength}
        minLength={minLength}
        pattern={pattern}
        required
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
