import React from "react";
import type { LineStatus, ProofLine } from "../types";

export interface RibbonEdge {
  line: ProofLine;
  yLeftTop: number;
  yLeftBottom: number;
  yLeftMid: number;
  yRightMid: number;
}

interface ProvenanceRibbonProps {
  edges: RibbonEdge[];
  height: number;
  selectedLineId: string | null;
  hoveredLineId: string | null;
  onSelectLine: (lineId: string) => void;
  onHoverLine: (lineId: string | null) => void;
}

const STATUS_COLOR: Record<LineStatus, string> = {
  verified: "#059669",
  flagged: "#dc2626",
  edited: "#4f46e5",
  unreviewed: "#64748b",
};

export const ProvenanceRibbon: React.FC<ProvenanceRibbonProps> = ({
  edges,
  height,
  selectedLineId,
  hoveredLineId,
  onSelectLine,
  onHoverLine,
}) => {
  const width = 92;
  const activeId = hoveredLineId ?? selectedLineId;

  // Draw inactive edges first, active edge last so it sits cleanly on top
  const sorted = [...edges].sort((a, b) => {
    const aActive = a.line.line_id === activeId ? 1 : 0;
    const bActive = b.line.line_id === activeId ? 1 : 0;
    return aActive - bActive;
  });

  return (
    <div className="ribbon-column" aria-label="Lean-to-LaTeX Provenance Mapping Ribbon">
      <svg
        className="ribbon-svg"
        width={width}
        height={Math.max(height, 300)}
        viewBox={`0 0 ${width} ${Math.max(height, 300)}`}
      >
        {sorted.map((edge) => {
          const { line, yLeftTop, yLeftBottom, yLeftMid, yRightMid } = edge;
          const isSelected = line.line_id === selectedLineId;
          const isHovered = line.line_id === hoveredLineId;
          const isActive = isSelected || isHovered;
          const isDimmed = activeId !== null && !isActive;

          const baseColor =
            line.status === "unreviewed" && line.derivation.opaque_automation
              ? "#d97706"
              : STATUS_COLOR[line.status];

          const cp1x = width * 0.44;
          const cp2x = width * 0.56;

          // Tapered Sankey band from Lean span [yLeftTop..yLeftBottom] -> LaTeX card midpoint
          const halfRight = isActive ? 5 : 2.5;
          const bandPath = [
            `M 2 ${yLeftTop}`,
            `C ${cp1x} ${yLeftTop}, ${cp2x} ${yRightMid - halfRight}, ${width - 2} ${yRightMid - halfRight}`,
            `L ${width - 2} ${yRightMid + halfRight}`,
            `C ${cp2x} ${yRightMid + halfRight}, ${cp1x} ${yLeftBottom}, 2 ${yLeftBottom}`,
            "Z",
          ].join(" ");

          const centerPath = `M 2 ${yLeftMid} C ${cp1x} ${yLeftMid}, ${cp2x} ${yRightMid}, ${width - 2} ${yRightMid}`;

          return (
            <g
              key={line.line_id}
              className={`ribbon-edge ${isActive ? "is-active" : ""} ${isDimmed ? "is-dimmed" : ""}`}
              onMouseEnter={() => onHoverLine(line.line_id)}
              onMouseLeave={() => onHoverLine(null)}
              onClick={() => onSelectLine(line.line_id)}
            >
              <path
                d={bandPath}
                fill={baseColor}
                fillOpacity={isActive ? 0.22 : isDimmed ? 0.04 : 0.1}
              />
              <path
                d={centerPath}
                fill="none"
                stroke={baseColor}
                strokeWidth={isActive ? 2.4 : 1.3}
                strokeOpacity={isActive ? 0.95 : isDimmed ? 0.2 : 0.55}
                strokeDasharray={line.status === "flagged" ? "4 2.5" : undefined}
              />
              <circle
                cx={4}
                cy={yLeftMid}
                r={isActive ? 3.8 : 2.3}
                fill={baseColor}
                fillOpacity={isDimmed ? 0.25 : 0.95}
              />
              <circle
                cx={width - 4}
                cy={yRightMid}
                r={isActive ? 3.8 : 2.3}
                fill={baseColor}
                fillOpacity={isDimmed ? 0.25 : 0.95}
              />
              {isActive && (
                <g transform={`translate(${width / 2}, ${(yLeftMid + yRightMid) / 2})`}>
                  <rect
                    x={-36}
                    y={-10}
                    width={72}
                    height={20}
                    rx={10}
                    fill="#0f172a"
                    fillOpacity={0.92}
                  />
                  <text
                    x={0}
                    y={3.5}
                    textAnchor="middle"
                    fill="#f8fafc"
                    fontSize={9.5}
                    fontFamily="'IBM Plex Mono', monospace"
                    fontWeight={600}
                  >
                    L{line.lean_span.start_line}–{line.lean_span.end_line}→#{line.line_number}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};
