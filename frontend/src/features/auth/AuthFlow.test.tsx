import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";

import { AppRoutes } from "../../App";
import { AuthProvider } from "./AuthProvider";

afterEach(() => {
  vi.restoreAllMocks();
});

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </MemoryRouter>,
  );
}

test("redirects an unauthenticated visitor away from the dashboard", async () => {
  renderAt("/dashboard");

  expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
});

test("logs in through the API, opens the protected page, and logs out", async () => {
  const fetchMock = vi
    .spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: "signed-test-token",
          token_type: "bearer",
          expires_in: 1800,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "10000000-0000-4000-8000-000000000001",
          email: "vendor@example.com",
          full_name: "Fictional Vendor",
          role: "vendor",
          created_at: "2026-10-17T00:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

  renderAt("/login");
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "vendor@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "correct-horse-battery-staple" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(
    await screen.findByRole("heading", { name: "Hello, Fictional Vendor" }),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
  const meRequest = fetchMock.mock.calls[1];
  expect(meRequest[0]).toContain("/auth/me");
  expect((meRequest[1]?.headers as Headers).get("Authorization")).toBe(
    "Bearer signed-test-token",
  );

  fireEvent.click(screen.getAllByRole("button", { name: "Log out" })[0]);
  expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
});

test("registers a vendor through the API and returns to sign in", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(
      JSON.stringify({
        id: "10000000-0000-4000-8000-000000000001",
        email: "new@example.com",
        full_name: "New Vendor",
        role: "vendor",
        created_at: "2026-10-17T00:00:00Z",
      }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    ),
  );

  renderAt("/register");
  fireEvent.change(screen.getByLabelText("Full name"), {
    target: { value: "New Vendor" },
  });
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "new@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "a-long-vendor-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));

  expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  const requestBody = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
  expect(requestBody).toEqual({
    full_name: "New Vendor",
    email: "new@example.com",
    password: "a-long-vendor-password",
  });
  expect(requestBody).not.toHaveProperty("role");
});
