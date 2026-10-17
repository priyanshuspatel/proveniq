export function reportFilename(projectId: string, version: number): string {
  return `proveniq-${projectId}-v${version}.md`;
}

export async function saveGeneratedReport(
  markdown: string | null | undefined,
  filename: string,
  writeFile: (filename: string, markdown: string) => Promise<boolean>,
): Promise<string> {
  if (!markdown || !markdown.trim()) {
    throw new Error("The report was not generated.");
  }
  const saved = await writeFile(filename, markdown);
  if (!saved) {
    throw new Error("The report file was not saved.");
  }
  return filename;
}

export async function writeMarkdownInBrowser(filename: string, markdown: string): Promise<boolean> {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  if (blob.size === 0) return false;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  let readable = false;
  try {
    readable = (await fetch(url).then((response) => response.text())) === markdown;
  } catch {
    readable = false;
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  return readable;
}
