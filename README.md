# Prey Energy Contribution Calculator (PECC)

**Prey Energy Contribution Calculator (PECC)** is a framework for estimating the energetic contribution of prey identified in fish stomach-content studies using literature-derived prey energy-density (ED) data and a hierarchical assignment procedure.

PECC was developed to complement conventional stomach-content indices, such as numerical, gravimetric, frequency-of-occurrence, and Index of Relative Importance (%IRI) approaches, by incorporating differences in the energetic value of prey.

---

## Overview

Conventional diet analyses generally quantify prey importance based on abundance, weight, occurrence, or combinations of these metrics. However, prey taxa with similar wet weights may provide substantially different amounts of energy.

PECC estimates energetic prey contributions by combining prey wet weight with energy-density values expressed as:

**kJ g⁻¹ wet weight**

When a direct energy-density value is unavailable for a prey taxon, PECC applies a hierarchical assignment framework to identify an appropriate substitute.

---

## Hierarchical energy-density assignment

PECC assigns prey energy density using the following hierarchy:

1. **Exact taxon match**
2. **Genus-level match**
3. **Family-level match**
4. **Ecological energy proxy**
5. **Broad taxonomic group**

This approach allows energetic contributions to be estimated even when species-specific energy-density measurements are unavailable.

For cases without a taxonomic ED match, an ecological energy proxy can be selected based on the biological and ecological characteristics of the prey.

---

## Prey energy-density database

The current PECC database contains:

- **187 literature-derived energy-density records**
- Energy density standardized to **kJ g⁻¹ wet weight**
- Taxonomic and ecological information used for hierarchical ED assignment
- **384 lookup/default entries** generated for the PECC assignment framework

The database is intended to provide a transparent and reproducible basis for energetic interpretation of fish stomach-content data.

---

## Validation

The hierarchical energy-density assignment framework was evaluated using leave-one-taxon-out validation.

Species-level taxa with observed energy-density information were sequentially removed from the database and their energy densities were re-estimated using the remaining hierarchical information.

### Leave-one-taxon-out validation

| Metric | Result |
|---|---:|
| Species evaluated | 128 |
| Predictions obtained | 127 / 128 |
| Coverage | 99.2% |
| MAE | 1.015 kJ g⁻¹ |
| RMSE | 1.418 kJ g⁻¹ |
| MAPE | 22.06% |

Genus-level substitutions showed relatively low prediction error, with an MAE of approximately **0.761 kJ g⁻¹**.

These validation results characterize the predictive performance of the hierarchical fallback framework when direct species-level energy-density information is unavailable.

---

## Energetic contribution

For prey taxon *i*, energetic content can be calculated from prey wet weight and assigned energy density:

**Energyᵢ = Wᵢ × EDᵢ**

where:

- **Wᵢ** = wet weight of prey taxon *i* (g)
- **EDᵢ** = assigned energy density of prey taxon *i* (kJ g⁻¹ wet weight)

The proportional energetic contribution is then calculated as:

**Energetic contributionᵢ (%) = Energyᵢ / ΣEnergy × 100**

This provides an energy-based complement to conventional measures of dietary importance.

---

## Intended applications

PECC is designed for applications including:

- Fish stomach-content analysis
- Feeding ecology
- Trophic ecology
- Predator–prey studies
- Bioenergetic interpretation of diet composition
- Comparison between conventional prey-importance indices and energy-based contributions

---

## Repository contents

This repository will contain the PECC software, prey energy-density database, example datasets, documentation, and validation materials.

The repository is being organized to include:

```text
prey-energy-contribution-calculator/
├── README.md
├── CITATION.cff
├── requirements.txt
├── pecc/
├── data/
├── examples/
├── validation/
└── docs/
