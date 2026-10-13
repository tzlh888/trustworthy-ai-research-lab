#!/usr/bin/env python3
"""Generate publication figures from frozen Phase 2B and Phase 3B outputs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METHODS = ("B0", "B1", "B2", "EARS")
COLORS = {"B0": "#6B7280", "B1": "#2563EB", "B2": "#D97706", "EARS": "#059669"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save(fig: plt.Figure, output: Path, name: str) -> None:
    fig.savefig(output / f"{name}.png", dpi=240, bbox_inches="tight", facecolor="white")
    fig.savefig(output / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9.5,
        "axes.titlesize": 11, "axes.labelsize": 9.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "figure.dpi": 120,
    })


def risk_coverage(root: Path, output: Path) -> None:
    fit = read_csv(root / "reports/phase2b/risk_coverage_curves.csv")
    test = read_csv(root / "reports/phase3b/risk_coverage_curves.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), sharey=True)
    for ax, rows, title, n in (
        (axes[0], fit, "Fit-only out-of-fold", 329),
        (axes[1], test, "Frozen Internal Test", 88),
    ):
        for method in METHODS:
            subset = [row for row in rows if row["method"] == method]
            ax.step([float(row["coverage"]) for row in subset], [float(row["selective_risk"]) for row in subset], where="post", color=COLORS[method], linewidth=1.7, label=method)
        ax.set_title(f"{title} (n={n})")
        ax.set_xlabel("Coverage (accepted claims / eligible claims)")
        ax.set_xlim(0, 1.01); ax.set_ylim(0, 1.02); ax.grid(alpha=.18, linewidth=.6)
    axes[0].set_ylabel("Selective risk (errors / accepted claims)")
    axes[1].legend(loc="upper right")
    fig.suptitle("Risk-Coverage Curves Without Smoothing", fontsize=13, fontweight="bold")
    fig.text(.5, -.01, "Lower curves are better. Every prefix k=1,...,n is shown using the frozen tie rule.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .03, 1, .95))
    save(fig, output, "figure_1_risk_coverage_fit_vs_test")


def method_bars(root: Path, output: Path) -> None:
    rows = {row["method"]: row for row in read_csv(root / "reports/phase3b/test_metrics.csv")}
    fig, axes = plt.subplots(1, 2, figsize=(9.3, 3.8))
    x = np.arange(len(METHODS))
    aurc = [float(rows[m]["aurc"]) for m in METHODS]
    errors = [int(rows[m]["errors_at_80"]) for m in METHODS]
    axes[0].bar(x, aurc, color=[COLORS[m] for m in METHODS], width=.7)
    axes[0].set_xticks(x, METHODS); axes[0].set_ylabel("AURC (mean prefix selective risk)")
    axes[0].set_title("Independent AURC (lower is better)")
    for i, value in enumerate(aurc): axes[0].text(i, value + .008, f"{value:.3f}", ha="center", fontsize=8)
    axes[1].bar(x, errors, color=[COLORS[m] for m in METHODS], width=.7)
    axes[1].set_xticks(x, METHODS); axes[1].set_ylabel("Errors among 70 accepted claims")
    axes[1].set_title("R80 error count (fixed k=70)")
    for i, value in enumerate(errors): axes[1].text(i, value + .35, str(value), ha="center", fontsize=8)
    for ax in axes: ax.grid(axis="y", alpha=.18, linewidth=.6)
    fig.suptitle("Frozen Internal Test: Method Comparison (n=88)", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, .93))
    save(fig, output, "figure_2_aurc_and_r80_comparison")


def bootstrap_ci(root: Path, output: Path) -> None:
    rows = read_csv(root / "reports/phase3b/paired_comparisons.csv")
    labels = ["Delta AURC", "Delta R80"]
    points = np.array([float(row["paired_difference"]) for row in rows])
    lower = np.array([float(row["ci_lower_95"]) for row in rows])
    upper = np.array([float(row["ci_upper_95"]) for row in rows])
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    y = np.arange(2)
    ax.errorbar(points, y, xerr=np.vstack((points-lower, upper-points)), fmt="o", color="#111827", ecolor="#4B5563", capsize=5, markersize=6)
    ax.axvline(0, color="#B91C1C", linestyle="--", linewidth=1.1)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_xlabel("Paired difference: EARS - B1 (lower favors EARS)")
    ax.set_title("Grouped Bootstrap Point Estimates and 95% Intervals", fontweight="bold")
    ax.grid(axis="x", alpha=.18, linewidth=.6)
    for i, (p, lo, hi) in enumerate(zip(points, lower, upper)):
        ax.text(hi + .004, i, f"{p:+.3f} [{lo:+.3f}, {hi:+.3f}]", va="center", fontsize=8)
    ax.set_xlim(min(lower)-.025, max(upper)+.09)
    fig.text(.5, -.01, "10,000 paired connected-group bootstrap replicates; seed 20261016. No model retraining.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .05, 1, 1))
    save(fig, output, "figure_3_primary_bootstrap_intervals")


def no_relation(root: Path, output: Path) -> None:
    rows = read_csv(root / "reports/phase3b/no_relation_sensitivity.csv")
    full = {row["method"]: row for row in rows if row["analysis"] == "A_full_eligible"}
    non = {row["method"]: row for row in rows if row["analysis"] == "B_non_no_relation_reranked"}
    methods = ("B1", "EARS")
    x = np.arange(2); width = .34
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.7))
    for ax, metric, title in ((axes[0], "aurc", "AURC"), (axes[1], "sr80", "R80")):
        ax.bar(x-width/2, [float(full[m][metric]) for m in methods], width, label="All eligible (n=88)", color="#93C5FD")
        ax.bar(x+width/2, [float(non[m][metric]) for m in methods], width, label="Exclude predicted NO_RELATION (n=82)", color="#10B981")
        ax.set_xticks(x, methods); ax.set_ylabel(title); ax.set_title(f"{title} sensitivity")
        ax.grid(axis="y", alpha=.18, linewidth=.6)
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5, .08), ncol=2, fontsize=8)
    fig.suptitle("NO_RELATION Sensitivity (Secondary Analysis)", fontsize=13, fontweight="bold")
    fig.text(.5, .015, "Six eligible NO_RELATION predictions were all errors. Scores were retained and reranked only within the subset.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .15, 1, .93))
    save(fig, output, "figure_4_no_relation_sensitivity")


def failure_table(root: Path, output: Path) -> None:
    cases = [json.loads(line) for line in (root / "reports/phase3b/error_analysis_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    wanted = []
    per_type: dict[str, int] = {}
    for row in cases:
        category = row["case_category"]
        if per_type.get(category, 0) >= (2 if category.startswith(("false", "unnecessary")) else 1):
            continue
        wanted.append(row); per_type[category] = per_type.get(category, 0) + 1
        if len(wanted) == 7: break
    labels = {
        "false_reassurance_low_EARS_risk_error": "False reassurance",
        "unnecessary_rejection_high_EARS_risk_correct": "Unnecessary rejection",
        "high_confidence_wrong_B0": "High-confidence error",
        "EARS_rescue_vs_B1_at_global80": "EARS rescue at R80",
        "EARS_harm_vs_B1_at_global80": "EARS harm at R80",
    }
    data = []
    for row in wanted:
        stages = ", ".join(row["failure_categories"]) or "correct prediction"
        data.append([labels[row["case_category"]], str(row["claim_id"]), row["gold_label"], row["predicted_label"], f"{row['risks']['EARS']:.3f}", stages.replace("_", " ")])
    fig, ax = plt.subplots(figsize=(11, 4.2)); ax.axis("off")
    table = ax.table(cellText=data, colLabels=["Case type", "Claim ID", "Gold", "E1 prediction", "EARS score", "Frozen diagnostic"], cellLoc="left", colLoc="left", loc="center", colWidths=[.20,.08,.10,.12,.10,.40])
    table.auto_set_font_size(False); table.set_fontsize(8.2); table.scale(1, 1.55)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#D1D5DB"); cell.set_linewidth(.6)
        if row == 0:
            cell.set_facecolor("#E5E7EB"); cell.set_text_props(weight="bold")
        elif row % 2 == 0: cell.set_facecolor("#F9FAFB")
    ax.set_title("Representative Frozen Internal-Test Cases", fontsize=13, fontweight="bold", pad=14)
    fig.text(.5, .03, "Selected by preregistered deterministic case rules; includes outcomes favorable and unfavorable to EARS.", ha="center", fontsize=8)
    save(fig, output, "table_1_representative_failure_cases")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    style()
    risk_coverage(root, output)
    method_bars(root, output)
    bootstrap_ci(root, output)
    no_relation(root, output)
    failure_table(root, output)
    captions = """# Phase 4 Figure Captions

**Figure 1. Fit-only and independent-test risk-coverage curves.** Every discrete coverage prefix is plotted without smoothing. Fit-only scores are five-fold out-of-fold scores over 329 eligible claims; Internal Test scores use the frozen final models over 88 eligible claims.

**Figure 2. Independent-test AURC and R80 error-count comparison.** Lower is better. R80 uses the same fixed 70 accepted claims for all four methods.

**Figure 3. Primary paired contrasts.** Points are EARS minus B1. Bars are percentile 95% intervals from 10,000 connected-group bootstrap replicates. The joint criterion required both upper bounds to be strictly below zero.

**Figure 4. NO_RELATION sensitivity.** The secondary subset excludes six eligible claims whose E1 prediction was NO_RELATION; all six were errors. Existing scores are reranked without retraining.

**Table 1. Representative cases.** Deterministically selected examples include false reassurance, unnecessary rejection, and R80 boundary exchanges. Frozen diagnostics are descriptive and do not prove causal failure mechanisms.
"""
    (output / "CAPTIONS.md").write_text(captions, encoding="utf-8")


if __name__ == "__main__":
    main()
