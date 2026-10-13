/**
 * Error reporting to Sentry from the browser, with what leaves it kept small.
 *
 * The SDK is loaded as its own chunk after the app starts, so it never sits in
 * front of first paint and the landing page's entry bundle does not grow.
 * Errors reported before it arrives are queued and sent once it does.
 *
 * Off in dev, in tests, and against the Firebase emulators (the E2E suite).
 *
 * What a report carries: the error and its stack, the page path, the browser,
 * the deploy it came from, and the Firebase uid. What it does not:
 * - no personal data (`sendDefaultPii: false`: no IP address, no email);
 * - no query strings anywhere — the dashboard's address bar holds the user's
 *   strategy settings, and admin search puts an email address in an API URL;
 * - no console output in breadcrumbs (it can echo API responses);
 * - no performance tracing and no session replay: errors only.
 */

// A DSN only lets a client SEND events to this project; it cannot read
// anything, and it ships in the bundle whichever way it is configured.
// VITE_SENTRY_DSN overrides it (set it empty to switch reporting off).
const DEFAULT_DSN =
  "https://2ce2cfecd79052321a0b85e401ff723f@o4512247279976448.ingest.us.sentry.io/4512247320018944";

function configuredDsn(env = import.meta.env) {
  if (env.VITE_FIREBASE_EMULATORS === "1") return "";
  if (env.VITE_SENTRY_DSN !== undefined) return env.VITE_SENTRY_DSN;
  return env.PROD ? DEFAULT_DSN : "";
}

/** "https://x/dashboard?ticker=AAPL#a" → "https://x/dashboard". */
export function stripQuery(url) {
  return typeof url === "string" ? url.split(/[?#]/, 1)[0] : url;
}

/** beforeSend: drop query strings, referrer and every user field but the id. */
export function scrubEvent(event) {
  if (event.request) {
    event.request.url = stripQuery(event.request.url);
    delete event.request.query_string;
    delete event.request.cookies;
    if (event.request.headers) {
      const { "User-Agent": ua } = event.request.headers;
      event.request.headers = ua ? { "User-Agent": ua } : {};
    }
  }
  if (event.user) event.user = event.user.id ? { id: event.user.id } : {};
  return event;
}

/** beforeBreadcrumb: no console lines; URLs without their query strings. */
export function scrubBreadcrumb(crumb) {
  if (crumb.category === "console") return null;
  if (crumb.data) {
    for (const key of ["url", "from", "to"]) {
      if (key in crumb.data) crumb.data[key] = stripQuery(crumb.data[key]);
    }
  }
  return crumb;
}

let sentry = null;
let pending = [];

function run(fn) {
  if (sentry) fn(sentry);
  else if (pending) pending.push(fn);
}

export function initMonitoring(env = import.meta.env) {
  const dsn = configuredDsn(env);
  if (!dsn) {
    pending = null; // nothing will ever drain the queue
    return false;
  }
  import("./sentryClient")
    .then((S) => {
      S.init({
        dsn,
        environment: env.VITE_VERCEL_ENV || env.MODE,
        release: env.VITE_VERCEL_GIT_COMMIT_SHA || undefined,
        sendDefaultPii: false,
        integrations: (defaults) => [
          ...defaults.filter((i) => i.name !== "Breadcrumbs"),
          S.breadcrumbsIntegration({ console: false }),
        ],
        beforeSend: scrubEvent,
        beforeBreadcrumb: scrubBreadcrumb,
      });
      sentry = S;
      const queued = pending || [];
      pending = null;
      queued.forEach((fn) => fn(S));
    })
    .catch(() => {
      // Blocked by an ad blocker or offline: reporting is best-effort.
      pending = null;
    });
  return true;
}

export function reportError(error, extra) {
  run((S) => S.captureException(error, extra ? { extra } : undefined));
}

/** The Firebase uid only — never email. null on sign-out. */
export function setMonitoringUser(uid) {
  run((S) => S.setUser(uid ? { id: uid } : null));
}
