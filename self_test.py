from pathlib import Path
import json
import math
import pandas as pd

BASE = Path(__file__).resolve().parent
DB = BASE / "data" / "prey_energy_db_v1_0_0.xlsx"
VAL = BASE / "validation" / "validation_reference.json"

def fail(msg):
    raise SystemExit("SELF-TEST FAILED: " + msg)

if not DB.exists():
    fail("data/prey_energy_db_v1_0_0.xlsx is missing")
if not VAL.exists():
    fail("validation_reference.json is missing")

energy = pd.read_excel(DB, sheet_name="EnergyDB_Final")
lookup = pd.read_excel(DB, sheet_name="Lookup_Defaults")

if len(energy) != 187:
    fail(f"Expected 187 EnergyDB_Final records, found {len(energy)}")
if len(lookup) != 384:
    fail(f"Expected 384 Lookup_Defaults entries, found {len(lookup)}")

def ed(key):
    hit = lookup[lookup["Key"] == key]
    if hit.empty:
        return None
    return float(hit.iloc[0]["Recommended_ED_kJ_g_WW"])

if ed("ExactTaxon|Engraulis japonicus") is not None:
    fail("Engraulis japonicus should not have an exact-taxon ED in the current DB")

eng = ed("Genus|Engraulis")
if eng is None or not math.isclose(eng, 6.825, rel_tol=0, abs_tol=1e-9):
    fail(f"Genus|Engraulis expected 6.825, found {eng}")

if ed("Family|Pandalidae") is not None:
    fail("Pandalidae should not have a family ED in the current DB")

pan = ed("Functional|Benthic decapods")
if pan is None or not math.isclose(pan, 3.07, rel_tol=0, abs_tol=1e-9):
    fail(f"Functional|Benthic decapods expected 3.070, found {pan}")

broad = ed("Broad|Crustacea")
if broad is None or not math.isclose(broad, 3.90, rel_tol=0, abs_tol=1e-9):
    fail(f"Broad|Crustacea expected 3.900, found {broad}")

data = json.loads(VAL.read_text(encoding="utf-8"))
if data.get("validation_targets") != 128:
    fail("Validation target count is not 128")

coverage = data.get("actual_hierarchy", {}).get("coverage_pct")
if coverage is None or abs(coverage - 99.21875) > 1e-6:
    fail(f"Unexpected validation coverage: {coverage}")

print("PECC SELF-TEST PASSED")
print("EnergyDB_Final records: 187")
print("Lookup_Defaults entries: 384")
print("Engraulis genus ED: 6.825 kJ/g WW")
print("Benthic decapod proxy ED: 3.070 kJ/g WW")
print("Crustacea broad ED: 3.900 kJ/g WW")
print("Validation targets: 128")
print("Fallback coverage: 99.2%")
