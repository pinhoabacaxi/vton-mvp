import { addSavedLook, clearSavedLooks, loadSavedLooks, saveSavedLooks } from "../lookStorage";

const sampleLook = {
  id: "test-1",
  created_at: new Date().toISOString(),
  title: "Teste",
  mannequin: { body_type: "standard", height_cm: 170, hip_cm: 90, waist_cm: 70, chest_cm: 90 } as any,
  garment: null,
  front_render: null,
  fit_zones: [],
  vton_payload: null,
  vton_result: { result_url: "https://example.com/1.png", provider: "mock", mode_requested: "test", used_fallback: false, success: true, message: "ok" } as any,
  source: null,
};

describe("lookStorage", () => {
  beforeEach(async () => {
    await clearSavedLooks();
  });

  it("should return an empty array when storage is empty", async () => {
    const looks = await loadSavedLooks();
    expect(looks).toEqual([]);
  });

  it("should save and load saved looks", async () => {
    await saveSavedLooks([sampleLook]);
    const looks = await loadSavedLooks();
    expect(looks).toHaveLength(1);
    expect(looks[0].id).toBe(sampleLook.id);
  });

  it("should append a new look at the beginning using addSavedLook", async () => {
    await saveSavedLooks([sampleLook]);

    const anotherLook = { ...sampleLook, id: "test-2", title: "Outro" };
    const updated = await addSavedLook(anotherLook as any);

    expect(updated[0].id).toBe("test-2");
    expect(updated[1].id).toBe("test-1");
  });
});
