import { describe, expect, it } from "vitest";
import { plain, segments } from "./markup";

describe("segments", () => {
  it("leaves text without marks as one run", () => {
    expect(segments("Find the lab.")).toEqual([{ kind: "text", text: "Find the lab." }]);
  });

  it("reads a bold pair", () => {
    expect(segments("one **searchable** platform")).toEqual([
      { kind: "text", text: "one " },
      { kind: "bold", text: "searchable" },
      { kind: "text", text: " platform" },
    ]);
  });

  it("reads a species pair", () => {
    expect(segments("for __Listeria monocytogenes__?")).toEqual([
      { kind: "text", text: "for " },
      { kind: "species", text: "Listeria monocytogenes" },
      { kind: "text", text: "?" },
    ]);
  });

  it("reads a mark at the very start and end without empty runs", () => {
    expect(segments("**Our mission**")).toEqual([{ kind: "bold", text: "Our mission" }]);
  });

  it("keeps a lone ** as literal text", () => {
    expect(segments("5 ** 2 is not a mark")).toEqual([
      { kind: "text", text: "5 ** 2 is not a mark" },
    ]);
  });

  it("keeps a lone __ as literal text", () => {
    expect(segments("a __dangling mark")).toEqual([{ kind: "text", text: "a __dangling mark" }]);
  });

  it("does not treat snake_case as a mark", () => {
    expect(segments("set database_url and app_env")).toEqual([
      { kind: "text", text: "set database_url and app_env" },
    ]);
  });

  it("reads adjacent pairs separately", () => {
    expect(segments("**a**__b__**c**")).toEqual([
      { kind: "bold", text: "a" },
      { kind: "species", text: "b" },
      { kind: "bold", text: "c" },
    ]);
  });

  it("reads a pair that spans a line break", () => {
    expect(segments("**two\nlines** after")).toEqual([
      { kind: "bold", text: "two\nlines" },
      { kind: "text", text: " after" },
    ]);
  });

  it("reads several pairs in one sentence", () => {
    expect(segments("**bridges** the gap for __E. coli__ and **more**").map((s) => s.kind)).toEqual(
      ["bold", "text", "species", "text", "bold"],
    );
  });
});

describe("plain", () => {
  it("drops the marks and keeps the words", () => {
    expect(plain("Who offers WGS for __Listeria monocytogenes__? **All** of it.")).toEqual(
      "Who offers WGS for Listeria monocytogenes? All of it.",
    );
  });

  it("leaves unmarked underscores alone", () => {
    expect(plain("snake_case stays")).toBe("snake_case stays");
  });
});
