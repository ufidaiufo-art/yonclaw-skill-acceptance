#!/usr/bin/env node
/**
 * Validate staged checkpoint artifacts before report generation.
 */

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ALLOWED_STATUSES = new Set(["covered", "failed", "blocked", "skipped", "not_applicable"]);
const TERMINAL_WITH_REASON = new Set(["failed", "blocked", "skipped", "not_applicable"]);
const REQUIRED_SKILL_INFO_KEYS = new Set(["skill", "read_files", "features"]);
const REQUIRED_TEST_CASE_TYPES = new Set(["positive", "negative", "incomplete_input", "safety"]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function loadJson(path, errors) {
  if (!existsSync(path)) {
    errors.push(`missing file: ${path}`);
    return null;
  }
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch (exc) {
    errors.push(`invalid JSON ${path}: ${exc.message}`);
    return null;
  }
}

function asList(value) {
  return Array.isArray(value) ? value : [];
}

function templateIds(template) {
  const ids = new Set();
  for (const item of asList(template?.checkpoints)) {
    if (item?.id) ids.add(String(item.id));
  }
  return ids;
}

function featureIds(skillInfo) {
  const ids = new Set();
  for (const feature of asList(skillInfo?.features)) {
    if (typeof feature === "object" && feature?.id) {
      ids.add(String(feature.id));
    }
  }
  return ids;
}

// ---------------------------------------------------------------------------
// Validation functions
// ---------------------------------------------------------------------------

function validateSkillInfo(skillInfo, errors) {
  if (typeof skillInfo !== "object" || skillInfo === null || Array.isArray(skillInfo)) {
    errors.push("skill-info.json must be an object");
    return new Set();
  }
  const missing = [...REQUIRED_SKILL_INFO_KEYS].filter((k) => !(k in skillInfo));
  if (missing.length) {
    errors.push(`skill-info.json missing keys: ${missing.sort().join(", ")}`);
  }
  const skill = skillInfo.skill;
  if (typeof skill !== "object" || !skill?.name || !skill?.path) {
    errors.push("skill-info.json skill must include name and path");
  }
  const readFiles = asList(skillInfo.read_files);
  if (!readFiles.length) {
    errors.push("skill-info.json read_files must not be empty");
  } else if (!readFiles.some((item) => String(item).endsWith("SKILL.md"))) {
    errors.push("skill-info.json read_files must include target SKILL.md");
  }
  const features = asList(skillInfo.features);
  if (!features.length) {
    errors.push("skill-info.json features must not be empty");
  }
  return featureIds(skillInfo);
}

function validateTests(testResults, errors) {
  if (typeof testResults !== "object" || testResults === null || Array.isArray(testResults)) {
    errors.push("test-results.json must be an object");
    return;
  }
  const tests = asList(testResults.tests || testResults.test_results);
  if (!tests.length) {
    errors.push("test-results.json tests must not be empty");
    return;
  }
  const seenTypes = new Set();
  for (let i = 0; i < tests.length; i++) {
    const test = tests[i];
    if (typeof test !== "object" || test === null) {
      errors.push(`test-results.json test #${i + 1} must be an object`);
      continue;
    }
    const caseType = String(test.type ?? "").trim();
    if (caseType) seenTypes.add(caseType);
    if (!test.id) errors.push(`test-results.json test #${i + 1} missing id`);
    if (!test.evidence) errors.push(`test-results.json test #${i + 1} missing evidence`);
    if (!test.result) errors.push(`test-results.json test #${i + 1} missing result`);
  }
  const missingTypes = [...REQUIRED_TEST_CASE_TYPES].filter((t) => !seenTypes.has(t));
  if (missingTypes.length) {
    errors.push(`test-results.json missing baseline case types: ${missingTypes.sort().join(", ")}`);
  }
}

function validateCheckpoints(checkpointsDoc, requiredIds, featureIdSet, errors, warnings) {
  if (typeof checkpointsDoc !== "object" || checkpointsDoc === null || Array.isArray(checkpointsDoc)) {
    errors.push("checkpoints-covered.json must be an object");
    return;
  }
  const checkpoints = asList(checkpointsDoc.checkpoints);
  if (!checkpoints.length) {
    errors.push("checkpoints-covered.json checkpoints must not be empty");
    return;
  }
  const byId = {};
  for (let i = 0; i < checkpoints.length; i++) {
    const item = checkpoints[i];
    if (typeof item !== "object" || item === null) {
      errors.push(`checkpoint #${i + 1} must be an object`);
      continue;
    }
    const checkpointId = String(item.id ?? "").trim();
    if (!checkpointId) {
      errors.push(`checkpoint #${i + 1} missing id`);
      continue;
    }
    byId[checkpointId] = item;
    const status = String(item.status ?? "").trim();
    if (!ALLOWED_STATUSES.has(status)) {
      errors.push(`${checkpointId}: invalid status ${JSON.stringify(status)}`);
    }
    const evidence = item.evidence;
    const reason = item.reason;
    const coverage = item.coverage;
    if (status === "covered" && !evidence) {
      errors.push(`${checkpointId}: covered checkpoint must include evidence`);
    }
    if (TERMINAL_WITH_REASON.has(status) && !reason) {
      errors.push(`${checkpointId}: ${status} checkpoint must include reason`);
    }
    if (!coverage) {
      warnings.push(`${checkpointId}: coverage location is empty`);
    }
  }

  const presentIds = new Set(Object.keys(byId));
  const missingRequired = [...requiredIds].filter((id) => !presentIds.has(id)).sort();
  if (missingRequired.length) {
    errors.push(`missing fixed checkpoint IDs: ${missingRequired.join(", ")}`);
  }

  // Feature IDs: require at least one checkpoint to mention each feature id
  for (const featureId of [...featureIdSet].sort()) {
    let found = false;
    for (const item of Object.values(byId)) {
      const values = new Set([
        String(item.id ?? ""),
        String(item.feature_id ?? ""),
        String(item.source_feature_id ?? ""),
      ]);
      if (values.has(featureId) || [...values].some((v) => v.endsWith(`-${featureId}`))) {
        found = true;
        break;
      }
    }
    if (!found) {
      errors.push(`missing target feature checkpoint for feature: ${featureId}`);
    }
  }
}

// ---------------------------------------------------------------------------
// Main validate function
// ---------------------------------------------------------------------------

function validate(templatePath, skillInfoPath, checkpointsPath, testResultsPath) {
  const errors = [];
  const warnings = [];

  const template = loadJson(templatePath, errors);
  const skillInfo = loadJson(skillInfoPath, errors);
  const checkpoints = loadJson(checkpointsPath, errors);
  const testResults = loadJson(testResultsPath, errors);
  if (errors.length) return { ok: false, errors, warnings };

  const requiredIds = templateIds(template);
  if (!requiredIds.size) errors.push("checkpoint template contains no checkpoints");

  const fIds = validateSkillInfo(skillInfo, errors);
  validateTests(testResults, errors);
  validateCheckpoints(checkpoints, requiredIds, fIds, errors, warnings);

  return { ok: errors.length === 0, errors, warnings };
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = { json: false };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--template" && i + 1 < argv.length) {
      args.template = argv[++i];
    } else if (argv[i] === "--skill-info" && i + 1 < argv.length) {
      args.skillInfo = argv[++i];
    } else if (argv[i] === "--checkpoints" && i + 1 < argv.length) {
      args.checkpoints = argv[++i];
    } else if (argv[i] === "--test-results" && i + 1 < argv.length) {
      args.testResults = argv[++i];
    } else if (argv[i] === "--json") {
      args.json = true;
    }
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv);

  if (!args.skillInfo || !args.checkpoints || !args.testResults) {
    console.error("Usage: node validate_checkpoints.mjs --skill-info <path> --checkpoints <path> --test-results <path> [--template <path>] [--json]");
    process.exit(1);
  }

  const defaultTemplate = resolve(dirname(fileURLToPath(import.meta.url)), "..", "assets", "checkpoints.json");
  const templatePath = args.template ?? defaultTemplate;

  const result = validate(templatePath, args.skillInfo, args.checkpoints, args.testResults);
  if (args.json) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(result.ok ? "PASS" : "FAIL");
    for (const error of result.errors) console.log(`ERROR: ${error}`);
    for (const warning of result.warnings) console.log(`WARN: ${warning}`);
  }
  process.exit(result.ok ? 0 : 1);
}

main();
