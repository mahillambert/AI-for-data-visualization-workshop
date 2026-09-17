# CPS mobility and college-enrollment figure

`cps_mobility_vs_college_enrollment.pdf` is a vector PDF scatter plot based on
`data/CPS_merged.csv`. Each point is a school with complete values for
`Mobility_Rate_Pct` and `College_Enrollment_School_Pct_Year_2`. The chart includes
an ordinary-least-squares trendline and a shaded one-standard-deviation confidence
interval for the estimated mean line.

Regenerate the figure from the repository root with:

```bash
python3 scripts/create_cps_mobility_college_figure.py
```
