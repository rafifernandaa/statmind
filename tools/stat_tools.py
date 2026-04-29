"""
Pure-Python statistical tools — no R, no scipy dependency needed for hackathon demo.
Called as function declarations by the google-genai client directly.
"""

import json
import statistics
import math
from typing import Optional
from datetime import datetime, timedelta

from db.database import get_db
from db.models import Task, AnalysisJob, ResearchNote, Dataset, DatasetColumn


# ─── Statistical computation ──────────────────────────────────────────────────


# ─── Data resolution ──────────────────────────────────────────────────────────
# All stat tools accept either:
#   - Raw JSON array:    "[1, 2, 3, 4, 5]"
#   - Dataset reference: "ds:42:score"  (dataset_id=42, column=score)
#   - Short form:        "42:score"     (same as above)
# This lets the agent reference stored data without the user pasting values.

def _resolve_data(ref: str) -> list:
    """
    Resolve a data reference to a Python list of floats.
    Accepts raw JSON or 'ds:ID:column' / 'ID:column' references.
    Raises ValueError with a helpful message if the reference is invalid.
    """
    ref = ref.strip()
    # Raw JSON array
    if ref.startswith("["):
        return [float(v) for v in json.loads(ref)]

    # Dataset column reference: ds:42:score  or  42:score
    parts = ref.lstrip("ds:").split(":")
    if len(parts) == 2:
        try:
            ds_id = int(parts[0])
            col_name = parts[1].strip()
        except ValueError:
            raise ValueError(
                f"Invalid reference '{ref}'. Use JSON array or 'dataset_id:column_name'."
            )
        with get_db() as db:
            col = (db.query(DatasetColumn)
                   .filter(DatasetColumn.dataset_id == ds_id,
                           DatasetColumn.column_name == col_name)
                   .first())
            if not col:
                # Try case-insensitive match
                col = (db.query(DatasetColumn)
                       .filter(DatasetColumn.dataset_id == ds_id,
                               DatasetColumn.column_name.ilike(col_name))
                       .first())
            if not col:
                available = [c.column_name for c in
                             db.query(DatasetColumn)
                             .filter(DatasetColumn.dataset_id == ds_id).all()]
                raise ValueError(
                    f"Column '{col_name}' not found in dataset {ds_id}. "
                    f"Available columns: {available}"
                )
            return [float(v) for v in json.loads(col.data_json)
                    if v is not None and v != ""]
    raise ValueError(
        f"Cannot resolve '{ref}'. Provide a JSON array like '[1,2,3]' "
        f"or a reference like '42:score'."
    )


def store_dataset_columns(dataset_id: int, columns_json: str) -> dict:
    """
    Store column data for a registered dataset so stat tools can reference it.
    Call this after register_dataset to make the data usable.

    Args:
        dataset_id:   ID returned by register_dataset.
        columns_json: JSON object mapping column names to arrays of values.
                      E.g. '{"score": [4,3,5,4], "anxiety": [2,3,2,1]}'
    """
    try:
        cols = json.loads(columns_json)
        if not isinstance(cols, dict):
            return {"error": "columns_json must be a JSON object: {col_name: [values]}"}

        stored = []
        with get_db() as db:
            # Verify dataset exists
            ds = db.get(Dataset, dataset_id)
            if not ds:
                return {"error": f"Dataset {dataset_id} not found. Call register_dataset first."}

            for col_name, values in cols.items():
                if not isinstance(values, list):
                    continue
                numeric_vals = []
                dtype = "categorical"
                for v in values:
                    try:
                        numeric_vals.append(float(v))
                        dtype = "numeric"
                    except (TypeError, ValueError):
                        numeric_vals.append(v)

                # Delete existing column with same name (upsert)
                existing = (db.query(DatasetColumn)
                            .filter(DatasetColumn.dataset_id == dataset_id,
                                    DatasetColumn.column_name == col_name)
                            .first())
                if existing:
                    db.delete(existing)

                db_col = DatasetColumn(
                    dataset_id=dataset_id,
                    column_name=col_name,
                    data_json=json.dumps(numeric_vals),
                    dtype=dtype,
                    n_rows=len(values),
                )
                db.add(db_col)
                stored.append(col_name)

            # Update dataset sample_size
            if stored:
                first_col = list(cols.values())[0]
                ds.sample_size = len(first_col)

            db.commit()

        return {
            "dataset_id": dataset_id,
            "columns_stored": stored,
            "n_columns": len(stored),
            "usage": (f"Reference columns as '{dataset_id}:column_name' in any stat tool. "
                      f"Example: cronbach_alpha with items referencing '{dataset_id}:q1'"),
            "message": f"Stored {len(stored)} column(s) for dataset {dataset_id}.",
        }
    except Exception as e:
        return {"error": str(e)}


def list_dataset_columns(dataset_id: int) -> dict:
    """
    List all columns stored for a dataset with basic stats.
    Use this to find column names before running analyses.

    Args:
        dataset_id: Dataset ID from register_dataset or list_datasets.
    """
    try:
        with get_db() as db:
            ds = db.get(Dataset, dataset_id)
            if not ds:
                return {"error": f"Dataset {dataset_id} not found."}

            cols = (db.query(DatasetColumn)
                    .filter(DatasetColumn.dataset_id == dataset_id)
                    .all())

            if not cols:
                return {
                    "dataset_id": dataset_id,
                    "dataset_name": ds.name,
                    "columns": [],
                    "message": ("No column data stored yet. "
                                "Use store_dataset_columns to upload data."),
                }

            col_info = []
            for c in cols:
                vals = json.loads(c.data_json)
                info = {
                    "column": c.column_name,
                    "dtype": c.dtype,
                    "n_rows": c.n_rows,
                    "reference": f"{dataset_id}:{c.column_name}",
                }
                if c.dtype == "numeric":
                    numeric = [v for v in vals if isinstance(v, (int, float))]
                    if numeric:
                        info["min"] = round(min(numeric), 3)
                        info["max"] = round(max(numeric), 3)
                        info["mean"] = round(statistics.mean(numeric), 3)
                col_info.append(info)

        return {
            "dataset_id": dataset_id,
            "dataset_name": ds.name,
            "n_columns": len(cols),
            "columns": col_info,
            "tip": (f"Use reference format '{dataset_id}:column_name' "
                    "in stat tools instead of pasting raw data."),
        }
    except Exception as e:
        return {"error": str(e)}


def cronbach_alpha(items_json: str) -> dict:
    """
    Calculate Cronbach's alpha reliability for a survey instrument.

    Args:
        items_json: 2D JSON array — rows = respondents, columns = items.
                    Example: "[[4,3,5],[3,2,4],[5,5,5],[4,4,4]]"

    Returns:
        dict with alpha, interpretation, item-total correlations, and flagged items.
    """
    try:
        # Support dataset column reference: "42:q1,q2,q3,q4"
        if not items_json.strip().startswith("["):
            ref_parts = items_json.strip().lstrip("ds:").split(":")
            if len(ref_parts) == 2:
                ds_id = int(ref_parts[0])
                col_names = [c.strip() for c in ref_parts[1].split(",")]
                columns = [_resolve_data(f"{ds_id}:{c}") for c in col_names]
                data = [[columns[c][r] for c in range(len(columns))]
                        for r in range(len(columns[0]))]
            else:
                data = json.loads(items_json)
        else:
            data = json.loads(items_json)
        n_items = len(data[0])
        n_subjects = len(data)
        if n_subjects < 2:
            return {"error": "Need at least 2 respondents to compute alpha."}

        item_vars = [statistics.variance([row[i] for row in data]) for i in range(n_items)]
        totals = [sum(row) for row in data]
        total_var = statistics.variance(totals)

        alpha = round((n_items / (n_items - 1)) * (1 - sum(item_vars) / total_var), 4)

        if alpha >= 0.9:
            label = "Excellent (α ≥ 0.9)"
        elif alpha >= 0.8:
            label = "Good (α ≥ 0.8)"
        elif alpha >= 0.7:
            label = "Acceptable (α ≥ 0.7)"
        elif alpha >= 0.6:
            label = "Questionable (α ≥ 0.6) — consider revising items"
        else:
            label = "Poor (α < 0.6) — instrument needs revision"

        # Item-total correlations (corrected)
        itc = {}
        for i in range(n_items):
            item_scores = [row[i] for row in data]
            rest = [sum(row) - row[i] for row in data]
            m_i, m_r = statistics.mean(item_scores), statistics.mean(rest)
            cov = sum((a - m_i) * (b - m_r) for a, b in zip(item_scores, rest)) / (n_subjects - 1)
            sd_i = statistics.stdev(item_scores)
            sd_r = statistics.stdev(rest)
            corr = round(cov / (sd_i * sd_r), 4) if sd_i > 0 and sd_r > 0 else 0.0
            itc[f"item_{i+1}"] = corr

        return {
            "alpha": alpha,
            "interpretation": label,
            "n_items": n_items,
            "n_respondents": n_subjects,
            "item_total_correlations": itc,
            "flagged_items": [k for k, v in itc.items() if v < 0.3],
        }
    except Exception as e:
        return {"error": str(e)}


def descriptive_stats(values_json: str, variable_name: str = "variable") -> dict:
    """
    Compute descriptive statistics for a numeric variable.

    Args:
        values_json: JSON array of numbers. Example: "[4.2, 3.8, 5.0, 4.5, 3.1]"
        variable_name: Label for the variable.

    Returns:
        dict with n, mean, median, std, min, max, quartiles, skewness, and interpretation.
    """
    try:
        vals = _resolve_data(values_json)
        n = len(vals)
        if n < 2:
            return {"error": "Need at least 2 values."}
        s = sorted(vals)
        mean = statistics.mean(vals)
        median = statistics.median(vals)
        std = statistics.stdev(vals)
        q1 = s[n // 4]
        q3 = s[(3 * n) // 4]
        skew = round((3 * (mean - median) / std), 4) if std > 0 else 0.0

        return {
            "variable": variable_name,
            "n": n,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std_dev": round(std, 4),
            "min": min(vals),
            "max": max(vals),
            "q1": q1,
            "q3": q3,
            "iqr": round(q3 - q1, 4),
            "skewness": skew,
            "skewness_note": (
                "Approximately symmetric" if abs(skew) < 0.5
                else "Moderately skewed" if abs(skew) < 1.0
                else "Highly skewed — consider transformation"
            ),
        }
    except Exception as e:
        return {"error": str(e)}


def pearson_correlation(x_json: str, y_json: str, x_label: str = "X", y_label: str = "Y") -> dict:
    """
    Compute Pearson correlation between two variables.

    Args:
        x_json: JSON array for variable X.
        y_json: JSON array for variable Y.
        x_label: Name of X variable.
        y_label: Name of Y variable.

    Returns:
        dict with r, r², interpretation, and significance note.
    """
    try:
        x = _resolve_data(x_json)
        y = _resolve_data(y_json)
        if len(x) != len(y):
            return {"error": "X and Y must have the same length."}
        n = len(x)
        mx, my = statistics.mean(x), statistics.mean(y)
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        den = math.sqrt(sum((xi - mx)**2 for xi in x) * sum((yi - my)**2 for yi in y))
        r = round(num / den, 4) if den > 0 else 0.0
        r2 = round(r ** 2, 4)

        if abs(r) >= 0.7:
            strength = "Strong"
        elif abs(r) >= 0.4:
            strength = "Moderate"
        elif abs(r) >= 0.2:
            strength = "Weak"
        else:
            strength = "Negligible"
        direction = "positive" if r >= 0 else "negative"

        return {
            "r": r,
            "r_squared": r2,
            "n": n,
            "interpretation": f"{strength} {direction} correlation",
            "note": "Use α=0.05 significance table for n to confirm statistical significance.",
        }
    except Exception as e:
        return {"error": str(e)}




# ─── Spearman correlation ─────────────────────────────────────────────────────

def spearman_correlation(x_json: str, y_json: str,
                         x_label: str = "X", y_label: str = "Y") -> dict:
    """
    Compute Spearman rank correlation between two variables.
    Use for ordinal data or when Pearson normality assumptions are violated.

    Args:
        x_json: JSON array for variable X. E.g. "[3,1,4,1,5,9,2,6]"
        y_json: JSON array for variable Y. Same length as X.
        x_label: Name of X variable.
        y_label: Name of Y variable.
    """
    try:
        x = _resolve_data(x_json)
        y = _resolve_data(y_json)
        if len(x) != len(y):
            return {"error": "X and Y must have the same length."}
        n = len(x)
        if n < 3:
            return {"error": "Need at least 3 pairs to compute correlation."}

        def rank(lst):
            sorted_vals = sorted(enumerate(lst), key=lambda t: t[1])
            ranks = [0.0] * len(lst)
            i = 0
            while i < len(sorted_vals):
                j = i
                while j < len(sorted_vals) - 1 and sorted_vals[j+1][1] == sorted_vals[i][1]:
                    j += 1
                avg_rank = (i + j) / 2.0 + 1
                for k in range(i, j + 1):
                    ranks[sorted_vals[k][0]] = avg_rank
                i = j + 1
            return ranks

        rx, ry = rank(x), rank(y)
        mrx, mry = statistics.mean(rx), statistics.mean(ry)
        num = sum((a - mrx) * (b - mry) for a, b in zip(rx, ry))
        den = math.sqrt(
            sum((a - mrx) ** 2 for a in rx) * sum((b - mry) ** 2 for b in ry)
        )
        rs = round(num / den, 4) if den > 0 else 0.0

        strength = ("Strong" if abs(rs) >= 0.7
                    else "Moderate" if abs(rs) >= 0.4
                    else "Weak" if abs(rs) >= 0.2
                    else "Negligible")
        direction = "positive" if rs >= 0 else "negative"

        # Approximate t-statistic for significance
        t_stat = rs * math.sqrt((n - 2) / max(1 - rs ** 2, 1e-10))
        sig_note = ("Likely significant at α=0.05 (|t| > 2)" if abs(t_stat) > 2
                    else "Not significant at α=0.05 — interpret with caution")

        return {
            "rs": rs,
            "rs_squared": round(rs ** 2, 4),
            "n": n,
            "t_statistic": round(t_stat, 4),
            "interpretation": f"{strength} {direction} rank correlation",
            "significance_note": sig_note,
            "note": ("Spearman rs is appropriate for ordinal scales and "
                     "non-normal distributions."),
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Independent samples t-test ───────────────────────────────────────────────

def independent_ttest(group1_json: str, group2_json: str,
                      group1_label: str = "Group 1",
                      group2_label: str = "Group 2") -> dict:
    """
    Independent samples t-test comparing means of two groups.
    Uses Welch's t-test (unequal variances) — safer than Student's t.

    Args:
        group1_json: JSON array of numeric scores for group 1.
        group2_json: JSON array of numeric scores for group 2.
        group1_label: Name for group 1. E.g. "Laki-laki"
        group2_label: Name for group 2. E.g. "Perempuan"
    """
    try:
        g1 = _resolve_data(group1_json)
        g2 = _resolve_data(group2_json)
        n1, n2 = len(g1), len(g2)
        if n1 < 2 or n2 < 2:
            return {"error": "Each group needs at least 2 observations."}

        m1, m2 = statistics.mean(g1), statistics.mean(g2)
        v1, v2 = statistics.variance(g1), statistics.variance(g2)

        # Welch's t
        se = math.sqrt(v1 / n1 + v2 / n2)
        if se == 0:
            return {"error": "Both groups have zero variance — t-test not applicable."}
        t = round((m1 - m2) / se, 4)

        # Welch-Satterthwaite degrees of freedom
        df_num = (v1 / n1 + v2 / n2) ** 2
        df_den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
        df = round(df_num / df_den, 2) if df_den > 0 else n1 + n2 - 2

        # Cohen's d (pooled SD)
        pooled_sd = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
        cohens_d = round((m1 - m2) / pooled_sd, 4) if pooled_sd > 0 else 0.0
        effect = ("Large (d ≥ 0.8)" if abs(cohens_d) >= 0.8
                  else "Medium (d ≥ 0.5)" if abs(cohens_d) >= 0.5
                  else "Small (d ≥ 0.2)" if abs(cohens_d) >= 0.2
                  else "Negligible (d < 0.2)")

        sig_note = ("Likely significant at α=0.05 (|t| > 2)" if abs(t) > 2
                    else "Not significant at α=0.05")

        return {
            "t_statistic": t,
            "degrees_of_freedom": df,
            "mean_group1": round(m1, 4),
            "mean_group2": round(m2, 4),
            "mean_difference": round(m1 - m2, 4),
            "cohens_d": cohens_d,
            "effect_size": effect,
            "n_group1": n1,
            "n_group2": n2,
            "significance_note": sig_note,
            "method": "Welch independent samples t-test (unequal variances)",
        }
    except Exception as e:
        return {"error": str(e)}


# ─── One-way ANOVA ────────────────────────────────────────────────────────────

def one_way_anova(*args, **kwargs) -> dict:
    """
    One-way ANOVA testing whether means differ across 2+ groups.
    Pass groups_json (a 2D JSON array, rows = groups).

    Args:
        groups_json: JSON array of arrays. E.g. "[[5,4,3],[7,6,8],[4,3,2]]"
        group_labels: Optional JSON array of group names. E.g. '["A","B","C"]'
    """
    try:
        groups_json = kwargs.get("groups_json") or (args[0] if args else None)
        group_labels_json = kwargs.get("group_labels") or (args[1] if len(args) > 1 else None)

        if groups_json is None:
            return {"error": "groups_json is required."}

        groups = [list(map(float, g)) for g in json.loads(groups_json)]
        k = len(groups)
        if k < 2:
            return {"error": "Need at least 2 groups for ANOVA."}
        if any(len(g) < 2 for g in groups):
            return {"error": "Each group needs at least 2 observations."}

        labels = (json.loads(group_labels_json)
                  if group_labels_json else [f"Group {i+1}" for i in range(k)])

        all_vals = [v for g in groups for v in g]
        grand_mean = statistics.mean(all_vals)
        N = len(all_vals)

        # SS Between
        ss_between = sum(len(g) * (statistics.mean(g) - grand_mean) ** 2 for g in groups)
        df_between = k - 1

        # SS Within
        ss_within = sum(sum((v - statistics.mean(g)) ** 2 for v in g) for g in groups)
        df_within = N - k

        ms_between = ss_between / df_between
        ms_within = ss_within / df_within if df_within > 0 else 0
        f_stat = round(ms_between / ms_within, 4) if ms_within > 0 else 0.0

        # Eta-squared (effect size)
        eta2 = round(ss_between / (ss_between + ss_within), 4)
        effect = ("Large (η²≥0.14)" if eta2 >= 0.14
                  else "Medium (η²≥0.06)" if eta2 >= 0.06
                  else "Small (η²≥0.01)" if eta2 >= 0.01
                  else "Negligible")

        group_stats = {labels[i]: {
            "n": len(groups[i]),
            "mean": round(statistics.mean(groups[i]), 4),
            "std": round(statistics.stdev(groups[i]), 4),
        } for i in range(k)}

        sig_note = (f"F({df_between},{df_within}) = {f_stat}. "
                    + ("Likely significant at α=0.05 — consider post-hoc test (Tukey HSD)"
                       if f_stat > 3.0 else "Not significant at α=0.05"))

        return {
            "f_statistic": f_stat,
            "df_between": df_between,
            "df_within": df_within,
            "ss_between": round(ss_between, 4),
            "ss_within": round(ss_within, 4),
            "ms_between": round(ms_between, 4),
            "ms_within": round(ms_within, 4),
            "eta_squared": eta2,
            "effect_size": effect,
            "group_stats": group_stats,
            "significance_note": sig_note,
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Normality tests ──────────────────────────────────────────────────────────

def normality_test(values_json: str, variable_name: str = "variable") -> dict:
    """
    Test normality using Shapiro-Wilk (n ≤ 50) or a moment-based test (n > 50).
    Reports skewness, kurtosis, and practical normality verdict.

    Args:
        values_json: JSON array of numeric values.
        variable_name: Variable label for reporting.
    """
    try:
        vals = _resolve_data(values_json)
        n = len(vals)
        if n < 3:
            return {"error": "Need at least 3 values for normality testing."}

        mean = statistics.mean(vals)
        std = statistics.stdev(vals)

        # Skewness (Fisher)
        skew = (sum((v - mean) ** 3 for v in vals) / n) / (std ** 3) if std > 0 else 0.0
        # Kurtosis (excess)
        kurt = (sum((v - mean) ** 4 for v in vals) / n) / (std ** 4) - 3 if std > 0 else 0.0

        skew = round(skew, 4)
        kurt = round(kurt, 4)

        # Shapiro-Wilk approximation for small samples (n ≤ 50)
        # For larger n: use skewness/kurtosis z-scores
        if n <= 50:
            # W approximation via correlation of ordered values with expected normal scores
            s = sorted(vals)
            # Blom's formula for normal scores
            normal_scores = [
                statistics.NormalDist().inv_cdf((i - 0.375) / (n + 0.25))
                for i in range(1, n + 1)
            ]
            mn = statistics.mean(normal_scores)
            num = sum((a - mean) * (b - mn) for a, b in zip(s, normal_scores))
            den_x = math.sqrt(sum((a - mean) ** 2 for a in s))
            den_y = math.sqrt(sum((b - mn) ** 2 for b in normal_scores))
            w = round((num / (den_x * den_y)) ** 2, 4) if den_x > 0 and den_y > 0 else 0.0
            method = f"Shapiro-Wilk W approximation (n={n})"
            stat_label = "W"
            stat_value = w
            # Heuristic: W > 0.95 suggests normality
            normal_verdict = w >= 0.95
        else:
            # D'Agostino: use skewness and kurtosis z-scores
            se_skew = math.sqrt(6 * n * (n - 1) / ((n - 2) * (n + 1) * (n + 3)))
            se_kurt = 2 * se_skew * math.sqrt((n ** 2 - 1) / ((n - 3) * (n + 5)))
            z_skew = abs(skew / se_skew) if se_skew > 0 else 0
            z_kurt = abs(kurt / se_kurt) if se_kurt > 0 else 0
            stat_value = round(max(z_skew, z_kurt), 4)
            stat_label = "max(|z_skew|, |z_kurt|)"
            method = f"Skewness-kurtosis z-score test (n={n})"
            normal_verdict = stat_value < 1.96

        verdict = ("Approximately normal — parametric tests (t-test, ANOVA, regression) appropriate"
                   if normal_verdict
                   else "Non-normal distribution — consider Spearman, Mann-Whitney, or Kruskal-Wallis")

        return {
            "variable": variable_name,
            "n": n,
            "skewness": skew,
            "kurtosis_excess": kurt,
            stat_label: stat_value,
            "method": method,
            "normal": normal_verdict,
            "verdict": verdict,
            "skewness_note": ("Symmetric" if abs(skew) < 0.5
                              else "Moderate skew" if abs(skew) < 1.0
                              else "High skew — normality unlikely"),
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Simple linear regression ─────────────────────────────────────────────────

def simple_linear_regression(x_json: str, y_json: str,
                              x_label: str = "X", y_label: str = "Y") -> dict:
    """
    Simple linear regression: Y = b0 + b1*X.
    Returns coefficients, R², standard errors, and model diagnostics.

    Args:
        x_json: JSON array for predictor variable X.
        y_json: JSON array for outcome variable Y.
        x_label: Name of predictor. E.g. "Study hours"
        y_label: Name of outcome. E.g. "Exam score"
    """
    try:
        x = _resolve_data(x_json)
        y = _resolve_data(y_json)
        if len(x) != len(y):
            return {"error": "X and Y must have the same length."}
        n = len(x)
        if n < 3:
            return {"error": "Need at least 3 observations for regression."}

        mx, my = statistics.mean(x), statistics.mean(y)
        ss_xx = sum((xi - mx) ** 2 for xi in x)
        ss_xy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))

        if ss_xx == 0:
            return {"error": "X has zero variance — regression not possible."}

        b1 = round(ss_xy / ss_xx, 4)
        b0 = round(my - b1 * mx, 4)

        # Predictions and residuals
        y_pred = [b0 + b1 * xi for xi in x]
        residuals = [yi - yp for yi, yp in zip(y, y_pred)]

        ss_res = sum(r ** 2 for r in residuals)
        ss_tot = sum((yi - my) ** 2 for yi in y)
        r2 = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 0.0
        r2_adj = round(1 - (1 - r2) * (n - 1) / (n - 2), 4) if n > 2 else r2

        # Standard error of estimate
        mse = ss_res / (n - 2) if n > 2 else 0
        se_est = round(math.sqrt(mse), 4)

        # SE of b1 and t-statistic
        se_b1 = round(math.sqrt(mse / ss_xx), 4) if ss_xx > 0 else 0
        t_b1 = round(b1 / se_b1, 4) if se_b1 > 0 else 0
        sig_note = ("Predictor is significant at α=0.05 (|t| > 2)"
                    if abs(t_b1) > 2 else "Predictor is NOT significant at α=0.05")

        # F-statistic
        ss_reg = ss_tot - ss_res
        f_stat = round((ss_reg / 1) / (ss_res / (n - 2)), 4) if ss_res > 0 else 0.0

        effect = ("Strong" if r2 >= 0.49
                  else "Moderate" if r2 >= 0.09
                  else "Weak")

        return {
            "equation": f"{y_label} = {b0} + {b1} × {x_label}",
            "b0_intercept": b0,
            "b1_slope": b1,
            "r_squared": r2,
            "r_squared_adjusted": r2_adj,
            "r_squared_interpretation": f"{effect} fit — {x_label} explains {round(r2*100,1)}% of {y_label} variance",
            "se_estimate": se_est,
            "se_b1": se_b1,
            "t_statistic_b1": t_b1,
            "f_statistic": f_stat,
            "n": n,
            "significance_note": sig_note,
            "assumption_note": ("Check residual plot and normality test before reporting "
                                "results in a formal analysis."),
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Sample size calculator ───────────────────────────────────────────────────

def sample_size_calculator(method: str, **kwargs) -> dict:
    """
    Calculate required sample size for common research designs.
    Supports: cochran (survey proportions), correlation, ttest, anova.

    Args:
        method: One of "cochran", "correlation", "ttest", "anova"
        p:      Cochran — estimated proportion (default 0.5 for max size)
        e:      Cochran — margin of error (default 0.05)
        confidence: Cochran/all — confidence level 0.90/0.95/0.99 (default 0.95)
        r:      Correlation — expected r (required for method=correlation)
        alpha:  All — significance level (default 0.05)
        power:  All — desired power (default 0.80)
        d:      T-test — Cohen's d effect size (default 0.5)
        f:      ANOVA — Cohen's f effect size (default 0.25)
        k:      ANOVA — number of groups (default 3)
    """
    try:
        z_table = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        confidence = float(kwargs.get("confidence", 0.95))
        z = z_table.get(confidence, 1.96)
        alpha = float(kwargs.get("alpha", 0.05))
        power = float(kwargs.get("power", 0.80))

        # z_beta from power
        power_z = {0.80: 0.842, 0.85: 1.036, 0.90: 1.282, 0.95: 1.645}
        z_beta = power_z.get(power, 0.842)
        z_alpha2 = z_table.get(1 - alpha / 2, 1.96)

        if method == "cochran":
            p = float(kwargs.get("p", 0.5))
            e = float(kwargs.get("e", 0.05))
            n0 = round((z ** 2 * p * (1 - p)) / e ** 2)
            return {
                "method": "Cochran formula (survey proportion)",
                "required_n": n0,
                "parameters": {"p": p, "margin_of_error": e, "confidence": confidence},
                "note": (f"For population < 10,000, apply finite correction: "
                         f"n = n0 / (1 + n0/N)"),
            }

        elif method == "correlation":
            r = float(kwargs.get("r", 0.3))
            # Fisher z transformation
            zr = 0.5 * math.log((1 + r) / (1 - r)) if abs(r) < 1 else 0
            n = math.ceil((z_alpha2 + z_beta) ** 2 / zr ** 2 + 3) if zr != 0 else 999
            return {
                "method": "Sample size for Pearson/Spearman correlation",
                "required_n": n,
                "parameters": {"expected_r": r, "alpha": alpha, "power": power},
            }

        elif method == "ttest":
            d = float(kwargs.get("d", 0.5))
            n = math.ceil(2 * ((z_alpha2 + z_beta) / d) ** 2) if d > 0 else 999
            return {
                "method": "Sample size for independent t-test (per group)",
                "required_n_per_group": n,
                "total_n": n * 2,
                "parameters": {"cohens_d": d, "alpha": alpha, "power": power},
            }

        elif method == "anova":
            f = float(kwargs.get("f", 0.25))
            k = int(kwargs.get("k", 3))
            # Approximation: n per group
            n = math.ceil((z_alpha2 + z_beta) ** 2 / f ** 2 + 1) if f > 0 else 999
            return {
                "method": f"Sample size for one-way ANOVA ({k} groups)",
                "required_n_per_group": n,
                "total_n": n * k,
                "parameters": {"cohens_f": f, "k_groups": k, "alpha": alpha, "power": power},
            }

        else:
            return {
                "error": f"Unknown method '{method}'. Use: cochran, correlation, ttest, anova"
            }
    except Exception as e:
        return {"error": str(e)}


# ─── Item analysis ────────────────────────────────────────────────────────────

def item_analysis(items_json: str, item_labels_json: Optional[str] = None) -> dict:
    """
    Full item analysis for survey/test instruments.
    Reports difficulty index, discriminating power, corrected item-total
    correlation, and alpha-if-item-deleted for each item.
    Standard output for reliability reporting in Indonesian academic papers.

    Args:
        items_json: 2D JSON array — rows = respondents, columns = items.
                    E.g. "[[4,3,5,4],[3,2,4,3],[5,5,5,5]]"
        item_labels_json: Optional JSON array of item names.
                          E.g. '["Q1","Q2","Q3","Q4"]'
    """
    try:
        # Support dataset column reference: "42:q1,q2,q3,q4"
        if not items_json.strip().startswith("["):
            ref_parts = items_json.strip().lstrip("ds:").split(":")
            if len(ref_parts) == 2:
                ds_id = int(ref_parts[0])
                col_names = [c.strip() for c in ref_parts[1].split(",")]
                columns = [_resolve_data(f"{ds_id}:{c}") for c in col_names]
                data = [[columns[c][r] for c in range(len(columns))]
                        for r in range(len(columns[0]))]
            else:
                data = json.loads(items_json)
        else:
            data = json.loads(items_json)
        n_subj = len(data)
        n_items = len(data[0]) if data else 0
        if n_subj < 5:
            return {"error": "Need at least 5 respondents for item analysis."}
        if n_items < 2:
            return {"error": "Need at least 2 items."}

        labels = (json.loads(item_labels_json)
                  if item_labels_json
                  else [f"Item_{i+1}" for i in range(n_items)])

        totals = [sum(row) for row in data]
        grand_mean_total = statistics.mean(totals)

        items_result = {}
        for i in range(n_items):
            scores = [row[i] for row in data]
            rest_scores = [totals[j] - scores[j] for j in range(n_subj)]

            mean_i = statistics.mean(scores)
            std_i = statistics.stdev(scores) if n_subj > 1 else 0

            # Corrected item-total correlation (item vs rest-of-test)
            m_rest = statistics.mean(rest_scores)
            std_rest = statistics.stdev(rest_scores) if n_subj > 1 else 0
            if std_i > 0 and std_rest > 0:
                cov = sum((scores[j] - mean_i) * (rest_scores[j] - m_rest)
                          for j in range(n_subj)) / (n_subj - 1)
                ritc = round(cov / (std_i * std_rest), 4)
            else:
                ritc = 0.0

            # Alpha if item deleted
            remaining = [[data[r][c] for c in range(n_items) if c != i]
                         for r in range(n_subj)]
            ni = n_items - 1
            if ni >= 2:
                iv = [statistics.variance([row[c] for row in remaining])
                      for c in range(ni)]
                tv = statistics.variance([sum(row) for row in remaining])
                aid = round((ni / (ni - 1)) * (1 - sum(iv) / tv), 4) if tv > 0 else 0.0
            else:
                aid = 0.0

            # Difficulty index (mean / max_possible) — assumes Likert max = max observed
            max_score = max(scores)
            difficulty = round(mean_i / max_score, 4) if max_score > 0 else 0.0

            disc = ("Good" if ritc >= 0.3
                    else "Acceptable (borderline)" if ritc >= 0.2
                    else "Poor — consider revising or dropping")

            items_result[labels[i]] = {
                "mean": round(mean_i, 4),
                "std_dev": round(std_i, 4),
                "difficulty_index": difficulty,
                "corrected_item_total_r": ritc,
                "discrimination": disc,
                "alpha_if_deleted": aid,
                "flag": ritc < 0.3,
            }

        flagged = [k for k, v in items_result.items() if v["flag"]]

        return {
            "n_respondents": n_subj,
            "n_items": n_items,
            "items": items_result,
            "flagged_items": flagged,
            "flagged_note": (
                f"{len(flagged)} item(s) with r_itc < 0.3 should be revised or removed: "
                + ", ".join(flagged)
                if flagged else "All items meet the r_itc ≥ 0.3 threshold."
            ),
        }
    except Exception as e:
        return {"error": str(e)}

# ─── Task management ──────────────────────────────────────────────────────────

def create_task(title: str, project: str, due_date: Optional[str] = None,
                priority: str = "medium", notes: Optional[str] = None) -> dict:
    """
    Create an academic/research task with optional deadline.

    Args:
        title: Task description. E.g. "Submit BAB IV draft to advisor"
        project: Project name. E.g. "Skripsi", "Gen AI Hackathon", "Metodologi Survei"
        due_date: ISO date string, e.g. "2025-05-20" or "2025-05-20T14:00:00". Optional.
        priority: "high", "medium", or "low". Default: "medium"
        notes: Extra context. Optional.
    """
    with get_db() as db:
        t = Task(
            title=title, project=project,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            priority=priority, notes=notes,
        )
        db.add(t)
        db.flush()
        return {"task_id": t.id, "title": t.title, "project": t.project,
                "due_date": str(t.due_date) if t.due_date else None,
                "priority": t.priority, "message": f"Task created with ID {t.id}."}


def list_tasks(project: Optional[str] = None, status: str = "pending") -> list:
    """
    List research tasks. Optionally filter by project or status.

    Args:
        project: Filter by project name (partial match). Optional.
        status: "pending" or "completed". Default: "pending"
    """
    with get_db() as db:
        q = db.query(Task).filter(Task.status == status)
        if project:
            q = q.filter(Task.project.ilike(f"%{project}%"))
        tasks = q.order_by(Task.due_date.asc()).limit(25).all()
        return [{"task_id": t.id, "title": t.title, "project": t.project,
                 "due_date": str(t.due_date) if t.due_date else "No deadline",
                 "priority": t.priority, "status": t.status} for t in tasks]


def complete_task(task_id: int) -> dict:
    """Mark a task as completed by its ID."""
    with get_db() as db:
        t = db.get(Task, task_id)
        if not t:
            return {"error": f"Task {task_id} not found."}
        t.status = "completed"
        t.completed_at = datetime.utcnow()
        return {"task_id": t.id, "title": t.title, "status": "completed"}


def complete_task_by_title(title_fragment: str) -> dict:
    """
    Mark the first pending task whose title contains title_fragment as completed.
    Useful when the agent knows the task name but not its numeric ID.

    Args:
        title_fragment: Partial or full task title to search for.
    """
    with get_db() as db:
        task = (db.query(Task)
                .filter(Task.status == "pending")
                .filter(Task.title.ilike(f"%{title_fragment}%"))
                .first())
        if not task:
            return {"error": f"No pending task matching '{title_fragment}' found."}
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        return {"task_id": task.id, "title": task.title, "status": "completed",
                "message": f"Task '{task.title}' marked as completed."}



def get_upcoming_deadlines(days_ahead: int = 7) -> list:
    """
    Get pending tasks with deadlines in the next N days.

    Args:
        days_ahead: How many days ahead to look. Default: 7.
    """
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days_ahead)
    with get_db() as db:
        tasks = (db.query(Task)
                 .filter(Task.status == "pending")
                 .filter(Task.due_date >= now)
                 .filter(Task.due_date <= cutoff)
                 .order_by(Task.due_date.asc()).all())
        return [{"task_id": t.id, "title": t.title, "project": t.project,
                 "due_date": str(t.due_date),
                 "days_remaining": (t.due_date - now).days} for t in tasks]


# ─── Analysis job tracking ────────────────────────────────────────────────────

def create_analysis_job(name: str, method: str, dataset_ref: str,
                        parameters_json: Optional[str] = None,
                        notes: Optional[str] = None) -> dict:
    """
    Register a statistical analysis job for tracking.

    Args:
        name: Descriptive job name. E.g. "Rasch calibration - survey batch 2"
        method: Method used. E.g. "IRT_Rasch", "SEM_PLS", "CFA", "logistic_regression"
        dataset_ref: Where the data lives. E.g. "BigQuery: statmind_data.survey_responses"
        parameters_json: Optional JSON of model parameters.
        notes: Optional notes about the job.
    """
    with get_db() as db:
        job = AnalysisJob(name=name, method=method, dataset_ref=dataset_ref,
                          parameters_json=parameters_json, notes=notes)
        db.add(job)
        db.flush()
        return {"job_id": job.id, "name": job.name, "method": job.method,
                "status": "pending", "message": f"Analysis job created with ID {job.id}."}


def list_analysis_jobs(status_filter: Optional[str] = None) -> list:
    """
    List analysis jobs. Filter by status if provided.

    Args:
        status_filter: "pending", "running", "completed", or "failed". Optional.
    """
    with get_db() as db:
        q = db.query(AnalysisJob)
        if status_filter:
            q = q.filter(AnalysisJob.status == status_filter)
        jobs = q.order_by(AnalysisJob.created_at.desc()).limit(20).all()
        return [{"job_id": j.id, "name": j.name, "method": j.method,
                 "status": j.status, "dataset_ref": j.dataset_ref,
                 "created_at": str(j.created_at)} for j in jobs]


# ─── Research notes ───────────────────────────────────────────────────────────

def save_research_note(title: str, content: str, tags: str,
                       project: Optional[str] = None,
                       source_ref: Optional[str] = None) -> dict:
    """
    Save a research note (paper summary, method note, dataset observation).

    Args:
        title: Note title. E.g. "Rasch model fit statistics summary"
        content: Full note body.
        tags: Comma-separated keywords. E.g. "IRT,Rasch,validity,skripsi"
        project: Project association. E.g. "Skripsi". Optional.
        source_ref: Citation or URL. E.g. "Bond & Fox (2015)". Optional.
    """
    with get_db() as db:
        note = ResearchNote(title=title, content=content, tags=tags,
                            project=project, source_ref=source_ref)
        db.add(note)
        db.flush()
        return {"note_id": note.id, "title": note.title,
                "message": f"Note '{title}' saved with ID {note.id}."}


def search_research_notes(query: str) -> list:
    """
    Search saved research notes by keyword across title, content, and tags.

    Args:
        query: Search terms. E.g. "Cronbach reliability survey"
    """
    with get_db() as db:
        results = (db.query(ResearchNote)
                   .filter(ResearchNote.title.ilike(f"%{query}%")
                           | ResearchNote.content.ilike(f"%{query}%")
                           | ResearchNote.tags.ilike(f"%{query}%"))
                   .order_by(ResearchNote.created_at.desc()).limit(10).all())
        return [{"note_id": n.id, "title": n.title, "tags": n.tags,
                 "project": n.project,
                 "preview": n.content[:250] + "..." if len(n.content) > 250 else n.content}
                for n in results]


def list_research_notes(project: Optional[str] = None,
                        tag: Optional[str] = None) -> list:
    """
    List research notes, optionally filtered by project or tag.

    Args:
        project: Filter by project name. Optional.
        tag: Filter by tag keyword. Optional.
    """
    with get_db() as db:
        q = db.query(ResearchNote)
        if project:
            q = q.filter(ResearchNote.project.ilike(f"%{project}%"))
        if tag:
            q = q.filter(ResearchNote.tags.ilike(f"%{tag}%"))
        notes = q.order_by(ResearchNote.created_at.desc()).limit(20).all()
        return [{"note_id": n.id, "title": n.title, "tags": n.tags,
                 "project": n.project, "source": n.source_ref,
                 "created_at": str(n.created_at)} for n in notes]


# ─── Dataset registry ─────────────────────────────────────────────────────────

def register_dataset(name: str, source: str, description: str,
                     variables: str, sample_size: Optional[int] = None,
                     collection_method: Optional[str] = None,
                     notes: Optional[str] = None) -> dict:
    """
    Register a dataset in the StatMind catalog.

    Args:
        name: Dataset name. E.g. "SMARVUS OSF", "UNJ Statistics 2023 Survey"
        source: Where data lives. E.g. "OSF", "BigQuery: statmind_data.survey_responses"
        description: What the dataset covers.
        variables: Comma-separated key variables.
        sample_size: Number of observations. Optional.
        collection_method: E.g. "Google Forms", "Secondary data / OSF". Optional.
        notes: Data quality notes. Optional.
    """
    with get_db() as db:
        ds = Dataset(name=name, source=source, description=description,
                     variables=variables, sample_size=sample_size,
                     collection_method=collection_method, notes=notes)
        db.add(ds)
        db.flush()
        return {"dataset_id": ds.id, "name": ds.name, "source": ds.source,
                "message": f"Dataset '{name}' registered with ID {ds.id}."}


def list_datasets(search: Optional[str] = None) -> list:
    """
    List registered datasets. Optionally filter by name or description keyword.

    Args:
        search: Filter keyword. Optional.
    """
    with get_db() as db:
        q = db.query(Dataset)
        if search:
            q = q.filter(Dataset.name.ilike(f"%{search}%")
                         | Dataset.description.ilike(f"%{search}%")
                         | Dataset.variables.ilike(f"%{search}%"))
        datasets = q.order_by(Dataset.created_at.desc()).all()
        return [{"dataset_id": d.id, "name": d.name, "source": d.source,
                 "sample_size": d.sample_size, "variables": d.variables,
                 "collection_method": d.collection_method} for d in datasets]
