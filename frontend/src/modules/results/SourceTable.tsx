import { useEffect, useRef } from "react";

type Props = {
  grid: Array<Array<string | null>>;
  sheetName: string;
  highlightRow?: number | null;
  highlightCol?: number | null;
};

export function SourceTable({ grid, sheetName, highlightRow, highlightCol }: Props) {
  const rowRefs = useRef<Map<number, HTMLTableRowElement | null>>(new Map());

  useEffect(() => {
    if (highlightRow != null && rowRefs.current.has(highlightRow)) {
      rowRefs.current.get(highlightRow)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [highlightRow]);

  if (!grid || grid.length === 0) {
    return (
      <section className="source-table-section">
        <h2>原表</h2>
        <div className="empty-state"><p>暂无原表数据</p></div>
      </section>
    );
  }

  return (
    <section className="source-table-section">
      <h2>原表 — {sheetName}</h2>
      <div className="source-table-wrap">
        <table className="source-table">
          <tbody>
            {grid.map((row, ri) => (
              <tr
                key={ri}
                ref={(el) => { rowRefs.current.set(ri, el); }}
                className={
                  highlightRow === ri ? "source-row-highlight" : ""
                }
              >
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className={
                      highlightRow === ri && highlightCol === ci
                        ? "source-cell-highlight"
                        : highlightRow === ri
                          ? "source-cell-dim"
                          : ""
                    }
                  >
                    {cell ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}