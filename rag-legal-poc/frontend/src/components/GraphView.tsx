// src/components/GraphView.tsx
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

const BRAND = {
  navy: "#0b3a6a",
  blue: "#1e88e5",
  sky: "#e3f2fd",
  green: "#2e7d32",
  gray: "#94a3b8",
};

const baseStyle: cytoscape.Stylesheet[] = [
  {
    selector: "node",
    style: {
      "background-color": BRAND.sky,
      "border-color": "#1e88e5",
      "border-width": 2,
      color: "#0f172a",
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
      "background-color": BRAND.navy,
      "border-color": "#082a4d",
      "border-width": 3,
      color: "white",
      "font-weight": 700,
      shape: "hexagon",
      width: 70,
      height: 70,
    },
  },
  {
    selector: "node.keyword",
    style: {
      "background-color": "#e2e8f0",
      "border-color": BRAND.gray,
      "border-width": 1,
      color: "#334155",
      shape: "round-rectangle",
      padding: "6px",
      "text-max-width": 160,
    },
  },
  {
    selector: "node.chunk",
    style: {
      "background-color": "#eaf3ff",
      "border-color": "#1e88e5",
      "border-width": 2,
      shape: "ellipse",
    },
  },
  {
    selector: "node.doc",
    style: {
      "background-color": "#e8f5e9",
      "border-color": BRAND.green,
      "border-width": 2,
      shape: "round-rectangle",
      "text-max-width": 200,
    },
  },
  // Edges
  {
    selector: "edge",
    style: {
      width: "mapData(weight, 0, 1, 1, 6)",
      "line-color": "#cbd5e1",
      "target-arrow-color": "#cbd5e1",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "font-size": 10,
      color: "#475569",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.85,
      "text-background-padding": 2,
      "z-index": 1,
    },
  },
  {
    selector: "edge.semantic",
    style: {
      "line-color": "#1e88e5",
      "target-arrow-color": "#1e88e5",
      width: "mapData(weight, 0, 1, 2, 8)",
    },
  },
  {
    selector: "edge.match",
    style: {
      "line-style": "dashed",
      "line-color": "#94a3b8",
      "target-arrow-color": "#94a3b8",
      "target-arrow-shape": "vee",
    },
  },
  {
    selector: "edge.ref",
    style: {
      "line-color": "#66bb6a",
      "target-arrow-color": "#66bb6a",
    },
  },
  // selection
  {
    selector: ":selected",
    style: {
      "border-width": 4,
      "border-color": "#fb923c",
      "line-color": "#fb923c",
      "target-arrow-color": "#fb923c",
    },
  },
];

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

function formatPct(x?: number) {
  if (x == null) return "—";
  return `${Math.round(x * 100)}%`;
}

function escapeHtml(s: string) {
  return String(s || "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]!));
}

/** ---------- Small UI helpers ---------- */
function Section({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border rounded-xl bg-white">
      <button
        type="button"
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-slate-700">{title}</span>
        <span className="text-slate-500">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="border-t px-3 py-3">{children}</div>}
    </div>
  );
}

function Pill({ text, tone = "slate" }: { text: string; tone?: "slate" | "blue" | "green" | "orange" }) {
  const map: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700 border-slate-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    green: "bg-emerald-50 text-emerald-700 border-emerald-200",
    orange: "bg-orange-50 text-orange-700 border-orange-200",
  };
  return <span className={`px-2 py-0.5 rounded-full text-[11px] border ${map[tone] || map.slate}`}>{text}</span>;
}

function InfoRow({ k, v, mono = false }: { k: string; v: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <div className="text-[12px] text-slate-500">{k}</div>
      <div className={`text-[12px] text-slate-800 ${mono ? "font-mono break-all" : ""}`}>{v}</div>
    </div>
  );
}

function CopyBtn({ text, label = "کپی" }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text || "");
          setOk(true);
          setTimeout(() => setOk(false), 1200);
        } catch {}
      }}
      className="px-2 py-0.5 text-[11px] rounded border bg-white hover:bg-slate-50 text-slate-700"
      title="کپی در کلیپ‌بورد"
    >
      {ok ? "✔" : label}
    </button>
  );
}

function Progress({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden" title={`${pct}%`}>
      <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

function MetaKV({ meta }: { meta: any }) {
  if (!meta || typeof meta !== "object") return <div className="text-[12px] text-slate-500">—</div>;
  const entries = Object.entries(meta);
  if (!entries.length) return <div className="text-[12px] text-slate-500">—</div>;
  return (
    <div className="space-y-2">
      {entries.map(([k, v]) => {
        const val =
          typeof v === "string" || typeof v === "number" || typeof v === "boolean"
            ? String(v)
            : JSON.stringify(v, null, 2);
        return (
          <div key={k} className="text-[12px]">
            <div className="text-slate-500">{k}</div>
            <div className="bg-slate-50 border rounded p-2 whitespace-pre-wrap break-words leading-7 text-[13px]">
              {val}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** ---------- Main Component ---------- */
export default function GraphView({ data, height = 540 }: Props) {
  const cyRef = useRef<Core | null>(null);
  const [mode, setMode] = useState<"overview" | "evidence" | "keywords">("overview");
  const [minW, setMinW] = useState<number>(0.0);
  const [selected, setSelected] = useState<any | null>(null);
  const [showMore, setShowMore] = useState<boolean>(false);

  const elements = useMemo<ElementDefinition[]>(() => {
    if (!data?.elements) return [];
    return data.elements;
  }, [data]);

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
  }, [mode, minW, layout]);

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
    cy.on("tap", (evt: any) => {
      if (evt.target === cy) onTapBg();
    });

    return () => {
      cy.off("tap", "node", onTapNode);
      cy.off("tap", onTapBg);
    };
  }, [elements]);

  // Export PNG
  const exportPng = () => {
    const cy = cyRef.current;
    if (!cy) return;
    const png = cy.png({ full: true, bg: "#ffffff", scale: 2 });
    const a = document.createElement("a");
    a.href = png;
    a.download = `graph-${Date.now()}.png`;
    a.click();
  };

  const typeTone = (t: string | undefined) =>
    t?.includes("query") ? "blue" : t?.includes("doc") ? "green" : t?.includes("chunk") ? "orange" : "slate";

  return (
    <div className="bg-white rounded-2xl shadow-card p-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-slate-600 text-sm">حالت:</span>
          <div className="flex gap-1">
            {(["overview", "evidence", "keywords"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1 rounded-lg text-sm border ${
                  mode === m ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                {m === "overview" ? "نمای کلی" : m === "evidence" ? "شواهد" : "کلیدواژه‌ها"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 ml-4">
            <span className="text-slate-600 text-sm">حداقل وزن یال:</span>
            <input type="range" min={0} max={1} step={0.05} value={minW} onChange={(e) => setMinW(+e.target.value)} />
            <span className="text-xs text-slate-500 w-10 text-left">{minW.toFixed(2)}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Legend />
          <button onClick={exportPng} className="px-3 py-1 rounded-lg border text-sm hover:bg-slate-50">
            Export PNG
          </button>
        </div>
      </div>

      {/* KPI bar */}
      {!!data?.kpis && (
        <div className="flex gap-3 text-xs text-slate-600 mb-3">
          <Badge label="اسناد استنادی" value={String(data.kpis.sources ?? "—")} />
          <Badge label="پوشش کلیدواژه" value={formatPct(data.kpis.keywordCoverage)} />
          <Badge label="اعتماد پاسخ" value={formatPct(data.kpis.confidence)} />
        </div>
      )}

      {/* Graph (top) */}
      <div className="w-full">
        <CytoscapeComponent
          elements={elements}
          style={{ width: "100%", height }}
          cy={(cy) => (cyRef.current = cy)}
          stylesheet={baseStyle as any}
          layout={layout as any}
        />
      </div>

      {/* Details (bottom, full-width) */}
      <div className="mt-4">
        <div className="border rounded-2xl p-3 bg-slate-50">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-semibold">جزئیات نود</div>
            {selected && (
              <button
                className="px-2 py-1 rounded border text-xs text-slate-700 hover:bg-white"
                onClick={() => setSelected(null)}
              >
                بستن
              </button>
            )}
          </div>

          {!selected ? (
            <div className="text-xs text-slate-500">روی یک نود کلیک کنید تا جزئیات نمایش داده شود.</div>
          ) : (
            <div className="space-y-3">
              {/* header card */}
              <div className="bg-white border rounded-2xl p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Pill text={selected.type || "node"} tone={typeTone(selected.type) as any} />
                    {typeof selected.score === "number" && (
                      <span className="text-[11px] text-slate-600">امتیاز: {Number(selected.score).toFixed(2)}</span>
                    )}
                  </div>
                  {selected.id && <CopyBtn text={String(selected.id)} label="کپی شناسه" />}
                </div>
                <div className="mt-2 text-sm font-semibold text-slate-800 truncate" title={selected.label || ""}>
                  {selected.label || "—"}
                </div>
                {typeof selected.score === "number" && (
                  <div className="mt-2">
                    <Progress value={Number(selected.score) || 0} />
                  </div>
                )}
              </div>

              {/* two-column detail layout (responsive) */}
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
                      className="bg-white border rounded p-3 leading-8 text-[14px] max-h-[360px] overflow-auto"
                    >
                      <span className="whitespace-pre-wrap break-words">
                        {escapeHtml(
                          showMore
                            ? String(selected.preview)
                            : String(selected.preview).slice(0, 1600) + (String(selected.preview).length > 1600 ? "…" : "")
                        )}
                      </span>
                    </div>
                    {String(selected.preview).length > 1600 && (
                      <div className="mt-2">
                        <button
                          className="px-2 py-1 text-[12px] rounded border bg-white hover:bg-slate-50 text-slate-700"
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

/** --- Helpers --- */
function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-slate-600">
      <LegendDot color="#0b3a6a" shape="hexagon" label="پرسش" />
      <LegendDot color="#e2e8f0" shape="round-rectangle" label="کلیدواژه" />
      <LegendDot color="#eaf3ff" shape="ellipse" label="قطعه" />
      <LegendDot color="#e8f5e9" shape="round-rectangle" label="سند" />
    </div>
  );
}
function LegendDot({ color, shape, label }: { color: string; shape: string; label: string }) {
  return (
    <div className="flex items-center gap-1">
      <span
        style={{ display: "inline-block", width: 14, height: 14, background: color, borderRadius: shape === "ellipse" ? "50%" : "6px" }}
      />
      <span>{label}</span>
    </div>
  );
}
function Badge({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-2 py-1 bg-slate-50 border rounded-lg">
      <span className="text-slate-500">{label}: </span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
