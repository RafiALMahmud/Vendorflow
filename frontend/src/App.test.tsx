import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

test("shows the backend health result", async () => {
  window.history.pushState({}, "", "/");
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "ok",
        service: "VendorFlow AI",
        environment: "test",
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );

  render(<App />);

  expect(screen.getByRole("heading", { name: "VendorFlow AI" })).toBeInTheDocument();
  expect(await screen.findByText("Backend online")).toBeInTheDocument();
  expect(screen.getByText("VendorFlow AI · test")).toBeInTheDocument();
});

