import { describe, expect, it } from "vitest";
import { ApiError } from "../src/modules/api-client";

describe("ApiError", () => {
  it("has correct name and status", () => {
    const err = new ApiError(404, "Not found");
    expect(err.name).toBe("ApiError");
    expect(err.status).toBe(404);
    expect(err.detail).toBe("Not found");
    expect(err.message).toBe("Not found");
  });
});
