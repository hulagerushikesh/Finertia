import React from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { DocHeader, Term } from "../components/Prose";
import { Rise } from "../components/motion";
import { useAuth } from "../hooks/useAuth";
import { usePageTitle } from "../hooks/usePageTitle";
import { ARTICLES, article } from "./learn/articles";
import { STRATEGY_PAGES } from "../lib/strategyPages";
import NotFoundPage from "./NotFoundPage";

const LINK = "text-pencil underline underline-offset-2";

/**
 * /learn and /learn/:id: short articles on the questions people search for
 * before they trust a backtest. Pre-rendered like the other public pages
 * (src/lib/pageMeta.js, scripts/prerender.mjs); the articles themselves are
 * in ./learn/articles.jsx.
 */
export default function LearnPage() {
  const { id } = useParams();
  if (id === undefined) return <LearnIndex />;
  const a = article(id);
  if (!a) return <NotFoundPage />;
  return <Article key={a.id} a={a} />;
}

function LearnIndex() {
  usePageTitle("learn");
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <DocHeader eyebrow="Learn" title="Before you trust a backtest.">
          Short answers to the questions that decide whether a result is worth anything, each
          tied to what this engine actually does about it.
        </DocHeader>
      </Rise>
      <ul className="flex flex-col gap-6">
        {ARTICLES.map((a) => (
          <li key={a.id}>
            <Term name={<Link to={a.path} className="hover:text-pencil transition-colors">{a.title}</Link>}>
              <p className="eyebrow">{a.eyebrow}</p>
              <p>{a.lede}</p>
            </Term>
          </li>
        ))}
      </ul>
      <p className="text-sm text-graphite leading-relaxed mt-12 max-w-prose">
        The rules themselves are on <Link to="/strategies" className={LINK}>Strategies</Link>, and
        every formula is on <Link to="/docs" className={LINK}>How it works</Link>.
      </p>
    </div>
  );
}

function Article({ a }) {
  usePageTitle(`learn-${a.id}`);
  const { user } = useAuth();
  const { Body } = a;
  const others = ARTICLES.filter((o) => o.id !== a.id);

  return (
    <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Rise>
        <nav aria-label="Breadcrumb" className="text-xs text-faint mb-4">
          <Link to="/learn" className="hover:text-pencil transition-colors">Learn</Link>
          <span aria-hidden="true"> / </span>
          <span>{a.eyebrow}</span>
        </nav>
        <DocHeader title={a.title}>{a.lede}</DocHeader>
      </Rise>

      <div className="flex flex-col gap-14">
        <Body />

        <section aria-labelledby="try-heading" className="sheet px-6 py-8 flex flex-col gap-4">
          <h2 id="try-heading" className="font-display text-xl font-semibold text-foreground">
            See it on a real strategy.
          </h2>
          <p className="text-sm text-graphite leading-relaxed max-w-prose">
            Finertia runs these checks on any stock you pick. The free plan runs the backtest;
            Pro adds the validation.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link to={user ? "/dashboard" : "/register"}>{user ? "Open the workspace" : "Create a free account"}</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/demo">See a full result first</Link>
            </Button>
          </div>
        </section>

        <nav aria-label="More to read" className="grid sm:grid-cols-2 gap-6 text-sm">
          <div>
            <p className="eyebrow mb-2">More on this</p>
            <ul className="flex flex-col gap-1.5">
              {others.map((o) => (
                <li key={o.id}><Link to={o.path} className={LINK}>{o.title}</Link></li>
              ))}
            </ul>
          </div>
          <div>
            <p className="eyebrow mb-2">The strategies</p>
            <ul className="flex flex-col gap-1.5">
              {STRATEGY_PAGES.map((s) => (
                <li key={s.id}><Link to={s.path} className={LINK}>{s.label}</Link></li>
              ))}
              <li><Link to="/writeup" className={LINK}>The write-up: the best-looking one was the worst on new data</Link></li>
            </ul>
          </div>
        </nav>
      </div>
    </article>
  );
}
