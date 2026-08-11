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
