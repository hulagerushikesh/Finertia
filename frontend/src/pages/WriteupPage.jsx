import React, { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { Rise } from "../components/motion";
import { Block, inline, parse, slug } from "../lib/markdown";
// The page IS planning/write-up.md — the same file reproduce_writeup.py checks —
// so what is published cannot drift from what was verified.
import source from "../../../planning/write-up.md?raw";

const TITLE = "The best in-sample strategy was the worst out-of-sample one";

export default function WriteupPage() {
  const blocks = useMemo(() => parse(source), []);

  useEffect(() => {
    const previous = document.title;
    document.title = `${TITLE} · Finertia`;
    return () => {
      document.title = previous;
    };
  }, []);

  // Title, then the italic meta line, then the body. The "Draft N, date" line
  // is for the repo; the page shows its date and its proof instead.
  const [title, meta, ...body] = blocks;
  const sections = body.filter((b) => b.type === "h" && b.level === 2);
  const metaText = meta?.text?.replace(/^_|_$/g, "") ?? "";
  const dated = metaText.match(/(\d{1,2} \w{3} \d{4})/)?.[1];

  return (
    <article className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <header className="mb-10">
          <p className="eyebrow mb-4">Research write-up{dated ? ` · ${dated}` : ""}</p>
          <h1 className="font-display text-display-md font-semibold tracking-tight text-foreground text-balance">
            {inline(title.text, "t")}
          </h1>
          <p className="text-sm text-faint leading-relaxed mt-5 max-w-prose">
            Every number on this page is re-run and checked by a script in the repository. Try the
            same set-up yourself on the <Link to="/demo" className="text-pencil underline underline-offset-2">demo</Link> or
            the dashboard.
          </p>
        </header>
      </Rise>

      <nav aria-label="Contents" className="mb-10 border-y border-border py-5">
        <p className="eyebrow mb-3">Contents</p>
        <ol className="sm:columns-2 gap-x-8 text-sm">
          {sections.map((s, i) => (
            <li key={s.text} className="break-inside-avoid mb-1.5">
              <a href={`#${slug(s.text)}`} className="text-graphite hover:text-pencil transition-colors rounded-sm">
                <span className="font-mono text-2xs text-faint mr-3">{String(i + 1).padStart(2, "0")}</span>
                {s.text}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      <div className="flex flex-col gap-4 text-[0.98rem]">
        {body.map((b, i) => (
          <Block key={i} block={b} index={i} />
        ))}
      </div>
    </article>
  );
}
