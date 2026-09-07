# Prey Energy Contribution Calculator (PECC)

**PECC v1.0.0** is a literature-derived prey energy-density (ED) database and software workflow for estimating the energetic contribution of prey in fish stomach-content studies.

Associated manuscript (in preparation):

> **A literature-derived prey energy-density database and hierarchical framework for estimating energetic contributions in fish stomach-content studies**

## What PECC does

PECC combines prey wet mass with literature-derived ED values (kJ g⁻¹ wet weight) and applies a fixed fallback hierarchy when a direct taxon-specific ED value is unavailable:

**Exact taxon → Genus → Family → Ecological energy proxy → Broad taxonomic group**

For prey taxon *i*:

**Energyᵢ = Wᵢ × EDᵢ**

and

**Energetic contributionᵢ (%) = Energyᵢ / ΣEnergy × 100**

PECC is intended to complement conventional stomach-content metrics such as %N, %W, %F, and %IRI. It estimates potential energetic contribution from ingested prey and is not a complete predator bioenergetics model.

## Reference database

The frozen PECC v1.0.0 reference library contains:

- **187** literature-derived ED records
- **384** lookup/default entries
- ED standardized to **kJ g⁻¹ wet weight (WW)**
- taxonomic and ecological metadata supporting hierarchical assignment

The database used by the application is:

`data/prey_energy_db_v1_0_0.xlsx`

The workbook includes the reference library, lookup defaults, classification map, quality-control information, references, and summary sheets.

## Validation

### Leave-one-taxon-out validation

The frozen v1.0.0 hierarchy was evaluated across 128 species-level targets. After removing each target taxon and rebuilding fallback values, a fallback prediction was available for 127/128 targets (99.2%).

| Metric | Result |
|---|---:|
| Targets | 128 |
| Predictions | 127 / 128 |
| Coverage | 99.2% |
| MAE | 1.015 kJ g⁻¹ WW |
| RMSE | 1.418 kJ g⁻¹ WW |
| MAPE | 22.06% |

Genus-level substitutions had MAE = **0.761 kJ g⁻¹ WW** when that level was selected.

### Leave-one-source-out validation

| Analysis | Coverage | MAE | RMSE | MAPE |
|---|---:|---:|---:|---:|
| Overall | 129/133 (97.0%) | 1.125 | 1.557 | 26.99% |
| Fallback-only | 119/123 (96.7%) | 1.097 | 1.485 | 27.47% |

### Independent external evaluation

The strict fallback-only external evaluation contained **1,082 publication–taxon units**, representing **782 taxa from 77 independent publications**. Ecological-proxy assignment was not externally evaluated because ecological-proxy membership could not be reconstructed objectively from the external source data.

| Metric | Result |
|---|---:|
| MAE | 1.607 kJ g⁻¹ WW |
| RMSE | 2.048 kJ g⁻¹ WW |
| MAPE | 57.84% |
| MdAPE | 32.09% |
| Calibration slope | 0.354 |

These results should be interpreted as evaluation of taxonomic and broad-group fallback transferability rather than validation of every PECC pathway.

## Quick start

### Windows

1. Install 64-bit Python (the supplied Windows launcher/build workflow was tested around Python 3.13).
2. Clone or download this repository.
3. Double-click `start_app.bat`.
4. On first run, the script creates `.venv` and installs the required Python packages.
5. Open the local Streamlit address shown in the console if a browser does not open automatically.

The ED database and calculations are local. WoRMS scientific-name/taxonomy lookup requires an internet connection; resolved taxonomy is cached locally.

### Command line

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Repository structure

```text
prey-energy-contribution-calculator/
├── app.py
├── launcher.py
├── self_test.py
├── start_app.bat
├── requirements.txt
├── README.md
├── CITATION.cff
├── CHANGELOG.md
├── LICENSE_SELECTION_REQUIRED.md
├── data/
│   ├── prey_energy_db_v1_0_0.xlsx
│   └── README.md
├── validation/
│   ├── validation_reference.json
│   ├── Supplementary_Data_S1_PECC_v1_0_0_Reference_Library.xlsx
│   ├── Supplementary_Data_S2_Leave_One_Taxon_Out.xlsx
│   ├── Supplementary_Data_S3_Leave_One_Source_Out.xlsx
│   ├── Supplementary_Data_S4_Nested_Holdout_and_Baseline.xlsx
│   ├── Supplementary_Data_S5_Independent_External_Evaluation.xlsx
│   ├── Supplementary_Data_S5_Independent_External_Evaluation.csv
│   └── Supplementary_Data_S6_Empirical_Application.xlsx
├── reproducibility/
│   ├── PECC_Fig2_and_Fig4_Reproducible_Plots.R
│   ├── Fig3_External_Evaluation_FINAL.R
│   └── figure input files
├── build/
│   └── windows/
│       ├── BUILD_EXE_PORTABLE.bat
│       ├── BUILD_EXE_SINGLE_FILE.bat
│       └── build_requirements.txt
└── docs/
    ├── USER_GUIDE.md
    └── WINDOWS_BUILD.md
```

## Reproducing manuscript figures

The `reproducibility/` folder contains R scripts and the corresponding frozen input files. The scripts have been made repository-relative; no user-specific absolute path is required.

- `PECC_Fig2_and_Fig4_Reproducible_Plots.R` reproduces the internal/source-held-out and empirical-application plots from the included Excel inputs.
- `Fig3_External_Evaluation_FINAL.R` reproduces the independent external-evaluation figure from `Fig3_input_external_fallback_only_1082.csv`.

Outputs are written to `reproducibility/PECC_Figures_R/`.

## Self-test

The supplied `self_test.py` checks key frozen v1.0.0 invariants, including the 187-record database, 384 lookup entries, selected fallback values, and validation coverage.

```bash
python self_test.py
```

## Reproducibility and interpretation

When reporting PECC results, retain the assignment level used for each prey item. Literature-derived ED values can vary among species, individuals, seasons, life stages, regions, size classes, and analytical methods. Direct measurements from the study population should be preferred when reliable study-specific ED values are available.

ED min–max propagation in the application represents a sensitivity range, not a statistical confidence interval.

## Citation

Software citation metadata are provided in [`CITATION.cff`](CITATION.cff). The manuscript citation and Zenodo DOI should be added after publication/deposit.

## Author

**Joon-Young Son**  
Department of Marine Biology and Aquaculture  
College of Marine Science  
Gyeongsang National University  
Tongyeong 53064, Republic of Korea  
ORCID: https://orcid.org/0009-0004-0145-1468

## License

No open-source or data license has yet been selected for this release candidate. See [`LICENSE_SELECTION_REQUIRED.md`](LICENSE_SELECTION_REQUIRED.md) before formal public release. Third-party literature sources retain their original rights and licensing conditions.
