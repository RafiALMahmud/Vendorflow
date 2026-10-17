import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import type { AuthUser } from "../../shared/api";
import { AuthContext } from "../auth/auth-context";
import { VendorProfilePage } from "./VendorProfilePage";

const user: AuthUser = {
  id: "10000000-0000-4000-8000-000000000001",
  email: "vendor@example.com",
  full_name: "Fictional Vendor",
  role: "vendor",
  created_at: "2026-10-17T00:00:00Z",
};

const profile = {
  id: "20000000-0000-4000-8000-000000000001",
  owner_user_id: user.id,
  company_name: "Example Trading Ltd",
  registration_number: "REG-001",
  contact_email: "operations@example.com",
  phone: "+880 1700-000000",
  address: "100 Fictional Commerce Road, Dhaka",
  created_at: "2026-10-17T00:00:00Z",
  updated_at: "2026-10-17T00:00:00Z",
};

afterEach(() => vi.restoreAllMocks());

function renderProfile() {
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
        <VendorProfilePage />
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

test("loads the setup form and creates a vendor profile", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Vendor profile not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(profile), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );

  renderProfile();
  expect(screen.getByText("Loading vendor profile…")).toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: "Set up company profile" }),
  ).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Company name"), {
    target: { value: profile.company_name },
  });
  fireEvent.change(screen.getByLabelText("Registration number"), {
    target: { value: profile.registration_number },
  });
  fireEvent.change(screen.getByLabelText("Contact email"), {
    target: { value: profile.contact_email },
  });
  fireEvent.change(screen.getByLabelText("Phone"), {
    target: { value: profile.phone },
  });
  fireEvent.change(screen.getByLabelText("Address"), {
    target: { value: profile.address },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create profile" }));

  expect(await screen.findByText("Profile saved successfully.")).toBeInTheDocument();
  const createRequest = fetchMock.mock.calls[1];
  expect(createRequest[0]).toContain("/vendors/me");
  expect(createRequest[1]?.method).toBe("POST");
  expect((createRequest[1]?.headers as Headers).get("Authorization")).toBe(
    "Bearer signed-test-token",
  );
});

test("loads and edits an existing vendor profile", async () => {
  const updatedProfile = { ...profile, company_name: "Example Trading Updated" };
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify(profile), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(updatedProfile), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

  renderProfile();
  expect(
    await screen.findByRole("heading", { name: "Edit company profile" }),
  ).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Company name"), {
    target: { value: updatedProfile.company_name },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(fetchMock.mock.calls[1][1]?.method).toBe("PATCH");
  expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body)).company_name).toBe(
    "Example Trading Updated",
  );
  expect(await screen.findByText("Profile saved successfully.")).toBeInTheDocument();
});

test("does not mistake a network failure for a missing profile", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new TypeError("offline"))
    .mockResolvedValueOnce(
      new Response(JSON.stringify(profile), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

  renderProfile();

  expect(
    await screen.findByRole("heading", { name: "Unable to load company profile" }),
  ).toBeInTheDocument();
  expect(screen.getByText(/Network error/)).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Set up company profile" }),
  ).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("heading", { name: "Edit company profile" }),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});
