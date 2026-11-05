import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../content/assets/javascripts/analytics.js", import.meta.url),
  "utf8",
);
const origin = "https://boxferry.dev";
const version = "2026-11-05-ga4-v2";
const ttl = 180 * 86400000;
const timestamp = Date.UTC(2026, 10, 5);
const choiceKey = "/.__consent";
const metadataKey = "/.__bf_analytics_consent";
const accepted = { analytics: true };
const metadata = {
  version,
  savedAt: timestamp,
  expiresAt: timestamp + ttl,
};

function browser(options = {}) {
  let now = timestamp;
  const values = new Map();
  if (Object.hasOwn(options, "choice")) values.set(choiceKey, JSON.stringify(options.choice));
  if (Object.hasOwn(options, "metadata")) values.set(metadataKey, JSON.stringify(options.metadata));
  for (const [key, value] of Object.entries(options.raw ?? {})) values.set(key, value);
  const handlers = new Map();
  const timers = new Map();
  let timerId = 0;
  const scripts = [];
  const cookieWrites = [];
  const cookies = new Map(Object.entries(options.cookies ?? { _ga: "old", _ga_TX06VP39B2: "old" }));
  const observers = new Set();
  let subscriptions = 0;
  let reloads = 0;
  const checkbox = { checked: false, disabled: false };
  const consentContainer = { hidden: true };
  const form = {
    elements: { namedItem: (name) => (name === "analytics" ? checkbox : null) },
  };
  const settings = {
    measurementId: "G-TX06VP39B2",
    productionOrigin: origin,
    enabled: "true",
    policyVersion: version,
    consentDays: "180",
    ...options.settings,
  };
  const nativeReads = [];
  const storage = {
    getItem(key) {
      if (options.readFailure) throw new Error("Storage blocked");
      return values.get(key) ?? null;
    },
    setItem(key, value) {
      const failure = options.writeFailures?.[key] ?? options.writeFailure;
      if (failure === "throw") throw new Error("Storage blocked");
      if (failure !== "silent") values.set(key, String(value));
    },
    removeItem(key) {
      if (options.removeFailure === "throw") throw new Error("Removal blocked");
      if (options.removeFailure === "silent") return;
      if (options.writeFailure === "throw") throw new Error("Storage blocked");
      if (options.writeFailure !== "silent") values.delete(key);
    },
  };
  function register(target, type, callback, capture) {
    const list = handlers.get(`${target}:${type}`) ?? [];
    list.push({ callback, capture });
    handlers.set(`${target}:${type}`, list);
  }
  const location = new URL(options.url ?? `${origin}/docs/`);
  location.reload = () => reloads++;
  const document = {
    readyState: options.loading ? "loading" : "complete",
    title: "Authored documentation title",
    referrer: options.referrer ?? "https://search.example/results?q=secret#private",
    forms: { namedItem: (name) => (name === "consent" ? form : null) },
    getElementById: () => ({ dataset: settings }),
    canonical: Object.hasOwn(options, "canonical") ? options.canonical : `${origin}/docs/`,
    nativeConsentContainer: consentContainer,
    querySelector(selector) {
      if (selector === 'link[rel="canonical"]')
        return this.canonical === null ? null : { href: this.canonical };
      if (selector === '[data-md-component="consent"]')
        return options.missingContainer ? null : consentContainer;
      return null;
    },
    createElement: (tag) => ({ tagName: tag }),
    head: { appendChild: (script) => scripts.push(script) },
    addEventListener: (type, callback, capture) => register("document", type, callback, capture),
    get cookie() {
      if (options.cookieFailure) throw new Error("Cookies blocked");
      return [...cookies].map(([key, value]) => `${key}=${value}`).join("; ");
    },
    set cookie(value) {
      if (options.cookieFailure) throw new Error("Cookies blocked");
      cookieWrites.push(value);
      cookies.delete(value.split("=", 1)[0]);
    },
  };
  const context = {
    document,
    location,
    URL,
    console,
    localStorage: storage,
    Date: class extends Date {
      constructor(...args) {
        super(...(args.length ? args : [now]));
      }
      static now() {
        return now;
      }
    },
    setTimeout(callback, delay) {
      timers.set(++timerId, { callback, delay });
      return timerId;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
    __md_scope: new URL(origin),
    __md_get(...args) {
      nativeReads.push({ receiver: this, args });
      const [name, selectedStorage = storage, scope = context.__md_scope] = args;
      return JSON.parse(selectedStorage.getItem(scope.pathname + "." + name));
    },
    __md_set(name, value) {
      try {
        storage.setItem(`/.${name}`, JSON.stringify(value));
      } catch {
        // Match the pinned theme's intentionally swallowed write failures.
      }
    },
    addEventListener: (type, callback) => register("window", type, callback),
  };
  context.window = context;
  if (!options.missingHook)
    context.document$ = {
      subscribe(callback) {
        subscriptions++;
        observers.add(callback);
        callback(document);
        return { unsubscribe: () => observers.delete(callback) };
      },
    };
  vm.createContext(context);
  vm.runInContext(source, context);
  function emit(target, type, event = {}) {
    for (const { callback } of handlers.get(`${target}:${type}`) ?? []) callback(event);
  }
  return {
    context,
    document,
    scripts,
    cookies,
    cookieWrites,
    timers,
    values,
    handlers,
    nativeReads,
    consentContainer,
    get subscriptions() {
      return subscriptions;
    },
    get reloads() {
      return reloads;
    },
    init: () => context.__md_analytics(),
    evaluateAgain: () => vm.runInContext(source, context),
    commands: () => Array.from(context.dataLayer ?? [], (args) => Array.from(args)),
    record: (key) => JSON.parse(values.get(key) ?? "null"),
    nativeBootstrap() {
      vm.runInContext(
        "if (__md_get('__consent')?.analytics) __md_analytics();" +
          "if (!__md_get('__consent')) setTimeout(() => { document.nativeConsentBound = true; document.nativeConsentContainer.hidden = false; }, 250);",
        context,
      );
    },
    themeBootstrap() {
      vm.runInContext("__md_get('__palette')", context);
    },
    clickSettings(target = { closest: () => ({ href: "#__consent" }) }) {
      let prevented = false;
      emit("document", "click", {
        target,
        preventDefault() {
          prevented = true;
        },
      });
      return prevented;
    },
    ready() {
      document.readyState = "complete";
      emit("document", "DOMContentLoaded");
    },
    navigate(path, canonical = path) {
      location.href = new URL(path, origin).href;
      document.canonical = new URL(canonical, origin).href;
      for (const callback of [...observers]) callback(document);
    },
    setNow(value) {
      now = value;
    },
    tick() {
      const pending = [...timers.values()];
      timers.clear();
      for (const { callback } of pending) callback();
    },
    storage(key, value) {
      if (key === null) values.clear();
      else if (value === undefined) values.delete(key);
      else values.set(key, JSON.stringify(value));
      emit("window", "storage", { key });
    },
    choose(checked, type = "submit") {
      checkbox.checked = checked;
      let prevented = false;
      let halted = false;
      emit("document", type, {
        target: form,
        preventDefault() {
          prevented = true;
        },
        stopImmediatePropagation() {
          halted = true;
        },
      });
      const beforeNative = {
        prevented,
        halted,
        disabled: context["ga-disable-G-TX06VP39B2"],
        metadata: JSON.parse(values.get(metadataKey) ?? "null"),
        cookies: [...cookies.keys()],
      };
      // Equivalent of the native bubble handler: adapter must act before this.
      if (!halted) {
        if (type === "reset") checkbox.checked = false;
        context.__md_set("__consent", checkbox.checked ? { analytics: true } : {});
        location.hash = "";
        location.reload();
      }
      return beforeNative;
    },
    unrelatedSubmit() {
      emit("document", "submit", { target: {} });
    },
  };
}

function optedIn(options = {}) {
  return browser({ choice: accepted, metadata, ...options });
}

function virtualViews(site) {
  return site.commands().filter(([command, name]) => command === "event" && name === "page_view");
}

test("first visit and rejection never insert Google, and native UI retains control", () => {
  for (const site of [browser(), browser({ choice: { analytics: false }, metadata })]) {
    site.init();
    assert.equal(site.scripts.length, 0);
    assert.equal(site.commands().length, 0);
  }
  const site = browser();
  site.unrelatedSubmit();
  assert.equal(site.record(metadataKey), null);
  const capture = site.choose(true);
  assert.equal(capture.metadata.savedAt, timestamp);
  assert.equal(capture.metadata.expiresAt, timestamp + ttl);
  assert.equal(capture.metadata.version, version);
  assert.deepEqual(Object.keys(capture.metadata).sort(), ["expiresAt", "savedAt", "version"]);
  assert.equal(site.record(choiceKey).analytics, true);
  assert.equal(site.reloads, 1);
  assert.equal(site.scripts.length, 0);
  const afterReload = browser({
    choice: site.record(choiceKey),
    metadata: site.record(metadataKey),
  });
  afterReload.init();
  assert.equal(afterReload.scripts.length, 1);
  for (const type of ["submit", "reset"])
    assert.equal(site.handlers.get(`document:${type}`)[0].capture, true);
});

test("native omitted unchecked categories remain a valid rejection after reload", () => {
  const site = browser();
  site.choose(false);
  assert.deepEqual(site.record(choiceKey), {});
  assert.deepEqual(site.record(metadataKey), metadata);
  const afterReload = browser({
    choice: site.record(choiceKey),
    metadata: site.record(metadataKey),
  });
  afterReload.init();
  assert.deepEqual(afterReload.record(choiceKey), {});
  assert.deepEqual(afterReload.record(metadataKey), metadata);
  assert.equal(afterReload.scripts.length, 0);
});

test("disabled, local, staging and malformed configuration stay closed", () => {
  const cases = [
    { settings: { enabled: "false" } },
    { settings: { enabled: "TRUE" } },
    { url: "http://localhost:8000/docs/" },
    { url: "https://staging.boxferry.dev/docs/" },
    { settings: { productionOrigin: "http://boxferry.dev" } },
    { settings: { productionOrigin: `${origin}/` } },
    { settings: { measurementId: "G-bad?query" } },
    { settings: { consentDays: "179" } },
    { settings: { policyVersion: "" } },
  ];
  for (const options of cases) {
    const site = optedIn(options);
    site.init();
    assert.equal(site.scripts.length, 0, JSON.stringify(options));
    assert.equal(site.commands().length, 0);
  }
  const disabled = browser({ settings: { enabled: "false" } });
  disabled.choose(true);
  assert.deepEqual(disabled.record(metadataKey), metadata);
  assert.equal(disabled.record(choiceKey).analytics, true);
});

test("legacy, malformed, expired and changed-policy choices require new opt-in", () => {
  const cases = [
    { choice: accepted },
    { choice: { analytics: "true" }, metadata },
    { choice: [true], metadata },
    { choice: { analytics: true, extra: "not boolean" }, metadata },
    { choice: accepted, metadata: {} },
    { choice: accepted, metadata: { ...metadata, extra: "identifier" } },
    { choice: accepted, metadata: { ...metadata, version: "previous" } },
    { choice: accepted, metadata: { ...metadata, version: "2026-11-05-ga4" } },
    { choice: accepted, metadata: { ...metadata, savedAt: timestamp + 1 } },
    { choice: accepted, metadata: { ...metadata, expiresAt: timestamp } },
    { choice: accepted, metadata: { ...metadata, savedAt: timestamp - ttl, expiresAt: timestamp } },
    { raw: { [choiceKey]: "{broken", [metadataKey]: JSON.stringify(metadata) } },
    { choice: accepted, raw: { [metadataKey]: "{broken" } },
  ];
  for (const options of cases) {
    const site = browser(options);
    site.init();
    assert.equal(site.scripts.length, 0, JSON.stringify(options));
    assert.equal(site.record(choiceKey), null);
    assert.equal(site.record(metadataKey), null);
    assert.equal(site.cookies.has("_ga"), false);
  }
});

test("blocked reads and failed metadata writes cannot authorize collection", () => {
  const blocked = optedIn({ readFailure: true });
  blocked.init();
  assert.equal(blocked.scripts.length, 0);
  for (const writeFailure of ["throw", "silent"]) {
    const existing = optedIn({ writeFailure });
    existing.init();
    assert.equal(existing.scripts.length, 0);
    assert.equal(existing.context["ga-disable-G-TX06VP39B2"], true);
    const staleProbe = optedIn({ writeFailure, raw: { "/.__bf_analytics_probe": "true" } });
    staleProbe.init();
    assert.equal(staleProbe.scripts.length, 0);
    const site = browser({ writeFailure });
    site.choose(true);
    site.init();
    assert.equal(site.scripts.length, 0);
    assert.equal(site.record(metadataKey), null);
    assert.equal(site.context["ga-disable-G-TX06VP39B2"], true);
  }
});

test("failed probe removal cannot enable Google and restricted cookies do not break choices", () => {
  for (const removeFailure of ["throw", "silent"]) {
    const site = optedIn({ removeFailure });
    site.init();
    assert.equal(site.scripts.length, 0);
    assert.equal(site.context["ga-disable-G-TX06VP39B2"], true);
  }
  const site = browser({ cookieFailure: true });
  site.choose(false);
  assert.deepEqual(site.record(choiceKey), {});
  assert.deepEqual(site.record(metadataKey), metadata);
});

test("Google configuration denies ads and owns one automatic initial view", () => {
  const site = optedIn();
  site.init();
  site.init();
  site.evaluateAgain();
  site.init();
  assert.equal(site.subscriptions, 1);
  assert.equal(site.scripts.length, 1);
  assert.equal(site.scripts[0].src, "https://www.googletagmanager.com/gtag/js?id=G-TX06VP39B2");
  assert.equal(site.scripts[0].async, true);
  assert.equal(site.values.has("/.__bf_analytics_probe"), false);
  const commands = site.commands();
  assert.deepEqual(JSON.parse(JSON.stringify(commands[0])), [
    "consent",
    "default",
    {
      analytics_storage: "denied",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
    },
  ]);
  const grant = commands.find(([name, action]) => name === "consent" && action === "update");
  assert.deepEqual(Object.keys(grant[2]), ["analytics_storage"]);
  assert.equal(grant[2].analytics_storage, "granted");
  const config = commands.find(([name]) => name === "config");
  assert.equal(config[1], "G-TX06VP39B2");
  assert.deepEqual(JSON.parse(JSON.stringify(config[2])), {
    send_page_view: true,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
    cookie_expires: 180 * 86400,
    cookie_update: false,
    cookie_domain: "boxferry.dev",
    cookie_path: "/",
  });
  assert.ok(commands.findIndex(([name]) => name === "set") < commands.indexOf(config));
  assert.equal(virtualViews(site).length, 0);
  assert.equal(Object.prototype.toString.call(site.context.dataLayer[0]), "[object Arguments]");
});

test("completed navigation uses clean canonical URLs and origin-only initial referrer", () => {
  const site = optedIn({ url: `${origin}/docs/?q=private#secret` });
  site.init();
  site.navigate("/docs/?q=another#different", "/docs/?bad=ignored#ignored");
  assert.equal(virtualViews(site).length, 0);
  site.document.title = "Authored support title";
  site.navigate("/support/?email=private#token", "/support/");
  site.navigate("/support/#again", "/support/");
  const events = virtualViews(site);
  const initial = site.commands().find(([command]) => command === "set")[1];
  assert.equal(initial.page_location, `${origin}/docs/`);
  assert.equal(initial.page_referrer, "https://search.example");
  assert.equal(events.length, 1);
  assert.equal(events[0][2].page_location, `${origin}/support/`);
  assert.equal(events[0][2].page_referrer, `${origin}/docs/`);
  assert.equal(events[0][2].page_title, "Authored support title");
  assert.equal(site.commands().filter(([command]) => command === "config").length, 1);
  assert.doesNotMatch(JSON.stringify(site.commands()), /private|secret|token|ignored/);
});

test("unknown, mismatched, foreign and 404 canonicals emit no views", () => {
  for (const options of [
    { canonical: null },
    { url: `${origin}/unknown/`, canonical: `${origin}/` },
    { canonical: "https://example.com/docs/" },
    { url: `${origin}/404.html`, canonical: `${origin}/404.html` },
  ]) {
    const site = optedIn(options);
    site.init();
    assert.equal(virtualViews(site).length, 0);
    assert.equal(site.scripts.length, 0);
  }
  const index = optedIn({ url: `${origin}/docs/index.html`, canonical: `${origin}/docs/` });
  index.init();
  assert.equal(
    index.commands().find(([command]) => command === "set")[1].page_location,
    `${origin}/docs/`,
  );
  const noReferrer = optedIn({ referrer: "file:///private/path" });
  noReferrer.init();
  assert.equal(noReferrer.commands().find(([command]) => command === "set")[1].page_referrer, "");
});

test("reset and unchecked submission disable immediately before native reload", () => {
  for (const type of ["submit", "reset"]) {
    const site = optedIn({
      cookies: { _ga: "a", _ga_TX06VP39B2: "b", _ga_other: "c", _gather: "keep", session: "keep" },
    });
    site.init();
    const commandsBefore = site.commands().length;
    const result = site.choose(type === "reset", type);
    assert.equal(result.disabled, true);
    assert.deepEqual(result.cookies.sort(), ["_gather", "session"]);
    assert.deepEqual(site.record(choiceKey), {});
    assert.equal(site.reloads, 1);
    assert.equal(site.timers.size, 0);
    site.navigate("/support/");
    assert.equal(site.commands().length, commandsBefore);
    assert.ok(site.cookieWrites.some((value) => value.includes("Domain=boxferry.dev")));
    assert.ok(site.cookieWrites.some((value) => value.includes("Domain=.boxferry.dev")));
  }
});

test("local withdrawal never erases unrelated app cookies", () => {
  const site = optedIn({ url: "http://localhost:8000/docs/" });
  site.choose(false);
  assert.equal(site.cookieWrites.length, 0);
  assert.equal(site.cookies.get("_ga"), "old");
});

test("another tab withdrawing or clearing storage stops views without Google pings", () => {
  for (const [key, value] of [
    [choiceKey, { analytics: false }],
    [metadataKey, undefined],
    [null, undefined],
  ]) {
    const site = optedIn();
    site.init();
    const before = site.commands().length;
    site.storage(key, value);
    assert.equal(site.context["ga-disable-G-TX06VP39B2"], true);
    assert.equal(site.cookies.has("_ga"), false);
    site.navigate("/support/");
    assert.equal(site.commands().length, before);
  }
  const unrelated = optedIn();
  unrelated.init();
  unrelated.storage("/.unrelated", false);
  unrelated.navigate("/support/");
  assert.equal(virtualViews(unrelated).length, 1);
});

test("expiry uses bounded timers and is rechecked before each view", () => {
  const site = optedIn();
  site.init();
  assert.ok([...site.timers.values()].every(({ delay }) => delay <= 2147483647));
  site.setNow(timestamp + ttl);
  site.tick();
  assert.equal(site.context["ga-disable-G-TX06VP39B2"], true);
  assert.equal(site.record(choiceKey), null);
  assert.equal(site.cookies.has("_ga"), false);
  const disabled = optedIn({ settings: { enabled: "false" } });
  disabled.setNow(timestamp + ttl);
  disabled.tick();
  assert.equal(disabled.record(choiceKey), null);
  assert.equal(disabled.scripts.length, 0);
  const betweenViews = optedIn();
  betweenViews.init();
  betweenViews.setNow(timestamp + ttl);
  betweenViews.navigate("/support/");
  assert.equal(virtualViews(betweenViews).length, 0);
  assert.equal(betweenViews.scripts.length, 1);
  assert.equal(betweenViews.record(choiceKey), null);
});

test("initialization waits for DOM readiness and requires the completed-navigation hook", () => {
  const loading = optedIn({ loading: true });
  loading.init();
  loading.init();
  assert.equal(loading.scripts.length, 0);
  loading.ready();
  assert.equal(loading.scripts.length, 1);
  const missing = optedIn({ missingHook: true });
  missing.init();
  assert.equal(missing.scripts.length, 0);
  assert.equal(missing.context["ga-disable-G-TX06VP39B2"], true);
  const revokedBeforeReady = optedIn({ loading: true });
  revokedBeforeReady.init();
  revokedBeforeReady.choose(false);
  revokedBeforeReady.ready();
  assert.equal(revokedBeforeReady.scripts.length, 0);
});

test("native consent bootstrap still binds after blocked reads or malformed JSON", () => {
  for (const options of [
    { choice: accepted, metadata, readFailure: true },
    {
      raw: { [choiceKey]: "{broken" },
      metadata,
      writeFailures: { [choiceKey]: "silent" },
    },
  ]) {
    const site = browser(options);
    assert.doesNotThrow(() => site.nativeBootstrap());
    site.tick();
    assert.equal(site.document.nativeConsentBound, true);
    assert.equal(site.scripts.length, 0);
  }
});

test("safe native getter preserves receiver, all arguments, and unrelated failures", () => {
  const site = browser();
  const receiver = {};
  const store = { getItem: (key) => JSON.stringify({ key }) };
  const scope = { pathname: "/alternate" };
  const result = site.context.__md_get.call(receiver, "other", store, scope, "extra");
  assert.equal(result.key, "/alternate.other");
  const lastRead = site.nativeReads.at(-1);
  assert.equal(lastRead.receiver, receiver);
  assert.deepEqual(lastRead.args, ["other", store, scope, "extra"]);
  const broken = {
    getItem() {
      throw new Error("Unrelated storage failure");
    },
  };
  assert.throws(() => site.context.__md_get("other", broken), /Unrelated storage failure/);
  assert.equal(site.context.__md_get("__consent", broken), null);
  const wrapper = site.context.__md_get;
  site.evaluateAgain();
  assert.equal(site.context.__md_get, wrapper);
});

test("failed native withdrawal cannot renew metadata or revive Google after reload", () => {
  for (const failure of ["throw", "silent"]) {
    for (const type of ["submit", "reset"]) {
      const writeFailures = {};
      const site = optedIn({ writeFailures });
      site.init();
      site.setNow(timestamp + 1000);
      const before = site.commands().length;
      writeFailures[choiceKey] = failure;
      const result = site.choose(type === "reset", type);
      assert.equal(result.prevented, true);
      assert.equal(result.halted, true);
      assert.equal(site.reloads, 0);
      assert.equal(site.context["ga-disable-G-TX06VP39B2"], true);
      assert.equal(site.cookies.has("_ga"), false);
      assert.equal(site.record(metadataKey), null);
      site.navigate("/support/");
      assert.equal(site.commands().length, before);
      // Even when storage works again, the failed withdrawal left no grant metadata.
      const reloaded = browser({
        choice: site.record(choiceKey),
        metadata: site.record(metadataKey),
      });
      reloaded.nativeBootstrap();
      reloaded.init();
      assert.equal(reloaded.scripts.length, 0);
    }
  }
});

test("failed metadata writes independently invalidate the native choice", () => {
  for (const failure of ["throw", "silent"]) {
    const writeFailures = {};
    const site = optedIn({ writeFailures });
    site.init();
    site.setNow(timestamp + 1000);
    writeFailures[metadataKey] = failure;
    const result = site.choose(false);
    assert.equal(result.prevented, true);
    assert.equal(result.halted, true);
    assert.equal(site.record(choiceKey), null);
    assert.equal(site.reloads, 0);
    const reloaded = browser({
      choice: site.record(choiceKey),
      metadata: site.record(metadataKey),
    });
    reloaded.init();
    assert.equal(reloaded.scripts.length, 0);
  }
});

test("when both stored records are immutable, withdrawal stops this document and suppresses reload", () => {
  const writeFailures = {};
  const site = optedIn({ writeFailures });
  site.init();
  writeFailures[choiceKey] = "silent";
  writeFailures[metadataKey] = "silent";
  const result = site.choose(false);
  assert.equal(result.prevented, true);
  assert.equal(result.halted, true);
  assert.equal(site.reloads, 0);
  assert.equal(site.context["ga-disable-G-TX06VP39B2"], true);
  const before = site.commands().length;
  site.navigate("/support/");
  assert.equal(site.commands().length, before);
  // No script can promise durable withdrawal when the browser refuses every write.
  assert.equal(site.record(choiceKey).analytics, true);
  assert.deepEqual(site.record(metadataKey), metadata);
});

test("failed persistence dismisses native consent and footer reopens it without theme runtime", () => {
  for (const options of [
    { readFailure: true, writeFailure: "throw" },
    { readFailure: true, writeFailure: "silent" },
    { writeFailure: "throw" },
    { writeFailure: "silent" },
    { writeFailures: { [choiceKey]: "silent" } },
    { writeFailures: { [metadataKey]: "silent" } },
  ]) {
    const site = browser(options);
    site.nativeBootstrap();
    site.tick();
    assert.equal(site.consentContainer.hidden, false);
    if (options.readFailure) assert.throws(() => site.themeBootstrap(), /Storage blocked/);
    site.context.location.hash = "__consent";
    for (let attempt = 0; attempt < 2; attempt++) {
      const result = site.choose(false, "reset");
      assert.equal(result.prevented, true);
      assert.equal(result.halted, true);
      assert.equal(site.consentContainer.hidden, true);
      assert.equal(site.context.location.hash, "");
      assert.equal(site.reloads, 0);
      assert.equal(site.scripts.length, 0);
      assert.equal(site.commands().length, 0);
      assert.equal(site.clickSettings({}), false);
      assert.equal(site.clickSettings({ closest: () => null }), false);
      assert.equal(site.consentContainer.hidden, true);
      // A nested icon/text element can delegate to the native footer anchor.
      assert.equal(site.clickSettings(), true);
      assert.equal(site.consentContainer.hidden, false);
      assert.equal(site.context.location.hash, "#__consent");
    }
  }
});

test("settings-link fallback activates only after failure and tolerates a missing container", () => {
  const ordinary = browser();
  assert.equal(ordinary.clickSettings(), false);
  assert.equal(ordinary.consentContainer.hidden, true);
  ordinary.choose(false);
  assert.equal(ordinary.clickSettings(), false);
  const missing = browser({ writeFailure: "silent", missingContainer: true });
  assert.doesNotThrow(() => missing.choose(false));
  assert.equal(missing.clickSettings(), false);
});

test("failed-storage settings accept native absolute rewrites without consuming other links", () => {
  const site = browser({ url: `${origin}/docs/?q=local#chapter`, writeFailure: "throw" });
  site.nativeBootstrap();
  site.tick();
  site.choose(false, "reset");
  const click = (href) =>
    site.clickSettings({
      closest(selector) {
        assert.equal(selector, "a[href]");
        return { href };
      },
    });
  for (const href of [
    "https://example.com/docs/?q=local#__consent",
    "http://boxferry.dev/docs/?q=local#__consent",
    `${origin}/support/?q=local#__consent`,
    `${origin}/docs/?q=other#__consent`,
    `${origin}/docs/?q=local#chapter`,
    "http://[broken",
  ]) {
    assert.equal(click(href), false, href);
    assert.equal(site.consentContainer.hidden, true);
  }
  for (const href of [`${origin}/docs/?q=local#__consent`, "#__consent"]) {
    assert.equal(click(href), true, href);
    assert.equal(site.consentContainer.hidden, false);
    assert.equal(site.context.location.hash, "#__consent");
    site.choose(false, "reset");
    assert.equal(site.consentContainer.hidden, true);
  }
  assert.equal(site.scripts.length, 0);
  assert.equal(site.commands().length, 0);
  assert.equal(site.reloads, 0);
});
