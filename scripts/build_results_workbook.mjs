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

const FIGURE_SHEETS = [
  "Fig01_Core_Accuracy",
  "Fig02_Core_Fairness",
  "Fig03_FairFed",
  "Fig04_MLP_Sensitivity",
  "Fig05_Policy_Approval",
  "Fig06_Client_Scaling",
  "Fig07_IPFS_Overhead",
  "Fig08_Proof_Gas",
  "Fig09_Security_Trust",
  "Fig10_Poisoning",
  "Fig11_All_Fairness",
  "Fig12_Controlled_Baselines",
  "Fig13_Stage_Overhead",
  "Fig14_Gas_Batching_Cost",
  "Fig15_Adversarial_Matrix",
  "Fig16_Entropy_Representation",
  "Fig17_Proof_Trust_Paths",
  "Fig18_Privacy_Boundary",
  "Fig19_Ethics_Scope",
  "Fig20_Complexity",
];
const SERIES_COLORS = ["#176B87", "#C35A21", "#3B7A57", "#6B4C9A"];

function sourceFormula(sheetName, criteria, column) {
  const source = payload.sheets[sheetName];
  const rowIndex = source.rows.findIndex((row) =>
    Object.entries(criteria).every(([key, value]) => row[key] === value),
  );
  if (rowIndex < 0) {
    throw new Error(
      `No ${sheetName} row matches ${JSON.stringify(criteria)}`,
    );
  }
  const columnIndex = source.columns.indexOf(column);
  if (columnIndex < 0) {
    throw new Error(`No ${column} column exists in ${sheetName}`);
  }
  return `='${sheetName}'!$${columnName(columnIndex)}$${rowIndex + 2}`;
}

function conditionalAverageFormula(
  sheetName,
  criteriaColumn,
  criteriaValue,
  valueColumn,
) {
  const source = payload.sheets[sheetName];
  const criteriaIndex = source.columns.indexOf(criteriaColumn);
  const valueIndex = source.columns.indexOf(valueColumn);
  if (criteriaIndex < 0 || valueIndex < 0) {
    throw new Error(`Missing conditional-average column in ${sheetName}`);
  }
  const lastRow = source.rows.length + 1;
  const criterion = String(criteriaValue).replaceAll('"', '""');
  return `=AVERAGEIF('${sheetName}'!$${columnName(criteriaIndex)}$2:$${columnName(criteriaIndex)}$${lastRow},"${criterion}",'${sheetName}'!$${columnName(valueIndex)}$2:$${columnName(valueIndex)}$${lastRow})`;
}

function createFigureSheet(name, title, subtitle, sourceNote) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  sheet.getRange("A1:Q1").merge();
  sheet.getRange("A2:Q2").merge();
  sheet.getRange("A3:Q3").merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange("A3").values = [[sourceNote]];
  sheet.getRange("A1:Q1").format = {
    fill: "#174A5B",
    font: { bold: true, color: "#FFFFFF", size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange("A2:Q2").format = {
    fill: "#DDEFF4",
    font: { color: "#174A5B", italic: true },
    wrapText: true,
  };
  sheet.getRange("A3:Q3").format = {
    font: { color: "#52636B", size: 9 },
    wrapText: true,
    borders: { bottom: { style: "thin", color: "#A7BBC3" } },
  };
  sheet.getRange("A1:Q1").format.rowHeight = 30;
  sheet.getRange("A2:Q2").format.rowHeight = 30;
  sheet.getRange("A3:Q3").format.rowHeight = 28;
  sheet.getRange("A1:Q35").format.columnWidth = 11;
  sheet.getRange("A1:A35").format.columnWidth = 24;
  sheet.freezePanes.freezeRows(3);
  return sheet;
}

function writeLinkedTable(sheet, startRow, startColumn, headers, rows) {
  const start = columnName(startColumn);
  const end = columnName(startColumn + headers.length - 1);
  sheet.getRange(`${start}${startRow}:${end}${startRow}`).values = [headers];
  sheet.getRange(`${start}${startRow}:${end}${startRow}`).format = {
    fill: "#174A5B",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "center",
  };
  rows.forEach((row, rowOffset) => {
    row.forEach((cell, columnOffset) => {
      const target = sheet.getCell(
        startRow + rowOffset,
        startColumn + columnOffset,
      );
      if (typeof cell === "string" && cell.startsWith("=")) {
        target.formulas = [[cell]];
      } else {
        target.values = [[cell]];
      }
    });
  });
  const lastRow = startRow + rows.length;
  sheet.getRange(`${start}${startRow + 1}:${end}${lastRow}`).format = {
    borders: { insideHorizontal: { style: "hair", color: "#D9E2E7" } },
    verticalAlignment: "center",
  };
  return `${start}${startRow}:${end}${lastRow}`;
}

function addChart(sheet, type, sourceRange, title, start, end, numberFormat) {
  const chart = sheet.charts.add(type, sheet.getRange(sourceRange));
  chart.title = title;
  chart.titleTextStyle.fontSize = 12;
  chart.hasLegend = true;
  chart.xAxis = { axisType: "textAxis", textStyle: { fontSize: 9 } };
  chart.yAxis = { numberFormatCode: numberFormat, min: 0 };
  chart.series.items.forEach((series, index) => {
    series.fill = SERIES_COLORS[index % SERIES_COLORS.length];
  });
  chart.setPosition(start, end);
  return chart;
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

const coreAccuracy = createFigureSheet(
  FIGURE_SHEETS[0],
  "Figure 1. Core Accuracy Under Strong Heterogeneity",
  "Ten paired seeds; bars show means and the visible table reports sample SD.",
  "Source: Baseline_Comparison, joint Dirichlet alpha=0.3, B0 versus B3.",
);
writeLinkedTable(coreAccuracy, 5, 0, ["Dataset", "B0 mean", "B3 mean", "B0 SD", "B3 SD", "n"], [
  ["Adult", sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "accuracy" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "accuracy" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "n")],
  ["COMPAS", sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "accuracy" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "accuracy" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "n")],
]);
coreAccuracy.getRange("B6:E7").format.numberFormat = "0.0000";
addChart(coreAccuracy, "bar", "A5:C7", "Mean test accuracy", "A10", "J30", "0.00");
previewRanges.push({ sheetName: FIGURE_SHEETS[0], range: "A1:Q31" });

const coreFairness = createFigureSheet(
  FIGURE_SHEETS[1],
  "Figure 2. Core Fairness Gaps Under Strong Heterogeneity",
  "Lower is better; ten paired seeds. Adult uses DP gap and COMPAS uses EOdds gap.",
  "Source: Baseline_Comparison, joint Dirichlet alpha=0.3, B0 versus B3.",
);
writeLinkedTable(coreFairness, 5, 0, ["Dataset / metric", "B0 mean", "B3 mean", "B0 SD", "B3 SD", "n"], [
  ["Adult / DP gap", sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "demographic_parity_gap" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "demographic_parity_gap" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "demographic_parity_gap" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "demographic_parity_gap" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "adult_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "demographic_parity_gap" }, "n")],
  ["COMPAS / EOdds gap", sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "equalized_odds_gap" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "equalized_odds_gap" }, "mean"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "equalized_odds_gap" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B3", metric: "equalized_odds_gap" }, "std"), sourceFormula("Baseline_Comparison", { scenario_id: "compas_core", partition: "joint_dirichlet_0.3", method: "B0", metric: "equalized_odds_gap" }, "n")],
]);
coreFairness.getRange("B6:E7").format.numberFormat = "0.0000";
addChart(coreFairness, "bar", "A5:C7", "Mean fairness gap", "A10", "J30", "0.00");
previewRanges.push({ sheetName: FIGURE_SHEETS[1], range: "A1:Q31" });

const fairFed = createFigureSheet(
  FIGURE_SHEETS[2],
  "Figure 3. FairFed Utility-Fairness Trade-off",
  "Ten seeds; visible tables report sample SD. B5 applies the implemented stateful FairFed rule.",
  "Source: FairFed_Comparison, joint Dirichlet alpha=0.3, B0 versus B5.",
);
writeLinkedTable(fairFed, 5, 0, ["Dataset", "B0 accuracy", "B5 accuracy", "B0 SD", "B5 SD"], [
  ...["adult", "compas"].map((dataset) => [dataset === "adult" ? "Adult" : "COMPAS", sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "mean"), sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B5", metric: "accuracy" }, "mean"), sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B0", metric: "accuracy" }, "std"), sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B5", metric: "accuracy" }, "std")]),
]);
writeLinkedTable(fairFed, 5, 7, ["Dataset", "B0 EO gap", "B5 EO gap", "B0 SD", "B5 SD"], [
  ...["adult", "compas"].map((dataset) => [dataset === "adult" ? "Adult" : "COMPAS", sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B0", metric: "equal_opportunity_gap" }, "mean"), sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B5", metric: "equal_opportunity_gap" }, "mean"), sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B0", metric: "equal_opportunity_gap" }, "std"), sourceFormula("FairFed_Comparison", { suite: dataset, partition: "joint_dirichlet_0.3", method: "B5", metric: "equal_opportunity_gap" }, "std")]),
]);
fairFed.getRange("B6:E7").format.numberFormat = "0.0000";
fairFed.getRange("I6:L7").format.numberFormat = "0.0000";
addChart(fairFed, "bar", "A5:C7", "Mean accuracy", "A10", "H30", "0.00");
addChart(fairFed, "bar", "H5:J7", "Mean equal-opportunity gap", "J10", "Q30", "0.00");
previewRanges.push({ sheetName: FIGURE_SHEETS[2], range: "A1:Q31" });

const mlp = createFigureSheet(
  FIGURE_SHEETS[3],
  "Figure 4. MLP Model-Sensitivity Accuracy",
  "Five seeds under joint Dirichlet alpha=0.3; the large SD values limit generalization.",
  "Source: Statistics, MLP suite, B0/B3/B5.",
);
writeLinkedTable(mlp, 5, 0, ["Method", "Mean accuracy", "SD", "CI95 low", "CI95 high", "n"], [
  ...["B0", "B3", "B5"].map((method) => [method, sourceFormula("Statistics", { suite: "mlp", partition: "joint_dirichlet_0.3", method, metric: "accuracy" }, "mean"), sourceFormula("Statistics", { suite: "mlp", partition: "joint_dirichlet_0.3", method, metric: "accuracy" }, "std"), sourceFormula("Statistics", { suite: "mlp", partition: "joint_dirichlet_0.3", method, metric: "accuracy" }, "ci95_low"), sourceFormula("Statistics", { suite: "mlp", partition: "joint_dirichlet_0.3", method, metric: "accuracy" }, "ci95_high"), sourceFormula("Statistics", { suite: "mlp", partition: "joint_dirichlet_0.3", method, metric: "accuracy" }, "n")]),
]);
mlp.getRange("B6:E8").format.numberFormat = "0.0000";
addChart(mlp, "bar", "A5:B8", "Mean MLP accuracy", "A11", "J30", "0.00");
previewRanges.push({ sheetName: FIGURE_SHEETS[3], range: "A1:Q31" });

const policy = createFigureSheet(
  FIGURE_SHEETS[4],
  "Figure 5. Approval Rate by Policy Strictness",
  "Ten seeds; all-round scope has 50 seed-round observations and final-round scope has 10.",
  "Source: Policy_Approval; lenient, submitted, moderate, and strict profiles.",
);
writeLinkedTable(policy, 5, 0, ["Policy", "All rounds mean", "Final round mean", "All rounds SD", "Final round SD"], [
  ...["lenient", "submitted", "moderate", "strict"].map((profile) => [profile[0].toUpperCase() + profile.slice(1), sourceFormula("Policy_Approval", { policy_profile: profile, aggregation_scope: "all_five_rounds" }, "mean_approval_rate"), sourceFormula("Policy_Approval", { policy_profile: profile, aggregation_scope: "final_round" }, "mean_approval_rate"), sourceFormula("Policy_Approval", { policy_profile: profile, aggregation_scope: "all_five_rounds" }, "std_approval_rate"), sourceFormula("Policy_Approval", { policy_profile: profile, aggregation_scope: "final_round" }, "std_approval_rate")]),
]);
policy.getRange("B6:E9").format.numberFormat = "0.0%";
addChart(policy, "bar", "A5:C9", "Mean approval rate", "A12", "J31", "0%");
previewRanges.push({ sheetName: FIGURE_SHEETS[4], range: "A1:Q32" });

const scaling = createFigureSheet(
  FIGURE_SHEETS[5],
  "Figure 6. Runtime Scaling Across Logical Clients",
  "Five seeds per client count; logical clients executed on one host.",
  "Source: Scaling_Summary, B0/B5/B6 runtime_ms.",
);
writeLinkedTable(scaling, 5, 0, ["Clients", "B0 mean ms", "B5 mean ms", "B6 mean ms", "B0 SD", "B5 SD", "B6 SD"], [
  ...[3, 5, 10, 20, 50].map((clients) => [String(clients), ...["B0", "B5", "B6"].map((method) => sourceFormula("Scaling_Summary", { method, metric: "runtime_ms", client_count: clients }, "mean")), ...["B0", "B5", "B6"].map((method) => sourceFormula("Scaling_Summary", { method, metric: "runtime_ms", client_count: clients }, "std"))]),
]);
scaling.getRange("B6:G10").format.numberFormat = "0.00";
addChart(scaling, "line", "A5:D10", "Mean runtime by logical-client count", "A13", "K32", "0");
previewRanges.push({ sheetName: FIGURE_SHEETS[5], range: "A1:Q33" });

const ipfs = createFigureSheet(
  FIGURE_SHEETS[6],
  "Figure 7. Two-Peer Kubo Storage Overhead",
  "Thirty repetitions per payload size and concurrency condition; local loopback peers.",
  "Source: IPFS_Add, IPFS_Concurrency, and IPFS_Availability.",
);
const payloads = [[1024, "1 KiB"], [10240, "10 KiB"], [102400, "100 KiB"], [1048576, "1 MiB"], [10485760, "10 MiB"]];
writeLinkedTable(ipfs, 5, 0, ["Payload", "Add ms", "Cold get ms", "Warm get ms", "Pin ms", "n"], payloads.map(([bytes, label]) => [label, sourceFormula("IPFS_Add", { payload_bytes: bytes }, "upload_ms_mean"), sourceFormula("IPFS_Add", { payload_bytes: bytes }, "cold_retrieval_ms_mean"), sourceFormula("IPFS_Add", { payload_bytes: bytes }, "warm_retrieval_ms_mean"), sourceFormula("IPFS_Add", { payload_bytes: bytes }, "pin_ms_mean"), sourceFormula("IPFS_Add", { payload_bytes: bytes }, "n")]));
writeLinkedTable(ipfs, 5, 8, ["Concurrency", "Throughput MiB/s", "Elapsed ms", "n"], [1, 5, 10, 20].map((concurrency) => [String(concurrency), sourceFormula("IPFS_Concurrency", { concurrency }, "throughput_mib_s_mean"), sourceFormula("IPFS_Concurrency", { concurrency }, "elapsed_ms_mean"), sourceFormula("IPFS_Concurrency", { concurrency }, "n")]));
writeLinkedTable(ipfs, 11, 8, ["Recovery KPI", "Mean ms"], [["Outage detection", sourceFormula("IPFS_Availability", { payload_bytes: 1048576 }, "outage_retrieval_ms_mean")], ["Peer ready", sourceFormula("IPFS_Availability", { payload_bytes: 1048576 }, "restart_ready_ms_mean")], ["Verified recovery", sourceFormula("IPFS_Availability", { payload_bytes: 1048576 }, "recovery_verified_ms_mean")]]);
ipfs.getRange("I1:I35").format.columnWidth = 26;
ipfs.getRange("B6:E10").format.numberFormat = "0.00";
ipfs.getRange("J6:K9").format.numberFormat = "0.00";
ipfs.getRange("J12:J14").format.numberFormat = "0.00";
addChart(ipfs, "line", "A5:E10", "Sequential operation mean (ms)", "A16", "I34", "0");
addChart(ipfs, "line", "I5:J9", "Mean throughput by concurrency", "J16", "Q34", "0.0");
previewRanges.push({ sheetName: FIGURE_SHEETS[6], range: "A1:Q35" });

const proofGas = createFigureSheet(
  FIGURE_SHEETS[7],
  "Figure 8. Groth16 Time and Local Hardhat Gas",
  "Thirty valid proofs; six negative cases rejected. Gas is local Hardhat evidence.",
  "Source: Proof_Overhead and Gas_By_Function.",
);
writeLinkedTable(proofGas, 5, 0, ["Stage", "Mean ms", "SD ms", "p95 ms", "n"], ["witness", "proof", "verification"].map((stage) => [stage[0].toUpperCase() + stage.slice(1), sourceFormula("Proof_Overhead", { stage }, "mean_ms"), sourceFormula("Proof_Overhead", { stage }, "std_ms"), sourceFormula("Proof_Overhead", { stage }, "p95_ms"), sourceFormula("Proof_Overhead", { stage }, "n")]));
writeLinkedTable(proofGas, 5, 8, ["Operation", "Mean gas", "n"], [["Verify proof", sourceFormula("Gas_By_Function", { operation: "verify_v2_groth16" }, "mean_gas"), sourceFormula("Gas_By_Function", { operation: "verify_v2_groth16" }, "n")], ["Deploy verifier", sourceFormula("Gas_By_Function", { operation: "deploy_v2_groth16_verifier" }, "mean_gas"), sourceFormula("Gas_By_Function", { operation: "deploy_v2_groth16_verifier" }, "n")]]);
proofGas.getRange("B6:D8").format.numberFormat = "0.00";
proofGas.getRange("J6:J7").format.numberFormat = "#,##0";
addChart(proofGas, "bar", "A5:B8", "Mean Groth16 stage time (ms)", "A11", "H30", "0");
addChart(proofGas, "bar", "I5:J7", "Local Hardhat gas", "J11", "Q30", "#,##0");
previewRanges.push({ sheetName: FIGURE_SHEETS[7], range: "A1:Q31" });

const security = createFigureSheet(
  FIGURE_SHEETS[8],
  "Figure 9. Security Controls and Trust-Boundary Outcomes",
  "Observed test-case counts are not probabilities. One authorized-key compromise was accepted by design.",
  "Source: Verifier_Security and Trust_Boundary.",
);
writeLinkedTable(security, 5, 0, ["Control class", "Rejected cases", "Accepted false decisions"], [["Unauthorized signer (A2)", "=COUNTIF('Verifier_Security'!$B$2:$B$16,\"A2\")", null], ["Signed-field/lifecycle mutations (A3)", "=COUNTIF('Verifier_Security'!$B$2:$B$16,\"A3\")", null], ["Replay and nonce reuse (A4)", "=COUNTIF('Verifier_Security'!$B$2:$B$16,\"A4\")", null], ["Authorized-key compromise (A14)", null, "=COUNTIF('Verifier_Security'!$B$2:$B$16,\"A14\")"]]);
writeLinkedTable(security, 5, 8, ["Trust scenario", "On-chain approved", "Aggregated"], [["False metrics", "=IF('Trust_Boundary'!$E$2,1,0)", "=IF('Trust_Boundary'!$F$2,1,0)"], ["Approved artifact unavailable", "=IF('Trust_Boundary'!$E$3,1,0)", "=IF('Trust_Boundary'!$F$3,1,0)"]]);
security.getRange("A1:A32").format.columnWidth = 38;
security.getRange("I1:I32").format.columnWidth = 30;
security.getRange("B6:C9").format.numberFormat = "0";
security.getRange("J6:K7").format.numberFormat = "0";
addChart(security, "bar", "A5:C9", "Observed verifier-security outcomes", "A12", "H31", "0");
addChart(security, "bar", "I5:K7", "Trust-boundary approval and aggregation", "J12", "Q31", "0");
previewRanges.push({ sheetName: FIGURE_SHEETS[8], range: "A1:Q32" });

const poisoning = createFigureSheet(
  FIGURE_SHEETS[9],
  "Figure 10. Bounded Poisoning Accuracy",
  "Five seeds, 20% malicious clients; B6 is coordinate-wise median. Bars show means; SD is visible.",
  "Source: Statistics, adversarial suite. These tests do not establish universal poisoning detection.",
);
const attackLabels = [["none", "No attack"], ["label_flip", "Label flip"], ["sign_flip", "Sign flip"], ["random_weights", "Random weights"]];
writeLinkedTable(poisoning, 5, 0, ["Attack", "B0 mean", "B6 mean", "B0 SD", "B6 SD", "n"], attackLabels.map(([attack, label]) => [label, sourceFormula("Statistics", { suite: "adversarial", method: "B0", metric: "accuracy", attack_type: attack }, "mean"), sourceFormula("Statistics", { suite: "adversarial", method: "B6", metric: "accuracy", attack_type: attack }, "mean"), sourceFormula("Statistics", { suite: "adversarial", method: "B0", metric: "accuracy", attack_type: attack }, "std"), sourceFormula("Statistics", { suite: "adversarial", method: "B6", metric: "accuracy", attack_type: attack }, "std"), sourceFormula("Statistics", { suite: "adversarial", method: "B0", metric: "accuracy", attack_type: attack }, "n")]));
poisoning.getRange("B6:E9").format.numberFormat = "0.0000";
addChart(poisoning, "bar", "A5:C9", "Mean accuracy by attack", "A12", "J31", "0.00");
previewRanges.push({ sheetName: FIGURE_SHEETS[9], range: "A1:Q32" });

const allFairness = createFigureSheet(
  FIGURE_SHEETS[10],
  "Figure 11. All Measured Fairness Criteria",
  "Lower gaps indicate smaller measured disparity; ten paired seeds under joint Dirichlet alpha=0.3.",
  "Source: Baseline_Comparison, B0 versus B3. Calibration and domain-specific metrics were not executed.",
);
const fairnessMetrics = [
  ["DP gap", "demographic_parity_gap"],
  ["EO gap", "equal_opportunity_gap"],
  ["EOdds gap", "equalized_odds_gap"],
  ["Subgroup accuracy gap", "subgroup_accuracy_gap"],
];
for (const [startColumn, scenario, label] of [[0, "adult_core", "Adult"], [8, "compas_core", "COMPAS"]]) {
  writeLinkedTable(allFairness, 5, startColumn, ["Metric", "B0 mean", "B3 mean", "B0 SD", "B3 SD", "n"], fairnessMetrics.map(([metricLabel, metric]) => [
    metricLabel,
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method: "B0", metric }, "mean"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method: "B3", metric }, "mean"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method: "B0", metric }, "std"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method: "B3", metric }, "std"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method: "B0", metric }, "n"),
  ]));
  allFairness.getRange(`${columnName(startColumn + 1)}6:${columnName(startColumn + 4)}9`).format.numberFormat = "0.0000";
  addChart(allFairness, "bar", `${columnName(startColumn)}5:${columnName(startColumn + 2)}9`, `${label}: mean fairness gaps`, startColumn === 0 ? "A12" : "J12", startColumn === 0 ? "H32" : "Q32", "0.00");
}
allFairness.getRange("A1:A33").format.columnWidth = 28;
allFairness.getRange("I1:I33").format.columnWidth = 28;
previewRanges.push({ sheetName: FIGURE_SHEETS[10], range: "A1:Q33" });

const baselines = createFigureSheet(
  FIGURE_SHEETS[11],
  "Figure 12. Controlled Core Baselines and Ablation",
  "B0, B1, and B3 share the core ten-seed design; B2/B4/B5/B6/B7 belong to separate bounded experiments.",
  "Source: Baseline_Comparison, joint Dirichlet alpha=0.3. This sheet does not imply an unexecuted all-method comparison.",
);
for (const [startColumn, scenario, label, fairnessMetric, fairnessLabel] of [
  [0, "adult_core", "Adult", "demographic_parity_gap", "DP gap"],
  [8, "compas_core", "COMPAS", "equalized_odds_gap", "EOdds gap"],
]) {
  writeLinkedTable(baselines, 5, startColumn, ["Method", "Accuracy", "Macro-F1", fairnessLabel, "Runtime ms", "n"], ["B0", "B1", "B3"].map((method) => [
    method,
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method, metric: "accuracy" }, "mean"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method, metric: "macro_f1" }, "mean"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method, metric: fairnessMetric }, "mean"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method, metric: "runtime_ms" }, "mean"),
    sourceFormula("Baseline_Comparison", { scenario_id: scenario, partition: "joint_dirichlet_0.3", method, metric: "accuracy" }, "n"),
  ]));
  baselines.getRange(`${columnName(startColumn + 1)}6:${columnName(startColumn + 3)}8`).format.numberFormat = "0.0000";
  baselines.getRange(`${columnName(startColumn + 4)}6:${columnName(startColumn + 4)}8`).format.numberFormat = "0.00";
  addChart(baselines, "bar", `${columnName(startColumn)}5:${columnName(startColumn + 1)}8`, `${label}: mean accuracy`, startColumn === 0 ? "A11" : "J11", startColumn === 0 ? "H31" : "Q31", "0.00");
}
previewRanges.push({ sheetName: FIGURE_SHEETS[11], range: "A1:Q32" });

const stageOverhead = createFigureSheet(
  FIGURE_SHEETS[12],
  "Figure 13. Measured Workflow Stage Overhead",
  "Stages were instrumented independently across different experimental units; values are not additive end-to-end decomposition.",
  "Source: Stage_Timing. Direct Solidity wall-clock latency was not instrumented and is therefore excluded.",
);
const proofStages = [["Witness generation", "witness_generation"], ["Proof generation", "proof_generation"], ["Off-chain verification", "off_chain_proof_verification"]];
const workflowStages = [
  ["Local training", "local_training"],
  ["Local evaluation", "local_evaluation"],
  ["Fairness computation", "fairness_computation"],
  ["Artifact serialization", "artifact_serialization"],
  ["Kubo add", "kubo_add"],
  ["Consumer retrieval", "consumer_retrieval"],
  ["Contract submission", "contract_submission"],
  ["Approved retrieval", "approved_model_retrieval"],
  ["Aggregation", "aggregation"],
  ["Global publication", "global_publication"],
  ["End-to-end method", "end_to_end_method"],
];
writeLinkedTable(stageOverhead, 5, 0, ["Proof stage", "Mean ms", "SD ms", "p95 ms", "n"], proofStages.map(([label, stage]) => [label, sourceFormula("Stage_Timing", { stage }, "mean_ms"), sourceFormula("Stage_Timing", { stage }, "std_ms"), sourceFormula("Stage_Timing", { stage }, "p95_ms"), sourceFormula("Stage_Timing", { stage }, "n")]));
writeLinkedTable(stageOverhead, 5, 7, ["Workflow stage", "Mean ms", "SD ms", "p95 ms", "n"], workflowStages.map(([label, stage]) => [label, sourceFormula("Stage_Timing", { stage }, "mean_ms"), sourceFormula("Stage_Timing", { stage }, "std_ms"), sourceFormula("Stage_Timing", { stage }, "p95_ms"), sourceFormula("Stage_Timing", { stage }, "n")]));
stageOverhead.getRange("B6:D8").format.numberFormat = "0.00";
stageOverhead.getRange("I6:K16").format.numberFormat = "0.00";
stageOverhead.getRange("A1:A39").format.columnWidth = 28;
stageOverhead.getRange("H1:H39").format.columnWidth = 28;
addChart(stageOverhead, "bar", "A5:B8", "Groth16 stage means (ms)", "A19", "H38", "0");
addChart(stageOverhead, "bar", "H5:I15", "Operational stage means (ms); end-to-end shown in table", "J19", "Q38", "0.0");
previewRanges.push({ sheetName: FIGURE_SHEETS[12], range: "A1:Q39" });

const gasCost = createFigureSheet(
  FIGURE_SHEETS[13],
  "Figure 14. Lifecycle Gas, Batching, and Modeled Cost",
  "Gas is measured on local Hardhat. USD values are modeled at 10 Gwei and USD 2,000/ETH, not public-chain measurements.",
  "Source: Gas_By_Function, Gas_Batching, and Cost_Scenarios.",
);
const lifecycleOperations = [
  ["Create round", "create_round", 1],
  ["Submit model", "submit_model", 1],
  ["Close submissions", "close_submissions", 1],
  ["Start aggregation", "start_aggregation", 1],
  ["Publish global model", "publish_global_model", 1],
  ["Archive round", "archive_round", 1],
  ["Verify Groth16", "verify_v2_groth16", 0],
  ["Deploy Groth16 verifier", "deploy_v2_groth16_verifier", 0],
];
writeLinkedTable(gasCost, 5, 0, ["Operation", "Mean gas", "n"], lifecycleOperations.map(([label, operation, batch_size]) => [label, sourceFormula("Gas_By_Function", { operation, batch_size }, "mean_gas"), sourceFormula("Gas_By_Function", { operation, batch_size }, "n")]));
const batchSizes = [1, 5, 10, 20];
writeLinkedTable(gasCost, 5, 7, ["Batch", "Submit gas", "Publish gas", "Submit modeled USD", "Publish modeled USD"], batchSizes.map((batch_size) => [
  String(batch_size),
  sourceFormula("Gas_Batching", { operation: "submit_model", batch_size }, "mean_gas"),
  sourceFormula("Gas_Batching", { operation: "publish_global_model", batch_size }, "mean_gas"),
  sourceFormula("Cost_Scenarios", { operation: "submit_model", batch_size, gas_price_gwei_assumption: 10, eth_usd_assumption: 2000 }, "modeled_cost_usd"),
  sourceFormula("Cost_Scenarios", { operation: "publish_global_model", batch_size, gas_price_gwei_assumption: 10, eth_usd_assumption: 2000 }, "modeled_cost_usd"),
]));
gasCost.getRange("B6:B13").format.numberFormat = "#,##0";
gasCost.getRange("I6:J9").format.numberFormat = "#,##0";
gasCost.getRange("K6:L9").format.numberFormat = '"$"0.00';
gasCost.getRange("A1:A35").format.columnWidth = 30;
addChart(gasCost, "bar", "A5:B13", "Measured lifecycle gas", "A16", "H35", "#,##0");
addChart(gasCost, "line", "H5:J9", "Measured gas by batch size", "J16", "Q35", "#,##0");
previewRanges.push({ sheetName: FIGURE_SHEETS[13], range: "A1:Q36" });

const adversarial = createFigureSheet(
  FIGURE_SHEETS[14],
  "Figure 15. A1-A14 Adversarial and Failure Matrix",
  "Detected/rejected denotes the executed bounded control outcome; poisoning and trust-boundary non-detections are intentional findings.",
  "Source: Adversarial_Results. Superseded rows point to current evidence in their interpretation column.",
);
const adversarialScenarios = payload.sheets.Adversarial_Results.rows.map((row) => row.scenario);
writeLinkedTable(adversarial, 5, 0, ["Scenario", "Detected", "Rejected", "Evidence epoch", "Observed behavior", "Current interpretation"], adversarialScenarios.map((scenario) => [
  sourceFormula("Adversarial_Results", { scenario }, "scenario"),
  sourceFormula("Adversarial_Results", { scenario }, "detected"),
  sourceFormula("Adversarial_Results", { scenario }, "rejected"),
  sourceFormula("Adversarial_Results", { scenario }, "evidence_epoch"),
  sourceFormula("Adversarial_Results", { scenario }, "observed_behavior"),
  sourceFormula("Adversarial_Results", { scenario }, "current_interpretation"),
]));
adversarial.getRange("A1:A35").format.columnWidth = 38;
adversarial.getRange("D1:D35").format.columnWidth = 24;
adversarial.getRange("E1:F35").format.columnWidth = 48;
adversarial.getRange("A6:F19").format.wrapText = true;
adversarial.getRange("A6:F19").format.rowHeight = 38;
previewRanges.push({ sheetName: FIGURE_SHEETS[14], range: "A1:Q20" });

const entropyRepresentation = createFigureSheet(
  FIGURE_SHEETS[15],
  "Figure 16. Client Entropy and Representation Outcomes",
  "Entropy is measured over 100 client partitions per condition; representation outcomes are derived from measured client decisions.",
  "Source: Entropy and Representation_Fairness. These are associations and diagnostics, not causal estimates.",
);
const partitions = [["IID", "iid"], ["Dirichlet 1.0", "joint_dirichlet_1.0"], ["Dirichlet 0.3", "joint_dirichlet_0.3"]];
writeLinkedTable(entropyRepresentation, 5, 0, ["Partition", "Mean label entropy", "Mean group entropy"], partitions.map(([label, partition]) => [label, conditionalAverageFormula("Entropy", "partition", partition, "label_entropy"), conditionalAverageFormula("Entropy", "partition", partition, "group_entropy")]));
const representationRows = [];
for (const [label, partition] of partitions) {
  for (const minority_heavy of [false, true]) {
    representationRows.push([
      `${label} / ${minority_heavy ? "minority-heavy" : "other"}`,
      sourceFormula("Representation_Fairness", { partition, minority_heavy }, "approval_rate"),
      sourceFormula("Representation_Fairness", { partition, minority_heavy }, "rejection_rate"),
      sourceFormula("Representation_Fairness", { partition, minority_heavy }, "mean_minority_fraction"),
      sourceFormula("Representation_Fairness", { partition, minority_heavy }, "mean_excluded_sample_fraction"),
      sourceFormula("Representation_Fairness", { partition, minority_heavy }, "seeds"),
    ]);
  }
}
writeLinkedTable(entropyRepresentation, 5, 7, ["Group", "Approval", "Rejection", "Minority fraction", "Excluded sample fraction", "Seeds"], representationRows);
entropyRepresentation.getRange("B6:C8").format.numberFormat = "0.0000";
entropyRepresentation.getRange("I6:L11").format.numberFormat = "0.0%";
entropyRepresentation.getRange("A1:A33").format.columnWidth = 26;
entropyRepresentation.getRange("H1:H33").format.columnWidth = 34;
addChart(entropyRepresentation, "bar", "A5:C8", "Mean client entropy", "A14", "H33", "0.00");
addChart(entropyRepresentation, "bar", "H5:J11", "Approval and rejection by representation group", "J14", "Q33", "0%");
previewRanges.push({ sheetName: FIGURE_SHEETS[15], range: "A1:Q34" });

const proofTrust = createFigureSheet(
  FIGURE_SHEETS[16],
  "Figure 17. Proof Path Measurements and Trust Boundary",
  "Direct and signed paths were exercised locally, but they expose different measurements and trust assumptions.",
  "Source: Stage_Timing, Proof_Overhead, Gas_By_Function, Verifier_Security, and Proof_Semantics.",
);
writeLinkedTable(proofTrust, 5, 0, ["Path", "Measured latency ms", "Latency n", "Measured gas", "Gas n", "Observed trust finding", "Evidence class"], [
  ["Off-chain Groth16 verification", sourceFormula("Stage_Timing", { stage: "off_chain_proof_verification" }, "mean_ms"), sourceFormula("Stage_Timing", { stage: "off_chain_proof_verification" }, "n"), null, null, "Thirty valid proofs verified; six negative cases rejected", "measured"],
  ["Direct Solidity Groth16", null, null, sourceFormula("Gas_By_Function", { operation: "verify_v2_groth16", batch_size: 0 }, "mean_gas"), sourceFormula("Gas_By_Function", { operation: "verify_v2_groth16", batch_size: 0 }, "n"), "Wall-clock latency was not instrumented", "measured gas / missing latency"],
  ["EIP-712 signed verifier", sourceFormula("Stage_Timing", { stage: "eip712_decision_signing" }, "mean_ms"), sourceFormula("Stage_Timing", { stage: "eip712_decision_signing" }, "n"), null, null, "One authorized-key compromise was accepted by design", "measured bounded test"],
]);
writeLinkedTable(proofTrust, 5, 9, ["False-metric relation", "Value"], [
  ["Threshold-compliant relation accepted", sourceFormula("Proof_Semantics", { scenario: "A12" }, "proof_relation_accepts")],
  ["Independent metric derivation proved", sourceFormula("Proof_Semantics", { scenario: "A12" }, "independent_metric_derivation_proved")],
  ["False reporting detected", sourceFormula("Proof_Semantics", { scenario: "A12" }, "detected")],
]);
proofTrust.getRange("B6:B8").format.numberFormat = "0.00";
proofTrust.getRange("D6:D8").format.numberFormat = "#,##0";
proofTrust.getRange("A1:A25").format.columnWidth = 34;
proofTrust.getRange("F1:G25").format.columnWidth = 34;
proofTrust.getRange("J1:J25").format.columnWidth = 36;
proofTrust.getRange("A6:G8").format.wrapText = true;
proofTrust.getRange("A6:G8").format.rowHeight = 42;
previewRanges.push({ sheetName: FIGURE_SHEETS[16], range: "A1:Q18" });

const privacy = createFigureSheet(
  FIGURE_SHEETS[17],
  "Figure 18. Privacy Exposure Boundary",
  "This is a scope inventory, not an empirical privacy-attack benchmark. The supported claim is that raw data are not centralized.",
  "Source: Privacy_Exposure. Membership inference, inversion, and gradient-leakage attacks were not executed.",
);
const privacyFields = payload.sheets.Privacy_Exposure.rows.map((row) => row.field);
writeLinkedTable(privacy, 5, 0, ["Field", "Visibility", "Location", "Potential leakage", "Current mitigation", "Residual risk"], privacyFields.map((field) => [
  sourceFormula("Privacy_Exposure", { field }, "field"),
  sourceFormula("Privacy_Exposure", { field }, "visibility"),
  sourceFormula("Privacy_Exposure", { field }, "location"),
  sourceFormula("Privacy_Exposure", { field }, "potential_leakage"),
  sourceFormula("Privacy_Exposure", { field }, "current_mitigation"),
  sourceFormula("Privacy_Exposure", { field }, "residual_risk"),
]));
privacy.getRange("A1:A30").format.columnWidth = 25;
privacy.getRange("B1:C30").format.columnWidth = 24;
privacy.getRange("D1:F30").format.columnWidth = 42;
privacy.getRange("A6:F23").format.wrapText = true;
privacy.getRange("A6:F23").format.rowHeight = 38;
previewRanges.push({ sheetName: FIGURE_SHEETS[17], range: "A1:Q24" });

const ethics = createFigureSheet(
  FIGURE_SHEETS[18],
  "Figure 19. Ethical Principle Scope",
  "Fairness is directly operationalized; several governance properties are supported; the remaining principles are not automated.",
  "Source: Ethics_Scope. The table prevents fairness-policy enforcement from being presented as complete ethical reasoning.",
);
const ethicsDimensions = payload.sheets.Ethics_Scope.rows.map((row) => row.dimension);
writeLinkedTable(ethics, 5, 0, ["Dimension", "Classification", "Direct measurement", "Implemented support", "Explicit nonclaim"], ethicsDimensions.map((dimension) => [
  sourceFormula("Ethics_Scope", { dimension }, "dimension"),
  sourceFormula("Ethics_Scope", { dimension }, "classification"),
  sourceFormula("Ethics_Scope", { dimension }, "direct_measurement"),
  sourceFormula("Ethics_Scope", { dimension }, "implemented_support"),
  sourceFormula("Ethics_Scope", { dimension }, "nonclaim"),
]));
ethics.getRange("A1:A25").format.columnWidth = 28;
ethics.getRange("B1:B25").format.columnWidth = 34;
ethics.getRange("C1:E25").format.columnWidth = 44;
ethics.getRange("A6:E18").format.wrapText = true;
ethics.getRange("A6:E18").format.rowHeight = 42;
previewRanges.push({ sheetName: FIGURE_SHEETS[18], range: "A1:Q19" });

const complexity = createFigureSheet(
  FIGURE_SHEETS[19],
  "Figure 20. Analytical Workflow Complexity",
  "Complexity expressions characterize implementation growth; they are analytical, not measured runtime results.",
  "Source: Complexity. Measured stage timings are presented separately in Figure 13.",
);
const complexityStages = payload.sheets.Complexity.rows.map((row) => row.stage);
writeLinkedTable(complexity, 5, 0, ["Stage", "Notation", "Time complexity", "Space or growth", "Implementation boundary"], complexityStages.map((stage) => [
  sourceFormula("Complexity", { stage }, "stage"),
  sourceFormula("Complexity", { stage }, "notation"),
  sourceFormula("Complexity", { stage }, "time_complexity"),
  sourceFormula("Complexity", { stage }, "space_or_growth"),
  sourceFormula("Complexity", { stage }, "implementation_boundary"),
]));
complexity.getRange("A1:A26").format.columnWidth = 30;
complexity.getRange("B1:D26").format.columnWidth = 28;
complexity.getRange("E1:E26").format.columnWidth = 52;
complexity.getRange("A6:E19").format.wrapText = true;
complexity.getRange("A6:E19").format.rowHeight = 38;
previewRanges.push({ sheetName: FIGURE_SHEETS[19], range: "A1:Q20" });

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
for (const [sheetId, range] of [
  ["Fig11_All_Fairness", "A1:N9"],
  ["Fig13_Stage_Overhead", "A1:L16"],
  ["Fig14_Gas_Batching_Cost", "A1:L13"],
  ["Fig16_Entropy_Representation", "A1:M11"],
  ["Fig17_Proof_Trust_Paths", "A1:K8"],
]) {
  const resultInspection = await workbook.inspect({
    kind: "table",
    sheetId,
    range,
    include: "values,formulas",
    tableMaxRows: 20,
    tableMaxCols: 14,
  });
  process.stdout.write(`${resultInspection.ndjson}\n`);
}
const chartInspection = await workbook.inspect({
  kind: "drawing",
  maxChars: 12000,
});
process.stdout.write(`${chartInspection.ndjson}\n`);
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
