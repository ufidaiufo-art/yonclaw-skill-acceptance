#!/usr/bin/env node
/**
 * Generate YonClaw skill acceptance Excel report from staged artifacts.
 *
 * Reads skill-info.json, checkpoints-covered.json and test-results.json,
 * then produces a .xlsx report conforming to the yonclaw-skill-acceptance
 * Excel format specification (4 sheets, TARGET/READ/VERDICT exclusion, etc.).
 *
 * Usage:
 *     node generate_report.mjs \
 *         --skill-info <path>/skill-info.json \
 *         --checkpoints <path>/checkpoints-covered.json \
 *         --test-results <path>/test-results.json \
 *         [--output <path>/report.xlsx] \
 *         [--template <path>/checkpoints.json]
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ExcelJS from "exceljs";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Categories that must NOT appear in detail or skill-summary sheets. */
const CHECKPOINT_ONLY_CATEGORIES = new Set(["目标确认", "强制读取", "结论门禁", "报告交付自检"]);

/**
 * Ordered display categories for skill-summary / detail sheets.
 * Names MUST match checkpoints.json category values exactly.
 * Categories in CHECKPOINT_ONLY_CATEGORIES are excluded from detail/summary.
 */
const DISPLAY_ORDER = [
  "BIP 规范专项检查",
  "通用规范检查",
  "安全与风险审计",
  "异常输入与副作用审计",
  "平台集成检查",
  "功能清单与覆盖",
  "动态用例结果",
  "BIP 脚本合规检查",
  "Baseline Failure",
];

/** Allowed values */
const VALID_DETAIL_RESULTS = new Set(["通过", "不通过", "未执行"]);
const VALID_CHECK_RESULTS = new Set(["通过", "未通过", "阻塞", "不适用"]);

/** Checkpoint status -> detail test result mapping */
const STATUS_TO_RESULT = {
  covered: "通过",
  failed: "不通过",
  blocked: "未执行",
  skipped: "未执行",
  not_applicable: "不通过",
};

/** Checkpoint status -> self-check result mapping */
const STATUS_TO_SELF_CHECK = {
  covered: "通过",
  failed: "未通过",
  blocked: "阻塞",
  skipped: "未通过",
  not_applicable: "不适用",
};

// ---------------------------------------------------------------------------
// JSON loading helpers
// ---------------------------------------------------------------------------

function loadJson(path) {
  if (!existsSync(path)) {
    console.error(`ERROR: file not found: ${path}`);
    process.exit(1);
  }
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch (exc) {
    console.error(`ERROR: invalid JSON ${path}: ${exc.message}`);
    process.exit(1);
  }
}

function asList(value) {
  return Array.isArray(value) ? value : [];
}

// ---------------------------------------------------------------------------
// Data transformation
// ---------------------------------------------------------------------------

function categoryForCheckpoint(cp, templateMap) {
  const cpId = String(cp.id ?? "");
  if (cpId && templateMap[cpId]) {
    return templateMap[cpId].category ?? "";
  }
  return cp.category ?? "";
}

function detailCategory(rawCategory) {
  // Use the original category name from checkpoints.json as-is.
  // CHECKPOINT_ONLY_CATEGORIES are filtered out before reaching detail rows,
  // so they won't appear in detail/summary sheets regardless.
  return rawCategory;
}

function buildDetailRows(checkpoints, templateMap) {
  const rows = [];
  for (const cp of checkpoints) {
    const rawCat = categoryForCheckpoint(cp, templateMap);
    const displayCat = detailCategory(rawCat);

    if (CHECKPOINT_ONLY_CATEGORIES.has(rawCat)) continue;

    const status = String(cp.status ?? "").trim();
    const checkpointText = cp.checkpoint ?? templateMap[cp.id ?? ""]?.checkpoint ?? "";

    let testResult;
    if (status === "not_applicable") {
      testResult = "未执行";
    } else if (status in STATUS_TO_RESULT) {
      testResult = STATUS_TO_RESULT[status];
    } else {
      testResult = "未执行";
    }

    const noteParts = [];
    if (cp.evidence) noteParts.push(String(cp.evidence));
    if (cp.reason) noteParts.push(String(cp.reason));
    const note = noteParts.join("; ");

    rows.push({
      方法论大项: displayCat,
      具体测试点: String(checkpointText),
      测试结果: testResult,
      备注: note,
    });
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Excel generation
// ---------------------------------------------------------------------------

const HEADER_FILL = {
  type: "pattern",
  pattern: "solid",
  fgColor: { argb: "FF4472C4" },
};
const HEADER_FONT = { bold: true, size: 11, color: { argb: "FFFFFFFF" } };
const THIN_BORDER = {
  top: { style: "thin" },
  left: { style: "thin" },
  bottom: { style: "thin" },
  right: { style: "thin" },
};
const WRAP_ALIGN = { wrapText: true, vertical: "top" };
const CENTER_ALIGN = { horizontal: "center", vertical: "center" };

function applyHeaderStyle(ws, row, colCount) {
  for (let col = 1; col <= colCount; col++) {
    const cell = ws.getCell(row, col);
    cell.font = HEADER_FONT;
    cell.fill = HEADER_FILL;
    cell.border = THIN_BORDER;
    cell.alignment = CENTER_ALIGN;
  }
}

function applyCellBorder(ws, row, colCount) {
  for (let col = 1; col <= colCount; col++) {
    const cell = ws.getCell(row, col);
    cell.border = THIN_BORDER;
    cell.alignment = WRAP_ALIGN;
  }
}

function autoWidth(ws, colCount, maxWidth = 60) {
  for (let col = 1; col <= colCount; col++) {
    let maxLen = 0;
    ws.eachRow({ includeEmpty: false }, (row) => {
      const val = String(row.getCell(col).value ?? "");
      maxLen = Math.max(maxLen, Math.min(val.length, maxWidth));
    });
    ws.getColumn(col).width = Math.max(maxLen + 4, 12);
  }
}

async function generateReport(skillInfo, checkpointsData, testResults, templateData, outputPath) {
  const wb = new ExcelJS.Workbook();

  const skillName = skillInfo?.skill?.name ?? "unknown-skill";
  const checkpoints = asList(checkpointsData?.checkpoints);
  const templateMap = {};
  if (templateData) {
    for (const item of asList(templateData.checkpoints)) {
      const cpId = String(item.id ?? "");
      if (cpId) templateMap[cpId] = item;
    }
  }

  const detailSheetName = skillName;

  // ------------------------------------------------------------------
  // Build detail rows first to get statistics
  // ------------------------------------------------------------------
  const detailRows = buildDetailRows(checkpoints, templateMap);

  const stats = { 通过: 0, 不通过: 0, 未执行: 0 };
  for (const row of detailRows) {
    if (VALID_DETAIL_RESULTS.has(row.测试结果)) {
      stats[row.测试结果]++;
    }
  }

  const totalCount = stats.通过 + stats.不通过 + stats.未执行;
  const passRate = totalCount > 0 ? ((stats.通过 / totalCount) * 100).toFixed(1) + "%" : "0%";

  // ------------------------------------------------------------------
  // Sheet 1: 汇总
  // ------------------------------------------------------------------
  const wsSummary = wb.addWorksheet("汇总");
  const summaryHeaders = ["技能清单", "测试点总数", "验证通过", "验证不通过", "未执行", "通过率"];
  for (let col = 0; col < summaryHeaders.length; col++) {
    wsSummary.getCell(1, col + 1).value = summaryHeaders[col];
  }
  applyHeaderStyle(wsSummary, 1, summaryHeaders.length);

  wsSummary.getCell(2, 1).value = skillName;
  wsSummary.getCell(2, 2).value = totalCount;
  wsSummary.getCell(2, 3).value = stats.通过;
  wsSummary.getCell(2, 4).value = stats.不通过;
  wsSummary.getCell(2, 5).value = stats.未执行;
  wsSummary.getCell(2, 6).value = passRate;
  applyCellBorder(wsSummary, 2, summaryHeaders.length);
  autoWidth(wsSummary, summaryHeaders.length);

  // ------------------------------------------------------------------
  // Sheet 2: <skill-name>汇总
  // ------------------------------------------------------------------
  const wsSkillSummary = wb.addWorksheet(`${skillName}汇总`);
  const skillSummaryHeaders = ["项目", "测试点总数", "验证通过", "验证不通过", "未执行", "通过率"];
  for (let col = 0; col < skillSummaryHeaders.length; col++) {
    wsSkillSummary.getCell(1, col + 1).value = skillSummaryHeaders[col];
  }
  applyHeaderStyle(wsSkillSummary, 1, skillSummaryHeaders.length);

  // Group by display category
  const byCategory = {};
  for (const row of detailRows) {
    if (!byCategory[row.方法论大项]) {
      byCategory[row.方法论大项] = { 通过: 0, 不通过: 0, 未执行: 0 };
    }
    if (VALID_DETAIL_RESULTS.has(row.测试结果)) {
      byCategory[row.方法论大项][row.测试结果]++;
    }
  }

  let skillSummaryRow = 2;
  for (const displayCat of DISPLAY_ORDER) {
    const catStats = byCategory[displayCat];
    if (!catStats) continue; // Skip categories with no checkpoints
    const catTotal = catStats.通过 + catStats.不通过 + catStats.未执行;
    const catRate = catTotal > 0 ? ((catStats.通过 / catTotal) * 100).toFixed(1) + "%" : "0%";

    wsSkillSummary.getCell(skillSummaryRow, 1).value = displayCat;
    wsSkillSummary.getCell(skillSummaryRow, 2).value = catTotal;
    wsSkillSummary.getCell(skillSummaryRow, 3).value = catStats.通过;
    wsSkillSummary.getCell(skillSummaryRow, 4).value = catStats.不通过;
    wsSkillSummary.getCell(skillSummaryRow, 5).value = catStats.未执行;
    wsSkillSummary.getCell(skillSummaryRow, 6).value = catRate;
    applyCellBorder(wsSkillSummary, skillSummaryRow, skillSummaryHeaders.length);
    skillSummaryRow++;
  }
  autoWidth(wsSkillSummary, skillSummaryHeaders.length);

  // ------------------------------------------------------------------
  // Sheet 3: <skill-name> (detail)
  // ------------------------------------------------------------------
  const wsDetail = wb.addWorksheet(detailSheetName);
  const detailHeaders = ["方法论大项", "具体测试点", "测试结果", "备注"];
  for (let col = 0; col < detailHeaders.length; col++) {
    wsDetail.getCell(1, col + 1).value = detailHeaders[col];
  }
  applyHeaderStyle(wsDetail, 1, detailHeaders.length);

  const detailRowOffset = 2; // data starts at row 2
  for (let i = 0; i < detailRows.length; i++) {
    const rowNum = detailRowOffset + i;
    const row = detailRows[i];
    wsDetail.getCell(rowNum, 1).value = row.方法论大项;
    wsDetail.getCell(rowNum, 2).value = row.具体测试点;
    wsDetail.getCell(rowNum, 3).value = row.测试结果;
    wsDetail.getCell(rowNum, 4).value = row.备注;
    applyCellBorder(wsDetail, rowNum, detailHeaders.length);
  }
  autoWidth(wsDetail, detailHeaders.length);
  wsDetail.getColumn(2).width = 50;
  wsDetail.getColumn(4).width = 60;

  // ------------------------------------------------------------------
  // Sheet 4: 检查点自检
  // ------------------------------------------------------------------
  const wsCheck = wb.addWorksheet("检查点自检");
  const checkHeaders = ["检查点ID", "方法论大项", "检查点", "适用性", "覆盖位置", "自检结果", "备注"];
  for (let col = 0; col < checkHeaders.length; col++) {
    wsCheck.getCell(1, col + 1).value = checkHeaders[col];
  }
  applyHeaderStyle(wsCheck, 1, checkHeaders.length);

  // Build detail row map: checkpoint id -> detail row number
  const detailRowMap = {};
  let currentRow = detailRowOffset;
  for (const cp of checkpoints) {
    const rawCat = categoryForCheckpoint(cp, templateMap);
    if (CHECKPOINT_ONLY_CATEGORIES.has(rawCat)) continue;
    const cpId = String(cp.id ?? "");
    detailRowMap[cpId] = currentRow;
    currentRow++;
  }

  // Build self-check rows
  let checkRow = 2;
  for (const cp of checkpoints) {
    const cpId = String(cp.id ?? "");
    const rawCat = categoryForCheckpoint(cp, templateMap);
    const displayCat = detailCategory(rawCat);
    const checkpointText = cp.checkpoint ?? templateMap[cpId]?.checkpoint ?? "";
    const status = String(cp.status ?? "").trim();

    const selfCheck = status in STATUS_TO_SELF_CHECK ? STATUS_TO_SELF_CHECK[status] : "阻塞";
    const applicability = status === "not_applicable" ? "不适用" : "适用";

    let coverageLocation;
    if (CHECKPOINT_ONLY_CATEGORIES.has(rawCat)) {
      coverageLocation = selfCheck === "通过" ? "检查点自检" : "未覆盖";
    } else if (cpId in detailRowMap) {
      const rowNum = detailRowMap[cpId];
      coverageLocation = `${detailSheetName}!A${rowNum}`;
    } else {
      coverageLocation = "未覆盖";
    }

    const noteParts = [];
    if (cp.evidence) noteParts.push(String(cp.evidence));
    if (cp.reason) noteParts.push(String(cp.reason));
    const note = noteParts.join("; ");

    wsCheck.getCell(checkRow, 1).value = cpId;
    wsCheck.getCell(checkRow, 2).value = displayCat;
    wsCheck.getCell(checkRow, 3).value = checkpointText;
    wsCheck.getCell(checkRow, 4).value = applicability;
    wsCheck.getCell(checkRow, 5).value = coverageLocation;
    wsCheck.getCell(checkRow, 6).value = selfCheck;
    wsCheck.getCell(checkRow, 7).value = note;
    applyCellBorder(wsCheck, checkRow, checkHeaders.length);
    checkRow++;
  }
  autoWidth(wsCheck, checkHeaders.length);
  wsCheck.getColumn(3).width = 50;
  wsCheck.getColumn(7).width = 60;

  // ------------------------------------------------------------------
  // Save
  // ------------------------------------------------------------------
  const outDir = dirname(outputPath);
  mkdirSync(outDir, { recursive: true });
  await wb.xlsx.writeFile(outputPath);
  console.log(`Report generated: ${outputPath}`);
  return outputPath;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { template: null, output: null };
  const rest = [];
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--skill-info" && i + 1 < argv.length) {
      args.skillInfo = argv[++i];
    } else if (argv[i] === "--checkpoints" && i + 1 < argv.length) {
      args.checkpoints = argv[++i];
    } else if (argv[i] === "--test-results" && i + 1 < argv.length) {
      args.testResults = argv[++i];
    } else if (argv[i] === "--template" && i + 1 < argv.length) {
      args.template = argv[++i];
    } else if ((argv[i] === "--output" || argv[i] === "-o") && i + 1 < argv.length) {
      args.output = argv[++i];
    } else {
      rest.push(argv[i]);
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);

  if (!args.skillInfo || !args.checkpoints || !args.testResults) {
    console.error("Usage: node generate_report.mjs --skill-info <path> --checkpoints <path> --test-results <path> [--output <path>] [--template <path>]");
    process.exit(1);
  }

  const skillInfo = loadJson(args.skillInfo);
  const checkpointsData = loadJson(args.checkpoints);
  const testResults = loadJson(args.testResults);

  const defaultTemplate = resolve(dirname(fileURLToPath(import.meta.url)), "..", "assets", "checkpoints.json");
  const templatePath = args.template ?? defaultTemplate;
  const templateData = existsSync(templatePath) ? loadJson(templatePath) : null;

  const skillName = skillInfo?.skill?.name ?? "unknown-skill";
  const outputPath = args.output ?? `${skillName}-acceptance-report.xlsx`;

  await generateReport(skillInfo, checkpointsData, testResults, templateData, outputPath);
}

main().catch((err) => {
  console.error(`ERROR: ${err.message}`);
  process.exit(1);
});
