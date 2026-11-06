// cspell:words pypi
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [runtime, root, shared] = process.argv.slice(2);
const transportCalls = [];
const forbidden =
  (label) =>
  (...args) => {
    transportCalls.push(label);
    throw new Error("native ownership check forbids transport: " + label);
  };
for (const [name, methods] of [
  ["node:http", ["request", "get"]],
  ["node:https", ["request", "get"]],
  ["node:net", ["connect", "createConnection"]],
  ["node:tls", ["connect"]],
  ["node:dns", ["lookup", "resolve"]],
]) {
  const module = require(name);
  for (const method of methods) module[method] = forbidden(name + "." + method);
}
globalThis.fetch = forbidden("fetch");
const base = path.join(runtime, "dist");
await require(path.join(base, "logger/index.js")).init();
assert.equal(require(path.join(base, "util/regex.js")).regexEngineStatus.type, "available");
require(path.join(base, "config/global.js")).GlobalConfig.set({ localDir: root });
const memory = require(path.join(base, "util/cache/memory/index.js"));
memory.init();
const input = JSON.parse(fs.readFileSync(path.join(root, ".github/renovate.json")));
const manifest = JSON.parse(fs.readFileSync(path.join(root, ".github/automation.json")));
const {
  errors = [],
  warnings = [],
  ...raw
} = await require(path.join(base, "config/migrate-validate.js")).migrateAndValidate(
  { repoIsOnboarded: true },
  input,
);
assert.deepEqual(errors, []);
assert.deepEqual(warnings, []);
for (const reference of raw.extends) {
  const match = reference.match(
    /^github>Strukturpiloten\/boxferry\/\/renovate-presets\/(common|rust)#([a-f0-9]{40})$/,
  );
  assert(match && match[2] === manifest.revision, "preset must bind selected automation");
  memory.set(
    "preset:" + reference,
    JSON.parse(fs.readFileSync(path.join(shared, "renovate-presets", match[1] + ".json"))),
  );
}
const validation = await require(path.join(base, "config/validation.js")).validateConfig(
  "repository",
  raw,
);
assert.deepEqual(validation.errors, []);
assert.deepEqual(validation.warnings, []);
const { config } = await require(path.join(base, "config/presets/index.js")).resolveConfigPresets(
  raw,
);
const native = require(path.join(base, "modules/manager/github-actions/index.js"));
const regex = require(path.join(base, "modules/manager/custom/regex/index.js"));
const { matchRegexOrGlobList } = require(path.join(base, "util/string-match.js"));
const { normalizeDepNames } = require(
  path.join(base, "workers/repository/extract/manager-files.js"),
);
const { applyPackageRules } = require(path.join(base, "util/package-rules/index.js"));
const enabled = (configuration, manager) =>
  !configuration.enabledManagers || configuration.enabledManagers.includes(manager);
async function effective(configuration, manager, dependency, file, managerConfig = {}) {
  normalizeDepNames(dependency);
  return applyPackageRules(
    {
      ...configuration,
      ...managerConfig,
      ...dependency,
      manager,
      packageFile: file,
      updateType: "patch",
    },
    "website native Node ownership",
  );
}
async function owners(text, file, configuration = config) {
  const rows = [];
  if (
    enabled(configuration, "github-actions") &&
    configuration["github-actions"]?.enabled !== false
  ) {
    for (const dep of (
      await native.extractPackageFile(text, file, configuration["github-actions"] ?? {})
    )?.deps ?? []) {
      if (dep.packageName !== "actions/node-versions") continue;
      const policy = await effective(
        configuration,
        "github-actions",
        dep,
        file,
        configuration["github-actions"],
      );
      if (policy.enabled !== false && !dep.skipReason)
        rows.push({ manager: "github-actions", dependency: dep, policy });
    }
  }
  if (enabled(configuration, "custom.regex"))
    for (const manager of configuration.customManagers ?? []) {
      if (
        manager.customType !== "regex" ||
        manager.enabled === false ||
        !matchRegexOrGlobList(file, manager.managerFilePatterns)
      )
        continue;
      for (const dep of regex.extractPackageFile(text, file, manager)?.deps ?? []) {
        if (dep.datasource !== "node-version" || (dep.packageName ?? dep.depName) !== "node")
          continue;
        const policy = await effective(configuration, "custom.regex", dep, file, manager);
        if (policy.enabled !== false && !dep.skipReason)
          rows.push({ manager: "custom.regex", dependency: dep, policy });
      }
    }
  return rows;
}
function verifyNode(rows, expected) {
  assert.equal(rows.length, 1, "exactly one active Node owner is required");
  assert.equal(rows[0].manager, "github-actions");
  assert.equal(rows[0].dependency.packageName, "actions/node-versions");
  assert.equal(rows[0].dependency.currentValue, expected);
  assert.equal(rows[0].policy.automerge, true);
  assert.equal(rows[0].policy.dependencyDashboardApproval, false);
  assert.equal(rows[0].policy.minimumReleaseAge, "3 days");
  assert.equal(rows[0].policy.groupName, "GitHub Actions");
  assert.equal(rows[0].policy.pinDigests, true);
}
const marker = "# renovate: datasource=node-version depName=node";
const obsolete = {
  customType: "regex",
  managerFilePatterns: ["/^\\.github/workflows/.*\\.yml$/"],
  matchStrings: [
    "# renovate: datasource=(?<datasource>[^\\s]+) depName=(?<depName>[^\\s]+)\\n\\s+node-version: (?<currentValue>[^\\s]+)",
  ],
};
const workflows = [];
for (const file of [".github/workflows/ci.yml", ".github/workflows/deploy.yml"]) {
  const text = fs.readFileSync(path.join(root, file), "utf8");
  const declared = [...text.matchAll(/^\s+node-version: ([^\s]+)$/gm)].map((match) => match[1]);
  assert.equal(declared.length, 1, "retain one explicit workflow Node input");
  assert.match(declared[0], /^\d+\.\d+\.\d+$/);
  assert(!text.includes(marker), "obsolete Node annotation must stay removed");
  const current = await owners(text, file);
  verifyNode(current, declared[0]);
  const duplicateText = text.replace(/^(\s*)node-version: /m, "$1" + marker + "\n$1node-version: ");
  const duplicate = await owners(duplicateText, file, {
    ...config,
    customManagers: [...config.customManagers, obsolete],
  });
  assert.equal(duplicate.length, 2, "negative control must reproduce the old two-manager defect");
  assert.throws(() => verifyNode(duplicate, declared[0]), /exactly one active Node owner/);
  const missing = await owners(text, file, {
    ...config,
    "github-actions": { ...config["github-actions"], enabled: false },
  });
  assert.throws(() => verifyNode(missing, declared[0]), /exactly one active Node owner/);
  const approval = await owners(text, file, {
    ...config,
    packageRules: [
      ...config.packageRules,
      {
        matchManagers: ["github-actions"],
        matchPackageNames: ["actions/node-versions"],
        dependencyDashboardApproval: true,
      },
    ],
  });
  assert.throws(() => verifyNode(approval, declared[0]));
  workflows.push({
    file,
    owners: current.map((row) => ({
      manager: row.manager,
      dependency: row.dependency,
      automerge: row.policy.automerge,
      approval: row.policy.dependencyDashboardApproval,
      minimumReleaseAge: row.policy.minimumReleaseAge,
      groupName: row.policy.groupName,
      pinDigests: row.policy.pinDigests,
    })),
    duplicateOwners: duplicate.length,
    missingOwners: missing.length,
  });
}
async function documentationOwners(configuration) {
  const file = "documentation-sources.toml";
  const text = fs.readFileSync(path.join(root, file), "utf8");
  const rows = [];
  for (const manager of configuration.customManagers ?? []) {
    if (
      manager.customType !== "regex" ||
      manager.enabled === false ||
      !matchRegexOrGlobList(file, manager.managerFilePatterns)
    )
      continue;
    for (const dep of regex.extractPackageFile(text, file, manager)?.deps ?? []) {
      const policy = await effective(configuration, "custom.regex", dep, file, manager);
      if (policy.enabled !== false && !dep.skipReason) rows.push({ dependency: dep, policy });
    }
  }
  return rows;
}
function verifyDocumentation(rows) {
  assert.deepEqual(
    rows.map((row) => row.dependency.depName),
    [
      "Strukturpiloten/boxferry",
      "Strukturpiloten/compose-lens",
      "Strukturpiloten/podman-lens",
      "Strukturpiloten/quadlet-lens",
    ],
    "retain every documentation-source pin owner",
  );
  for (const row of rows) {
    assert.equal(row.dependency.datasource, "git-refs");
    assert.match(row.dependency.currentDigest, /^[a-f0-9]{40}$/);
    // Frozen Renovate normalizes the configured zero-day hold to null.
    assert.equal(row.policy.minimumReleaseAge, null);
    assert.equal(row.policy.groupName, "documentation sources");
    assert.equal(row.policy.automerge, true);
    assert.equal(row.policy.dependencyDashboardApproval, false);
  }
}
const documentation = await documentationOwners(config);
verifyDocumentation(documentation);
const withoutDocumentation = {
  ...config,
  customManagers: config.customManagers.filter(
    (manager) => manager.datasourceTemplate !== "git-refs",
  ),
};
const missingDocumentation = await documentationOwners(withoutDocumentation);
assert.throws(
  () => verifyDocumentation(missingDocumentation),
  /retain every documentation-source pin owner/,
);
const policyCases = [];
for (const [label, dependency, expectedAge] of [
  [
    "ordinary site Python",
    {
      manager: "pep621",
      datasource: "pypi",
      packageName: "zensical",
      packageFile: "pyproject.toml",
    },
    "3 days",
  ],
  [
    "ordinary Node package",
    { manager: "npm", datasource: "npm", packageName: "prettier", packageFile: "package.json" },
    "3 days",
  ],
  [
    "unrelated documentation source",
    {
      manager: "custom.regex",
      datasource: "git-refs",
      packageName: "Strukturpiloten/unrelated",
      packageFile: "documentation-sources.toml",
    },
    "3 days",
  ],
]) {
  const policy = await applyPackageRules({ ...config, ...dependency, updateType: "patch" });
  assert.equal(policy.minimumReleaseAge, expectedAge, label);
  assert.equal(policy.automerge, true, label);
  assert.equal(policy.dependencyDashboardApproval, false, label);
  policyCases.push({
    label,
    minimumReleaseAge: policy.minimumReleaseAge,
    automerge: policy.automerge,
    approval: policy.dependencyDashboardApproval,
  });
}
assert.deepEqual(transportCalls, []);
console.log(
  JSON.stringify({
    runtime: JSON.parse(fs.readFileSync(path.join(runtime, "package.json"))).version,
    selectedRuntimeImage: JSON.parse(
      fs.readFileSync(path.join(shared, "automation/renovate-runtime.json")),
    ).image,
    selectedAutomation: manifest.revision,
    workflows,
    documentation: documentation.map((row) => ({
      dependency: row.dependency,
      groupName: row.policy.groupName,
      minimumReleaseAge: row.policy.minimumReleaseAge,
      automerge: row.policy.automerge,
      approval: row.policy.dependencyDashboardApproval,
    })),
    policyCases,
    negativeCases: [
      "duplicate regex owner in each workflow",
      "disabled native owner in each workflow",
      "routine Node approval regression in each workflow",
      "removed documentation-source manager",
    ],
    transportCalls,
    scope:
      "actual frozen native/custom extraction and effective rules only; no datasource lookup, update, acquisition or engine",
  }),
);
