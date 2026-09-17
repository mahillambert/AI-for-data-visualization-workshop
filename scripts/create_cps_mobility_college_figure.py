#!/usr/bin/env python3
"""Create a publication-ready CPS mobility versus college-enrollment PDF."""

from __future__ import annotations

import csv
import math
from pathlib import Path


INPUT_FILE = Path("data/CPS_merged.csv")
OUTPUT_FILE = Path("figures/cps_mobility_vs_college_enrollment.pdf")
X_COLUMN = "Mobility_Rate_Pct"
Y_COLUMN = "College_Enrollment_School_Pct_Year_2"


def read_points(path: Path) -> list[tuple[float, float]]:
    """Return finite school-level mobility/enrollment pairs from the CPS CSV."""
    points: list[tuple[float, float]] = []
    with path.open(newline="", encoding="utf-8-sig") as source:
        for row in csv.DictReader(source):
            try:
                x, y = float(row[X_COLUMN]), float(row[Y_COLUMN])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isfinite(x) and math.isfinite(y):
                points.append((x, y))
    if len(points) < 3:
        raise ValueError("At least three complete school records are required for the regression.")
    return points


def regression(points: list[tuple[float, float]]) -> tuple[float, float, float, float, int]:
    """Return intercept, slope, residual SD, x mean, and x sum of squares."""
    n = len(points)
    x_mean = sum(x for x, _ in points) / n
    y_mean = sum(y for _, y in points) / n
    sxx = sum((x - x_mean) ** 2 for x, _ in points)
    if sxx == 0:
        raise ValueError("Mobility rates must vary to fit a regression.")
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / sxx
    intercept = y_mean - slope * x_mean
    residual_sd = math.sqrt(sum((y - (intercept + slope * x)) ** 2 for x, y in points) / (n - 2))
    return intercept, slope, residual_sd, x_mean, sxx


def text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def circle(commands: list[str], x: float, y: float, radius: float) -> None:
    """Append a filled Bezier-circle path to a PDF content stream."""
    k = radius * 0.55228475
    commands.append(
        f"{x + radius:.2f} {y:.2f} m {x + radius:.2f} {y + k:.2f} {x + k:.2f} {y + radius:.2f} {x:.2f} {y + radius:.2f} c "
        f"{x - k:.2f} {y + radius:.2f} {x - radius:.2f} {y + k:.2f} {x - radius:.2f} {y:.2f} c "
        f"{x - radius:.2f} {y - k:.2f} {x - k:.2f} {y - radius:.2f} {x:.2f} {y - radius:.2f} c "
        f"{x + k:.2f} {y - radius:.2f} {x + radius:.2f} {y - k:.2f} {x + radius:.2f} {y:.2f} c f"
    )


def write_pdf(path: Path, content: str, width: int, height: int) -> None:
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(content.encode('ascii'))} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, object_text in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n{object_text}\nendobj\n".encode("ascii"))
    start_xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f\n".encode("ascii"))
    output.extend(b"".join(f"{offset:010d} 00000 n\n".encode("ascii") for offset in offsets[1:]))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start_xref}\n%%EOF\n".encode("ascii"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)


def main() -> None:
    points = read_points(INPUT_FILE)
    intercept, slope, residual_sd, x_mean, sxx = regression(points)
    n = len(points)
    width, height = 612, 468  # 8.5 by 6.5 inches
    left, right, bottom, top = 84, 34, 70, 66
    plot_width, plot_height = width - left - right, height - bottom - top

    def sx(value: float) -> float:
        return left + value / 100 * plot_width

    def sy(value: float) -> float:
        return bottom + value / 100 * plot_height

    commands = ["1 J 1 j", "1 1 1 rg 0 0 612 468 re f", "0 0 0 rg",
                "BT /F2 16 Tf 84 430 Td (School Mobility and College Enrollment) Tj ET",
                "0.25 0.25 0.25 rg BT /F1 9 Tf 84 415 Td (Chicago Public Schools; each point is one school) Tj ET"]
    # One-standard-error confidence band for the estimated mean regression line.
    samples = list(range(101))
    upper = [(sx(x), sy(intercept + slope * x + residual_sd * math.sqrt(1 / n + (x - x_mean) ** 2 / sxx))) for x in samples]
    lower = [(sx(x), sy(intercept + slope * x - residual_sd * math.sqrt(1 / n + (x - x_mean) ** 2 / sxx))) for x in reversed(samples)]
    commands.append("0.78 0.88 0.96 rg")
    commands.append(f"{upper[0][0]:.2f} {upper[0][1]:.2f} m")
    commands.extend(f"{x:.2f} {y:.2f} l" for x, y in upper[1:] + lower)
    commands.append("h f")
    # Grid and axes.
    for value in range(0, 101, 20):
        commands.append(f"0.88 0.88 0.88 RG 0.45 w {sx(value):.2f} {bottom:.2f} m {sx(value):.2f} {bottom + plot_height:.2f} l S")
        commands.append(f"0.88 0.88 0.88 RG 0.45 w {left:.2f} {sy(value):.2f} m {left + plot_width:.2f} {sy(value):.2f} l S")
        commands.append(f"0.25 0.25 0.25 rg BT /F1 8 Tf {sx(value) - 6:.2f} {bottom - 18:.2f} Td ({value}) Tj ET")
        commands.append(f"0.25 0.25 0.25 rg BT /F1 8 Tf {left - 25:.2f} {sy(value) - 3:.2f} Td ({value}) Tj ET")
    commands.append(f"0 0 0 RG 0.8 w {left} {bottom} {plot_width} {plot_height} re S")
    commands.append("0.22 0.22 0.22 rg")
    for x, y in points:
        circle(commands, sx(x), sy(y), 1.45)
    line_points = [(sx(x), sy(intercept + slope * x)) for x in samples]
    commands.append("0.05 0.32 0.60 RG 1.8 w [] 0 d")
    commands.append(f"{line_points[0][0]:.2f} {line_points[0][1]:.2f} m")
    commands.extend(f"{x:.2f} {y:.2f} l" for x, y in line_points[1:])
    commands.append("S")
    # Labels and explanatory legend.
    commands.extend([
        "0 0 0 rg BT /F1 10 Tf 218 30 Td (Mobility rate (%)) Tj ET",
        "q 0 1 -1 0 24 160 cm BT /F1 10 Tf 0 0 Td (College enrollment rate (%), Year 2) Tj ET Q",
        "0.22 0.22 0.22 rg 224 390 6 6 re f 0 0 0 rg BT /F1 8 Tf 234 389 Td (School) Tj ET",
        "0.78 0.88 0.96 rg 302 389 19 7 re f 0.05 0.32 0.60 RG 1.3 w 302 392.5 m 321 392.5 l S 0 0 0 rg BT /F1 8 Tf 327 389 Td (Linear fit and 1 SD confidence interval) Tj ET",
        f"0.25 0.25 0.25 rg BT /F1 8 Tf 84 48 Td (n = {n}; fitted slope = {slope:.3f} percentage points of enrollment per percentage point of mobility.) Tj ET",
    ])
    write_pdf(OUTPUT_FILE, "\n".join(commands), width, height)
    print(f"Wrote {OUTPUT_FILE} using {n} schools; slope={slope:.6f}; residual SD={residual_sd:.6f}.")


if __name__ == "__main__":
    main()
