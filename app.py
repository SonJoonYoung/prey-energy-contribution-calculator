from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone
import json
import os
import re
import time

import pandas as pd
import requests
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DB_FILE = APP_DIR / "data" / "prey_energy_db_v1_0_0.xlsx"
VALIDATION_FILE = APP_DIR / "validation" / "validation_reference.json"
APP_VERSION = "1.0.0"

LOCAL_DATA_DIR = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home()))
) / "PreyEnergyCalculator"
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
TAXONOMY_CACHE_FILE = LOCAL_DATA_DIR / "worms_taxonomy_cache.csv"
WORMS_BASE = "https://www.marinespecies.org/rest"
MANUAL = "— Not listed / manual entry —"


st.set_page_config(
    page_title="Prey Energy Contribution Calculator",
    page_icon="🐟",
    layout="wide",
)


# ============================================================
# Database
# ============================================================

@st.cache_data(show_spinner=False)
def load_database():
    energy_db = pd.read_excel(DB_FILE, sheet_name="EnergyDB_Final")
    lookup_db = pd.read_excel(DB_FILE, sheet_name="Lookup_Defaults")
    references = pd.read_excel(DB_FILE, sheet_name="References")

    required_energy = {
        "Taxon_name",
        "Broad_taxonomic_group",
        "Taxonomic_subgroup",
        "Energy_proxy_group",
        "Family_standardized",
        "Genus_standardized",
    }
    required_lookup = {
        "Key",
        "Priority",
        "Level",
        "Name",
        "Recommended_ED_kJ_g_WW",
        "Available_min",
        "Available_max",
        "Primary_source",
        "Review_flag",
        "n_records",
        "n_unique_taxa",
    }

    missing_energy = sorted(required_energy - set(energy_db.columns))
    missing_lookup = sorted(required_lookup - set(lookup_db.columns))

    if missing_energy or missing_lookup:
        details = []
        if missing_energy:
            details.append("EnergyDB_Final missing: " + ", ".join(missing_energy))
        if missing_lookup:
            details.append("Lookup_Defaults missing: " + ", ".join(missing_lookup))
        raise ValueError("\n".join(details))

    return energy_db, lookup_db, references


def clean(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def unique_values(df: pd.DataFrame, col: str) -> list[str]:
    if df.empty or col not in df.columns:
        return []
    s = df[col].dropna().astype(str).str.strip()
    s = s[s != ""]
    return sorted(s.unique().tolist())


try:
    energy_db, lookup_db, references = load_database()
except Exception as exc:
    st.error("Could not load data/prey_energy_db_v1_0_0.xlsx.")
    st.exception(exc)
    st.stop()


@st.cache_data(show_spinner=False)
def load_validation_reference():
    if not VALIDATION_FILE.exists():
        return {}
    with open(VALIDATION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


validation_reference = load_validation_reference()


def level_validation(level: str) -> dict:
    return validation_reference.get("selected_level_metrics", {}).get(level, {})


def lower_group_validation(broad: str, proxy: str) -> dict:
    broad = clean(broad)
    proxy = clean(proxy)
    for row in validation_reference.get("lower_fallback_group_reference", []):
        if (
            clean(row.get("broad_group")) == broad
            and clean(row.get("energy_proxy_group")) == proxy
        ):
            return row
    return {}


def validation_note_for_match(match: dict, broad: str = "", proxy: str = "") -> dict:
    level = clean(match.get("level"))
    result = {
        "evidence_class": "",
        "validation_n": None,
        "validation_mae": None,
        "validation_mape": None,
        "validation_note": "",
    }

    if level == "Exact taxon":
        result["evidence_class"] = "Direct taxon ED"
        result["validation_note"] = (
            "Direct exact-taxon ED; fallback validation is not applicable."
        )
        return result

    if level in {"Genus", "Family", "Energy proxy group", "Broad taxonomic group"}:
        display_level = {
            "Energy proxy group": "Ecological proxy",
            "Broad taxonomic group": "Broad",
        }.get(level, level)

        stats_key = {
            "Broad": "Broad",
        }.get(display_level, display_level)

        stats = level_validation(stats_key)
        result["evidence_class"] = (
            "Taxonomic fallback"
            if level in {"Genus", "Family"}
            else "Lower-level fallback"
        )

        if stats:
            result["validation_n"] = stats.get("n")
            result["validation_mae"] = stats.get("mae_kJ_g")
            result["validation_mape"] = stats.get("mape_pct")
            result["validation_note"] = (
                f"Internal leave-one-taxon-out performance when this level was "
                f"actually selected: n={stats.get('n')}, "
                f"MAE={stats.get('mae_kJ_g'):.3f} kJ/g, "
                f"MAPE={stats.get('mape_pct'):.1f}%."
            )

        if level == "Energy proxy group" and proxy:
            grp = lower_group_validation(broad, proxy)
            if grp:
                result["validation_note"] += (
                    f" For actual lower-fallback cases in {proxy}: "
                    f"n={grp.get('n_actual_lower_cases')}, "
                    f"Proxy MAE={grp.get('proxy_mae_kJ_g'):.3f}, "
                    f"Broad MAE={grp.get('broad_mae_kJ_g'):.3f} kJ/g. "
                    f"This comparison is reference information only and does not "
                    f"override the selected ecological proxy."
                )

        if match.get("n_unique_taxa"):
            result["validation_note"] += (
                f" Current lookup support: {int(match.get('n_unique_taxa'))} "
                f"unique taxon/taxa from {int(match.get('n_records') or 0)} record(s)."
            )

    return result


# ============================================================
# WoRMS taxonomy
# ============================================================

CACHE_COLUMNS = [
    "query_name",
    "scientificname",
    "valid_name",
    "AphiaID",
    "valid_AphiaID",
    "rank",
    "status",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "match_type",
    "cached_at_utc",
]


def load_taxonomy_cache() -> pd.DataFrame:
    if TAXONOMY_CACHE_FILE.exists():
        try:
            df = pd.read_csv(TAXONOMY_CACHE_FILE, dtype=str).fillna("")
            for c in CACHE_COLUMNS:
                if c not in df.columns:
                    df[c] = ""
            return df[CACHE_COLUMNS]
        except Exception:
            pass
    return pd.DataFrame(columns=CACHE_COLUMNS)


def save_taxonomy_cache(df: pd.DataFrame):
    df = df.drop_duplicates(subset=["query_name"], keep="last")
    df.to_csv(TAXONOMY_CACHE_FILE, index=False, encoding="utf-8-sig")


def worms_request(path: str, params: dict | None = None):
    url = WORMS_BASE + path
    response = requests.get(
        url,
        params=params or {},
        timeout=15,
        headers={"User-Agent": "PreyEnergyCalculator/2.0 research-use"},
    )
    response.raise_for_status()
    return response.json()


def normalize_worms_record(record: dict, query_name: str) -> dict:
    if not record:
        return {}
    out = {c: "" for c in CACHE_COLUMNS}
    out["query_name"] = query_name
    for key in [
        "scientificname", "valid_name", "AphiaID", "valid_AphiaID",
        "rank", "status", "kingdom", "phylum", "class", "order",
        "family", "genus", "match_type",
    ]:
        value = record.get(key, "")
        out[key] = "" if value is None else str(value)
    out["cached_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return out


def worms_find_name(name: str, like: bool = False) -> list[dict]:
    name = clean(name)
    if not name:
        return []
    data = worms_request(
        f"/AphiaRecordsByName/{quote(name, safe='')}",
        params={
            "like": str(like).lower(),
            "marine_only": "false",
            "extant_only": "true",
            "offset": 1,
        },
    )
    if not isinstance(data, list):
        return []
    return [x for x in data if isinstance(x, dict)]


def select_best_worms_record(records: list[dict], query_name: str, preferred_rank: str = ""):
    if not records:
        return None

    q = clean(query_name).lower()
    preferred_rank = clean(preferred_rank).lower()

    def score(r):
        sci = clean(r.get("scientificname")).lower()
        valid = clean(r.get("valid_name")).lower()
        rank = clean(r.get("rank")).lower()
        status = clean(r.get("status")).lower()

        s = 0
        if sci == q:
            s += 100
        if valid == q:
            s += 90
        if status == "accepted":
            s += 20
        if preferred_rank and rank == preferred_rank:
            s += 30
        if clean(r.get("isMarine")) in {"1", "True", "true"}:
            s += 5
        return s

    return sorted(records, key=score, reverse=True)[0]


def worms_resolve_name(name: str, preferred_rank: str = "", use_cache: bool = True):
    name = clean(name)
    if not name:
        return None

    cache = load_taxonomy_cache()
    if use_cache and not cache.empty:
        hit = cache[cache["query_name"].str.lower() == name.lower()]
        if not hit.empty:
            return hit.iloc[-1].to_dict()

    try:
        records = worms_find_name(name, like=False)
        record = select_best_worms_record(records, name, preferred_rank)

        if record is None:
            records = worms_find_name(name, like=True)
            record = select_best_worms_record(records, name, preferred_rank)

        if record is None:
            return None

        normalized = normalize_worms_record(record, name)
        cache = pd.concat([cache, pd.DataFrame([normalized])], ignore_index=True)
        save_taxonomy_cache(cache)
        return normalized
    except Exception:
        return None


def worms_search(name: str) -> list[dict]:
    name = clean(name)
    if len(name) < 2:
        return []
    try:
        records = worms_find_name(name, like=True)
        # accepted/current names first, then scientific name
        records = sorted(
            records,
            key=lambda r: (
                clean(r.get("status")).lower() != "accepted",
                clean(r.get("valid_name") or r.get("scientificname")),
            ),
        )
        return records[:30]
    except Exception:
        return []


def worms_classification_nodes(record: dict) -> list[dict]:
    """
    Retrieve the complete WoRMS classification tree for a taxon.
    WoRMS AphiaRecord fields do not always expose intermediate ranks
    (e.g. Crustacea may be a subphylum and therefore absent from the
    simple kingdom/phylum/class/order fields).
    """
    aphia_id = clean(record.get("valid_AphiaID")) or clean(record.get("AphiaID"))
    if not aphia_id:
        return []

    try:
        data = worms_request(f"/AphiaClassificationByAphiaID/{aphia_id}")
    except Exception:
        return []

    nodes = []
    current = data
    guard = 0

    while isinstance(current, dict) and guard < 100:
        nodes.append(current)
        current = current.get("child")
        guard += 1

    return nodes


def broad_from_worms(record: dict) -> str:
    """
    Convert the complete WoRMS hierarchy to the broad groups used by
    the prey-energy database.

    The complete hierarchy is checked first, then conservative fallbacks
    based on the returned record/order are used if the classification
    endpoint is temporarily unavailable.
    """
    direct_values = {
        clean(record.get("kingdom")),
        clean(record.get("phylum")),
        clean(record.get("class")),
        clean(record.get("order")),
        clean(record.get("family")),
        clean(record.get("genus")),
    }

    nodes = worms_classification_nodes(record)
    hierarchy_names = {
        clean(node.get("scientificname"))
        for node in nodes
        if clean(node.get("scientificname"))
    }
    hierarchy_ranks = {
        clean(node.get("rank")).lower(): clean(node.get("scientificname"))
        for node in nodes
        if clean(node.get("rank")) and clean(node.get("scientificname"))
    }

    values = direct_values | hierarchy_names
    order_name = clean(record.get("order")) or hierarchy_ranks.get("order", "")
    class_name = clean(record.get("class")) or hierarchy_ranks.get("class", "")
    phylum_name = clean(record.get("phylum")) or hierarchy_ranks.get("phylum", "")

    # Vertebrates
    if "Chondrichthyes" in values:
        return "Chondrichthyes"
    if "Teleostei" in values:
        return "Teleostei"

    # Crustacea can occur at an intermediate rank in WoRMS, so the
    # complete hierarchy is essential. Order fallbacks cover cases
    # where the classification request is temporarily unavailable.
    crustacean_orders = {
        "Decapoda", "Euphausiacea", "Mysida", "Amphipoda",
        "Isopoda", "Stomatopoda", "Cumacea"
    }
    if "Crustacea" in values or order_name in crustacean_orders:
        return "Crustacea"

    # Molluscs
    if "Cephalopoda" in values:
        return "Cephalopoda"
    if "Mollusca" in values:
        return "Mollusca (non-cephalopods)"

    # Other major groups
    if "Annelida" in values:
        return "Annelida"
    if "Cnidaria" in values:
        return "Cnidaria"
    if "Ctenophora" in values:
        return "Ctenophora"
    if "Insecta" in values:
        return "Insecta"

    # Conservative fish fallback if WoRMS returns Actinopterygii/Actinopteri
    # without an explicit Teleostei node.
    if class_name in {"Actinopterygii", "Actinopteri"} and phylum_name == "Chordata":
        return "Teleostei"

    # If it is an animal but does not map to one of the controlled groups,
    # keep it in the database's final residual invertebrate category.
    if "Animalia" in values and "Chordata" not in values:
        return "Other invertebrates"

    return ""


def ensure_family_taxonomy(families: list[str], progress_label: str = "") -> pd.DataFrame:
    families = [clean(x) for x in families if clean(x)]
    cache = load_taxonomy_cache()
    cached_names = set(cache["query_name"].str.lower().tolist()) if not cache.empty else set()
    missing = [f for f in families if f.lower() not in cached_names]

    if missing:
        status = st.status(
            progress_label or f"Loading taxonomic orders from WoRMS ({len(missing)} families)...",
            expanded=True,
        )
        bar = status.progress(0.0)

        for i, family in enumerate(missing, start=1):
            status.write(f"Resolving {family} ({i}/{len(missing)})")
            worms_resolve_name(family, preferred_rank="Family", use_cache=False)
            bar.progress(i / len(missing))
            time.sleep(0.03)

        status.update(label="Taxonomy cache updated.", state="complete", expanded=False)
        cache = load_taxonomy_cache()

    return cache


# ============================================================
# ED matching
# ============================================================

def lookup_row(key: str):
    key = clean(key)
    if not key:
        return None
    hit = lookup_db[lookup_db["Key"].astype(str) == key]
    if hit.empty:
        return None
    return hit.iloc[0]


def infer_genus(name: str) -> str:
    name = clean(name)
    if not name:
        return ""
    first = name.split()[0]
    if re.fullmatch(r"[A-Z][A-Za-z.-]+", first):
        return first
    return ""


def match_ed(
    exact_taxon: str = "",
    genus: str = "",
    family: str = "",
    energy_proxy_group: str = "",
    broad_group: str = "",
):
    genus = clean(genus) or infer_genus(exact_taxon)

    candidates = [
        ("Exact taxon", f"ExactTaxon|{clean(exact_taxon)}" if clean(exact_taxon) else ""),
        ("Genus", f"Genus|{genus}" if genus else ""),
        ("Family", f"Family|{clean(family)}" if clean(family) else ""),
        ("Energy proxy group", f"Functional|{clean(energy_proxy_group)}" if clean(energy_proxy_group) else ""),
        ("Broad taxonomic group", f"Broad|{clean(broad_group)}" if clean(broad_group) else ""),
    ]

    for level, key in candidates:
        row = lookup_row(key)
        if row is not None:
            return {
                "level": level,
                "key": key,
                "name": clean(row.get("Name")),
                "ed": float(row["Recommended_ED_kJ_g_WW"]),
                "ed_min": float(row["Available_min"]) if pd.notna(row.get("Available_min")) else None,
                "ed_max": float(row["Available_max"]) if pd.notna(row.get("Available_max")) else None,
                "priority": int(row["Priority"]) if pd.notna(row.get("Priority")) else None,
                "source": clean(row.get("Primary_source")),
                "source_detail": clean(row.get("Source_detail")),
                "rule": clean(row.get("Selection_rule")),
                "review": clean(row.get("Review_flag")),
                "n_records": int(row["n_records"]) if pd.notna(row.get("n_records")) else None,
                "n_unique_taxa": int(row["n_unique_taxa"]) if pd.notna(row.get("n_unique_taxa")) else None,
            }
    return None


def taxonomy_match_available(exact_taxon="", genus="", family=""):
    return match_ed(
        exact_taxon=exact_taxon,
        genus=genus,
        family=family,
        energy_proxy_group="",
        broad_group="",
    )


def available_proxy_groups(broad: str, family: str = "") -> list[str]:
    if not broad:
        return []

    df = energy_db[
        energy_db["Broad_taxonomic_group"].astype(str) == broad
    ]

    if family:
        fam_hit = df[df["Family_standardized"].astype(str) == family]
        fam_proxy = unique_values(fam_hit, "Energy_proxy_group")
        if fam_proxy:
            return fam_proxy

    return unique_values(df, "Energy_proxy_group")


# ============================================================
# Result table / export
# ============================================================

def with_contributions(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records).copy()
    group_cols = ["Predator_species", "Specimen_ID"]

    wt = df.groupby(group_cols)["Prey_wet_mass_g"].transform("sum")
    et = df.groupby(group_cols)["Estimated_energy_kJ"].transform("sum")

    df["Within_stomach_weight_pct"] = (
        df["Prey_wet_mass_g"] / wt * 100
    ).where(wt > 0)

    df["Within_stomach_energy_pct"] = (
        df["Estimated_energy_kJ"] / et * 100
    ).where(et > 0)

    # Conservative sensitivity envelope:
    # focal prey at ED minimum while all other prey are at ED maximum,
    # and vice versa for the upper bound.
    if {
        "Estimated_energy_min_kJ",
        "Estimated_energy_max_kJ",
    }.issubset(df.columns):
        sum_min = df.groupby(group_cols)["Estimated_energy_min_kJ"].transform("sum")
        sum_max = df.groupby(group_cols)["Estimated_energy_max_kJ"].transform("sum")

        lower_den = (
            df["Estimated_energy_min_kJ"]
            + (sum_max - df["Estimated_energy_max_kJ"])
        )
        upper_den = (
            df["Estimated_energy_max_kJ"]
            + (sum_min - df["Estimated_energy_min_kJ"])
        )

        df["Within_stomach_energy_pct_lower"] = (
            df["Estimated_energy_min_kJ"] / lower_den * 100
        ).where(lower_den > 0)

        df["Within_stomach_energy_pct_upper"] = (
            df["Estimated_energy_max_kJ"] / upper_den * 100
        ).where(upper_den > 0)

    return df

def prey_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    agg_kwargs = {
        "Records": ("Prey_taxon", "size"),
        "Count": ("Count", "sum"),
        "Wet_mass_g": ("Prey_wet_mass_g", "sum"),
        "Estimated_energy_kJ": ("Estimated_energy_kJ", "sum"),
    }

    if "Estimated_energy_min_kJ" in df.columns:
        agg_kwargs["Estimated_energy_min_kJ"] = (
            "Estimated_energy_min_kJ", "sum"
        )
    if "Estimated_energy_max_kJ" in df.columns:
        agg_kwargs["Estimated_energy_max_kJ"] = (
            "Estimated_energy_max_kJ", "sum"
        )

    out = (
        df.groupby(
            ["Prey_taxon", "Match_level", "Matched_taxon_or_group"],
            dropna=False,
            as_index=False,
        )
        .agg(**agg_kwargs)
    )

    total_w = out["Wet_mass_g"].sum()
    total_e = out["Estimated_energy_kJ"].sum()

    out["Weight_pct"] = (
        out["Wet_mass_g"] / total_w * 100 if total_w > 0 else pd.NA
    )
    out["Energy_pct"] = (
        out["Estimated_energy_kJ"] / total_e * 100
        if total_e > 0 else pd.NA
    )

    if {
        "Estimated_energy_min_kJ",
        "Estimated_energy_max_kJ",
    }.issubset(out.columns):
        total_min = out["Estimated_energy_min_kJ"].sum()
        total_max = out["Estimated_energy_max_kJ"].sum()

        lower_den = (
            out["Estimated_energy_min_kJ"]
            + (total_max - out["Estimated_energy_max_kJ"])
        )
        upper_den = (
            out["Estimated_energy_max_kJ"]
            + (total_min - out["Estimated_energy_min_kJ"])
        )

        out["Energy_pct_lower_bound"] = (
            out["Estimated_energy_min_kJ"] / lower_den * 100
        ).where(lower_den > 0)

        out["Energy_pct_upper_bound"] = (
            out["Estimated_energy_max_kJ"] / upper_den * 100
        ).where(upper_den > 0)

    return out.sort_values("Estimated_energy_kJ", ascending=False)

def export_excel(raw_df, summary_df) -> bytes:
    bio = BytesIO()

    selected_rows = []
    for level, stats in validation_reference.get(
        "selected_level_metrics", {}
    ).items():
        selected_rows.append({"Level": level, **stats})

    forced_rows = []
    for level, stats in validation_reference.get(
        "forced_level_metrics", {}
    ).items():
        forced_rows.append({"Level": level, **stats})

    group_rows = validation_reference.get(
        "lower_fallback_group_reference", []
    )

    method_notes = pd.DataFrame(
        [
            ["PECC version", APP_VERSION],
            [
                "Final fallback hierarchy",
                "Exact taxon > Genus > Family > Ecological energy proxy > Broad taxonomic group",
            ],
            [
                "Validation use",
                "Displayed as evidence/uncertainty information only; it does not automatically override the fallback hierarchy.",
            ],
            [
                "Validation design",
                "Internal leave-one-taxon-out validation of 128 species-specific taxa.",
            ],
            [
                "Validation coverage",
                f"{validation_reference.get('actual_hierarchy', {}).get('coverage_pct', 0):.1f}%",
            ],
            [
                "Overall fallback MAE",
                f"{validation_reference.get('actual_hierarchy', {}).get('mae_kJ_g', float('nan')):.3f} kJ/g",
            ],
            [
                "Automatic Proxy/Broad switching",
                "Tested and rejected because it did not improve aggregate prediction performance.",
            ],
            [
                "Uncertainty bounds",
                "ED min-max values are propagated as conservative sensitivity bounds; these are not statistical confidence intervals.",
            ],
            [
                "Interpretation",
                "Estimated potential energetic contribution, not assimilated or metabolizable energy.",
            ],
        ],
        columns=["Item", "Description"],
    )

    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        raw_df.to_excel(writer, sheet_name="Raw_records", index=False)
        summary_df.to_excel(
            writer, sheet_name="Prey_energy_summary", index=False
        )
        lookup_db.to_excel(writer, sheet_name="ED_lookup", index=False)
        references.to_excel(writer, sheet_name="References", index=False)
        pd.DataFrame(selected_rows).to_excel(
            writer, sheet_name="Validation_selected", index=False
        )
        pd.DataFrame(forced_rows).to_excel(
            writer, sheet_name="Validation_forced", index=False
        )
        pd.DataFrame(group_rows).to_excel(
            writer, sheet_name="Proxy_group_reference", index=False
        )
        method_notes.to_excel(
            writer, sheet_name="Method_notes", index=False
        )

    return bio.getvalue()


# ============================================================
# Session state
# ============================================================

if "records" not in st.session_state:
    st.session_state.records = []
if "next_id" not in st.session_state:
    st.session_state.next_id = 1
if "online_selected" not in st.session_state:
    st.session_state.online_selected = None


# ============================================================
# UI
# ============================================================

st.title("🐟 Prey Energy Contribution Calculator")
st.caption(f"PECC v{APP_VERSION} · validated final workflow")
st.caption(
    "Taxonomic browsing: Broad group → Order → Family → Genus → Species · "
    "ED fallback: Exact taxon → Genus → Family → Ecological energy proxy → Broad group"
)

entry_tab, results_tab, db_tab, validation_tab, method_tab = st.tabs(
    ["1. Data entry", "2. Results / export", "3. ED database", "4. Validation", "5. Method"]
)


with entry_tab:
    st.subheader("Predator information")
    p1, p2 = st.columns(2)
    with p1:
        predator = st.text_input("Predator species", placeholder="e.g., Miichthys miiuy")
    with p2:
        specimen = st.text_input("Specimen ID", placeholder="e.g., M001")

    st.subheader("Find prey taxon")
    mode = st.radio(
        "Choose how to find the prey",
        ["Search scientific name", "Browse taxonomy"],
        horizontal=True,
    )

    selected_taxon = ""
    selected_broad = ""
    selected_order = ""
    selected_family = ""
    selected_genus = ""
    selected_proxy = ""
    taxonomy_source = "Local ED database"

    # --------------------------------------------------------
    # Scientific-name search
    # --------------------------------------------------------
    if mode == "Search scientific name":
        query = st.text_input(
            "Scientific name search",
            placeholder="Type a full or partial scientific name, e.g., Engraulis japonicus",
            help="Local ED database matches appear immediately. Use WoRMS search for taxa not in the local ED database.",
        ).strip()

        local_taxa = unique_values(energy_db, "Taxon_name")
        local_matches = [
            x for x in local_taxa
            if query and query.lower() in x.lower()
        ][:50]

        if query and local_matches:
            local_choice = st.selectbox(
                "Local ED-database matches",
                local_matches,
                index=None,
                placeholder="Select a local match",
            )
        else:
            local_choice = None

        c_online, c_note = st.columns([1, 3])
        with c_online:
            search_online = st.button(
                "Search WoRMS",
                disabled=len(query) < 2,
                use_container_width=True,
            )
        with c_note:
            st.caption(
                "Use WoRMS when the species is not present in the local ED database. "
                "The accepted name, Order, Family and Genus are then used for ED fallback."
            )

        if search_online:
            records = worms_search(query)
            st.session_state["worms_search_results"] = records

        online_records = st.session_state.get("worms_search_results", [])
        online_choice = None

        if online_records:
            labels = []
            index_to_record = {}
            for i, rec in enumerate(online_records):
                sci = clean(rec.get("scientificname"))
                valid = clean(rec.get("valid_name"))
                rank = clean(rec.get("rank"))
                status = clean(rec.get("status"))
                label = f"{valid or sci}  [{rank}; {status}]"
                if sci and valid and sci != valid:
                    label += f"  ← {sci}"
                labels.append(label)
                index_to_record[label] = rec

            online_choice = st.selectbox(
                "WoRMS matches",
                labels,
                index=None,
                placeholder="Select a WoRMS result",
            )

        worms_record = None

        if local_choice:
            selected_taxon = local_choice
            row = energy_db[energy_db["Taxon_name"].astype(str) == selected_taxon].iloc[0]
            selected_broad = clean(row.get("Broad_taxonomic_group"))
            selected_family = clean(row.get("Family_standardized"))
            selected_genus = clean(row.get("Genus_standardized"))

            wr = worms_resolve_name(selected_taxon)
            if wr:
                worms_record = wr
                selected_order = clean(wr.get("order"))
                selected_family = clean(wr.get("family")) or selected_family
                selected_genus = clean(wr.get("genus")) or selected_genus
                taxonomy_source = "WoRMS + local ED database"

        elif online_choice:
            raw = index_to_record[online_choice]
            selected_taxon = clean(raw.get("valid_name")) or clean(raw.get("scientificname"))
            worms_record = normalize_worms_record(raw, selected_taxon)

            # Save selected online result to local taxonomy cache.
            cache = load_taxonomy_cache()
            cache = pd.concat([cache, pd.DataFrame([worms_record])], ignore_index=True)
            save_taxonomy_cache(cache)

            selected_order = clean(worms_record.get("order"))
            selected_family = clean(worms_record.get("family"))
            selected_genus = clean(worms_record.get("genus"))
            selected_broad = broad_from_worms(worms_record)
            taxonomy_source = "WoRMS"

        elif query and not local_matches:
            st.info("No local ED-database match. Click **Search WoRMS**.")

        # If user typed a full name but didn't select anything yet:
        if not selected_taxon and query and " " in query:
            st.caption("Tip: search WoRMS, then select the accepted taxon before calculating ED.")

    # --------------------------------------------------------
    # Taxonomic browsing
    # --------------------------------------------------------
    else:
        broad_options = unique_values(energy_db, "Broad_taxonomic_group")
        selected_broad = st.selectbox(
            "Broad taxonomic group",
            broad_options,
            index=None,
            placeholder="e.g., Teleostei",
        ) or ""

        family_df = pd.DataFrame()
        if selected_broad:
            broad_df = energy_db[
                energy_db["Broad_taxonomic_group"].astype(str) == selected_broad
            ]
            broad_families = unique_values(broad_df, "Family_standardized")

            if broad_families:
                cache = ensure_family_taxonomy(
                    broad_families,
                    progress_label=f"Preparing Order → Family taxonomy for {selected_broad} (first use only)...",
                )

                fam_cache = cache[
                    cache["query_name"].isin(broad_families)
                ].copy()

                order_map = {}
                for fam in broad_families:
                    hit = fam_cache[fam_cache["query_name"] == fam]
                    order_map[fam] = clean(hit.iloc[-1].get("order")) if not hit.empty else ""

                order_options = sorted({v for v in order_map.values() if v})
                unresolved = [f for f, o in order_map.items() if not o]
                if unresolved:
                    order_options.append("Order unresolved")

                selected_order = st.selectbox(
                    "Order",
                    order_options,
                    index=None,
                    placeholder="Select order",
                    disabled=not order_options,
                ) or ""

                if selected_order:
                    if selected_order == "Order unresolved":
                        family_options = sorted(unresolved)
                    else:
                        family_options = sorted(
                            [f for f, o in order_map.items() if o == selected_order]
                        )

                    selected_family = st.selectbox(
                        "Family",
                        family_options,
                        index=None,
                        placeholder="Select family",
                    ) or ""

                    if selected_family:
                        family_df = broad_df[
                            broad_df["Family_standardized"].astype(str) == selected_family
                        ]
                        genus_options = unique_values(family_df, "Genus_standardized")

                        selected_genus = st.selectbox(
                            "Genus",
                            genus_options,
                            index=None,
                            placeholder="Select genus",
                            disabled=not genus_options,
                        ) or ""

                        if selected_genus:
                            genus_df = family_df[
                                family_df["Genus_standardized"].astype(str) == selected_genus
                            ]
                            species_options = unique_values(genus_df, "Taxon_name")
                        else:
                            species_options = unique_values(family_df, "Taxon_name")

                        species_options = species_options + [MANUAL]
                        species_choice = st.selectbox(
                            "Species / exact taxon",
                            species_options,
                            index=None,
                            placeholder="Select species or manual entry",
                        )

                        if species_choice == MANUAL:
                            selected_taxon = st.text_input(
                                "Scientific name not listed in ED database",
                                placeholder="e.g., Engraulis japonicus",
                            ).strip()

                            if selected_taxon:
                                wr = worms_resolve_name(selected_taxon)
                                if wr:
                                    selected_order = clean(wr.get("order")) or selected_order
                                    selected_family = clean(wr.get("family")) or selected_family
                                    selected_genus = clean(wr.get("genus")) or selected_genus
                                    selected_broad = broad_from_worms(wr) or selected_broad
                                    taxonomy_source = "WoRMS"
                        elif species_choice:
                            selected_taxon = species_choice

        if selected_broad and not selected_family:
            st.caption(
                "Order lists are retrieved from WoRMS and cached locally. "
                "After the first use of a broad group, browsing is much faster."
            )

    # --------------------------------------------------------
    # Taxonomy display + ecological fallback
    # --------------------------------------------------------
    if (selected_taxon or selected_family or selected_genus) and not selected_broad:
        st.error(
            "WoRMS taxonomy was resolved, but the record could not be mapped to a "
            "broad ED group. This taxon cannot be assigned an ED until its broad "
            "group is resolved."
        )

    if selected_taxon or selected_family or selected_genus:
        st.subheader("Resolved taxonomy")
        t1, t2, t3, t4, t5 = st.columns(5)
        t1.metric("Broad group", selected_broad or "—")
        t2.metric("Order", selected_order or "—")
        t3.metric("Family", selected_family or "—")
        t4.metric("Genus", selected_genus or "—")
        t5.metric("Exact taxon", selected_taxon or "—")
        st.caption(f"Taxonomy source: {taxonomy_source}")

    # --------------------------------------------------------
    # Strict ED fallback:
    # Exact taxon -> Genus -> Family -> Ecological proxy -> Broad group
    #
    # Ecological proxy is shown ONLY when no ED exists at
    # Exact taxon, Genus, or Family level.
    # --------------------------------------------------------
    tax_match = taxonomy_match_available(
        exact_taxon=selected_taxon,
        genus=selected_genus,
        family=selected_family,
    )

    USE_BROAD = "— No suitable ecological proxy: use broad-group ED —"

    if selected_broad and tax_match is None:
        proxy_options = available_proxy_groups(selected_broad, selected_family)

        if proxy_options:
            st.warning(
                "No ED is available at Exact taxon, Genus, or Family level. "
                "Select the closest ecological energy proxy. "
                "If none is appropriate, choose the broad-group fallback option."
            )

            proxy_choice = st.selectbox(
                "Ecological energy proxy",
                proxy_options + [USE_BROAD],
                index=None,
                placeholder="Choose the closest ecological role",
                help=(
                    "This field appears only because no Exact-taxon, Genus, "
                    "or Family ED is available."
                ),
            )

            if proxy_choice == USE_BROAD:
                selected_proxy = ""
                final_match = match_ed(
                    exact_taxon="",
                    genus="",
                    family="",
                    energy_proxy_group="",
                    broad_group=selected_broad,
                )
            elif proxy_choice:
                selected_proxy = proxy_choice
                final_match = match_ed(
                    exact_taxon="",
                    genus="",
                    family="",
                    energy_proxy_group=selected_proxy,
                    broad_group=selected_broad,
                )
            else:
                selected_proxy = ""
                final_match = None

        else:
            # No ecological proxy exists in the DB for this broad group.
            # Fall back automatically to the broad-group ED.
            selected_proxy = ""
            st.info(
                "No ecological energy proxy is available for this taxon. "
                "Broad taxonomic group ED will be used."
            )
            final_match = match_ed(
                exact_taxon="",
                genus="",
                family="",
                energy_proxy_group="",
                broad_group=selected_broad,
            )

    elif tax_match is not None:
        # Better taxonomic match exists: use it directly and do not show
        # any ecological-proxy selector.
        selected_proxy = ""
        final_match = tax_match

    else:
        selected_proxy = ""
        final_match = None

    if final_match:
        final_match.update(
            validation_note_for_match(
                final_match,
                selected_broad,
                selected_proxy,
            )
        )

    st.subheader("Prey measurement")
    m1, m2, m3 = st.columns(3)
    with m1:
        life_stage = st.selectbox(
            "Life stage",
            ["Unknown", "Larva", "Juvenile", "Adult", "Mixed", "Larva/Pupa"],
        )
    with m2:
        count = st.number_input("Count", min_value=0, value=1, step=1)
    with m3:
        wet_mass = st.number_input(
            "Wet mass (g)",
            min_value=0.0,
            value=0.0,
            step=0.001,
            format="%.3f",
        )

    st.subheader("Energy-density match")

    if final_match:
        estimated_energy = wet_mass * final_match["ed"]

        effective_min = (
            final_match["ed_min"]
            if final_match["ed_min"] is not None
            else final_match["ed"]
        )
        effective_max = (
            final_match["ed_max"]
            if final_match["ed_max"] is not None
            else final_match["ed"]
        )

        estimated_energy_min = wet_mass * effective_min
        estimated_energy_max = wet_mass * effective_max

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Match level", final_match["level"])
        k2.metric("ED", f'{final_match["ed"]:.3f} kJ/g WW')
        k3.metric("Estimated energy", f"{estimated_energy:.3f} kJ")
        k4.metric(
            "Evidence",
            final_match.get("evidence_class") or "—",
        )

        range_text = "—"
        if (
            final_match["ed_min"] is not None
            and final_match["ed_max"] is not None
        ):
            range_text = (
                f'{final_match["ed_min"]:.3f}–'
                f'{final_match["ed_max"]:.3f} kJ/g WW'
            )

        st.info(
            f"**Matched taxon/group:** {final_match['name']}  \n"
            f"**Available ED range:** {range_text}  \n"
            f"**Estimated energy range:** "
            f"{estimated_energy_min:.3f}–"
            f"{estimated_energy_max:.3f} kJ  \n"
            f"**Source:** {final_match['source'] or '—'}  \n"
            f"**Review:** {final_match['review'] or '—'}"
        )

        if final_match.get("validation_note"):
            st.caption(
                "Validation reference: "
                + final_match["validation_note"]
            )

        if final_match["level"] != "Exact taxon":
            st.caption(
                "Fallback ED is an estimate. Validation statistics are "
                "reference information from the current database and do "
                "not automatically replace the selected hierarchy level."
            )
    else:
        estimated_energy = None
        estimated_energy_min = None
        estimated_energy_max = None

        if selected_broad and tax_match is None and not selected_proxy:
            st.warning(
                "No taxonomic ED match. Select an ecological energy proxy to continue."
            )
        else:
            st.warning("No ED match is currently available.")

    if st.button("➕ Add prey item", type="primary", width="stretch"):
        problems = []
        if not clean(predator):
            problems.append("Predator species is required.")
        if not clean(specimen):
            problems.append("Specimen ID is required.")
        if not clean(selected_taxon):
            problems.append("A prey scientific name / exact taxon is required.")
        if wet_mass <= 0:
            problems.append("Wet mass must be greater than 0 g.")
        if final_match is None:
            problems.append("No ED could be assigned.")

        if problems:
            for p in problems:
                st.error(p)
        else:
            st.session_state.records.append(
                {
                    "Row_ID": st.session_state.next_id,
                    "Predator_species": clean(predator),
                    "Specimen_ID": clean(specimen),
                    "Broad_taxonomic_group": selected_broad,
                    "Order": selected_order,
                    "Family": selected_family,
                    "Genus": selected_genus or infer_genus(selected_taxon),
                    "Prey_taxon": selected_taxon,
                    "Life_stage": life_stage,
                    "Ecological_energy_proxy": selected_proxy,
                    "Count": int(count),
                    "Prey_wet_mass_g": float(wet_mass),
                    "ED_lookup_key": final_match["key"],
                    "Match_level": final_match["level"],
                    "Matched_taxon_or_group": final_match["name"],
                    "Energy_density_kJ_g_WW": final_match["ed"],
                    "Available_ED_min": final_match["ed_min"],
                    "Available_ED_max": final_match["ed_max"],
                    "Estimated_energy_kJ": float(estimated_energy),
                    "Estimated_energy_min_kJ": float(estimated_energy_min),
                    "Estimated_energy_max_kJ": float(estimated_energy_max),
                    "Estimated_energy_kcal": float(estimated_energy / 4.184),
                    "Evidence_class": final_match.get("evidence_class"),
                    "Validation_n": final_match.get("validation_n"),
                    "Validation_MAE_kJ_g": final_match.get("validation_mae"),
                    "Validation_MAPE_pct": final_match.get("validation_mape"),
                    "Validation_note": final_match.get("validation_note"),
                    "Primary_source": final_match["source"],
                    "Review_flag": final_match["review"],
                    "Taxonomy_source": taxonomy_source,
                }
            )
            st.session_state.next_id += 1
            st.success("Prey item added.")


with results_tab:
    st.subheader("Current dataset")
    result = with_contributions(st.session_state.records)

    if result.empty:
        st.info("No prey items have been added.")
    else:
        visible = [
            "Row_ID","Predator_species","Specimen_ID","Prey_taxon","Order","Family","Genus",
            "Count","Prey_wet_mass_g","Match_level","Energy_density_kJ_g_WW",
            "Estimated_energy_kJ","Estimated_energy_min_kJ","Estimated_energy_max_kJ",
            "Within_stomach_weight_pct","Within_stomach_energy_pct",
            "Within_stomach_energy_pct_lower","Within_stomach_energy_pct_upper",
            "Evidence_class","Validation_n","Validation_MAE_kJ_g","Primary_source",
        ]
        st.dataframe(result[visible], width="stretch", hide_index=True)

        st.subheader("Prey summary")
        summary = prey_summary(result)
        st.dataframe(summary, width="stretch", hide_index=True)
        st.caption("Energy_pct_lower_bound and Energy_pct_upper_bound are conservative ED-range sensitivity bounds, not confidence intervals.")

        c1, c2, c3 = st.columns([2, 2, 3])
        with c1:
            row_to_delete = st.selectbox(
                "Delete Row_ID",
                sorted(result["Row_ID"].tolist()),
                index=None,
            )
            if st.button("Delete selected row", width="stretch"):
                if row_to_delete is not None:
                    st.session_state.records = [
                        r for r in st.session_state.records
                        if r["Row_ID"] != row_to_delete
                    ]
                    st.rerun()

        with c2:
            if st.button("Clear all", width="stretch"):
                st.session_state.records = []
                st.session_state.next_id = 1
                st.rerun()

        with c3:
            st.download_button(
                "📥 Download results as Excel",
                data=export_excel(result, summary),
                file_name="prey_energy_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )


with db_tab:
    st.subheader("Local energy-density database")

    search = st.text_input(
        "Search taxon / family / genus",
        placeholder="e.g., Engraulis",
        key="db_search",
    ).strip()

    view = energy_db.copy()
    if search:
        mask = (
            view["Taxon_name"].astype(str).str.contains(search, case=False, na=False)
            | view["Family_standardized"].astype(str).str.contains(search, case=False, na=False)
            | view["Genus_standardized"].astype(str).str.contains(search, case=False, na=False)
        )
        view = view[mask]

    cols = [
        "Taxon_name","Broad_taxonomic_group","Taxonomic_subgroup","Energy_proxy_group",
        "Family_standardized","Genus_standardized","ED_representative_kJ_g_WW",
        "ED_min","ED_max","Source_short","Source_detail","QC_flag",
    ]
    st.dataframe(view[cols], width="stretch", hide_index=True)
    st.caption(f"{len(view):,} / {len(energy_db):,} records")


with validation_tab:
    st.subheader("Internal validation")

    actual = validation_reference.get("actual_hierarchy", {})
    if actual:
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Validation targets", f"{actual.get('targets', 0)}")
        a2.metric("Fallback coverage", f"{actual.get('coverage_pct', 0):.1f}%")
        a3.metric("Overall MAE", f"{actual.get('mae_kJ_g', 0):.3f} kJ/g")
        a4.metric("Overall MAPE", f"{actual.get('mape_pct', 0):.1f}%")

    st.info(
        "Final PECC hierarchy: Exact taxon > Genus > Family > "
        "Ecological energy proxy > Broad taxonomic group."
    )

    st.warning(
        "Validation is internal to the current ED database. "
        "It supports reporting fallback uncertainty but does not establish "
        "a universal accuracy ranking across all taxonomic and ecological levels."
    )

    selected_rows = []
    for level, stats in validation_reference.get(
        "selected_level_metrics", {}
    ).items():
        selected_rows.append({"Level": level, **stats})

    if selected_rows:
        st.markdown("**Performance when each fallback level was actually selected**")
        st.dataframe(
            pd.DataFrame(selected_rows),
            width="stretch",
            hide_index=True,
        )

    forced_rows = []
    for level, stats in validation_reference.get(
        "forced_level_metrics", {}
    ).items():
        forced_rows.append({"Level": level, **stats})

    if forced_rows:
        st.markdown("**Forced-level validation**")
        st.dataframe(
            pd.DataFrame(forced_rows),
            width="stretch",
            hide_index=True,
        )

    rv = validation_reference.get("revalidation_of_auto_switch", {})
    if rv:
        st.markdown("**Why PECC does not auto-switch Proxy and Broad**")
        original = rv.get("original_hierarchy", {})
        rejected = rv.get("rejected_auto_switch", {})
        r1, r2 = st.columns(2)

        with r1:
            st.metric(
                "Final hierarchy MAE",
                f"{original.get('mae_kJ_g', 0):.3f} kJ/g",
            )
            st.caption(
                f"RMSE {original.get('rmse_kJ_g', 0):.3f}; "
                f"MAPE {original.get('mape_pct', 0):.1f}%"
            )

        with r2:
            st.metric(
                "Tested auto-switch MAE",
                f"{rejected.get('mae_kJ_g', 0):.3f} kJ/g",
            )
            st.caption(
                f"RMSE {rejected.get('rmse_kJ_g', 0):.3f}; "
                f"MAPE {rejected.get('mape_pct', 0):.1f}%"
            )

        st.caption(
            f"Paired Wilcoxon P = {rv.get('wilcoxon_p', float('nan')):.3f}. "
            "The automatic switch was rejected because it did not improve "
            "aggregate prediction performance."
        )

    group_rows = validation_reference.get(
        "lower_fallback_group_reference", []
    )
    if group_rows:
        st.markdown("**Lower-fallback group reference**")
        st.dataframe(
            pd.DataFrame(group_rows),
            width="stretch",
            hide_index=True,
        )

    st.caption(
        "Group-level Proxy/Broad comparisons are displayed only as reference. "
        "They never automatically override the ecological proxy chosen by the researcher."
    )


with method_tab:
    st.subheader("Final ED assignment workflow")
    st.write(
        "PECC applies the most specific available taxonomic ED first. "
        "An ecological proxy is requested only when Exact-taxon, Genus, "
        "and Family ED values are all unavailable. Broad-group ED is used "
        "only when no suitable ecological proxy is available."
    )

    st.code(
        "Exact taxon > Genus > Family > Ecological energy proxy > Broad taxonomic group",
        language=None,
    )

    st.subheader("Why validation does not automatically change the hierarchy")
    st.write(
        "Internal leave-one-taxon-out validation was used to quantify fallback error. "
        "A separate validation-informed Proxy/Broad auto-switch was tested, but it "
        "slightly increased MAE, RMSE, and MAPE and did not significantly improve "
        "paired absolute errors. Therefore PECC v1.0.0 retains the biologically "
        "interpretable hierarchy and displays validation statistics as evidence "
        "and uncertainty information only."
    )

    st.subheader("Energy calculation")
    st.latex(r"E_{ij}=W_{ij}\times ED_j")
    st.latex(
        r"\%E_{ij}=\frac{E_{ij}}{\sum_j E_{ij}}\times100"
    )

    st.write(
        "Calculated values represent estimated potential energetic "
        "contributions of stomach contents, not assimilated or metabolizable energy."
    )

    st.subheader("ED-range sensitivity")
    st.write(
        "When minimum and maximum ED values are available, PECC also calculates "
        "minimum and maximum estimated energy. Lower and upper %E values are "
        "conservative scenario bounds obtained from the available ED range. "
        "They are not statistical confidence intervals."
    )

    st.subheader("Taxonomy service")
    st.write(
        "Scientific-name resolution and taxonomic Order/Family/Genus information "
        "can be obtained from WoRMS. Resolved records are cached locally in "
        "worms_taxonomy_cache.csv."
    )

    st.subheader("References")
    st.dataframe(
        references,
        width="stretch",
        hide_index=True,
    )
