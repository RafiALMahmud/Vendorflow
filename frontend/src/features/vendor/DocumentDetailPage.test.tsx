import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import type { AuthUser, ExtractedField, VendorDocument } from "../../shared/api";
import { AuthContext } from "../auth/auth-context";
import { DocumentDetailPage } from "./DocumentDetailPage";

const documentId = "30000000-0000-4000-8000-000000000001";
const user: AuthUser = {
  id: "10000000-0000-4000-8000-000000000001",
  email: "vendor@example.com",
  full_name: "Fictional Vendor",
  role: "vendor",
  created_at: "2026-10-17T00:00:00Z",
};
const document: VendorDocument = {
  id: documentId,
  vendor_id: "20000000-0000-4000-8000-000000000001",
  document_type: "trade_license",
  original_filename: "fictional-license.pdf",
  mime_type: "application/pdf",
  file_size: 2048,
  processing_status: "processed",
  processing_error: null,
  created_at: "2026-10-17T00:00:00Z",
  updated_at: "2026-10-17T00:00:00Z",
};
const field: ExtractedField = {
  id: "40000000-0000-4000-8000-000000000001",
  document_id: documentId,
  field_name: "registration_number",
  raw_value: "REG-001",
  normalized_value: null,
  confirmed_value: "REG-001",
  review_status: "confirmed",
  extraction_method: "pdf_text",
  review_note: null,
  created_at: "2026-10-17T00:00:01Z",
  updated_at: "2026-10-17T00:01:00Z",
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={[`/documents/${documentId}`]}>
      <AuthContext.Provider
        value={{ user, token: "signed-test-token", login: vi.fn(), logout: vi.fn() }}
      >
        <Routes>
          <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

test("renders document metadata and review progress from real API responses", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response(document))
    .mockResolvedValueOnce(response([field]));

  renderDetail();

  expect(
    await screen.findByRole("heading", { name: "fictional-license.pdf" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Trade license")).toBeInTheDocument();
  expect(screen.getByText("2.0 KB")).toBeInTheDocument();
  expect(screen.getByText("1 of 1")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Review extracted fields" })).toHaveAttribute(
    "href",
    `/documents/${documentId}/review`,
  );
  expect(screen.getByRole("button", { name: "Download original" })).toBeInTheDocument();
});

test("renders an ownership-safe not-found state", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response({ detail: "Document not found" }, 404))
    .mockResolvedValueOnce(response({ detail: "Document not found" }, 404));

  renderDetail();

  expect(
    await screen.findByRole("heading", { name: "Unable to load document" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Not found")).toBeInTheDocument();
  expect(screen.getByText("Document not found")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
});
