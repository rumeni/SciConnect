import { describe, expect, it } from "vitest";
import { institutionOptionLabel } from "./adminCatalog";
import { translate, type Translate } from "./i18n";
import type { Institution } from "./types";

const institution: Institution = {
  id: 5,
  name: "Research Institute",
  slug: "research-institute",
  city: "Belgrade",
  country: "Serbia",
};

const en: Translate = (key) => translate("en", key);
const sr: Translate = (key) => translate("sr", key);

describe("admin institution selector labels", () => {
  it("includes publication status for active, draft, and archived institutions", () => {
    expect(institutionOptionLabel({ ...institution, status: "active" }, en))
      .toBe("Research Institute (active)");
    expect(institutionOptionLabel({ ...institution, status: "draft" }, en))
      .toBe("Research Institute (draft)");
    expect(institutionOptionLabel({ ...institution, status: "archived" }, sr))
      .toBe("Research Institute (arhivirano)");
  });

  it("keeps public institution names unchanged", () => {
    expect(institutionOptionLabel(institution, sr)).toBe("Research Institute");
  });
});
