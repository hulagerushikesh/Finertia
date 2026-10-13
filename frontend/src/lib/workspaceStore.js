/**
 * The last workspace state — config, result, validation, tab — kept in memory
 * so leaving the workspace (to History, Profile, anywhere) and coming back
 * shows the run you left, instead of an empty panel and a re-run that costs a
 * monthly run and a duplicate History row (tester report, 13 Oct).
 *
 * Memory only, deliberately: it survives navigation inside the tab, not a
 * reload or a closed tab, and nothing is written to disk on a shared computer.
 * Keyed by uid, and cleared when the account signs out (AuthContext), so one
 * account never sees another's run.
 */
let saved = null; // { uid, state }

export function loadWorkspace(uid) {
  return saved && saved.uid === uid ? saved.state : null;
}

/** Merge `patch` into the saved state; a different uid starts afresh. */
export function saveWorkspace(uid, patch) {
  const base = saved && saved.uid === uid ? saved.state : {};
  saved = { uid, state: { ...base, ...patch } };
}

export function clearWorkspace() {
  saved = null;
}
