"""PDF reporting utilities for ZDP."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import os
from pathlib import Path
from typing import Mapping, Sequence

from matplotlib.figure import Figure
import numpy as np

try:  # pragma: no cover - optional dependency
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception as exc:  # pragma: no cover - optional dependency
    REPORTLAB_AVAILABLE = False
    _REPORTLAB_ERROR = exc
else:  # pragma: no cover - optional dependency
    REPORTLAB_AVAILABLE = True
    _REPORTLAB_ERROR = None

from zdp.data import FailureDataset, FailureSeriesType
from zdp.services.analysis import RankedModelResult
from zdp.visualization import figure_to_png_bytes


SERIES_TYPE_LABELS = {
    FailureSeriesType.TIME_BETWEEN_FAILURES: "故障间隔 (TBF)",
    FailureSeriesType.CUMULATIVE_FAILURES: "累计故障数",
}


def _series_label(series_type: FailureSeriesType) -> str:
    return SERIES_TYPE_LABELS.get(series_type, series_type.value)


def _register_default_cjk_font() -> str:
    """Register a usable CJK font for ReportLab and return its font name.

    Without an embedded CJK-capable font, ReportLab's default fonts will render
    Chinese text as black blocks / missing glyphs.
    """

    font_name = "ZDP_CJK"
    try:
        if font_name in set(pdfmetrics.getRegisteredFontNames()):
            return font_name
    except Exception:
        # If ReportLab internals change, fall back to best-effort registration.
        pass

    font_dir = Path(os.environ.get("WINDIR", r"C:\\Windows")) / "Fonts"
    candidates = [
        font_dir / "msyh.ttc",  # Microsoft YaHei
        font_dir / "msyhbd.ttc",
        font_dir / "simhei.ttf",  # SimHei
        font_dir / "simsun.ttc",  # SimSun
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(path)))
            return font_name
        except Exception:
            continue

    # As a last resort, use built-in font name; Chinese may not render.
    return "Helvetica"


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
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=48,
            bottomMargin=48,
        )
        styles = getSampleStyleSheet()
        font_name = _register_default_cjk_font()
        for key in ("Title", "Heading1", "Heading2", "Heading3", "Normal", "BodyText", "Code"):
            if key in styles:
                styles[key].fontName = font_name
        # Slightly tune typography to look cleaner.
        styles["Title"].fontSize = 20
        styles["Title"].leading = 24
        styles["Heading2"].spaceBefore = 10
        styles["Heading2"].spaceAfter = 6
        styles["Normal"].fontSize = 10.5
        styles["Normal"].leading = 14
        code_style = styles["Code"] if "Code" in styles else styles["Normal"]
        story: list[object] = []

        project_title = "Zero-Defect Prediction (ZDP)"

        # --- Cover
        story.append(Spacer(1, 2 * cm))
        story.append(Paragraph(project_title, styles["Title"]))
        story.append(Spacer(1, 10))
        story.append(Paragraph("软件可靠性分析报告", styles["Heading1"]))
        story.append(Spacer(1, 18))
        meta = (
            f"生成时间：{context['generated_at']}<br/>"
            f"数据来源：{dataset.metadata.get('path', 'N/A')}<br/>"
            f"数据类型：{_series_label(dataset.series_type)} · 记录数：{dataset.size}"
        )
        story.append(Paragraph(meta, styles["Normal"]))
        story.append(Spacer(1, 18))
        story.append(
            Paragraph(
                "本报告由 Zero-Defect Prediction 自动生成，包含数据概览、模型对比、可视化诊断与建议。",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 18))

        if ranked_results:
            best = ranked_results[0]
            story.append(
                Paragraph(
                    f"最佳模型：<b>{best.result.model_name}</b>（排名第 1）",
                    styles["Normal"],
                )
            )
        story.append(Spacer(1, 24))
        story.append(Paragraph("—", styles["Normal"]))
        story.append(Spacer(1, 24))

        # --- Summary
        story.append(Paragraph("分析摘要", styles["Heading2"]))
        story.append(Spacer(1, 6))
        if ranked_results:
            best = ranked_results[0]
            metrics = best.result.metrics or {}
            primary_metric = "cv_rmse" if any(k.startswith("cv_") for k in metrics.keys()) else "rmse"
            score = metrics.get(primary_metric, float("nan"))
            summary = (
                f"本次共运行成功 {len(ranked_results)} 个模型。"
                f" 最佳模型为 <b>{best.result.model_name}</b>，"
                f"按 {primary_metric.upper()} 排名得分为 {float(score):.4f}。"
            )
            story.append(Paragraph(summary, styles["Normal"]))
        else:
            story.append(Paragraph("本次未获得可用模型结果（可能因数据类型不兼容或拟合失败）。", styles["Normal"]))
        story.append(Spacer(1, 10))
        story.append(Paragraph("指标说明", styles["Heading3"]))
        story.append(
            Paragraph(
                "RMSE/MAE 越小越好；R² 越大越好。若启用走步验证（Walk-Forward），CV_* 指标更能反映泛化性能。",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 10))
        story.append(Paragraph("兼容性提示", styles["Heading3"]))
        story.append(
            Paragraph(
                "部分机器学习模型仅支持“累计故障数”数据；若导入的是 TBF（故障间隔）数据，这些模型会被自动跳过。",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 18))

        story.append(Paragraph("数据集概览", styles["Heading2"]))
        story.append(Spacer(1, 6))
        values = np.asarray(dataset.values, dtype=float)
        outliers = int(np.count_nonzero(dataset.detect_outliers()))
        table_data = [
            ["记录数", str(dataset.size)],
            ["序列类型", _series_label(dataset.series_type)],
            ["时间范围", f"{dataset.time_axis[0]:.2f} → {dataset.time_axis[-1]:.2f}"],
            ["数值范围", f"{values.min():.4f} → {values.max():.4f}"],
            ["均值 / 标准差", f"{values.mean():.4f} / {values.std(ddof=0):.4f}"],
            ["异常点(粗略)", str(outliers)],
        ]
        overview = Table(table_data, hAlign="LEFT", colWidths=[120, 360])
        overview.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.gray),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(overview)
        story.append(Spacer(1, 18))

        # --- Data preview
        story.append(Paragraph("数据预览（前 10 条）", styles["Heading2"]))
        story.append(Spacer(1, 6))
        preview_rows = min(10, int(dataset.size))
        value_label = "累计故障数" if dataset.series_type == FailureSeriesType.CUMULATIVE_FAILURES else "故障间隔"
        preview_data: list[list[str]] = [["序号", "时间", value_label]]
        for i in range(preview_rows):
            preview_data.append(
                [
                    str(i + 1),
                    f"{float(dataset.time_axis[i]):.4f}",
                    f"{float(dataset.values[i]):.4f}",
                ]
            )
        preview = Table(preview_data, repeatRows=1, hAlign="LEFT", colWidths=[50, 150, 280])
        preview.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("BOX", (0, 0), (-1, -1), 0.25, colors.gray),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.whitesmoke),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(preview)
        story.append(Spacer(1, 18))

        # --- Per-model quick summary (top N)
        if ranked_results:
            story.append(Paragraph("模型摘要（Top 5）", styles["Heading2"]))
            story.append(Spacer(1, 6))
            top_n = min(5, len(ranked_results))
            has_cv = any(
                any(key.startswith("cv_") for key in (row.result.metrics or {}).keys())
                for row in ranked_results
            )
            if has_cv:
                summary_rows = [["排名", "模型", "CV_RMSE", "CV_R²", "RMSE", "R²"]]
            else:
                summary_rows = [["排名", "模型", "RMSE", "MAE", "R²"]]
            for row in ranked_results[:top_n]:
                m = row.result.metrics or {}
                if has_cv:
                    summary_rows.append(
                        [
                            str(row.rank),
                            row.result.model_name,
                            f"{float(m.get('cv_rmse', float('nan'))):.4f}",
                            f"{float(m.get('cv_r2', float('nan'))):.4f}",
                            f"{float(m.get('rmse', float('nan'))):.4f}",
                            f"{float(m.get('r2', float('nan'))):.4f}",
                        ]
                    )
                else:
                    summary_rows.append(
                        [
                            str(row.rank),
                            row.result.model_name,
                            f"{float(m.get('rmse', float('nan'))):.4f}",
                            f"{float(m.get('mae', float('nan'))):.4f}",
                            f"{float(m.get('r2', float('nan'))):.4f}",
                        ]
                    )
            summary_table = Table(summary_rows, repeatRows=1, hAlign="LEFT")
            summary_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.gray),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.whitesmoke),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(summary_table)
            story.append(Spacer(1, 18))

        story.append(Paragraph("模型排行榜", styles["Heading2"]))
        story.append(Spacer(1, 6))
        has_cv = any(
            any(key.startswith("cv_") for key in (row.result.metrics or {}).keys())
            for row in ranked_results
        )
        if has_cv:
            leaderboard_data = [["排名", "模型", "CV_RMSE", "CV_MAE", "CV_R²", "RMSE", "MAE"]]
        else:
            leaderboard_data = [["排名", "模型", "RMSE", "MAE", "R²", "AIC", "BIC"]]
        for row in ranked_results:
            metrics = row.result.metrics
            if has_cv:
                leaderboard_data.append(
                    [
                        str(row.rank),
                        row.result.model_name,
                        f"{metrics.get('cv_rmse', float('nan')):.4f}",
                        f"{metrics.get('cv_mae', float('nan')):.4f}",
                        f"{metrics.get('cv_r2', float('nan')):.4f}",
                        f"{metrics.get('rmse', float('nan')):.4f}",
                        f"{metrics.get('mae', float('nan')):.4f}",
                    ]
                )
            else:
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
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
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

            # Best model key metrics
            story.append(Spacer(1, 8))
            story.append(Paragraph("关键指标", styles["Heading3"]))
            metrics = best.result.metrics or {}
            key_order = ["cv_rmse", "cv_mae", "cv_r2", "rmse", "mae", "r2", "aic", "bic"]
            metric_rows = [["指标", "数值"]]
            for key in key_order:
                if key in metrics:
                    value = metrics.get(key)
                    if value is None:
                        continue
                    metric_rows.append([key.upper(), f"{float(value):.6f}"])
            metric_table = Table(metric_rows, repeatRows=1, hAlign="LEFT", colWidths=[120, 360])
            metric_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), font_name),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.gray),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(metric_table)
            diagnostics = best.result.diagnostics or {}
            if diagnostics:
                story.append(Spacer(1, 6))
                story.append(Paragraph("诊断信息", styles["Heading3"]))
                interval = diagnostics.get("prediction_interval")
                if isinstance(interval, dict):
                    alpha = interval.get("alpha")
                    method = interval.get("method")
                    sigma = interval.get("sigma")
                    story.append(
                        Paragraph(
                            f"预测带：method={method}, alpha={alpha}, sigma={sigma}",
                            code_style,
                        )
                    )
                for key, value in diagnostics.items():
                    if key == "prediction_interval":
                        continue
                    story.append(Paragraph(f"{key}: {value}", code_style))

            story.append(Spacer(1, 10))
            story.append(Paragraph("结论与建议", styles["Heading3"]))
            story.append(
                Paragraph(
                    "1) 若数据为 TBF（故障间隔），请优先选择支持该类型的统计可靠性模型。<br/>"
                    "2) 若数据为累计故障数，可同时对比传统模型与机器学习模型。<br/>"
                    "3) 建议结合残差图与交叉验证指标（CV_*）评估泛化能力。",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 18))

        if figures:
            story.append(Paragraph("可视化诊断", styles["Heading2"]))
            story.append(Spacer(1, 6))
            for name, payload in figures.items():
                story.append(Paragraph(name, styles["Heading3"]))
                image = RLImage(BytesIO(payload), width=430, height=260)
                story.append(image)
                story.append(Spacer(1, 12))

        def _decorate(canvas, doc_obj):
            canvas.saveState()
            canvas.setFont(font_name, 9)
            canvas.setFillColor(colors.grey)
            header_y = doc_obj.pagesize[1] - 24
            canvas.drawString(doc_obj.leftMargin, header_y, project_title)
            canvas.drawRightString(
                doc_obj.pagesize[0] - doc_obj.rightMargin,
                header_y,
                f"第 {canvas.getPageNumber()} 页",
            )
            canvas.setFillColor(colors.black)
            footer_y = 18
            canvas.setFont(font_name, 8.5)
            canvas.setFillColor(colors.grey)
            canvas.drawString(doc_obj.leftMargin, footer_y, f"生成时间：{context['generated_at']}")
            canvas.restoreState()

        doc.build(story, onFirstPage=_decorate, onLaterPages=_decorate)


__all__ = ["ReportBuilder"]
