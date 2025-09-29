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
      "font-size": 12,
      "text-wrap": "wrap",
      "text-max-width": 120,
      "text-valign": "center",
      "text-halign": "center",
      label: "data(label)",
      width: "mapData(score, 0, 1, 28, 52)",
      height: "mapData(score, 0, 1, 28, 52)",
      "overlay-opacity": 0,
    },
  },
  // Query
  {
    selector: "node.query",
    style: {
      "background-color": BRAND.navy,
      "border-color": "#082a4d",
      "border-width": 3,
      color: "white",
      "font-weight": 700,
      shape: "hexagon",
      width: 64,
      height: 64,
    },
  },
  // Keyword
  {
    selector: "node.keyword",
    style: {
      "background-color": "#e2e8f0",
      "border-color": BRAND.gray,
      "border-width": 1,
      color: "#334155",
      shape: "round-rectangle",
      padding: "6px",
      // دیگر از width/height = 'label' استفاده نمی‌کنیم تا هشدار ندهد
      "text-max-width": 140,
    },
  },
  // Chunk
  {
    selector: "node.chunk",
    style: {
      "background-color": "#eaf3ff",
      "border-color": "#1e88e5",
      "border-width": 2,
      shape: "ellipse",
    },
  },
  // Document
  {
    selector: "node.doc",
    style: {
      "background-color": "#e8f5e9",
      "border-color": BRAND.green,
      "border-width": 2,
      shape: "round-rectangle",
      "text-max-width": 180,
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
      "font-size": 9,
      color: "#475569",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.8,
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

function escapeHtml(s: string){
  return String(s || "").replace(/[&<>"']/g, (m)=>({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" }[m]!));
}

export default function GraphView({ data, height = 540 }: Props) {
  const cyRef = useRef<Core | null>(null);
  const [mode, setMode] = useState<"overview" | "evidence" | "keywords">("overview");
  const [minW, setMinW] = useState<number>(0.0); // edge weight filter
  const [selected, setSelected] = useState<any | null>(null); // پنل جزئیات

  const elements = useMemo<ElementDefinition[]>(() => {
    if (!data?.elements) return [];
    return data.elements;
  }, [data]);

  const layout = layoutPresets[mode];

  // فیلتر یال‌ها + اجرای لایه‌بندی
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

  // هندل کلیک روی نود برای نمایش پنل اطلاعات
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

  return (
    <div className="bg-white rounded-2xl shadow-card p-4 relative">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-slate-600 text-sm">حالت:</span>
          <div className="flex gap-1">
            {(["overview", "evidence", "keywords"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1 rounded-lg text-sm border ${mode===m ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-700 hover:bg-slate-50"}`}
              >
                {m==="overview" ? "نمای کلی" : m==="evidence" ? "شواهد" : "کلیدواژه‌ها"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 ml-4">
            <span className="text-slate-600 text-sm">حداقل وزن یال:</span>
            <input type="range" min={0} max={1} step={0.05} value={minW} onChange={(e)=>setMinW(+e.target.value)} />
            <span className="text-xs text-slate-500 w-10 text-left">{minW.toFixed(2)}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Legend />
          <button onClick={exportPng} className="px-3 py-1 rounded-lg border text-sm hover:bg-slate-50">Export PNG</button>
        </div>
      </div>

      {/* KPI bar */}
      {!!data?.kpis && (
        <div className="flex gap-3 text-xs text-slate-600 mb-2">
          <Badge label="اسناد استنادی" value={String(data.kpis.sources ?? "—")} />
          <Badge label="پوشش کلیدواژه" value={formatPct(data.kpis.keywordCoverage)} />
          <Badge label="اعتماد پاسخ" value={formatPct(data.kpis.confidence)} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
        {/* Graph */}
        <div className="lg:col-span-3">
          <CytoscapeComponent
            elements={elements}
            style={{ width: "100%", height }}
            cy={(cy) => (cyRef.current = cy)}
            stylesheet={baseStyle as any}
            layout={layout as any}
          />
        </div>

        {/* Details panel (shows when a node is clicked) */}
        <div className="lg:col-span-1">
          <div className="border rounded-xl p-3 bg-slate-50 h-full">
            <div className="text-sm font-semibold mb-2">جزئیات نود</div>
            {!selected ? (
              <div className="text-xs text-slate-500">روی یک نود کلیک کنید.</div>
            ) : (
              <div className="text-xs space-y-2">
                <div><span className="text-slate-500">شناسه:</span> <span className="font-mono">{selected.id}</span></div>
                <div><span className="text-slate-500">نوع:</span> {selected.type || "—"}</div>
                <div><span className="text-slate-500">برچسب:</span> {selected.label || "—"}</div>
                {selected.docTitle && <div><span className="text-slate-500">سند:</span> {selected.docTitle}</div>}
                {selected.sourcePath && <div><span className="text-slate-500">مسیر:</span> {selected.sourcePath}</div>}
                {selected.score != null && <div><span className="text-slate-500">امتیاز:</span> {Number(selected.score).toFixed(2)}</div>}
                {selected.preview && (
                  <div>
                    <div className="text-slate-1000">مرور:</div>
                    <div dir="auto" className="bg-white border rounded p-2 leading-6">{escapeHtml(selected.preview)}</div>
                  </div>
                )}
                {selected.meta && (
                  <div>
                    <div className="text-slate-500">متادیتا:</div>
                    <pre className="bg-white border rounded p-2 overflow-auto max-h-52">{JSON.stringify(selected.meta, null, 2)}</pre>
                  </div>
                )}
                <button className="mt-2 px-3 py-1 rounded border text-slate-700 hover:bg-white" onClick={()=>setSelected(null)}>بستن</button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Helpers ---
function Legend(){
  return (
    <div className="flex items-center gap-3 text-xs text-slate-600">
      <LegendDot color="#0b3a6a" shape="hexagon" label="پرسش" />
      <LegendDot color="#e2e8f0" shape="round-rectangle" label="کلیدواژه" />
      <LegendDot color="#eaf3ff" shape="ellipse" label="قطعه" />
      <LegendDot color="#e8f5e9" shape="round-rectangle" label="سند" />
    </div>
  );
}
function LegendDot({color, shape, label}:{color:string; shape:string; label:string;}){
  return <div className="flex items-center gap-1">
    <span style={{ display:"inline-block", width:14, height:14, background:color, borderRadius: shape==="ellipse"?"50%":"6px" }} />
    <span>{label}</span>
  </div>;
}
function Badge({label, value}:{label:string; value:string}){
  return (
    <div className="px-2 py-1 bg-slate-50 border rounded-lg">
      <span className="text-slate-500">{label}: </span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
