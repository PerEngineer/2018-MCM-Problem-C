from __future__ import annotations

import csv
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


DATA_FILE = Path("2018_MCM_Problem_C_Data.xlsx")
OUT_DIR = Path("outputs")
STATES = ["AZ", "CA", "NM", "TX"]
YEARS = list(range(1960, 2010))
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_xlsx_xml(path: Path):
    with ZipFile(path) as z:
        shared = []
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            shared.append("".join(t.text or "" for t in si.findall(".//m:t", NS)))

        def cell_value(c):
            cell_type = c.attrib.get("t")
            v = c.find("m:v", NS)
            if cell_type == "s" and v is not None:
                return shared[int(v.text)]
            if cell_type == "inlineStr":
                return "".join(t.text or "" for t in c.findall(".//m:t", NS))
            return v.text if v is not None else None

        def read_sheet(filename):
            root = ET.fromstring(z.read(filename))
            rows = []
            for row in root.findall(".//m:sheetData/m:row", NS):
                values = {}
                for cell in row.findall("m:c", NS):
                    col = "".join(re.findall("[A-Z]+", cell.attrib.get("r", "")))
                    values[col] = cell_value(cell)
                rows.append(values)
            return rows

        return read_sheet("xl/worksheets/sheet1.xml"), read_sheet("xl/worksheets/sheet2.xml")


def safe_div(num, den):
    if den is None or den == 0 or math.isnan(den):
        return float("nan")
    return num / den


def minmax(values, benefit=True):
    clean = [v for v in values if not math.isnan(v)]
    lo, hi = min(clean), max(clean)
    if abs(hi - lo) < 1e-12:
        return [0.5 for _ in values]
    if benefit:
        return [(v - lo) / (hi - lo) for v in values]
    return [(hi - v) / (hi - lo) for v in values]


def ols(xs, ys):
    xbar = statistics.mean(xs)
    ybar = statistics.mean(ys)
    den = sum((x - xbar) ** 2 for x in xs)
    if den == 0:
        return ybar, 0.0
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / den
    intercept = ybar - slope * xbar
    return intercept, slope


def damped_horizon(year, base_year=2009, full_years=16, damping=0.35):
    horizon = year - base_year
    return min(horizon, full_years) + damping * max(0, horizon - full_years)


def fit_predict_linear(series, years, target_years, damp=False):
    xs, ys = [], []
    for y in years:
        v = series.get(y)
        if v is not None and not math.isnan(v):
            xs.append(y - 2009)
            ys.append(v)
    a, b = ols(xs, ys)
    base = series.get(2009, a)
    preds = {}
    for ty in target_years:
        horizon = damped_horizon(ty) if damp else ty - 2009
        preds[ty] = base + b * horizon
    return preds, (a, b)


def fit_predict_log(series, years, target_years, damp=False):
    xs, ys = [], []
    for y in years:
        v = series.get(y)
        if v is not None and v > 0 and not math.isnan(v):
            xs.append(y - 2009)
            ys.append(math.log(v))
    a, b = ols(xs, ys)
    base_value = series.get(2009)
    base = math.log(base_value) if base_value is not None and base_value > 0 else a
    preds = {}
    for ty in target_years:
        horizon = damped_horizon(ty) if damp else ty - 2009
        preds[ty] = math.exp(base + b * horizon)
    return preds, (a, b)


def logit(p):
    eps = 1e-6
    p = max(eps, min(1 - eps, p))
    return math.log(p / (1 - p))


def inv_logit(x):
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)


def fit_predict_share(series, years, target_years, damp=True):
    xs, ys = [], []
    for y in years:
        v = series.get(y)
        if v is not None and 0 < v < 1 and not math.isnan(v):
            xs.append(y - 2009)
            ys.append(logit(v))
    a, b = ols(xs, ys)
    base_value = series.get(2009)
    base = logit(base_value) if base_value is not None and 0 < base_value < 1 else a
    preds = {}
    for ty in target_years:
        horizon = damped_horizon(ty) if damp else ty - 2009
        preds[ty] = inv_logit(base + b * horizon)
    return preds, (a, b)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    seseds, msncodes = read_xlsx_xml(DATA_FILE)
    codebook = {r.get("A"): (r.get("B"), r.get("C")) for r in msncodes[1:]}
    data = {}
    codes = set()
    for r in seseds[1:]:
        code = r["A"]
        state = r["B"]
        year = int(float(r["C"]))
        value = float(r["D"])
        data[(state, year, code)] = value
        codes.add(code)

    def get(state, year, code):
        return data.get((state, year, code), float("nan"))

    metrics = {}
    for state in STATES:
        for year in YEARS:
            total = get(state, year, "TETCB")
            renew = get(state, year, "RETCB")
            total_prod = get(state, year, "TEPRB")
            renew_prod = get(state, year, "REPRB")
            fossil = get(state, year, "CLTCB") + get(state, year, "NGTCB") + get(state, year, "PMTCB")
            nuclear = get(state, year, "NUETB")
            profile = {
                "total_consumption": total,
                "renewable_consumption": renew,
                "renewable_consumption_share": safe_div(renew, total),
                "total_production": total_prod,
                "renewable_production": renew_prod,
                "renewable_production_share": safe_div(renew_prod, total_prod),
                "fossil_share": safe_div(fossil, total),
                "dirty_fossil_burden": safe_div(get(state, year, "CLTCB") + get(state, year, "PMTCB"), total),
                "coal_share": safe_div(get(state, year, "CLTCB"), total),
                "natural_gas_share": safe_div(get(state, year, "NGTCB"), total),
                "petroleum_share": safe_div(get(state, year, "PMTCB"), total),
                "nuclear_share": safe_div(nuclear, total),
                "per_capita_energy": get(state, year, "TETPB"),
                "energy_intensity": get(state, year, "TETGR"),
                "population_thousand": get(state, year, "TPOPP"),
                "real_gdp_million": get(state, year, "GDPRX"),
                "transport_share": safe_div(get(state, year, "TEACB"), total),
                "commercial_share": safe_div(get(state, year, "TECCB"), total),
                "industrial_share": safe_div(get(state, year, "TEICB"), total),
                "residential_share": safe_div(get(state, year, "TERCB"), total),
                "electric_power_ratio": safe_div(get(state, year, "TEEIB"), total),
                "biomass": get(state, year, "BMTCB"),
                "geothermal": get(state, year, "GETCB"),
                "hydro": get(state, year, "HYTCB"),
                "solar": get(state, year, "SOTCB"),
                "wind": get(state, year, "WYTCB"),
                "ethanol": get(state, year, "EMTCB"),
            }
            metrics[(state, year)] = profile

    # 2009 clean renewable profile index.
    indicators = [
        ("renewable_consumption_share", True, 0.35),
        ("renewable_production_share", True, 0.20),
        ("energy_intensity", False, 0.20),
        ("per_capita_energy", False, 0.10),
        ("dirty_fossil_burden", False, 0.15),
    ]
    normalized = {}
    for name, benefit, _ in indicators:
        vals = [metrics[(s, 2009)][name] for s in STATES]
        scaled = minmax(vals, benefit=benefit)
        for state, score in zip(STATES, scaled):
            normalized[(state, name)] = score

    ranking = []
    for state in STATES:
        score = sum(normalized[(state, name)] * weight for name, _, weight in indicators)
        ranking.append((state, score))
    ranking.sort(key=lambda x: x[1], reverse=True)

    # Evolution summaries by decade.
    decade_years = [1960, 1970, 1980, 1990, 2000, 2009]
    evolution_rows = []
    for state in STATES:
        for year in decade_years:
            m = metrics[(state, year)]
            evolution_rows.append({
                "State": state,
                "Year": year,
                "Total consumption, trillion Btu": m["total_consumption"] / 1000,
                "Renewable consumption share": m["renewable_consumption_share"],
                "Fossil share": m["fossil_share"],
                "Per-capita energy, MMBtu": m["per_capita_energy"],
                "Energy intensity, kBtu/$": m["energy_intensity"],
            })

    # Baseline prediction.
    forecast_years = [2025, 2050]
    forecast_rows = []
    fit_years_recent = list(range(1990, 2010))
    fit_years_gdp = list(range(1977, 2010))
    for state in STATES:
        series = defaultdict(dict)
        for year in YEARS:
            for key, value in metrics[(state, year)].items():
                series[key][year] = value

        share_pred, _ = fit_predict_share(series["renewable_consumption_share"], fit_years_recent, forecast_years)
        prod_share_pred, _ = fit_predict_share(series["renewable_production_share"], fit_years_recent, forecast_years)
        fossil_pred, _ = fit_predict_log(series["fossil_share"], fit_years_recent, forecast_years, damp=True)
        pc_pred, _ = fit_predict_log(series["per_capita_energy"], fit_years_recent, forecast_years, damp=True)
        ei_pred, _ = fit_predict_log(series["energy_intensity"], fit_years_gdp, forecast_years, damp=True)
        total_pred, _ = fit_predict_log(series["total_consumption"], fit_years_recent, forecast_years, damp=True)
        prod_pred, _ = fit_predict_log(series["total_production"], fit_years_recent, forecast_years, damp=True)

        for year in forecast_years:
            forecast_rows.append({
                "State": state,
                "Year": year,
                "Total consumption, trillion Btu": total_pred[year] / 1000,
                "Renewable consumption share": share_pred[year],
                "Renewable consumption, trillion Btu": total_pred[year] * share_pred[year] / 1000,
                "Total production, trillion Btu": prod_pred[year] / 1000,
                "Renewable production share": prod_share_pred[year],
                "Fossil share": fossil_pred[year],
                "Per-capita energy, MMBtu": max(0, pc_pred[year]),
                "Energy intensity, kBtu/$": max(0, ei_pred[year]),
            })

    compact_2009 = {}
    for year in [2009]:
        total = sum(metrics[(s, year)]["total_consumption"] for s in STATES)
        renew = sum(metrics[(s, year)]["renewable_consumption"] for s in STATES)
        compact_2009[year] = renew / total

    compact_forecast = {}
    for year in forecast_years:
        total = sum(r["Total consumption, trillion Btu"] for r in forecast_rows if r["Year"] == year)
        renew = sum(r["Renewable consumption, trillion Btu"] for r in forecast_rows if r["Year"] == year)
        compact_forecast[year] = renew / total

    # Suggested targets: exceed no-policy baseline and converge toward a common floor.
    compact_targets = {
        2025: {"compact_share": 0.12, "state_floor": 0.10},
        2050: {"compact_share": 0.30, "state_floor": 0.25},
    }

    def write_csv(path, rows):
        if not rows:
            return
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    profile_rows = []
    for state in STATES:
        m = metrics[(state, 2009)]
        profile_rows.append({
            "State": state,
            "Total consumption, trillion Btu": m["total_consumption"] / 1000,
            "Renewable consumption share": m["renewable_consumption_share"],
            "Renewable production share": m["renewable_production_share"],
            "Fossil share": m["fossil_share"],
            "Dirty fossil burden": m["dirty_fossil_burden"],
            "Coal share": m["coal_share"],
            "Natural gas share": m["natural_gas_share"],
            "Petroleum share": m["petroleum_share"],
            "Nuclear share": m["nuclear_share"],
            "Per-capita energy, MMBtu": m["per_capita_energy"],
            "Energy intensity, kBtu/$": m["energy_intensity"],
            "Transport share": m["transport_share"],
            "Commercial share": m["commercial_share"],
            "Industrial share": m["industrial_share"],
            "Residential share": m["residential_share"],
            "Clean profile score": dict(ranking)[state],
            "Rank": [s for s, _ in ranking].index(state) + 1,
        })

    write_csv(OUT_DIR / "state_profiles_2009.csv", profile_rows)
    write_csv(OUT_DIR / "evolution_decade_summary.csv", evolution_rows)
    write_csv(OUT_DIR / "baseline_forecasts_2025_2050.csv", forecast_rows)

    summary = {
        "data": {
            "codes_defined": len(codebook),
            "codes_in_data": len(codes),
            "states": STATES,
            "years": [min(YEARS), max(YEARS)],
        },
        "ranking_2009": ranking,
        "compact_renewable_consumption_share": {
            "2009": compact_2009[2009],
            **{str(k): v for k, v in compact_forecast.items()},
        },
        "targets": compact_targets,
        "profiles_2009": profile_rows,
        "forecasts": forecast_rows,
    }
    (OUT_DIR / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
