#!/usr/bin/env node
/**
 * Validate final YonClaw Excel acceptance reports.
 *
 * Dependency-free by design: parses .xlsx as zip/xml so the gate can run even
 * when exceljs is unavailable in the YonClaw runtime.
 */

import { readFileSync, existsSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { load as cheerioLoad } from "cheerio";

// Uses JSZip + cheerio to parse .xlsx as zip/xml — no openpyxl or exceljs needed.

import JSZip from "jszip";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SUMMARY_HEADERS = ["技能清单", "测试点总数", "验证通过", "验证不通过", "未执行", "通过率"];
const SKILL_SUMMARY_HEADERS = ["项目", "测试点总数", "验证通过", "验证不通过", "未执行", "通过率"];
const DETAIL_HEADERS = ["方法论大项", "具体测试点", "测试结果", "备注"];
const CHECK_HEADERS = ["检查点ID", "方法论大项", "检查点", "适用性", "覆盖位置", "自检结果", "备注"];

const VALID_DETAIL_RESULTS = new Set(["通过", "不通过", "未执行"]);
const VALID_CHECK_RESULTS = new Set(["通过", "未通过", "阻塞", "不适用"]);
const GENERIC_LOCATIONS = new Set(["已覆盖", "见报告", "见摘要", "报告中", "详见报告"]);
const NOT_APPLICABLE_VALUES = new Set(["不适用", "否", "N/A", "NA", "not_applicable"]);
const REPORT_SELF_CHECK_KEYWORDS = [
  "Excel 文件已生成",
  "Excel 路径",
  "默认输出 Excel",
  "公式错误扫描",
  "检查点自检",
  "只输出一份汇总报告",
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadJson(path, errors) {
  if (!path) return null;
  if (!existsSync(path)) {
    errors.push(`missing checkpoints artifact: ${path}`);
    return null;
  }
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch (exc) {
    errors.push(`invalid checkpoints JSON ${path}: ${exc.message}`);
    return null;
  }
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    errors.push(`checkpoints JSON must be an object: ${path}`);
    return null;
  }
}

/**
 * Parse xlsx file and return a Map of sheet name -> array of rows (string arrays).
 */
async function workbookRows(path, errors) {
  if (!existsSync(path)) {
    errors.push(`missing report: ${path}`);
    return new Map();
  }
  if (!path.toLowerCase().endsWith(".xlsx")) {
    errors.push(`report extension must be .xlsx: ${path.split(/[/\\]/).pop()}`);
  }
  const stat = statSync(path);
  if (stat.size <= 0) {
    errors.push(`report is empty: ${path}`);
  }

  let zip;
  try {
    const buf = readFileSync(path);
    zip = await JSZip.loadAsync(buf);
  } catch (exc) {
    errors.push("report is not a readable xlsx/zip archive");
    return new Map();
  }

  try {
    const shared = await sharedStrings(zip);
    const targets = await sheetTargets(zip);
    const result = new Map();
    for (const [name, target] of targets) {
      result.set(name, await sheetRows(zip, target, shared));
    }
    return result;
  } catch (exc) {
    errors.push(`failed to parse workbook: ${exc.message}`);
    return new Map();
  }
}

async function sharedStrings(zip) {
  const entry = zip.file("xl/sharedStrings.xml");
  if (!entry) return [];
  const xml = await entry.async("string");
  const $ = cheerioLoad(xml, { xmlMode: true });
  const values = [];
  $("si").each(function () {
    let text = "";
    $(this).find("t").each(function () {
      text += $(this).text() || "";
    });
    values.push(text);
  });
  return values;
}

async function sheetTargets(zip) {
  const workbookXml = await zip.file("xl/workbook.xml").async("string");
  const relsXml = await zip.file("xl/_rels/workbook.xml.rels").async("string");

  const relMap = new Map();
  const $rels = cheerioLoad(relsXml, { xmlMode: true });
  $rels("Relationship").each(function () {
    const id = $rels(this).attr("Id");
    let target = $rels(this).attr("Target") || "";
    if (id) {
      if (!target.startsWith("/")) target = "xl/" + target;
      relMap.set(id, target.replace(/^\/+/, ""));
    }
  });

  const targets = new Map();
  const $wb = cheerioLoad(workbookXml, { xmlMode: true });
  $wb("sheet").each(function () {
    const name = $wb(this).attr("name") || "";
    const relId = $wb(this).attr("r:id") || $wb(this).attr("xmlns\\:r:id") || "";
    if (name && relId && relMap.has(relId)) {
      targets.set(name, relMap.get(relId));
    }
  });
  return targets;
}

function columnIndex(ref) {
  const letters = (ref.match(/[A-Z]+/i) || [""])[0];
  let result = 0;
  for (const ch of letters) {
    result = result * 26 + (ch.toUpperCase().charCodeAt(0) - "A".charCodeAt(0) + 1);
  }
  return Math.max(result - 1, 0);
}

async function sheetRows(zip, target, shared) {
  const entry = zip.file(target);
  if (!entry) return [];
  const xml = await entry.async("string");
  const $ = cheerioLoad(xml, { xmlMode: true });

  const rows = [];
  $("row").each(function () {
    const values = [];
    $(this).find("c").each(function () {
      const ref = $(this).attr("r") || "";
      const index = columnIndex(ref);
      const cellType = $(this).attr("t") || "";
      let text = "";

      if (cellType === "inlineStr") {
        $(this).find("t").each(function () {
          text += $(this).text() || "";
        });
        text = text.trim();
      } else {
        const vEl = $(this).find("v");
        const raw = vEl.length ? vEl.text() || "" : "";
        if (cellType === "s") {
          try {
            text = (shared[parseInt(raw)] || "").trim();
          } catch {
            text = raw.trim();
          }
        } else {
          text = raw.trim();
        }
      }

      while (values.length <= index) values.push("");
      values[index] = text;
    });
    // Trim trailing empty cells
    while (values.length && values[values.length - 1] === "") values.pop();
    rows.push(values);
  });
  return rows;
}

function findHeader(rows, headers) {
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    if (headers.length <= row.length && headers.every((h, idx) => row[idx] === h)) {
      return i;
    }
  }
  return null;
}

function dataRows(rows, headerIndex, minCols) {
  const output = [];
  for (let offset = headerIndex + 1; offset < rows.length; offset++) {
    const row = rows[offset];
    if (!row || !row.some((v) => v !== "" && v !== undefined && v !== null)) continue;
    const padded = [...row];
    while (padded.length < minCols) padded.push("");
    output.push([offset + 1, padded]); // 1-based excel row number
  }
  return output;
}

function toInt(value) {
  try {
    return parseInt(parseFloat(String(value).trim()));
  } catch {
    return null;
  }
}

function coverageTarget(location) {
  if (!location || location === "未覆盖" || GENERIC_LOCATIONS.has(location)) return null;
  let match = location.match(/^(.+?)![A-Z]*([0-9]+)$/);
  if (match) return [match[1], parseInt(match[2])];
  match = location.match(/^(.+?)\s*(?:row|行)\s*([0-9]+)$/i);
  if (match) return [match[1], parseInt(match[2])];
  return [location, null];
}

function checkpointIds(data) {
  if (!data) return new Set();
  const cps = data.checkpoints;
  if (!Array.isArray(cps)) return new Set();
  const ids = new Set();
  for (const item of cps) {
    if (item && item.id) ids.add(String(item.id));
  }
  return ids;
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

async function validate(report, checkpoints) {
  const errors = [];
  const warnings = [];
  const checkpointData = loadJson(checkpoints, errors);
  const expectedCheckpointIds = checkpointIds(checkpointData);
  const sheets = await workbookRows(report, errors);

  if (errors.length && sheets.size === 0) {
    return { ok: false, errors, warnings };
  }

  if (!sheets.has("汇总")) errors.push("missing required sheet: 汇总");
  if (!sheets.has("检查点自检")) errors.push("missing required sheet: 检查点自检");

  const detailSheets = [...sheets.keys()].filter(
    (n) => n !== "汇总" && n !== "检查点自检" && !n.endsWith("汇总")
  );
  if (!detailSheets.length) errors.push("missing target skill detail sheet");

  const detailStats = new Map();
  for (const sheetName of detailSheets) {
    const rows = sheets.get(sheetName);
    const headerIndex = findHeader(rows, DETAIL_HEADERS);
    if (headerIndex === null) {
      errors.push(`${sheetName}: missing headers ${JSON.stringify(DETAIL_HEADERS)}`);
      continue;
    }
    const total = { 通过: 0, 不通过: 0, 未执行: 0 };
    const byCategory = {};
    for (const [excelRow, row] of dataRows(rows, headerIndex, DETAIL_HEADERS.length)) {
      const [category, point, result, note] = row;
      if (!VALID_DETAIL_RESULTS.has(result)) {
        errors.push(`${sheetName}!row ${excelRow}: invalid test result ${JSON.stringify(result)}`);
        continue;
      }
      if (REPORT_SELF_CHECK_KEYWORDS.some((kw) => row.join(" ").includes(kw))) {
        errors.push(`${sheetName}!row ${excelRow}: report self-check item appears in target detail sheet`);
      }
      total[result]++;
      if (!byCategory[category]) byCategory[category] = { 通过: 0, 不通过: 0, 未执行: 0 };
      byCategory[category][result]++;
    }
    detailStats.set(sheetName, { total, byCategory });
  }

  if (sheets.has("汇总")) {
    const rows = sheets.get("汇总");
    const headerIndex = findHeader(rows, SUMMARY_HEADERS);
    if (headerIndex === null) {
      errors.push(`汇总: missing headers ${JSON.stringify(SUMMARY_HEADERS)}`);
    } else {
      const summary = new Map();
      for (const [, row] of dataRows(rows, headerIndex, SUMMARY_HEADERS.length)) {
        summary.set(row[0], row);
      }
      for (const [skillName, { total }] of detailStats) {
        const row = summary.get(skillName);
        if (!row) {
          errors.push(`汇总: missing skill row ${skillName}`);
          continue;
        }
        const expected = [total.通过 + total.不通过 + total.未执行, total.通过, total.不通过, total.未执行];
        const actual = [toInt(row[1]), toInt(row[2]), toInt(row[3]), toInt(row[4])];
        if (expected.some((v, i) => v !== actual[i])) {
          errors.push(`汇总/${skillName}: expected total/pass/fail/unexecuted=${JSON.stringify(expected)}, actual=${JSON.stringify(actual)}`);
        }
      }
    }
  }

  for (const [skillName, { total, byCategory }] of detailStats) {
    const summaryName = `${skillName}汇总`;
    if (!sheets.has(summaryName)) {
      errors.push(`missing skill summary sheet: ${summaryName}`);
      continue;
    }
    const rows = sheets.get(summaryName);
    const headerIndex = findHeader(rows, SKILL_SUMMARY_HEADERS);
    if (headerIndex === null) {
      errors.push(`${summaryName}: missing headers ${JSON.stringify(SKILL_SUMMARY_HEADERS)}`);
      continue;
    }
    const summary = new Map();
    for (const [, row] of dataRows(rows, headerIndex, SKILL_SUMMARY_HEADERS.length)) {
      summary.set(row[0], row);
    }
    for (const [category, counts] of Object.entries(byCategory)) {
      const row = summary.get(category);
      if (!row) {
        errors.push(`${summaryName}: missing category row ${category}`);
        continue;
      }
      const expected = [counts.通过 + counts.不通过 + counts.未执行, counts.通过, counts.不通过, counts.未执行];
      const actual = [toInt(row[1]), toInt(row[2]), toInt(row[3]), toInt(row[4])];
      if (expected.some((v, i) => v !== actual[i])) {
        errors.push(`${summaryName}/${category}: expected total/pass/fail/unexecuted=${JSON.stringify(expected)}, actual=${JSON.stringify(actual)}`);
      }
    }
    if (total.不通过 || total.未执行) {
      warnings.push(`${skillName}: contains fail/unexecuted detail rows; final verdict must be downgraded or justified`);
    }
  }

  if (sheets.has("检查点自检")) {
    const rows = sheets.get("检查点自检");
    const headerIndex = findHeader(rows, CHECK_HEADERS);
    if (headerIndex === null) {
      errors.push(`检查点自检: missing headers ${JSON.stringify(CHECK_HEADERS)}`);
    } else {
      const seenIds = new Set();
      for (const [excelRow, row] of dataRows(rows, headerIndex, CHECK_HEADERS.length)) {
        const [checkpointId, _category, _point, applicability, location, result, note] = row;
        if (!checkpointId) {
          errors.push(`检查点自检!row ${excelRow}: missing checkpoint ID`);
          continue;
        }
        seenIds.add(checkpointId);
        if (!VALID_CHECK_RESULTS.has(result)) {
          errors.push(`检查点自检!row ${excelRow}: invalid self-check result ${JSON.stringify(result)}`);
        }
        if ((result === "未通过" || result === "阻塞") && !note) {
          errors.push(`检查点自检!row ${excelRow}: failing/blocking checkpoint must include note`);
        }
        if (!NOT_APPLICABLE_VALUES.has(applicability)) {
          if (!location) {
            errors.push(`检查点自检!row ${excelRow}: coverage location is empty`);
          } else if (VALID_CHECK_RESULTS.has(location)) {
            errors.push(
              `检查点自检!row ${excelRow}: coverage location looks like a self-check result, ` +
                `expected concrete location such as <skill-name>!B12 or 未覆盖: ${location}`
            );
          } else if (GENERIC_LOCATIONS.has(location)) {
            errors.push(`检查点自检!row ${excelRow}: coverage location is too generic: ${location}`);
          } else if (location !== "未覆盖") {
            const target = coverageTarget(location);
            if (!target) {
              errors.push(`检查点自检!row ${excelRow}: invalid coverage location ${JSON.stringify(location)}`);
            } else {
              const [sheetName, rowNumber] = target;
              if (!sheets.has(sheetName)) {
                errors.push(`检查点自检!row ${excelRow}: coverage sheet not found: ${sheetName}`);
              } else if (rowNumber !== null && rowNumber > sheets.get(sheetName).length) {
                errors.push(`检查点自检!row ${excelRow}: coverage row out of range: ${location}`);
              }
            }
          }
        }
      }

      if (expectedCheckpointIds.size) {
        const missing = [...expectedCheckpointIds].filter((id) => !seenIds.has(id)).sort();
        if (missing.length) {
          errors.push(`检查点自检: missing checkpoint IDs from checkpoints-covered.json: ${missing.join(", ")}`);
        }
      }
    }
  }

  return { ok: errors.length === 0, errors, warnings };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { json: false };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--checkpoints" && i + 1 < argv.length) {
      args.checkpoints = argv[++i];
    } else if (argv[i] === "--json") {
      args.json = true;
    } else if (!argv[i].startsWith("-")) {
      args.report = argv[i];
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);
  if (!args.report) {
    console.error("Usage: node validate_excel_report.mjs <report.xlsx> [--checkpoints <path>] [--json]");
    process.exit(1);
  }

  const result = await validate(args.report, args.checkpoints);
  if (args.json) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(result.ok ? "PASS" : "FAIL");
    for (const error of result.errors) console.log(`ERROR: ${error}`);
    for (const warning of result.warnings) console.log(`WARN: ${warning}`);
  }
  process.exit(result.ok ? 0 : 1);
}

main().catch((err) => {
  console.error(`ERROR: ${err.message}`);
  process.exit(1);
});
