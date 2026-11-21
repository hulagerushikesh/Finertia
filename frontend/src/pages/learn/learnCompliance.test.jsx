/**
 * Guard for what the /learn articles may say (planning/SEO-PLAN.md, "SEBI").
 *
 * Finertia is a research tool, not a SEBI-registered adviser or research
 * analyst. The articles may describe what rules did on past prices; they must
 * not claim to predict prices, promise returns, or tell a reader to buy, sell
 * or hold anything. This test reads each article's full text, its search
 * title and description, and fails on wording that crosses that line. If a
 * new article trips it, rewrite the sentence; do not widen the allow-list
 * without the author's yes.
 */
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ARTICLES } from "./articles";
import { PAGE_META } from "../../lib/pageMeta";
import { ResearchNote } from "../LearnPage";

const text = (el) =>
  renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>)
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");

const FORBIDDEN = [
  [/\bpredict(s|ed|ing|ion|ions|ive)?\b/i, "prediction claim"],
  [/\bforecast(s|ed|ing)?\b/i, "forecast claim"],
  [/\bguarantee(d|s)?\b/i, "guarantee"],
  [/\bassured\b/i, "assured return"],
  [/\bsure[- ]?shot\b/i, "sure-shot"],
  [/\bmulti-?bagger\b/i, "multibagger"],
  [/\btarget price\b/i, "target price"],
  [/\b(buy|sell) (now|today|this)\b/i, "call to trade"],
  [/\byou should (buy|sell|hold|invest|trade)\b/i, "personal advice"],
  [/\bwe (recommend|suggest|advise)\b/i, "recommendation"],
  [/\b(best|top) stocks? to (buy|invest)\b/i, "stock tip"],
  [/\bwill (rise|fall|go up|go down|double|beat|outperform)\b/i, "statement about the future"],
  [/\bfinertia (tells|shows) you (what|when|which) to (buy|sell|trade)\b/i, "advice claim"],
  [/\b(earn|make) (money|profits?|returns?) (with|using) finertia\b/i, "return promise"],
];

function offences(where, s) {
  return FORBIDDEN.filter(([re]) => re.test(s)).map(([re, why]) => `${where}: ${why} — "${s.match(re)[0]}"`);
}

describe("learn articles stay within research, not advice", () => {
  for (const a of ARTICLES) {
    it(`${a.id}: no prediction, promise or call to trade`, () => {
      const meta = PAGE_META[`learn-${a.id}`];
      const found = [
        ...offences("title", a.title),
        ...offences("lede", a.lede),
        ...offences("body", text(<a.Body />)),
        ...offences("search title", meta.title),
        ...offences("search description", meta.description),
        ...offences("share-card text", meta.imageAlt || ""),
      ];
      expect(found).toEqual([]);
    });
  }

  it("the note under every article says research, not prediction or advice", () => {
    const note = text(<ResearchNote />);
    expect(note).toMatch(/hypothetical/);
    expect(note).toMatch(/does not predict prices/);
    expect(note).toMatch(/not investment advice/);
    expect(note).toMatch(/not a SEBI-registered investment adviser or research analyst/);
  });
});
