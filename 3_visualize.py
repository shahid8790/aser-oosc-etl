"""Step 3 - Findings and charts.

Pulls the final tables into Pandas, prints the key findings, assigns district risk
tiers with NumPy percentiles, and saves four charts plus a CSV.

Run: python 3_visualize.py
"""
import matplotlib

matplotlib.use("Agg")  # render to files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from db import CHART_DIR, TABLE_DIR, get_engine

engine = get_engine()
CHART_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
np.random.seed(42)  # stable jitter in the strip plot

district_kpis = pd.read_sql("SELECT * FROM district_kpis", engine).sort_values("oosc_rate", ascending=False)
fact = pd.read_sql("SELECT * FROM fact_child_status", engine)
status = pd.read_sql("""
    SELECT SUM(CASE WHEN childeducationne = 1 THEN 1 ELSE 0 END) AS never_enrolled,
           SUM(CASE WHEN childeducationdp = 1 THEN 1 ELSE 0 END) AS dropped_out
    FROM clean_children
""", engine).iloc[0]

# ---- Key findings (every number quoted in the README / LinkedIn post prints here) ----
oosc_total = int(fact["oosc_flag"].sum())
never, dropped = int(status["never_enrolled"]), int(status["dropped_out"])
gender_rate = fact.groupby("gender")["oosc_flag"].mean()
top = district_kpis.iloc[0]

print("--- KEY FINDINGS (ASER 2012, children aged 5-16) ---")
print(f"Children analysed:            {len(fact):,}")
print(f"Out of school:                {oosc_total:,}  ({fact['oosc_flag'].mean():.1%})")
print(f"  never enrolled:             {never:,}  ({never / oosc_total:.0%} of out-of-school)")
print(f"  dropped out:                {dropped:,}  ({dropped / oosc_total:.0%} of out-of-school)")
print(f"Out-of-school rate, girls:    {gender_rate['F']:.1%}")
print(f"Out-of-school rate, boys:     {gender_rate['M']:.1%}")
print(f"Highest district:             {top['district_name']} ({top['oosc_rate']:.1%}, n={int(top['total_children']):,})")
print(f"Districts with data:          {len(district_kpis)}")

# ---- NumPy: risk tiers from percentile cut-offs ----
rates = district_kpis["oosc_rate"].to_numpy()
low_cut, high_cut = np.percentile(rates, [33, 66])
district_kpis["risk_tier"] = np.select(
    [rates <= low_cut, (rates > low_cut) & (rates <= high_cut), rates > high_cut],
    ["low_risk", "medium_risk", "high_risk"], default="unknown")
print(f"\nRisk-tier cut-offs (33rd / 66th percentile): {low_cut:.3f} / {high_cut:.3f}")
print(district_kpis["risk_tier"].value_counts().to_string())
district_kpis.to_csv(TABLE_DIR / "district_risk_tiers.csv", index=False)

# ---- Chart 1: top 10 districts (Matplotlib) ----
top10 = district_kpis.head(10).sort_values("oosc_rate")
plt.figure(figsize=(10, 6))
plt.barh(top10["district_name"], top10["oosc_rate"], color="crimson")
plt.xlabel("Out-of-School Rate")
plt.title("Top 10 Districts by Out-of-School Rate (ASER 2012)")
plt.tight_layout()
plt.savefig(CHART_DIR / "insight_1_top_districts.png", dpi=100)
plt.close()

# ---- Chart 2: gender ----
plt.figure(figsize=(6, 5))
plt.bar(["Female", "Male"], [gender_rate["F"], gender_rate["M"]], color=["steelblue", "salmon"])
plt.ylabel("Out-of-School Rate")
plt.title("Out-of-School Rate by Gender (ASER 2012)")
plt.tight_layout()
plt.savefig(CHART_DIR / "insight_2_gender.png", dpi=100)
plt.close()

# ---- Chart 3: age of out-of-school children ----
plt.figure(figsize=(8, 5))
plt.hist(fact.loc[fact["oosc_flag"] == 1, "age"], bins=12, color="orange", edgecolor="black")
plt.xlabel("Age")
plt.ylabel("Number of Children")
plt.title("Age Distribution of Out-of-School Children (ASER 2012)")
plt.tight_layout()
plt.savefig(CHART_DIR / "insight_3_age.png", dpi=100)
plt.close()

# ---- Chart 4: risk tiers (Seaborn) ----
plt.figure(figsize=(9, 6))
sns.stripplot(
    data=district_kpis.sort_values("oosc_rate"), x="oosc_rate", y=[""] * len(district_kpis),
    hue="risk_tier", hue_order=["low_risk", "medium_risk", "high_risk"],
    palette={"low_risk": "seagreen", "medium_risk": "goldenrod", "high_risk": "crimson"},
    size=8, jitter=0.25)
plt.title("District Risk Tiers by Out-of-School Rate (NumPy percentile cut-offs)")
plt.xlabel("Out-of-School Rate")
plt.ylabel("")
plt.tight_layout()
plt.savefig(CHART_DIR / "insight_4_risk_tiers.png", dpi=100)
plt.close()

print(f"\nSaved 4 charts to {CHART_DIR}/ and a CSV to {TABLE_DIR}/")
