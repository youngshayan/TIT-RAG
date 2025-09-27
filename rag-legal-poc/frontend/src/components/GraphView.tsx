import React from "react";
import CytoscapeComponent from "react-cytoscapejs";

/**
 * شکل ورودی که بک‌اند برمی‌گرداند:
 * {
 *   nodes: [{ data: { id, label, type, score, ... }, classes?: "query|chunk|doc" }],
 *   edges: [{ data: { id, source, target, weight }, classes?: "ref|match|semantic" }]
 * }
 *
 * یا اینکه ممکن است مستقیم elements (آرایه‌ی ترکیبی node/edge) بدهد.
 */

type GraphInput =
  | {
      nodes?: Array<{ data: any; classes?: string }>;
      edges?: Array<{ data: any; classes?: string }>;
      elements?: any[];
    }
  | any[];

type Props = {
  graph: GraphInput | null | undefined;
  height?: number;
  layoutName?: "cose" | "cose-bilkent" | "grid" | "concentric" | "breadthfirst" | "circle";
};

function toElements(graph: GraphInput): any[] {
  if (!graph) return [];
  // حالت ۱: اگر خودش elements باشد
  if (Array.isArray(graph)) return graph as any[];
  // حالت ۲: اگر nodes/edges داشته باشد
  const nodes = Array.isArray((graph as any).nodes) ? (graph as any).nodes : [];
  const edges = Array.isArray((graph as any).edges) ? (graph as any).edges : [];
  return [...nodes, ...edges];
}

const defaultStylesheet: any[] = [
  // گره‌ها
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-wrap": "wrap",
      "text-max-width": 140,
      "font-size": 11,
      "text-valign": "center",
      "text-halign": "center",
      "background-color": "#e2e8f0",
      "border-color": "#94a3b8",
      "border-width": 1,
      color: "#0f172a",
      width: "mapData(score, 0, 1, 28, 56)",
      height: "mapData(score, 0, 1, 28, 56)",
    },
  },
  // کوئری
  {
    selector: "node.query",
    style: {
      "background-color": "#22c55e",
      "border-color": "#16a34a",
      color: "#052e16",
      "font-weight": "600",
      width: 56,
      height: 56,
    },
  },
  // چانک
  {
    selector: "node.chunk",
    style: {
      "background-color": "#93c5fd",
      "border-color": "#60a5fa",
    },
  },
  // سند
  {
    selector: "node.doc",
    style: {
      "background-color": "#facc15",
      "border-color": "#eab308",
    },
  },

  // یال‌ها
  {
    selector: "edge",
    style: {
      width: "mapData(weight, 0, 1, 1.5, 6)",
      "line-color": "#94a3b8",
      "target-arrow-color": "#94a3b8",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      label: "data(label)",
      "font-size": 9,
      color: "#334155",
      "text-background-color": "#ffffff",
      "text-background-opacity": 0.8,
      "text-background-padding": 2,
    },
  },
  // انواع یال
  {
    selector: "edge.ref",
    style: {
      "line-color": "#64748b",
      "target-arrow-color": "#64748b",
    },
  },
  {
    selector: "edge.match",
    style: {
      "line-color": "#16a34a",
      "target-arrow-color": "#16a34a",
    },
  },
  {
    selector: "edge.semantic",
    style: {
      "line-color": "#2563eb",
      "target-arrow-color": "#2563eb",
      "line-style": "dashed",
    },
  },
];

const layoutPresets: Record<string, any> = {
  cose: { name: "cose", animate: false, fit: true, padding: 20 },
  grid: { name: "grid", fit: true, padding: 20, avoidOverlap: true },
  circle: { name: "circle", fit: true, padding: 20 },
  concentric: { name: "concentric", fit: true, padding: 30, minNodeSpacing: 20 },
  breadthfirst: { name: "breadthfirst", fit: true, padding: 20, directed: true, spacingFactor: 1.3 },
};

const GraphView: React.FC<Props> = ({ graph, height = 420, layoutName = "cose" }) => {
  const elements = React.useMemo(() => toElements(graph || []), [graph]);
  const layout = React.useMemo(() => layoutPresets[layoutName] || layoutPresets.cose, [layoutName]);

  // اگر چیزی برای نمایش نیست
  if (!elements || elements.length === 0) {
    return (
      <div
        className="w-full rounded-xl border border-dashed border-slate-300 text-slate-500 text-sm flex items-center justify-center"
        style={{ height }}
      >
        گرافی برای نمایش وجود ندارد.
      </div>
    );
  }

  return (
    <div className="w-full">
      <CytoscapeComponent
        elements={elements as any}
        stylesheet={defaultStylesheet}
        layout={layout as any}
        style={{ width: "100%", height }}
        cy={(cy: any) => {
          // تعامل ساده: کلیک روی نود/یال → لاگ و هایلایت موقت
          cy.on("tap", "node", (evt: any) => {
            const node = evt.target;
            console.log("node:", node.data());
            node.addClass("selected");
            setTimeout(() => node.removeClass("selected"), 800);
          });
          cy.on("tap", "edge", (evt: any) => {
            const edge = evt.target;
            console.log("edge:", edge.data());
            edge.addClass("selected");
            setTimeout(() => edge.removeClass("selected"), 800);
          });
        }}
      />
    </div>
  );
};

export default GraphView;
