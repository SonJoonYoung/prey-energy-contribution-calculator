# Changelog

## [1.0.0] - 2026-09-07

### Added
- Initial PECC public-release repository structure.
- Frozen 187-record prey energy-density reference library and 384-entry lookup framework.
- Streamlit application, Windows launcher, self-test, and EXE build scripts.
- Internal, source-held-out, nested-holdout, independent external-evaluation, and empirical-application supplementary files.
- Portable R scripts and frozen figure inputs for manuscript reproducibility.
- Citation metadata and release documentation.

### Release-candidate cleanup
- Standardized source-code data paths to `data/prey_energy_db_v1_0_0.xlsx`.
- Standardized validation metadata path to `validation/validation_reference.json`.
- Removed a user-specific absolute Windows path from the external-evaluation R script.
- Updated figure scripts to use the filenames distributed in `reproducibility/`.
- Corrected stale aggregate `actual_hierarchy` values in `validation_reference.json` to match frozen Supplementary Data S2 (MAE 1.0145669; RMSE 1.4175328; MAPE 22.0580%). The database and fallback algorithm were not changed.
