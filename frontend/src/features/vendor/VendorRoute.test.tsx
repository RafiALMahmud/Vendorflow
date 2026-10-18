import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, test, vi } from "vitest";

import type { AuthUser } from "../../shared/api";
import { AuthContext } from "../auth/auth-context";
import { VendorRoute } from "./VendorRoute";

test("shows a forbidden state to an authenticated non-vendor", () => {
  const admin: AuthUser = {
    id: "10000000-0000-4000-8000-000000000009",
    email: "admin@example.com",
    full_name: "Fictional Admin",
    role: "admin",
    created_at: "2026-10-17T00:00:00Z",
  };

  render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <AuthContext.Provider
        value={{ user: admin, token: "admin-token", login: vi.fn(), logout: vi.fn() }}
      >
        <Routes>
          <Route element={<VendorRoute />}>
            <Route path="/dashboard" element={<p>private vendor content</p>} />
          </Route>
        </Routes>
      </AuthContext.Provider>
    </MemoryRouter>,
  );

  expect(screen.getByRole("heading", { name: "Vendor access required" })).toBeInTheDocument();
  expect(screen.getByText("Forbidden")).toBeInTheDocument();
  expect(screen.queryByText("private vendor content")).not.toBeInTheDocument();
});
