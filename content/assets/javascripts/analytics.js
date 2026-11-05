/* Zensical owns the consent UI and native choice; this adapter owns only GA4. */
(() => {
  "use strict";

  if (typeof window.__md_analytics === "function") return;

  const script = document.getElementById("__analytics");
  const settings = script?.dataset ?? {};
  const measurementId = settings.measurementId;
  const metadataKey = "__bf_analytics_consent";
  const nativeKey = "__consent";
  const nativeGet = window.__md_get;
  // Native bootstrap must still bind its banner when consent storage is blocked.
  window.__md_get = function (...args) {
    try {
      return Reflect.apply(nativeGet, this, args);
    } catch (error) {
      if (args[0] === nativeKey) return null;
      throw error;
    }
  };
  const days = Number(settings.consentDays);
  const lifetime = days * 86400000;
  let production;
  try {
    production = new URL(settings.productionOrigin);
    if (production.protocol !== "https:" || production.origin !== settings.productionOrigin)
      production = undefined;
  } catch {
    production = undefined;
  }
  const configured =
    /^G-[A-Z0-9]+$/.test(measurementId ?? "") &&
    production !== undefined &&
    typeof settings.policyVersion === "string" &&
    settings.policyVersion.length > 0 &&
    settings.consentDays === "180" &&
    Number.isSafeInteger(lifetime);
  const onProduction = configured && location.origin === production.origin;
  let started = false;
  let stopped = false;
  let subscription;
  let expiryTimer;
  let loaded = false;
  let previousPage;
  let persistenceFailed = false;

  function read(key) {
    return window.__md_get(key);
  }

  // The native setter swallows storage errors. Read back every adapter write.
  function write(key, value) {
    window.__md_set(key, value);
    if (JSON.stringify(read(key)) !== JSON.stringify(value))
      throw new Error("Consent storage unavailable");
  }

  function writableStorage() {
    const name = "__bf_analytics_probe";
    const key = window.__md_scope.pathname + "." + name;
    try {
      localStorage.removeItem(key);
      if (read(name) !== null) return false;
      write(name, true);
      localStorage.removeItem(key);
      return read(name) === null;
    } catch {
      return false;
    } finally {
      try {
        localStorage.removeItem(key);
      } catch {
        // A failed probe cannot authorize Google, even if cleanup is blocked.
      }
    }
  }

  function clearCookies() {
    if (!onProduction) return;
    let entries;
    try {
      entries = document.cookie.split(";");
    } catch {
      return;
    }
    for (const entry of entries) {
      const name = entry.split("=", 1)[0].trim();
      if (!/^_ga(?:_[^=;\s]+)?$/.test(name)) continue;
      for (const domain of ["", production.hostname, `.${production.hostname}`]) {
        try {
          document.cookie = `${name}=; Max-Age=0; Path=/${domain ? `; Domain=${domain}` : ""}; Secure; SameSite=Lax`;
        } catch {
          // Cookie restrictions must not prevent native choice persistence.
        }
      }
    }
  }

  function stop(clear = true) {
    stopped = true;
    if (configured) window[`ga-disable-${measurementId}`] = true;
    clearTimeout(expiryTimer);
    subscription?.unsubscribe();
    subscription = undefined;
    if (clear) clearCookies();
  }

  function invalidate() {
    stop();
    for (const key of [nativeKey, metadataKey]) {
      try {
        write(key, null);
      } catch {
        // Invalidate each record even when the other key cannot be written.
      }
    }
    return false;
  }

  function consent() {
    if (!configured) return false;
    try {
      const choice = read(nativeKey);
      const metadata = read(metadataKey);
      if (choice == null && metadata == null) return false;
      const now = Date.now();
      if (
        choice === null ||
        typeof choice !== "object" ||
        Array.isArray(choice) ||
        (Object.hasOwn(choice, "analytics") && typeof choice.analytics !== "boolean") ||
        Object.values(choice).some((value) => typeof value !== "boolean") ||
        metadata === null ||
        typeof metadata !== "object" ||
        Array.isArray(metadata) ||
        Object.keys(metadata).sort().join(",") !== "expiresAt,savedAt,version" ||
        metadata.version !== settings.policyVersion ||
        !Number.isSafeInteger(metadata.savedAt) ||
        !Number.isSafeInteger(metadata.expiresAt) ||
        metadata.savedAt > now ||
        metadata.expiresAt - metadata.savedAt !== lifetime ||
        metadata.expiresAt <= now
      )
        return invalidate();
      return Object.hasOwn(choice, "analytics") && choice.analytics === true;
    } catch {
      return invalidate();
    }
  }

  function scheduleExpiry() {
    clearTimeout(expiryTimer);
    try {
      const remaining = read(metadataKey).expiresAt - Date.now();
      expiryTimer = setTimeout(
        () => {
          if (!consent()) stop();
          else scheduleExpiry();
        },
        Math.max(1, Math.min(remaining, 2147483647)),
      );
    } catch {
      invalidate();
    }
  }

  function canonicalPage() {
    const href = document.querySelector('link[rel="canonical"]')?.href;
    if (!href) return undefined;
    try {
      const url = new URL(href);
      const path = (value) => value.replace(/\/index\.html$/, "/");
      if (
        url.origin !== production.origin ||
        path(url.pathname) !== path(location.pathname) ||
        /(?:^|\/)404(?:\.html|\/|$)/.test(url.pathname)
      )
        return undefined;
      return `${url.origin}${path(url.pathname)}`;
    } catch {
      return undefined;
    }
  }

  function initialReferrer() {
    try {
      const url = new URL(document.referrer);
      return ["https:", "http:"].includes(url.protocol) ? url.origin : "";
    } catch {
      return "";
    }
  }

  function view() {
    if (stopped) return;
    if (!consent()) {
      stop();
      return;
    }
    const page = canonicalPage();
    if (!page || page === previousPage) return;
    const fields = {
      page_location: page,
      page_referrer: previousPage ?? initialReferrer(),
      page_title: document.title,
    };
    if (!loaded) {
      if (!writableStorage()) {
        stop();
        return;
      }
      loaded = true;
      window[`ga-disable-${measurementId}`] = false;
      window.dataLayer = window.dataLayer || [];
      window.gtag = function () {
        window.dataLayer.push(arguments);
      };
      window.gtag("consent", "default", {
        analytics_storage: "denied",
        ad_storage: "denied",
        ad_user_data: "denied",
        ad_personalization: "denied",
      });
      // Set clean defaults before Google initializes or configures the property.
      window.gtag("set", fields);
      window.gtag("consent", "update", { analytics_storage: "granted" });
      window.gtag("js", new Date());
      window.gtag("config", measurementId, {
        send_page_view: true,
        allow_google_signals: false,
        allow_ad_personalization_signals: false,
        cookie_expires: days * 86400,
        cookie_update: false,
        cookie_domain: production.hostname,
        cookie_path: "/",
      });
      const loader = document.createElement("script");
      loader.async = true;
      loader.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
      document.head.appendChild(loader);
    } else {
      window.gtag("set", fields);
      window.gtag("event", "page_view", fields);
    }
    previousPage = page;
  }

  window.__md_analytics = function () {
    if (started || stopped || !onProduction || settings.enabled !== "true" || !consent()) return;
    started = true;
    const ready = () => {
      if (stopped || !consent()) return;
      if (typeof document$ === "undefined" || typeof document$.subscribe !== "function") {
        stop();
        return;
      }
      scheduleExpiry();
      subscription = document$.subscribe(view);
      if (stopped) subscription?.unsubscribe();
    };
    if (document.readyState === "loading")
      document.addEventListener("DOMContentLoaded", ready, { once: true });
    else ready();
  };

  for (const type of ["submit", "reset"]) {
    document.addEventListener(
      type,
      (event) => {
        const form = document.forms.namedItem("consent");
        if (!form || event.target !== form) return;
        const checkbox = form.elements.namedItem("analytics");
        const accepted = type === "submit" && checkbox?.checked === true && !checkbox.disabled;
        stop(!accepted);
        if (!configured) return;
        try {
          write(nativeKey, accepted ? { analytics: true } : {});
          const savedAt = Date.now();
          write(metadataKey, {
            version: settings.policyVersion,
            savedAt,
            expiresAt: savedAt + lifetime,
          });
        } catch {
          invalidate();
          // Keep collection off in this document if persistence cannot be proved.
          event.preventDefault();
          event.stopImmediatePropagation();
          persistenceFailed = true;
          const container = document.querySelector('[data-md-component="consent"]');
          if (container) container.hidden = true;
          if (location.hash === "#__consent") location.hash = "";
        }
      },
      true,
    );
  }

  // The native settings link must remain usable even if blocked storage broke
  // the theme runtime. Reopen its existing container only after a failed choice.
  document.addEventListener("click", (event) => {
    if (!persistenceFailed || typeof event.target?.closest !== "function") return;
    const link = event.target.closest("a[href]");
    if (!link) return;
    try {
      const target = new URL(link.href, location.href);
      if (
        target.origin !== location.origin ||
        target.pathname !== location.pathname ||
        target.search !== location.search ||
        target.hash !== "#__consent"
      )
        return;
    } catch {
      return;
    }
    const container = document.querySelector('[data-md-component="consent"]');
    if (!container) return;
    event.preventDefault();
    container.hidden = false;
    location.hash = "__consent";
  });

  window.addEventListener("storage", (event) => {
    const prefix = window.__md_scope.pathname + ".";
    if (
      event.key !== null &&
      event.key !== prefix + nativeKey &&
      event.key !== prefix + metadataKey
    )
      return;
    if (!consent()) stop();
  });

  // Run before Zensical's native analytics gate can consume an old choice.
  if (!consent()) stop();
  else scheduleExpiry();
})();
