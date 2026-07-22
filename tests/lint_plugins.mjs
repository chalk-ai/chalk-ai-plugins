#!/usr/bin/env node
// Structural lint for the plugin marketplace.
//
// Complements `claude plugin validate .` (which only checks the Claude
// marketplace manifest schema) with cross-file consistency checks:
//
//   - every plugins/<name>/ directory ships a well-formed
//     .claude-plugin/plugin.json whose name matches the directory
//   - Claude/Codex plugin manifests agree on name and version
//   - every plugin is registered in the matching marketplace catalog(s),
//     and every catalog entry points at a real plugin directory
//   - every skills/<name>/SKILL.md has frontmatter with a matching
//     `name` and a non-empty `description`
//
// Run from anywhere: node tests/lint_plugins.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pluginsDir = path.join(repoRoot, "plugins");

const failures = [];
const fail = (msg) => failures.push(msg);

function readJson(relPath) {
  const abs = path.join(repoRoot, relPath);
  if (!fs.existsSync(abs)) {
    fail(`${relPath}: file not found`);
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(abs, "utf8"));
  } catch (err) {
    fail(`${relPath}: invalid JSON (${err.message})`);
    return null;
  }
}

// Minimal frontmatter parser: top-level `key: value` pairs between --- fences.
function parseFrontmatter(relPath) {
  const abs = path.join(repoRoot, relPath);
  const lines = fs.readFileSync(abs, "utf8").split("\n");
  if (lines[0]?.trim() !== "---") {
    fail(`${relPath}: missing frontmatter (file must start with ---)`);
    return null;
  }
  const end = lines.slice(1).findIndex((l) => l.trim() === "---");
  if (end === -1) {
    fail(`${relPath}: unterminated frontmatter (no closing ---)`);
    return null;
  }
  const fields = {};
  for (const line of lines.slice(1, end + 1)) {
    const m = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (m) fields[m[1]] = m[2].trim();
  }
  return fields;
}

function requireField(obj, field, relPath) {
  if (typeof obj?.[field] !== "string" || obj[field].trim() === "") {
    fail(`${relPath}: missing or empty "${field}"`);
    return null;
  }
  return obj[field];
}

// --- Per-plugin manifests -------------------------------------------------

const pluginDirs = fs
  .readdirSync(pluginsDir, { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => e.name)
  .sort();

const claudePlugins = new Set();
const codexPlugins = new Set();

for (const dir of pluginDirs) {
  const claudeManifestRel = path.join("plugins", dir, ".claude-plugin", "plugin.json");
  const codexManifestRel = path.join("plugins", dir, ".codex-plugin", "plugin.json");

  const claudeManifest = readJson(claudeManifestRel);
  let claudeVersion = null;
  if (claudeManifest) {
    claudePlugins.add(dir);
    const name = requireField(claudeManifest, "name", claudeManifestRel);
    if (name && name !== dir) {
      fail(`${claudeManifestRel}: name "${name}" does not match directory "${dir}"`);
    }
    claudeVersion = requireField(claudeManifest, "version", claudeManifestRel);
    requireField(claudeManifest, "description", claudeManifestRel);
  }

  if (fs.existsSync(path.join(repoRoot, codexManifestRel))) {
    const codexManifest = readJson(codexManifestRel);
    if (codexManifest) {
      codexPlugins.add(dir);
      const name = requireField(codexManifest, "name", codexManifestRel);
      if (name && name !== dir) {
        fail(`${codexManifestRel}: name "${name}" does not match directory "${dir}"`);
      }
      const codexVersion = requireField(codexManifest, "version", codexManifestRel);
      if (claudeVersion && codexVersion && claudeVersion !== codexVersion) {
        fail(
          `plugins/${dir}: version mismatch between Claude (${claudeVersion}) and Codex (${codexVersion}) manifests`
        );
      }
      requireField(codexManifest, "description", codexManifestRel);
      if (typeof codexManifest.skills === "string") {
        const skillsAbs = path.join(repoRoot, "plugins", dir, codexManifest.skills);
        if (!fs.existsSync(skillsAbs)) {
          fail(`${codexManifestRel}: skills path "${codexManifest.skills}" does not exist`);
        }
      }
    }
  }

  // Skills: every skills/<name>/ directory must contain a SKILL.md whose
  // frontmatter name matches the directory.
  const skillsDir = path.join(repoRoot, "plugins", dir, "skills");
  if (fs.existsSync(skillsDir)) {
    const skillDirs = fs
      .readdirSync(skillsDir, { withFileTypes: true })
      .filter((e) => e.isDirectory())
      .map((e) => e.name);
    if (skillDirs.length === 0) {
      fail(`plugins/${dir}/skills: directory exists but contains no skills`);
    }
    for (const skill of skillDirs) {
      const skillRel = path.join("plugins", dir, "skills", skill, "SKILL.md");
      if (!fs.existsSync(path.join(repoRoot, skillRel))) {
        fail(`${skillRel}: file not found`);
        continue;
      }
      const fm = parseFrontmatter(skillRel);
      if (!fm) continue;
      const name = requireField(fm, "name", skillRel);
      if (name && name !== skill) {
        fail(`${skillRel}: frontmatter name "${name}" does not match directory "${skill}"`);
      }
      requireField(fm, "description", skillRel);
    }
  }
}

// --- Claude marketplace catalog --------------------------------------------

const claudeCatalogRel = path.join(".claude-plugin", "marketplace.json");
const claudeCatalog = readJson(claudeCatalogRel);
if (claudeCatalog) {
  const seen = new Set();
  for (const entry of claudeCatalog.plugins ?? []) {
    const name = entry.name ?? "<unnamed>";
    if (seen.has(name)) fail(`${claudeCatalogRel}: duplicate plugin entry "${name}"`);
    seen.add(name);
    if (typeof entry.source !== "string") {
      fail(`${claudeCatalogRel}: plugin "${name}" has a non-string source`);
      continue;
    }
    const srcAbs = path.join(repoRoot, entry.source);
    if (!fs.existsSync(srcAbs)) {
      fail(`${claudeCatalogRel}: plugin "${name}" source "${entry.source}" does not exist`);
    } else if (path.basename(entry.source) !== name) {
      fail(`${claudeCatalogRel}: plugin "${name}" source "${entry.source}" does not match its name`);
    }
    if (!claudePlugins.has(name)) {
      fail(`${claudeCatalogRel}: plugin "${name}" has no plugins/${name}/.claude-plugin/plugin.json`);
    }
  }
  for (const dir of claudePlugins) {
    if (!seen.has(dir)) {
      fail(`${claudeCatalogRel}: plugins/${dir} has a Claude manifest but is not registered in the catalog`);
    }
  }
}

// --- Codex marketplace catalog ----------------------------------------------

const codexCatalogRel = path.join(".agents", "plugins", "marketplace.json");
const codexCatalog = readJson(codexCatalogRel);
if (codexCatalog) {
  const seen = new Set();
  for (const entry of codexCatalog.plugins ?? []) {
    const name = entry.name ?? "<unnamed>";
    if (seen.has(name)) fail(`${codexCatalogRel}: duplicate plugin entry "${name}"`);
    seen.add(name);
    const srcPath = entry.source?.path;
    if (typeof srcPath !== "string") {
      fail(`${codexCatalogRel}: plugin "${name}" has no source.path`);
      continue;
    }
    if (!fs.existsSync(path.join(repoRoot, srcPath))) {
      fail(`${codexCatalogRel}: plugin "${name}" source path "${srcPath}" does not exist`);
    } else if (path.basename(srcPath) !== name) {
      fail(`${codexCatalogRel}: plugin "${name}" source path "${srcPath}" does not match its name`);
    }
    if (!codexPlugins.has(name)) {
      fail(`${codexCatalogRel}: plugin "${name}" has no plugins/${name}/.codex-plugin/plugin.json`);
    }
  }
  for (const dir of codexPlugins) {
    if (!seen.has(dir)) {
      fail(`${codexCatalogRel}: plugins/${dir} has a Codex manifest but is not registered in the catalog`);
    }
  }
}

// --- Report -----------------------------------------------------------------

if (failures.length > 0) {
  console.error(`lint_plugins: ${failures.length} problem(s) found:\n`);
  for (const f of failures) console.error(`  ✗ ${f}`);
  process.exit(1);
}
console.log(
  `lint_plugins: OK — ${pluginDirs.length} plugin(s), ${claudePlugins.size} Claude manifest(s), ${codexPlugins.size} Codex manifest(s)`
);
