import type { IntendedUse } from "./types";

export type DemoExample = {
  id: string;
  label: string;
  note: string;
  title: string;
  assetType: string;
  creator: string;
  sourceUrl: string;
  declaredLicense: string;
  licenseText: string;
  intendedUse: IntendedUse;
};

export const DEMO_EXAMPLES: DemoExample[] = [
  {
    id: "recognized",
    label: "Recognized license",
    note: "Example only. Not a verified assessment of a real asset.",
    title: "Example wordmark",
    assetType: "image",
    creator: "Example Studio",
    sourceUrl: "https://example.com/wordmark",
    declaredLicense: "CC-BY-4.0",
    licenseText: "This work is licensed under CC-BY-4.0 by Example Studio.",
    intendedUse: "noncommercial",
  },
  {
    id: "conflict",
    label: "Potential conflict",
    note: "Example only. Not a verified assessment of a real asset.",
    title: "Example campaign still",
    assetType: "image",
    creator: "Example Studio",
    sourceUrl: "https://example.com/campaign",
    declaredLicense: "CC-BY-NC-4.0",
    licenseText: "This work is licensed under CC-BY-NC-4.0 by Example Studio.",
    intendedUse: "commercial",
  },
  {
    id: "unknown",
    label: "Unknown license",
    note: "Example only. Not a verified assessment of a real asset.",
    title: "Example sketch",
    assetType: "illustration",
    creator: "",
    sourceUrl: "https://example.com/sketch",
    declaredLicense: "studio-custom",
    licenseText: "Internal studio draft. No standard license is named here.",
    intendedUse: "client-delivery-as-is",
  },
];
