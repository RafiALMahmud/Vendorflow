import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import type {
  AuthUser,
  ExtractedField,
  VendorDocument,
} from "../../shared/api";
import { AuthContext } from "../auth/auth-context";
import { ExtractionReviewPage } from "./ExtractionReviewPage";

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
  file_size: 128,
  processing_status: "processed",
  processing_error: null,
  created_at: "2026-10-17T00:00:00Z",
  updated_at: "2026-10-17T00:00:00Z",
};

const expiryField: ExtractedField = {
  id: "40000000-0000-4000-8000-000000000001",
  document_id: documentId,
  field_name: "expiry_date",
  raw_value: "17 October 2027",
  normalized_value: "2027-10-17",
  confirmed_value: null,
  review_status: "unreviewed",
  extraction_method: "pdf_text",
  review_note: null,
  created_at: "2026-10-17T00:00:01Z",
  updated_at: "2026-10-17T00:00:01Z",
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderReview() {
  return render(
    <MemoryRouter initialEntries={[`/documents/${documentId}/review`]}>
      <AuthContext.Provider
        value={{
          user,
          token: "signed-test-token",
          login: vi.fn(),
          logout: vi.fn(),
        }}
      >
        <Routes>
          <Route
            path="/documents/:documentId/review"
            element={<ExtractionReviewPage />}
          />
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

afterEach(() => vi.restoreAllMocks());

test("confirms a candidate and reloads the persisted review", async () => {
  const confirmed = {
    ...expiryField,
    confirmed_value: "2027-10-17",
    review_status: "confirmed" as const,
  };
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response(document))
    .mockResolvedValueOnce(response([expiryField]))
    .mockResolvedValueOnce(response([confirmed]))
    .mockResolvedValueOnce(response([confirmed]));

  renderReview();

  expect(await screen.findByText("17 October 2027")).toBeInTheDocument();
  expect(screen.getByText("2027-10-17")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Confirm extracted value" }));

  expect(
    await screen.findByText("Expiry date review saved and reloaded."),
  ).toBeInTheDocument();
  expect(screen.getByText("confirmed")).toBeInTheDocument();
  expect(screen.getByText("Vendor-confirmed:").parentElement).toHaveTextContent(
    "2027-10-17",
  );
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));

  const patchRequest = fetchMock.mock.calls[2][1];
  expect(patchRequest?.method).toBe("PATCH");
  expect((patchRequest?.headers as Headers).get("Authorization")).toBe(
    "Bearer signed-test-token",
  );
  expect(JSON.parse(patchRequest?.body as string)).toEqual({
    fields: [
      {
        field_name: "expiry_date",
        confirmed_value: "2027-10-17",
        review_status: "confirmed",
      },
    ],
  });
  expect(fetchMock.mock.calls[3][0]).toContain(
    `/documents/${documentId}/extracted-fields`,
  );
});

test("saves a correction and clearly displays unreadable values", async () => {
  const unknownField: ExtractedField = {
    ...expiryField,
    id: "40000000-0000-4000-8000-000000000002",
    field_name: "issue_date",
    raw_value: null,
    normalized_value: null,
    review_note: "Date was unreadable and requires human review.",
  };
  const corrected = {
    ...unknownField,
    confirmed_value: "2026-10-17",
    review_status: "corrected" as const,
  };
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(response(document))
    .mockResolvedValueOnce(response([unknownField]))
    .mockResolvedValueOnce(response([corrected]))
    .mockResolvedValueOnce(response([corrected]));

  renderReview();

  expect(await screen.findByText("Unknown or unreadable")).toBeInTheDocument();
  expect(
    screen.getByText("Date was unreadable and requires human review."),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/This date could not be normalized/),
  ).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Verified value (YYYY-MM-DD)"), {
    target: { value: "2026-10-17" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));

  expect(
    await screen.findByText("Issue date review saved and reloaded."),
  ).toBeInTheDocument();
  expect(screen.getByText("corrected")).toBeInTheDocument();
  expect(screen.getByText("Vendor-confirmed:").parentElement).toHaveTextContent(
    "2026-10-17",
  );
  const payload = JSON.parse(fetchMock.mock.calls[2][1]?.body as string);
  expect(payload.fields[0]).toEqual({
    field_name: "issue_date",
    confirmed_value: "2026-10-17",
    review_status: "corrected",
  });
});
