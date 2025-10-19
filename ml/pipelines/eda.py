import argparse
import json
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def load_data(path: str) -> pd.DataFrame:
    """Load dataset from the provided path."""
    return pd.read_csv(path)


def initial_exploration(df: pd.DataFrame, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    summary = {
        "describe": df.describe(include="all").to_dict(),
        "missing": df.isnull().sum().to_dict(),
    }

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()

    for col in num_cols:
        plt.figure()
        sns.histplot(df[col], kde=True)
        plt.title(f"Histogram - {col}")
        plt.savefig(f"{outdir}/hist_{col}.png")
        plt.close()

        plt.figure()
        sns.boxplot(x=df[col])
        plt.title(f"Boxplot - {col}")
        plt.savefig(f"{outdir}/box_{col}.png")
        plt.close()

    for col in cat_cols:
        plt.figure()
        sns.countplot(x=df[col])
        plt.title(f"Count - {col}")
        plt.savefig(f"{outdir}/count_{col}.png")
        plt.close()

    return summary, num_cols, cat_cols


def relational_analysis(df: pd.DataFrame, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    if {"sex", "charges"}.issubset(df.columns):
        plt.figure()
        sns.boxplot(x="sex", y="charges", data=df)
        plt.title("Charges by Gender")
        plt.savefig(f"{outdir}/box_charges_gender.png")
        plt.close()

    if {"bmi", "charges", "smoker", "children"}.issubset(df.columns):
        plt.figure()
        sns.scatterplot(x="bmi", y="charges", hue="smoker", size="children", data=df)
        plt.title("Charges vs BMI by Smoker/Children")
        plt.savefig(f"{outdir}/scatter_charges_bmi.png")
        plt.close()

    corr = df.corr(numeric_only=True)
    plt.figure()
    sns.heatmap(corr, annot=True, cmap="coolwarm")
    plt.title("Correlation Heatmap")
    plt.savefig(f"{outdir}/heatmap_corr.png")
    plt.close()

    return corr.to_dict()


def detect_outliers(df: pd.DataFrame, column: str, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    q1, q3 = df[column].quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = df[(df[column] < lo) | (df[column] > hi)]
    outliers.to_csv(f"{outdir}/outliers.csv", index=False)
    return {"count": int(len(outliers)), "lower": float(lo), "upper": float(hi)}


def save_summary(summary: dict, outpath: str) -> None:
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--outliers-col", default="charges")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    df = load_data(args.input)

    exploration_summary, num_cols, cat_cols = initial_exploration(df, f"{args.output}/plots")
    corr_summary = relational_analysis(df, f"{args.output}/plots")

    outliers_summary = {}
    if args.outliers_col in df.columns:
        outliers_summary = detect_outliers(df, args.outliers_col, args.output)

    summary = {
        "describe": exploration_summary["describe"],
        "missing": exploration_summary["missing"],
        "correlation": corr_summary,
        "outliers": outliers_summary,
        "columns": {"numeric": num_cols, "categorical": cat_cols},
    }
    save_summary(summary, f"{args.output}/eda-summary.json")

    report_path = os.path.join(args.output, "eda-report.html")
    plots_dir = os.path.join(args.output, "plots")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("<html><body><h1>EDA Report</h1><ul>")
        for plot in sorted(os.listdir(plots_dir)):
            f.write(
                f'<li><img src="plots/{plot}" alt="{plot}" style="max-width: 800px"/></li>'
            )
        f.write("</ul></body></html>")


if __name__ == "__main__":
    main()
