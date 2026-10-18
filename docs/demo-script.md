# Demo script

About five minutes. Use a machine with the backend, the frontend, and `gemma2:2b` already running. Say at the start that the result is a checklist of declarations and quotations, not a legal clearance.

The buttons named Recognized license, Potential conflict, and Unknown license fill the form with example text. Each one is marked “Example only. Not a verified assessment of a real asset.”

## 1. Add an asset and a license notice

1. Open `http://127.0.0.1:3000`.
2. Create a project named `Demo handoff`. The form label is **Declared intended use**. It starts as Commercial. Change it to Noncommercial. The client label can stay blank.
3. Open the project. The header says `Declared use Noncommercial`. Click **Potential conflict**.
4. The form fills with title `Example campaign still`, type `image`, creator `Example Studio`, source `https://example.com/campaign`, declared license `CC-BY-NC-4.0`, the notice `This work is licensed under CC-BY-NC-4.0 by Example Studio.`, and intended use Commercial.
5. Click **Add asset**. The inventory shows the new row with the stored record status `manual review required`. That label is the default record. It is not a saved assessment.

## 2. Let Gemma read the notice locally

1. Open the asset.
2. Click **Analyze**. The request goes to the local API, which calls Ollama on this computer. No source URL is fetched.
3. When it returns, the extracted section shows a quotation only if that exact string was found once in the notice. A verified license quotation for this example is the sentence containing `CC-BY-NC-4.0`. The typed creator stays in the form. Extraction does not treat the bare phrase “by Example Studio” as a confirmed creator.
4. If Ollama is stopped, the page shows an error and does not show a pass.

## 3. Correct or confirm

1. Compare the form with the extracted lines. The typed creator and the extracted creator are separate.
2. Change anything that is wrong. Editing the form clears confirmation.
3. Click **Confirm fields**. The assessment button stays disabled until this step. Confirming does not run the rules.

## 4. Show a conflict

1. Click **Run assessment**.
2. The result is potential conflict. The reasons include the NonCommercial label paired with commercial use, and the asset use differing from the project’s noncommercial use.
3. Read the sentence that this is not a legal ruling.
4. Optional second beat: go back, add the **Unknown license** example (`studio-custom`, notice `Internal studio draft. No standard license is named here.`), analyze, confirm, and run assessment. The status is unsupported license, with no invented quotation.

A missing-information result is the same path with a CC BY asset whose creator and attribution text are both empty.

## 5. Export the report

1. Return to the project page.
2. Click **Download Markdown Report**.
3. A success message appears after the file is generated and the browser still has the bytes. The file name looks like `proveniq-<project-id>-v1.md`.
4. Open the file. It lists user-typed facts separately from quotations, repeats the disclaimer, and does not say the asset is legally approved.
5. Click **Open the print view**, then **Print or save as PDF**, if you want to show the browser print path. There is no PDF library in the app.

Reload the asset page after the assessment. The quotation and the reasons come back from the API. The reload does not run Analyze or Run assessment again.
