import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = process.cwd();
const outputRoot = `${repoRoot}/outputs/major_revision`;
const payload = JSON.parse(
  await fs.readFile(`${outputRoot}/workbook_payload.json`, "utf8"),
);

function columnName(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    value -= 1;
    result = String.fromCharCode(65 + (value % 26)) + result;
    value = Math.floor(value / 26);
  }
  return result;
}

function cleanValue(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "number" && !Number.isFinite(value)) return null;
  if (typeof value === "object") return JSON.stringify(value);
  return value;
}

const workbook = Workbook.create();
const previewRanges = [];
for (const [sheetName, sheetPayload] of Object.entries(payload.sheets)) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const columns = sheetPayload.columns;
  const matrix = [
    columns,
    ...sheetPayload.rows.map((row) =>
      columns.map((column) => cleanValue(row[column])),
    ),
  ];
  const lastColumn = columnName(columns.length - 1);
  const lastRow = matrix.length;
  const range = sheet.getRange(`A1:${lastColumn}${lastRow}`);
  range.values = matrix;
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: "#174A5B",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "center",
    borders: {
      bottom: { style: "medium", color: "#0F2F3A" },
    },
  };
  sheet.getRange(`A1:${lastColumn}1`).format.rowHeight = 30;
  if (lastRow > 1) {
    sheet.getRange(`A2:${lastColumn}${lastRow}`).format = {
      font: { color: "#1F2933" },
      verticalAlignment: "top",
      borders: {
        insideHorizontal: { style: "hair", color: "#D9E2E7" },
      },
    };
  }
  for (let index = 0; index < columns.length; index += 1) {
    const column = columnName(index);
    const sample = matrix
      .slice(0, Math.min(matrix.length, 250))
      .map((row) => String(row[index] ?? ""));
    const width = Math.min(
      42,
      Math.max(9, ...sample.map((value) => Math.min(value.length + 2, 42))),
    );
    sheet.getRange(`${column}1:${column}${lastRow}`).format.columnWidth = width;
    if (
      columns[index].includes("source") ||
      columns[index].includes("reason") ||
      columns[index].includes("limitation") ||
      columns[index].includes("blocker") ||
      columns[index].includes("effect") ||
      columns[index].includes("resolution") ||
      columns[index] === "value"
    ) {
      sheet.getRange(`${column}1:${column}${lastRow}`).format.wrapText = true;
    }
    if (
      columns[index].includes("rate") ||
      columns[index].includes("accuracy") ||
      columns[index].includes("gap") ||
      columns[index].includes("mean") ||
      columns[index].includes("std") ||
      columns[index].includes("ci95") ||
      columns[index].includes("p_value")
    ) {
      sheet.getRange(`${column}2:${column}${lastRow}`).format.numberFormat =
        "0.0000";
    }
  }
  sheet.freezePanes.freezeRows(1);
  if (lastRow > 1 && columns.length > 1) {
    const tableName = `${sheetName.replace(/[^A-Za-z0-9]/g, "")}Table`;
    const table = sheet.tables.add(
      `A1:${lastColumn}${lastRow}`,
      true,
      tableName,
    );
    table.style = "TableStyleMedium2";
    table.showBandedRows = true;
    table.showFilterButton = true;
  }
  previewRanges.push({
    sheetName,
    range: `A1:${lastColumn}${Math.min(lastRow, 12)}`,
  });
}

const readme = workbook.worksheets.getItem("README");
const readmeRows = payload.sheets.README.rows.length + 1;
readme.getRange(`A1:B${readmeRows}`).format.rowHeight = 28;
readme.getRange(`A2:A${readmeRows}`).format.font = { bold: true, color: "#174A5B" };
readme.getRange(`B2:B${readmeRows}`).format.wrapText = true;

const inspection = await workbook.inspect({
  kind: "table",
  sheetId: "README",
  range: `A1:B${readmeRows}`,
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 4,
});
process.stdout.write(`${inspection.ndjson}\n`);
for (const [sheetId, range] of [
  ["Policy_Approval", "A1:K9"],
  ["Paired_Inference", "A1:Q25"],
  ["Scaling_Summary", "A1:P16"],
]) {
  const evidenceInspection = await workbook.inspect({
    kind: "table",
    sheetId,
    range,
    include: "values,formulas",
    tableMaxRows: 25,
    tableMaxCols: 17,
  });
  process.stdout.write(`${evidenceInspection.ndjson}\n`);
}
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
process.stdout.write(`${errors.ndjson}\n`);

const previewDirectory = `${outputRoot}/workbook_previews`;
await fs.rm(previewDirectory, { recursive: true, force: true });
await fs.mkdir(previewDirectory, { recursive: true });
for (let index = 0; index < previewRanges.length; index += 1) {
  const { sheetName, range } = previewRanges[index];
  const preview = await workbook.render({
    sheetName,
    range,
    scale: 0.8,
    format: "png",
  });
  const filename = `${String(index + 1).padStart(2, "0")}-${sheetName}.png`;
  await fs.writeFile(
    `${previewDirectory}/${filename}`,
    new Uint8Array(await preview.arrayBuffer()),
  );
}
await fs.copyFile(
  `${previewDirectory}/01-README.png`,
  `${outputRoot}/workbook_preview.png`,
);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputRoot}/FairAI_Major_Revision_Results.xlsx`);
