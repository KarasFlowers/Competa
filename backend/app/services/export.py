"""Report export service — convert report JSON to Markdown or Word (.docx)."""

from __future__ import annotations

import io
from typing import Any


def report_to_markdown(report: dict[str, Any], sources: list[dict[str, Any]] | None = None) -> str:
    """Convert a report dict to a Markdown string."""
    lines: list[str] = []

    # Title
    title = report.get("title", "Competitive Analysis Report")
    lines.append(f"# {title}")
    lines.append("")

    # Executive summary
    summary = report.get("executive_summary", "")
    if summary:
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(summary)
        lines.append("")

    # Sections (recursive)
    def _render_sections(sections: list[dict], depth: int = 2) -> None:
        for section in sections:
            heading = "#" * (depth + 1) + " " + section.get("title", "Untitled")
            lines.append(heading)
            lines.append("")

            content = section.get("content", "")
            if content:
                lines.append(content)
                lines.append("")

            # Claims
            for claim in section.get("claims", []):
                claim_text = claim.get("content", "")
                evidence_ids = claim.get("evidence_ids", [])
                severity = claim.get("severity", "")
                prefix = "- "
                if severity:
                    prefix = f"- **[{severity.upper()}]** "
                line = f"{prefix}{claim_text}"
                if evidence_ids:
                    line += f" *(evidence: {', '.join(str(e) for e in evidence_ids)})*"
                lines.append(line)
            if section.get("claims"):
                lines.append("")

            # Subsections
            _render_sections(section.get("subsections", []), depth + 1)

    _render_sections(report.get("sections", []))

    # Source references
    if sources:
        lines.append("## Sources")
        lines.append("")
        for i, src in enumerate(sources, 1):
            src_type = src.get("type", "url")
            title = src.get("title", "Untitled")
            url = src.get("url", "")
            snippet = src.get("content_snippet", "")
            lines.append(f"[{i}] **{title}** ({src_type})")
            if url:
                lines.append(f"    URL: {url}")
            if snippet:
                lines.append(f"    {snippet[:200]}")
            lines.append("")

    return "\n".join(lines)


def report_to_docx(report: dict[str, Any], sources: list[dict[str, Any]] | None = None) -> bytes:
    """Convert a report dict to a Word (.docx) file and return bytes."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
    except ImportError:
        raise RuntimeError("python-docx is not installed. Install with: pip install python-docx")

    doc = Document()

    # Title
    title = report.get("title", "Competitive Analysis Report")
    doc.add_heading(title, level=0)

    # Executive summary
    summary = report.get("executive_summary", "")
    if summary:
        doc.add_heading("Executive Summary", level=1)
        doc.add_paragraph(summary)

    # Sections (recursive)
    def _add_sections(sections: list[dict], level: int = 1) -> None:
        for section in sections:
            doc.add_heading(section.get("title", "Untitled"), level=min(level, 9))
            content = section.get("content", "")
            if content:
                doc.add_paragraph(content)

            for claim in section.get("claims", []):
                claim_text = claim.get("content", "")
                severity = claim.get("severity", "")
                prefix = f"[{severity.upper()}] " if severity else ""
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(f"{prefix}{claim_text}")
                evidence_ids = claim.get("evidence_ids", [])
                if evidence_ids:
                    ev_run = p.add_run(f" (evidence: {', '.join(str(e) for e in evidence_ids)})")
                    ev_run.font.color.rgb = RGBColor(128, 128, 128)
                    ev_run.font.size = Pt(9)

            _add_sections(section.get("subsections", []), level + 1)

    _add_sections(report.get("sections", []))

    # Sources
    if sources:
        doc.add_heading("Sources", level=1)
        for i, src in enumerate(sources, 1):
            p = doc.add_paragraph()
            run = p.add_run(f"[{i}] {src.get('title', 'Untitled')} ({src.get('type', 'url')})")
            run.bold = True
            url = src.get("url", "")
            if url:
                doc.add_paragraph(f"URL: {url}", style="List Bullet 2")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
