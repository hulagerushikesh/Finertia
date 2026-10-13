// The only parts of the Sentry SDK the app uses. Named re-exports let the
// bundler drop the rest (tracing, replay, feedback); a dynamic import of the
// package itself pulls in the whole namespace, about 150 kB gzipped.
export { init, captureException, setUser, breadcrumbsIntegration } from "@sentry/browser";
