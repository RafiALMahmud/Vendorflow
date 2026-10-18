import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import type { AuthUser, VendorDocument, VendorProfile } from "../../shared/api";
import { AuthContext } from "../auth/auth-context";
import { VendorDashboardPage } from "./VendorDashboardPage";

const user: AuthUser = {
  id: "10000000-0000-4000-8000-000000000001",
  email: "vendor@example.com",
  full_name: "Fictional Vendor",
  role: "vendor",
  created_at: "2026-10-17T00:00:00Z",
};

const profile: VendorProfile = {
  id: "20000000-0000-4000-8000-000000000001",
  owner_user_id: user.id,
  company_name: "Example Trading Ltd",
  registration_number: "REG-001",
  contact_email: "operations@example.com",
  phone: "+880 1700-000000",
  address: "100 Fictional Commerce Road",
  created_at: "2026-10-17T00:00:00Z",
  updated_at: "2026-10-17T00:00:00Z",
};

const documents: VendorDocument[] = [
  {
    id: "30000000-0000-4000-8000-000000000001",
    vendor_id: profile.id,
    document_type: "trade_license",
    original_filename: "license.pdf",
    mime_type: "application/pdf",
    file_size: 128,
    processing_status: "processed",
    processing_error: null,
    created_at: "2026-10-17T00:00:00Z",
    updated_at: "2026-10-17T00:00:00Z",
  },
  {
    id: "30000000-0000-4000-8000-000000000002",
    vendor_id: profile.id,
    document_type: "tax_certificate",
    original_filename: "tax.png",
    mime_type: "image/png",
    file_size: 256,
    processing_status: "failed",
    processing_error: "Image did not contain readable text.",
    created_at: "2026-10-17T00:00:00Z",
    updated_at: "2026-10-17T00:00:00Z",
  },
];

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <AuthContext.Provider
        value={{ user, token: "signed-test-token", login: vi.fn(), logout: vi.fn() }}
      >
        <VendorDashboardPage />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

test("renders only profile and document metrics returned by the APIs", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response(profile))
    .mockResolvedValueOnce(response(documents));

  renderDashboard();

  expect(screen.getByText("Loading your vendor workspace…")).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: "Welcome, Fictional Vendor" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Company profile").parentElement).toHaveTextContent(
    "Complete",
  );
  expect(screen.getByText("Documents").parentElement).toHaveTextContent("2");
  expect(screen.getByText("Processed").parentElement).toHaveTextContent("1");
  expect(screen.getByText("Failed").parentElement).toHaveTextContent("1");
  expect(screen.getByText("Example Trading Ltd")).toBeInTheDocument();
  expect(screen.getByText("Review and submit")).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Manage applications' })).toHaveAttribute('href', '/applications');
});

test("shows a network error and retries with live responses", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(response({ detail: "Vendor profile not found" }, 404))
    .mockResolvedValueOnce(response([]));

  renderDashboard();

  expect(
    await screen.findByText("Network error. Check that the backend is running, then retry."),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));

  expect(
    await screen.findByRole("heading", { name: "Welcome, Fictional Vendor" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Not set up")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(3);
});
