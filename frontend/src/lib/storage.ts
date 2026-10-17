const KEY = "proveniq.licenseTrail.v1";

export type AssetMeta = {
  assetType: string;
  confirmed: boolean;
};

type Store = {
  version: 1;
  assets: Record<string, AssetMeta>;
};

const empty = (): Store => ({ version: 1, assets: {} });

export function readStore(): { store: Store; warning: string | null } {
  if (typeof window === "undefined") return { store: empty(), warning: null };
  const raw = window.localStorage.getItem(KEY);
  if (!raw) return { store: empty(), warning: null };
  try {
    const parsed = JSON.parse(raw) as Partial<Store>;
    if (parsed.version !== 1 || !parsed.assets || typeof parsed.assets !== "object") {
      window.localStorage.removeItem(KEY);
      return { store: empty(), warning: "Saved browser data was invalid and has been cleared." };
    }
    return { store: { version: 1, assets: parsed.assets }, warning: null };
  } catch {
    window.localStorage.removeItem(KEY);
    return { store: empty(), warning: "Saved browser data could not be read and has been cleared." };
  }
}

export function writeAssetMeta(assetId: string, meta: AssetMeta) {
  const { store } = readStore();
  store.assets[assetId] = meta;
  window.localStorage.setItem(KEY, JSON.stringify(store));
}

export function readAssetMeta(assetId: string): AssetMeta {
  const { store } = readStore();
  const meta = store.assets[assetId];
  if (!meta || typeof meta.assetType !== "string" || typeof meta.confirmed !== "boolean") {
    return { assetType: "", confirmed: false };
  }
  return meta;
}
