import { buildAffiliateUrl } from "../affiliate";

describe("buildAffiliateUrl", () => {
  it("should append UTM parameters to a valid URL", () => {
    const result = buildAffiliateUrl({
      sourceUrl: "https://example.com/product/123?color=blue",
      sourceName: "Example Store",
      campaign: "test_campaign",
    });

    expect(result).toContain("utm_source=vton_mvp");
    expect(result).toContain("utm_medium=app");
    expect(result).toContain("utm_campaign=test_campaign");
    expect(result).toContain("utm_content=Example+Store");
    expect(result).toContain("color=blue");
  });

  it("should return the original URL when the source URL is invalid", () => {
    const sourceUrl = "not-a-valid-url";
    const result = buildAffiliateUrl({ sourceUrl, sourceName: "Example" });

    expect(result).toBe(sourceUrl);
  });

  it("should return null when no source URL is provided", () => {
    const result = buildAffiliateUrl({ sourceUrl: null });
    expect(result).toBeNull();
  });
});
