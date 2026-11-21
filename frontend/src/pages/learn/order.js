import { ARTICLES } from "./articles";
import { PAGE_META } from "../../lib/pageMeta";

export const published = (a) => PAGE_META[`learn-${a.id}`].published;

/**
 * The /learn list, newest first. Articles published the same day go by the
 * order they were added to ARTICLES, last added first, so a new article is
 * always at the top. Kept apart from LearnPage so its test needs no Firebase.
 */
export const NEWEST_FIRST = ARTICLES.map((a, i) => ({ a, i }))
  .sort((x, y) => published(y.a).localeCompare(published(x.a)) || y.i - x.i)
  .map(({ a }) => a);
