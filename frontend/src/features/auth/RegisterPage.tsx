import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, registerVendor } from "../../shared/api";
import { AuthCard, FormField } from "./LoginPage";

export function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await registerVendor({ full_name: fullName, email, password });
      navigate("/login", { replace: true, state: { registered: true } });
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiError
          ? caughtError.detail
          : "Unable to create the account. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthCard
      title="Create vendor account"
      subtitle="Public registration always creates a vendor role."
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        <FormField
          id="full-name"
          label="Full name"
          type="text"
          value={fullName}
          onChange={setFullName}
          autoComplete="name"
        />
        <FormField
          id="register-email"
          label="Email"
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
        />
        <FormField
          id="register-password"
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          minLength={12}
        />
        <p className="text-xs text-slate-500">
          Use at least 12 characters. Passwords are sent only to the authentication
          endpoint and stored as Argon2 hashes.
        </p>
        {error && (
          <p className="text-sm text-rose-300" role="alert">
            {error}
          </p>
        )}
        <button
          className="primary-button w-full"
          disabled={submitting}
          type="submit"
        >
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-sm text-slate-400">
        Already registered?{" "}
        <Link className="text-cyan-300 hover:text-cyan-200" to="/login">
          Sign in
        </Link>
      </p>
    </AuthCard>
  );
}
