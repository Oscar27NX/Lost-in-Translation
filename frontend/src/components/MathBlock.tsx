import React, { useMemo } from "react";
import katex from "katex";

interface MathBlockProps {
  latex: string;
  displayMode?: boolean;
  className?: string;
}

export const MathBlock: React.FC<MathBlockProps> = ({
  latex,
  displayMode = false,
  className = "",
}) => {
  const rendered = useMemo(() => {
    try {
      const html = katex.renderToString(latex, {
        displayMode,
        throwOnError: true,
        strict: "ignore",
        trust: false,
      });
      return { html, error: null as string | null };
    } catch (err) {
      return {
        html: "",
        error: err instanceof Error ? err.message : "Invalid LaTeX syntax",
      };
    }
  }, [latex, displayMode]);

  if (rendered.error) {
    return (
      <div className={`math-error ${className}`}>
        <span className="math-error-badge">LaTeX Syntax Error</span>
        <code className="math-error-raw">{latex}</code>
        <span className="math-error-msg">{rendered.error}</span>
      </div>
    );
  }

  return (
    <span
      className={`math-rendered ${displayMode ? "math-display" : "math-inline"} ${className}`}
      dangerouslySetInnerHTML={{ __html: rendered.html }}
    />
  );
};
