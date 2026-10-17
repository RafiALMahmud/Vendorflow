import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

type StoredListener = EventListenerOrEventListenerObject;

class FakeXMLHttpRequest {
  static instance: FakeXMLHttpRequest | null = null;
  status = 0;
  responseText = "";
  body: XMLHttpRequestBodyInit | null = null;
  method = "";
  url = "";
  headers = new Map<string, string>();
  private listeners = new Map<string, StoredListener>();
  private progressListener: StoredListener | null = null;
  upload = {
    addEventListener: (_type: string, listener: StoredListener) => {
      this.progressListener = listener;
    },
  };

  constructor() {
    FakeXMLHttpRequest.instance = this;
  }

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string) {
    this.headers.set(name, value);
  }

  addEventListener(type: string, listener: StoredListener) {
    this.listeners.set(type, listener);
  }

  send(body: XMLHttpRequestBodyInit | null) {
    this.body = body;
  }

  emitProgress(loaded: number, total: number) {
    this.callListener(
      this.progressListener,
      new ProgressEvent("progress", { lengthComputable: true, loaded, total }),
    );
  }

  finish(payload: unknown, status = 201) {
    this.status = status;
    this.responseText = JSON.stringify(payload);
    this.callListener(this.listeners.get("load") ?? null, new Event("load"));
  }

  private callListener(listener: StoredListener | null, event: Event) {
    if (typeof listener === "function") listener(event);
    else listener?.handleEvent(event);
  }
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  FakeXMLHttpRequest.instance = null;
});

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
  vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(JSON.stringify([]), {
      status: 200,
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

  const request = FakeXMLHttpRequest.instance;
  expect(request).not.toBeNull();
  act(() => request?.emitProgress(64, 128));
  expect(screen.getByText("50%")).toBeInTheDocument();
  expect(screen.getByLabelText("Document upload progress")).toHaveAttribute(
    "value",
    "50",
  );
  act(() => request?.finish(document));

  expect(
    await screen.findByText("fictional-license.pdf uploaded securely."),
  ).toBeInTheDocument();
  expect(screen.getByText("fictional-license.pdf")).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(request?.method).toBe("POST");
  expect(request?.url).toContain("/documents/upload");
  expect(request?.headers.get("Authorization")).toBe("Bearer signed-test-token");
  expect(request?.headers.has("Content-Type")).toBe(false);
  const formData = request?.body as FormData;
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
  expect(metadata).toHaveTextContent("Uploaded");
  expect(screen.getByRole("button", { name: "Download" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View details" })).toHaveAttribute(
    "href",
    `/documents/${document.id}`,
  );
});
