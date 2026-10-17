import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import type { AuthUser, VendorDocument } from "../../shared/api";
import { AuthContext } from "../auth/auth-context";
import { DocumentsPage } from "./DocumentsPage";

const user: AuthUser = {
  id: "10000000-0000-4000-8000-000000000001",
  email: "vendor@example.com",
  full_name: "Fictional Vendor",
  role: "vendor",
  created_at: "2026-10-17T00:00:00Z",
};

const document: VendorDocument = {
  id: "30000000-0000-4000-8000-000000000001",
  vendor_id: "20000000-0000-4000-8000-000000000001",
  document_type: "trade_license",
  original_filename: "fictional-license.pdf",
  mime_type: "application/pdf",
  file_size: 128,
  processing_status: "uploaded",
  processing_error: null,
  created_at: "2026-10-17T00:00:00Z",
  updated_at: "2026-10-17T00:00:00Z",
};

afterEach(() => vi.restoreAllMocks());

function renderDocuments() {
  return render(
    <MemoryRouter>
      <AuthContext.Provider
        value={{
          user,
          token: "signed-test-token",
          login: vi.fn(),
          logout: vi.fn(),
        }}
      >
        <DocumentsPage />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

test("loads an empty list and uploads a real multipart request", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(document), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

  renderDocuments();
  expect(screen.getByText("Loading documents…")).toBeInTheDocument();
  expect(await screen.findByText("No documents uploaded yet.")).toBeInTheDocument();

  const file = new File(["fictional-pdf"], document.original_filename, {
    type: document.mime_type,
  });
  fireEvent.change(screen.getByLabelText("File"), {
    target: { files: [file] },
  });
  const uploadButton = screen.getByRole("button", { name: "Upload document" });
  fireEvent.submit(uploadButton.closest("form") as HTMLFormElement);

  expect(
    await screen.findByText("fictional-license.pdf uploaded securely."),
  ).toBeInTheDocument();
  expect(screen.getByText("fictional-license.pdf")).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  const uploadRequest = fetchMock.mock.calls[1][1];
  expect(uploadRequest?.method).toBe("POST");
  expect((uploadRequest?.headers as Headers).get("Authorization")).toBe(
    "Bearer signed-test-token",
  );
  expect((uploadRequest?.headers as Headers).has("Content-Type")).toBe(false);
  const formData = uploadRequest?.body as FormData;
  expect(formData.get("document_type")).toBe("trade_license");
  expect((formData.get("file") as File).name).toBe("fictional-license.pdf");
});

test("renders document metadata returned by the list API", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(JSON.stringify([document]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

  renderDocuments();

  expect(await screen.findByText("fictional-license.pdf")).toBeInTheDocument();
  const metadata = screen.getByText((_, element) =>
    Boolean(
      element?.tagName === "P" &&
        element.textContent?.includes("Trade license") &&
        element.textContent.includes("128 B"),
    ),
  );
  expect(metadata).toHaveTextContent("uploaded");
  expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
});
