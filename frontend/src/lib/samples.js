/**
 * The onboarding example strategies, as full configs.
 *
 * The data lives in `data/sampleStrategies.json` so the backend tests can run
 * the very same configs through the API. Nothing renders these yet: the
 * first-run hint that offers them waits for the tester round to close
 * (NEXT-MILESTONE, sprint 2 item 3).
 */
import { DEFAULTS } from "../components/ConfigPanel";
import data from "../data/sampleStrategies.json";
import { encodeParams } from "../utils/permalink";

export const SAMPLES = data.samples.map((s) => ({
  ...s,
  params: { ...DEFAULTS, ...s.params },
}));

export function sampleById(id) {
  return SAMPLES.find((s) => s.id === id) || null;
}

/**
 * The example a config is, if it is one unchanged. Matched on the share-link
 * encoding, which keeps exactly the keys the run uses, so a tweaked example is
 * no longer that example and its "what to look at" note goes away.
 */
export function sampleFor(params) {
  if (!params) return null;
  const link = encodeParams(params);
  return SAMPLES.find((s) => encodeParams(s.params) === link) || null;
}
