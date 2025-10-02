// frontend/src/components/GraphView.tsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape, { Core, ElementDefinition } from "cytoscape";

export type GraphPayload = {
  elements: ElementDefinition[];
  kpis?: {
    sources?: number;
    keywordCoverage?: number; // 0..1
    confidence?: number;      // 0..1
  };
};

type Props = {
  data: GraphPayload | null;
  height?: number | string;
};

/* ---------------------------
   Theme-aware palette helpers
   --------------------------- */
function cssVar(name: string, fallback: string) {
  try {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  } catch { return fallback; }
}

type Palette = {
  surface: string;
  surface2: string;
  text: string;
  muted: string;
  border: string;
  brandRed: string;
  brandRedDark: string;
  brandBlue: string;

  nodeBase: string;     // بدنه نودهای معمولی
  nodeKeyword: string;  // پس‌زمینه کلیدواژه
  nodeChunk: string;    // پس‌زمینه چانک
  nodeDoc: string;      // پس‌زمینه سند
  edgeBase: string;     // یال‌های عمومی
  edgeSemantic: string; // یال‌های معنایی
  edgeMatch: string;    // یال‌های match
  edgeRef: string;      // یال‌های ارجاعی (سبز)
  nodeText: string;     // متن روی نودها
};

function readPalette(): Palette {
  // خواندن از CSS variables تعریف‌شده در styles.css
  const surface = cssVar("--surface", "rgba(255,255,255,0.75)");
  const surface2 = cssVar("--surface-2", "rgba(255,255,255,0.6)");
  const text = cssVar("--text", "#0f172a");
  const muted = cssVar("--muted", "#64748b");
  const border = cssVar("--border", "rgba(15,23,42,0.08)");

  const brandRed = cssVar("--brand-red", "rgb(214, 28, 47)");
  const brandRedDark = cssVar("--brand-red-700", "rgb(160, 20, 35)");
  const brandBlue = cssVar("--brand-blue", "rgb(46, 140, 167)");

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";

  // برای تم‌ها، کانتراست مناسب انتخاب می‌کنیم
  return {
    surface,
    surface2,
    text,
    muted,
    border,
    brandRed,
    brandRedDark,
    brandBlue,
    nodeBase: isDark ? "#12151d" : "#f4f7fb",
    nodeKeyword: isDark ? "#16202c" : "#e7f2f6",
    nodeChunk: isDark ? "#141b24" : "#eef5ff",
    nodeDoc: isDark ? "#12241a" : "#eaf8ef",
    edgeBase: isDark ? "#3a3f4a" : "#cbd5e1",
    edgeSemantic: brandBlue,
    edgeMatch: isDark ? "#a1a8b3" : "#7c8797",
    edgeRef: "#22c55e",
    nodeText: isDark ? "#e6e8ee" : "#0f172a",
  };
}

/* stylesheet ساز پویا بر اساس پالت */
function buildStyles(p: Palette): cytoscape.Stylesheet[] {
  return [
    // Nodes
    {
      selector: "node",
      style: {
        "background-color": p.nodeBase,
        "border-color": p.brandRed,
        "border-width": 2,
        color: p.nodeText,
        "font-size": 13,
        "min-zoomed-font-size": 10,
        "text-wrap": "wrap",
        "text-max-width": 160,
        "text-valign": "center",
        "text-halign": "center",
        label: "data(label)",
        width: "mapData(score, 0, 1, 32, 64)",
        height: "mapData(score, 0, 1, 32, 64)",
        "overlay-opacity": 0,
      },
    },
    {
      selector: "node.query",
      style: {
        "background-color": p.brandRedDark,
        "border-color": p.brandRed,
        "border-width": 3,
        color: "#ffffff",
        "font-weight": 700,
        shape: "hexagon",
        width: 70,
        height: 70,
      },
    },
    {
      selector: "node.keyword",
      style: {
        "background-color": p.nodeKeyword,
        "border-color": p.brandBlue,
        "border-width": 2,
        color: p.nodeText,
        shape: "round-rectangle",
        padding: "6px",
        "text-max-width": 160,
      },
    },
    {
      selector: "node.chunk",
      style: {
        "background-color": p.nodeChunk,
        "border-color": p.brandRed,
        "border-width": 2,
        shape: "ellipse",
        color: p.nodeText,
      },
    },
    {
      selector: "node.doc",
      style: {
        "background-color": p.nodeDoc,
        "border-color": "#22c55e",
        "border-width": 2,
        shape: "round-rectangle",
        "text-max-width": 200,
        color: p.nodeText,
      },
    },

    // Edges
    {
      selector: "edge",
      style: {
        width: "mapData(weight, 0, 1, 1, 6)",
        "line-color": p.edgeBase,
        "target-arrow-color": p.edgeBase,
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        "font-size": 10,
        color: p.muted,
        "text-background-color": p.surface,
        "text-background-opacity": 0.85,
        "text-background-padding": 2,
        "z-index": 1,
      },
    },
    {
      selector: "edge.semantic",
      style: {
        "line-color": p.edgeSemantic,
        "target-arrow-color": p.edgeSemantic,
        width: "mapData(weight, 0, 1, 2, 8)",
      },
    },
    {
      selector: "edge.match",
      style: {
        "line-style": "dashed",
        "line-color": p.edgeMatch,
        "target-arrow-color": p.edgeMatch,
        "target-arrow-shape": "vee",
      },
    },
    {
      selector: "edge.ref",
      style: {
        "line-color": p.edgeRef,
        "target-arrow-color": p.edgeRef,
      },
    },

    // selection
    {
      selector: ":selected",
      style: {
        "border-width": 4,
        "border-color": "#f59e0b",
        "line-color": "#f59e0b",
        "target-arrow-color": "#f59e0b",
      },
    },
  ];
}

const layoutPresets: Record<string, cytoscape.LayoutOptions> = {
  overview: { name: "cose", fit: true, padding: 40, animate: true },
  evidence: {
    name: "breadthfirst",
    directed: true,
    spacingFactor: 1.15,
    padding: 40,
    animate: true,
    roots: "node.query",
  },
  keywords: {
    name: "concentric",
    padding: 40,
    animate: true,
    concentric: (n) => (n.hasClass("query") ? 3 : n.hasClass("chunk") ? 2 : n.hasClass("keyword") ? 1 : 0),
    levelWidth: () => 1,
  },
};

function formatPct(x?: number) { return x == null ? "—" : `${Math.round(x * 100)}%`; }
function escapeHtml(s: string) {
  return String(s || "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]!));
}

/* ---------- Small UI helpers (تم‌محور) ---------- */
function Section({ title, children, defaultOpen = true }:{
  title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-border rounded-xl bg-card">
      <button
        type="button"
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-primary">{title}</span>
        <span className="text-muted">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="border-t border-border px-3 py-3">{children}</div>}
    </div>
  );
}

function Pill({ text }: { text: string }) {
  return <span className="px-2 py-0.5 rounded-full text-[11px] bg-card text-primary border border-border">{text}</span>;
}

function InfoRow({ k, v, mono = false }: { k: string; v: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="text-[12px] text-muted">{k}</div>
      <div className={`text-[12px] text-primary ${mono ? "font-mono break-all" : ""}`}>{v}</div>
    </div>
  );
}

function CopyBtn({ text, label = "کپی" }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      onClick={async () => {
        try { await navigator.clipboard.writeText(text || ""); setOk(true); setTimeout(() => setOk(false), 1200); } catch {}
      }}
      className="px-2 py-0.5 text-[11px] rounded border border-border bg-card hover:bg-card-2 text-primary"
      title="کپی در کلیپ‌بورد"
    >
      {ok ? "✔" : label}
    </button>
  );
}

function Progress({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  const bar = cssVar("--brand-blue", "rgb(46, 140, 167)");
  return (
    <div className="w-full h-2 bg-card-2 rounded-full overflow-hidden" title={`${pct}%`}>
      <div className="h-full" style={{ width: `${pct}%`, background: bar }} />
    </div>
  );
}

function MetaKV({ meta }: { meta: any }) {
  if (!meta || typeof meta !== "object") return <div className="text-[12px] text-muted">—</div>;
  const entries = Object.entries(meta);
  if (!entries.length) return <div className="text-[12px] text-muted">—</div>;
  return (
    <div className="space-y-2">
      {entries.map(([k, v]) => {
        const val = (typeof v === "string" || typeof v === "number" || typeof v === "boolean")
          ? String(v) : JSON.stringify(v, null, 2);
        return (
          <div key={k} className="text-[12px]">
            <div className="text-muted">{k}</div>
            <div className="bg-card border border-border rounded p-2 whitespace-pre-wrap break-words leading-7 text-[13px]">
              {val}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* -------------- Main Component -------------- */
export default function GraphView({ data, height = 540 }: Props) {
  const cyRef = useRef<Core | null>(null);
  const [mode, setMode] = useState<"overview" | "evidence" | "keywords">("overview");
  const [minW, setMinW] = useState<number>(0.0);
  const [selected, setSelected] = useState<any | null>(null);
  const [showMore, setShowMore] = useState<boolean>(false);

  // رصد تغییر تم (با MutationObserver روی data-theme)
  const [themeKey, setThemeKey] = useState<string>(() =>
    document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light"
  );
  useEffect(() => {
    const el = document.documentElement;
    const obs = new MutationObserver(() => {
      const next = el.getAttribute("data-theme") === "dark" ? "dark" : "light";
      setThemeKey(next);
    });
    obs.observe(el, { attributes: true, attributeFilter: ["data-theme"] });
    return () => obs.disconnect();
  }, []);

  const palette = useMemo(() => readPalette(), [themeKey]);
  const stylesheet = useMemo(() => buildStyles(palette), [palette]);

  const elements = useMemo<ElementDefinition[]>(() => (data?.elements ? data.elements : []), [data]);
  const layout = layoutPresets[mode];

  // Filter edges + layout
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.edges().forEach((e) => {
      const w = Number(e.data("weight") ?? 0);
      e.style("display", w >= minW ? "element" : "none");
    });
    cy.nodes().forEach((n) => {
      const visible = n.connectedEdges(":visible").length > 0 || n.hasClass("query");
      n.style("display", visible ? "element" : "none");
    });

    cy.layout(layout).run();
  }, [mode, minW, layout, themeKey]); // با تغییر تم هم ری‌لی‌اوت شود (برای بازخوانی رندر)

  // Node click -> open details panel
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const onTapNode = (evt: any) => {
      const d = evt.target.data();
      setSelected({
        id: d.id,
        label: d.label,
        type: evt.target.classes().join(" "),
        preview: d.preview,
        docTitle: d.docTitle,
        sourcePath: d.sourcePath,
        meta: d.meta,
        score: d.score,
      });
      setShowMore(false);
    };
    const onTapBg = () => setSelected(null);

    cy.on("tap", "node", onTapNode);
    cy.on("tap", (evt: any) => { if (evt.target === cy) onTapBg(); });

    return () => {
      cy.off("tap", "node", onTapNode);
      cy.off("tap", onTapBg);
    };
  }, [elements]);

  // Export PNG (پس‌زمینه بر اساس تم)
  const exportPng = () => {
    const cy = cyRef.current;
    if (!cy) return;
    const isDark = themeKey === "dark";
    const bg = isDark ? "#0b0b0f" : "#ffffff";
    const png = cy.png({ full: true, bg, scale: 2 });
    const a = document.createElement("a");
    a.href = png; a.download = `graph-${Date.now()}.png`; a.click();
  };

  return (
    <div className="bg-card rounded-2xl shadow-card p-4 border border-border">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-muted text-sm">حالت:</span>
          <div className="flex gap-1">
            {(["overview", "evidence", "keywords"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1 rounded-lg text-sm border ${
                  mode === m ? "bg-brand-red text-white border-transparent" : "bg-card-2 text-primary hover:bg-card border-border"
                }`}
              >
                {m === "overview" ? "نمای کلی" : m === "evidence" ? "شواهد" : "کلیدواژه‌ها"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 ml-4">
            <span className="text-muted text-sm">حداقل وزن یال:</span>
            <input type="range" min={0} max={1} step={0.05} value={minW} onChange={(e) => setMinW(+e.target.value)} />
            <span className="text-xs text-muted w-10 text-left">{minW.toFixed(2)}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Legend themeKey={themeKey} palette={palette} />
          <button onClick={exportPng} className="btn-ghost">Export PNG</button>
        </div>
      </div>

      {/* KPI bar */}
      {!!data?.kpis && (
        <div className="flex gap-3 text-xs text-muted mb-3">
          <Badge label="اسناد استنادی" value={String(data.kpis.sources ?? "—")} />
          <Badge label="پوشش کلیدواژه" value={formatPct(data.kpis.keywordCoverage)} />
          <Badge label="اعتماد پاسخ" value={formatPct(data.kpis.confidence)} />
        </div>
      )}

      {/* Graph */}
      <div className="w-full">
        <CytoscapeComponent
          elements={elements}
          style={{ width: "100%", height }}
          cy={(cy) => (cyRef.current = cy)}
          stylesheet={stylesheet as any}
          layout={layout as any}
        />
      </div>

      {/* Details */}
      <div className="mt-4">
        <div className="border border-border rounded-2xl p-3 bg-card-2">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-semibold">جزئیات نود</div>
            {selected && (
              <button
                className="px-2 py-1 rounded border border-border text-xs text-primary hover:bg-card"
                onClick={() => setSelected(null)}
              >
                بستن
              </button>
            )}
          </div>

          {!selected ? (
            <div className="text-xs text-muted">روی یک نود کلیک کنید تا جزئیات نمایش داده شود.</div>
          ) : (
            <div className="space-y-3">
              {/* header card */}
              <div className="bg-card border border-border rounded-2xl p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Pill text={selected.type || "node"} />
                    {typeof selected.score === "number" && (
                      <span className="text-[11px] text-muted">امتیاز: {Number(selected.score).toFixed(2)}</span>
                    )}
                  </div>
                  {selected.id && <CopyBtn text={String(selected.id)} label="کپی شناسه" />}
                </div>
                <div className="mt-2 text-sm font-semibold text-primary truncate" title={selected.label || ""}>
                  {selected.label || "—"}
                </div>
                {typeof selected.score === "number" && (
                  <div className="mt-2">
                    <Progress value={Number(selected.score) || 0} />
                  </div>
                )}
              </div>

              {/* two-column detail layout */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                <Section title="اطلاعات پایه" defaultOpen>
                  <div className="space-y-2">
                    <InfoRow k="شناسه" v={<span className="font-mono break-all">{selected.id || "—"}</span>} />
                    <InfoRow k="نوع" v={<span dir="auto">{selected.type || "—"}</span>} />
                    {selected.docTitle && <InfoRow k="سند" v={<span dir="auto">{selected.docTitle}</span>} />}
                    {selected.sourcePath && (
                      <InfoRow
                        k="مسیر"
                        mono
                        v={
                          <div className="flex items-center gap-2">
                            <span className="truncate max-w-[420px]" title={selected.sourcePath}>
                              {selected.sourcePath}
                            </span>
                            <CopyBtn text={String(selected.sourcePath)} />
                          </div>
                        }
                      />
                    )}
                  </div>
                </Section>

                {selected.preview && (
                  <Section title="پیش‌نمایش محتوا" defaultOpen>
                    <div
                      dir="auto"
                      className="bg-card border border-border rounded p-3 leading-8 text-[14px] max-h-[360px] overflow-auto"
                    >
                      <span className="whitespace-pre-wrap break-words">
                        {escapeHtml(
                          showMore
                            ? String(selected.preview)
                            : String(selected.preview).slice(0, 1600) +
                              (String(selected.preview).length > 1600 ? "…" : "")
                        )}
                      </span>
                    </div>
                    {String(selected.preview).length > 1600 && (
                      <div className="mt-2">
                        <button
                          className="px-2 py-1 text-[12px] rounded border border-border bg-card hover:bg-card-2 text-primary"
                          onClick={() => setShowMore((v) => !v)}
                        >
                          {showMore ? "کمتر نشان بده" : "نمایش بیشتر"}
                        </button>
                      </div>
                    )}
                  </Section>
                )}

                {selected.meta && (
                  <Section title="متادیتا" defaultOpen={false}>
                    <MetaKV meta={selected.meta} />
                  </Section>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* --- Legend & Badges (theme-aware) --- */
function Legend({ themeKey, palette }: { themeKey: string; palette: Palette }) {
  return (
    <div className="flex items-center gap-3 text-xs text-muted">
      <LegendDot color={palette.brandRedDark} shape="hexagon" label="پرسش" />
      <LegendDot color={palette.nodeKeyword} shape="round-rectangle" label="کلیدواژه" />
      <LegendDot color={palette.nodeChunk} shape="ellipse" label="قطعه" />
      <LegendDot color={palette.nodeDoc} shape="round-rectangle" label="سند" />
    </div>
  );
}

function LegendDot({ color, shape, label }: { color: string; shape: string; label: string }) {
  return (
    <div className="flex items-center gap-1">
      <span
        style={{
          display: "inline-block",
          width: 14,
          height: 14,
          background: color,
          borderRadius: shape === "ellipse" ? "50%" : "6px",
          border: "1px solid rgba(0,0,0,0.12)"
        }}
      />
      <span>{label}</span>
    </div>
  );
}

function Badge({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-2 py-1 bg-card border border-border rounded-lg">
      <span className="text-muted">{label}: </span>
      <span className="font-semibold text-primary">{value}</span>
    </div>
  );
}
