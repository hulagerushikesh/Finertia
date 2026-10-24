/**
 * Where sign-in and registration send someone afterwards.
 *
 * A page that needs an account links to /login or /register with `?next=`
 * set to where the visitor was going, so a set-up opened from a strategy
 * page, or a shared run link, survives the detour through creating an
 * account. It travels in the URL rather than router state so it also
 * survives the static, pre-rendered links and the hop between the two forms.
 *
 * Only a same-site path is honoured: `//evil.example` and `/\evil.example`
 * are read by browsers as another host, so an open redirect would otherwise
 * be one crafted link away.
 */

export const AFTER_AUTH = "/dashboard";

export function nextPath(search) {
  const next = new URLSearchParams(search).get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return AFTER_AUTH;
  // Back to the form itself would only bounce off PublicOnlyRoute.
  if (/^\/(login|register)(?:[/?#]|$)/.test(next)) return AFTER_AUTH;
  return next;
}

/** `/login` or `/register`, carrying `next` when it is somewhere other than the default. */
export function authPath(form, next) {
  return next && next !== AFTER_AUTH ? `${form}?next=${encodeURIComponent(next)}` : form;
}
