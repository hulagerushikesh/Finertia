import React from "react";

/**
 * A renderer for the small slice of Markdown that planning/write-up.md uses:
 * #/##/### headings, paragraphs, pipe tables, "-" and "1." lists, a "---" rule,
 * and inline code, bold, italics and bare URLs.
 *
 * Hand-written rather than a library because that subset is all the write-up
 * needs, and because it returns React elements — no HTML string, so nothing in
 * the file can inject markup. Anything outside the subset renders as plain
 * paragraph text rather than disappearing.
 */

export function slug(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*)|((?:^|(?<=[\s(]))_[^_\s][^_]*_(?=[\s).,;:]|$))|(https?:\/\/[^\s)]+[^\s).,;:])/g;

export function inline(text, keyPrefix = "i") {
  const out = [];
  let last = 0;
  let n = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const tok = m[0];
    const key = `${keyPrefix}-${n++}`;
    if (m[1]) out.push(<code key={key} className="font-mono text-[0.85em] bg-muted px-1 py-0.5 rounded">{tok.slice(1, -1)}</code>);
    else if (m[2]) out.push(<strong key={key} className="font-semibold text-foreground">{inline(tok.slice(2, -2), key)}</strong>);
    else if (m[3] || m[4]) out.push(<em key={key}>{inline(tok.slice(1, -1), key)}</em>);
    else if (m[5]) out.push(<a key={key} href={tok} className="text-pencil underline underline-offset-2 break-words">{tok.replace(/^https?:\/\//, "")}</a>);
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function cells(row) {
  return row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

/** Parse into blocks: {type, ...}. Exported for the page's contents list. */
export function parse(source) {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) { blocks.push({ type: "h", level: h[1].length, text: h[2] }); i++; continue; }

    if (/^---+\s*$/.test(line)) { blocks.push({ type: "hr" }); i++; continue; }

    if (line.trim().startsWith("|")) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) rows.push(lines[i++]);
      const [head, , ...body] = rows;
      blocks.push({ type: "table", head: cells(head), rows: body.map(cells) });
      continue;
    }

    const list = line.match(/^(\d+\.|-)\s+/);
    if (list) {
      const ordered = list[1] !== "-";
      const items = [];
      while (i < lines.length && lines[i].trim()) {
        const item = lines[i].match(/^(\d+\.|-)\s+(.*)$/);
        if (item) items.push(item[2]);
        else items[items.length - 1] += " " + lines[i].trim();
        i++;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,3}\s|\||---+\s*$|(\d+\.|-)\s)/.test(lines[i])) {
      para.push(lines[i++].trim());
    }
    blocks.push({ type: "p", text: para.join(" ") });
  }
  return blocks;
}

const NUMERIC = /^[−+\-]?[\d.,]+(\s?%|%\/yr)?(\s*\[.*\])?$|^\*\*[−+\-]?[\d.,]+/;

export function Block({ block, index }) {
  const key = `b${index}`;
  switch (block.type) {
    case "h": {
      const id = slug(block.text);
      if (block.level === 2) {
        return (
          <h2 id={id} className="scroll-mt-20 font-display text-2xl font-semibold tracking-tight text-foreground text-balance mt-12 mb-1">
            {inline(block.text, key)}
          </h2>
        );
      }
      return <h3 id={id} className="font-display text-lg font-semibold text-foreground mt-8">{inline(block.text, key)}</h3>;
    }
    case "hr":
      return <hr className="my-12 border-border" />;
    case "table":
      return (
        <div className="overflow-x-auto -mx-4 sm:mx-0 my-2 border-y sm:border border-border sm:rounded-lg bg-card">
          <table className="w-full text-sm border-collapse min-w-[34rem]">
            <thead>
              <tr>
                {block.head.map((c, j) => (
                  <th key={j} className="text-left font-mono text-2xs uppercase tracking-wider text-faint font-medium px-4 py-2.5 border-b border-border align-bottom">
                    {inline(c, `${key}h${j}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, r) => (
                <tr key={r} className="border-b border-border last:border-0">
                  {row.map((c, j) => (
                    <td
                      key={j}
                      className={
                        "px-4 py-2.5 align-top text-graphite " +
                        (j > 0 && NUMERIC.test(c) ? "font-mono tabular-nums whitespace-nowrap" : "")
                      }
                    >
                      {inline(c, `${key}r${r}c${j}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "list": {
      const Tag = block.ordered ? "ol" : "ul";
      return (
        <Tag className={(block.ordered ? "list-decimal" : "list-disc") + " pl-5 flex flex-col gap-2 text-graphite marker:text-faint"}>
          {block.items.map((it, j) => <li key={j} className="pl-1 leading-relaxed">{inline(it, `${key}l${j}`)}</li>)}
        </Tag>
      );
    }
    default:
      return <p className="text-graphite leading-relaxed">{inline(block.text, key)}</p>;
  }
}
