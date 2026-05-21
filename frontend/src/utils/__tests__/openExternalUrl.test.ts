import { Linking } from "react-native";
import { getPreferredBuyUrl, normalizeUrl, openExternalUrl } from "../openExternalUrl";

describe("openExternalUrl", () => {
  beforeEach(() => {
    jest.spyOn(Linking, "canOpenURL").mockResolvedValue(true);
    jest.spyOn(Linking, "openURL").mockResolvedValue(undefined);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("should normalize bare URLs and open them", async () => {
    await openExternalUrl("example.com/test");
    expect(Linking.canOpenURL).toHaveBeenCalledWith("https://example.com/test");
    expect(Linking.openURL).toHaveBeenCalledWith("https://example.com/test");
  });

  it("should throw when URL is missing", async () => {
    await expect(openExternalUrl("")).rejects.toThrow("URL indisponível.");
  });

  it("should throw when Linking cannot open the URL", async () => {
    (Linking.canOpenURL as jest.Mock).mockResolvedValue(false);
    await expect(openExternalUrl("https://example.com")).rejects.toThrow(
      "Não foi possível abrir esta URL."
    );
  });
});

describe("getPreferredBuyUrl", () => {
  it("should prefer affiliate_url over product_url", () => {
    const url = getPreferredBuyUrl({ product_url: "https://original.com", affiliate_url: "https://affiliado.com" });
    expect(url).toBe("https://affiliado.com");
  });

  it("should return product_url when affiliate_url is missing", () => {
    const url = getPreferredBuyUrl({ product_url: "https://original.com" });
    expect(url).toBe("https://original.com");
  });

  it("should return null when source is missing", () => {
    expect(getPreferredBuyUrl(null)).toBeNull();
  });
});
