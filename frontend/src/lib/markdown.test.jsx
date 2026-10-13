import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { parse, slug, Block } from "./markdown";

describe("parse", () => {
  it("splits headings, rules, tables, lists and paragraphs", () => {
    const blocks = parse(
      ["# Title", "", "First line", "continues here.", "", "---", "| A | B |", "|---|---|", "| 1 | 2 |", "", "- one", "- two", "  wrapped", "", "1. first"].join("\n")
    );
    expect(blocks.map((b) => b.type)).toEqual(["h", "p", "hr", "table", "list", "list"]);
    expect(blocks[1].text).toBe("First line continues here.");
    expect(blocks[3]).toMatchObject({ head: ["A", "B"], rows: [["1", "2"]] });
    expect(blocks[4]).toMatchObject({ ordered: false, items: ["one", "two wrapped"] });
    expect(blocks[5].ordered).toBe(true);
  });

  it("handles Windows line endings", () => {
    expect(parse("## A\r\nb")).toEqual([{ type: "h", level: 2, text: "A" }, { type: "p", text: "b" }]);
  });
});

describe("slug", () => {
  it("makes heading anchors", () => {
    expect(slug("What the numbers say (2018–2024)")).toBe("what-the-numbers-say-20182024");
  });
});

describe("Block", () => {
  it("renders inline code, bold, italics and links", () => {
    const { container } = render(
      <Block index={0} block={{ type: "p", text: "Run `pytest`, **bold** and *soft*; see https://example.com/x." }} />
    );
    expect(container.querySelector("code")).toHaveTextContent("pytest");
    expect(container.querySelector("strong")).toHaveTextContent("bold");
    expect(container.querySelector("em")).toHaveTextContent("soft");
    expect(screen.getByRole("link", { name: "example.com/x" })).toHaveAttribute("href", "https://example.com/x");
  });

  // It returns React elements, never an HTML string: markup in the file stays text.
  it("does not inject HTML", () => {
    const { container } = render(<Block index={0} block={{ type: "p", text: "<img src=x onerror=alert(1)>" }} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container).toHaveTextContent("<img src=x onerror=alert(1)>");
  });

  it("gives h2 an id for the contents list", () => {
    render(<Block index={0} block={{ type: "h", level: 2, text: "The result" }} />);
    expect(screen.getByRole("heading", { level: 2, name: "The result" })).toHaveAttribute("id", "the-result");
  });
});
