"""Step 2 - Transform and load the analytical layers (all SQL, inside PostgreSQL).

raw_* -> clean_children / rejected_children / clean_households
      -> dim_district -> fact_child_status -> district_kpis

Everything runs in ONE transaction with quality gates at the end: if any gate
fails, the transaction is rolled back and no half-built tables are left behind.

Run: python 2_transform.py
"""
import sys

from sqlalchemy import text

from db import get_engine

DERIVED = [
    "district_kpis", "fact_child_status", "dim_district",
    "clean_households", "rejected_children", "clean_children",
]

BUILD = {
    # ASER's reporting age bracket is 5-16.
    "clean_children": """
        CREATE TABLE clean_children AS
        SELECT * FROM raw_5tlbhhchild
        WHERE childage BETWEEN 5 AND 16
    """,
    # Quarantine: kept and inspectable, never silently dropped.
    "rejected_children": """
        CREATE TABLE rejected_children AS
        SELECT * FROM raw_5tlbhhchild
        WHERE childage IS NULL OR childage < 5 OR childage > 16
    """,
    # Personal data (family head name, surveyor names) is deliberately NOT carried
    # into the clean layer. Note: facility flags use Access-style booleans
    # (-1 = yes, 0 = no, NULL = not asked); they are loaded but not analysed yet.
    "clean_households": """
        CREATE TABLE clean_households AS
        SELECT householdsurvey_id, villagemapsurveyid, housetype, ishouseowned,
               iselectricityconnectionavailable, istoiletavailable,
               ismobileavailable, istvavailable, nearestschooldistance,
               spokenlanguage, preferredschoolmedium, anyoneknowsusecomputer
        FROM raw_4household
    """,
    "dim_district": """
        CREATE TABLE dim_district AS
        SELECT districtsid, districts FROM raw_1tbldistricts
    """,
    # One row per child. A child is out of school unless flagged currently enrolled.
    # (Gate 3 below proves every child has exactly one of the three status flags.)
    "fact_child_status": """
        CREATE TABLE fact_child_status AS
        SELECT
            c.hhcid       AS child_id,
            c.childage    AS age,
            c.childgender AS gender,
            CASE WHEN c.childeducationen = 1.0 THEN 0 ELSE 1 END AS oosc_flag,
            d.districts   AS district_name
        FROM clean_children c
        JOIN clean_households h        ON c.hhid = h.householdsurvey_id
        JOIN raw_3villagemapsurvey vms ON h.villagemapsurveyid = vms.villagemap_id
        JOIN raw_2tblvillages v        ON vms.villageid = v.villageid
        JOIN dim_district d            ON v.districtid = d.districtsid
    """,
    "district_kpis": """
        CREATE TABLE district_kpis AS
        SELECT
            district_name,
            COUNT(child_id) AS total_children,
            SUM(oosc_flag)  AS oosc_count,
            ROUND(SUM(oosc_flag) * 1.0 / COUNT(child_id), 3) AS oosc_rate
        FROM fact_child_status
        GROUP BY district_name
        ORDER BY oosc_rate DESC
    """,
}


def scalar(conn, sql):
    return conn.execute(text(sql)).scalar()


def run(conn):
    for t in DERIVED:
        conn.execute(text(f"DROP TABLE IF EXISTS {t}"))
    for name in ["clean_children", "rejected_children", "clean_households",
                 "dim_district", "fact_child_status", "district_kpis"]:
        conn.execute(text(BUILD[name]))
        print(f"  built {name}: {scalar(conn, f'SELECT COUNT(*) FROM {name}'):,} rows")

    raw = scalar(conn, "SELECT COUNT(*) FROM raw_5tlbhhchild")
    clean = scalar(conn, "SELECT COUNT(*) FROM clean_children")
    rejected = scalar(conn, "SELECT COUNT(*) FROM rejected_children")
    fact = scalar(conn, "SELECT COUNT(*) FROM fact_child_status")
    kpi_total = scalar(conn, "SELECT SUM(total_children) FROM district_kpis")
    bad_flags = scalar(conn, """
        SELECT COUNT(*) FROM clean_children
        WHERE COALESCE(childeducationne,0) + COALESCE(childeducationdp,0)
            + COALESCE(childeducationen,0) <> 1
    """)

    print("\nQuality gates")
    gates = [
        (f"1. clean + rejected = raw            ({clean:,} + {rejected:,} = {raw:,})", clean + rejected == raw),
        (f"2. no child lost in the join         (clean {clean:,} vs fact {fact:,})", clean == fact),
        (f"3. one enrollment flag per child     ({bad_flags:,} children violate)", bad_flags == 0),
        (f"4. district totals add up to fact    ({kpi_total:,} vs {fact:,})", kpi_total == fact),
    ]
    for label, ok in gates:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not all(ok for _, ok in gates):
        raise RuntimeError("Quality gate failed - rolling back, nothing was written.")


def main():
    engine = get_engine()
    try:
        with engine.begin() as conn:  # one transaction: commit on success, rollback on error
            run(conn)
    except RuntimeError as e:
        sys.exit(str(e))
    print("\nTransform complete.")


if __name__ == "__main__":
    main()
