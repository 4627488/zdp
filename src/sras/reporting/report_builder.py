"""PDF reporting utilities for SRAS."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Mapping, Sequence

from matplotlib.figure import Figure

try:  # pragma: no cover - optional dependency
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception as exc:  # pragma: no cover - optional dependency
    REPORTLAB_AVAILABLE = False
    _REPORTLAB_ERROR = exc
else:  # pragma: no cover - optional dependency
    REPORTLAB_AVAILABLE = True
    _REPORTLAB_ERROR = None

from sras.data import FailureDataset, FailureSeriesType
from sras.services.analysis import RankedModelResult
from sras.visualization import figure_to_png_bytes


SERIES_TYPE_LABELS = {
    FailureSeriesType.TIME_BETWEEN_FAILURES: "故障间隔 (TBF)",
    FailureSeriesType.CUMULATIVE_FAILURES: "累计故障数",
}


def _series_label(series_type: FailureSeriesType) -> str:
    return SERIES_TYPE_LABELS.get(series_type, series_type.value)


class ReportBuilder:
    """Build PDF reports showing dataset + model diagnostics."""

    def __init__(self) -> None:
        if not REPORTLAB_AVAILABLE:  # pragma: no cover - import guard
            raise RuntimeError(
                "ReportLab is required for PDF export."
                f" Original error: {(_REPORTLAB_ERROR or 'unknown')}"
            )

    def build(
        self,
        dataset: FailureDataset,
        ranked_results: Sequence[RankedModelResult],
        *,
        output_path: str | Path,
        figures: Mapping[str, Figure] | None = None,
        extra_context: Mapping[str, object] | None = None,
    ) -> Path:
        png_figures = {name: figure_to_png_bytes(fig) for name, fig in (figures or {}).items()}
        context = {
            "dataset": dataset,
            "ranked": ranked_results,
            "best": ranked_results[0] if ranked_results else None,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        if extra_context:
            context.update(extra_context)
        output_path = Path(output_path)
        self._build_reportlab_pdf(output_path, dataset, ranked_results, png_figures, context)
        return output_path

    def _build_reportlab_pdf(
        self,
        output_path: Path,
        dataset: FailureDataset,
        ranked_results: Sequence[RankedModelResult],
        figures: Mapping[str, bytes],
        context: Mapping[str, object],
    ) -> None:
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=48,
            bottomMargin=48,
        )
        styles = getSampleStyleSheet()
        code_style = styles["Code"] if "Code" in styles else styles["Normal"]
        story: list[object] = []

        story.append(Paragraph("软件可靠性分析报告", styles["Title"]))
        story.append(Spacer(1, 12))
        meta = f"生成时间 {context['generated_at']} · 数据来源：{dataset.metadata.get('path', 'N/A')}"
        story.append(Paragraph(meta, styles["Normal"]))
        story.append(Spacer(1, 18))

        story.append(Paragraph("数据集概览", styles["Heading2"]))
        story.append(Spacer(1, 6))
        table_data = [
            ["记录数", str(dataset.size)],
            ["序列类型", _series_label(dataset.series_type)],
            ["时间范围", f"{dataset.time_axis[0]:.2f} → {dataset.time_axis[-1]:.2f}"],
        ]
        overview = Table(table_data, hAlign="LEFT", colWidths=[120, 360])
        overview.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.gray),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(overview)
        story.append(Spacer(1, 18))

        story.append(Paragraph("模型排行榜", styles["Heading2"]))
        story.append(Spacer(1, 6))
        leaderboard_data = [["排名", "模型", "RMSE", "MAE", "R²", "AIC", "BIC"]]
        for row in ranked_results:
            metrics = row.result.metrics
            leaderboard_data.append(
                [
                    str(row.rank),
                    row.result.model_name,
                    f"{metrics.get('rmse', 0):.4f}",
                    f"{metrics.get('mae', 0):.4f}",
                    f"{metrics.get('r2', 0):.4f}",
                    f"{metrics.get('aic', 0):.2f}",
                    f"{metrics.get('bic', 0):.2f}",
                ]
            )
        leaderboard = Table(leaderboard_data, repeatRows=1, hAlign="LEFT")
        leaderboard.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.gray),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.whitesmoke),
                ]
            )
        )
        story.append(leaderboard)
        story.append(Spacer(1, 18))

        if ranked_results:
            best = ranked_results[0]
            story.append(Paragraph(f"最佳模型 — {best.result.model_name}", styles["Heading2"]))
            params = ", ".join(f"{k}={v}" for k, v in best.result.parameters.items()) or "暂无"
            story.append(Paragraph(f"参数：{params}", styles["Normal"]))
            diagnostics = best.result.diagnostics or {}
            if diagnostics:
                story.append(Spacer(1, 6))
                story.append(Paragraph("诊断信息", styles["Heading3"]))
                for key, value in diagnostics.items():
                    story.append(Paragraph(f"{key}: {value}", code_style))
            story.append(Spacer(1, 18))

        if figures:
            story.append(Paragraph("可视化诊断", styles["Heading2"]))
            story.append(Spacer(1, 6))
            for name, payload in figures.items():
                story.append(Paragraph(name, styles["Heading3"]))
                image = RLImage(BytesIO(payload), width=430, height=260)
                story.append(image)
                story.append(Spacer(1, 12))

        doc.build(story)


__all__ = ["ReportBuilder"]
