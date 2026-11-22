# COBRApy model-checking checklist

> Absorbed from the former core skill `metabolic-modeling-cobrapy` (now a redirect to the systems-biology bundle). Biorouter original, Apache-2.0; no text was taken from third-party COBRApy skills.

Use this before trusting a flux prediction from a genome-scale model built or loaded with COBRApy.

- **Provenance.** Record the model file, its source (BiGG, BioModels, a reconstruction pipeline), version, and the namespace of metabolite and reaction ids.
- **Objective.** State the objective reaction and its direction (`model.objective`), and whether it matches the biology (growth, ATP maintenance, a product).
- **Medium.** Print `model.medium` and confirm exchange bounds. A model that grows on nothing, or on the wrong carbon source, has a medium error before it has a biology error.
- **Gene-protein-reaction rules.** Check that `AND` and `OR` rules parse, that knockouts go through `cobra.manipulation` or `model.genes.get_by_id(...).knock_out()`, and that isozymes are not treated as complexes.
- **Feasibility.** Run `model.optimize()` and read the status. `infeasible` or a growth rate of zero means stop and curate; do not interpret fluxes.
- **Alternative optima.** Use `cobra.flux_analysis.flux_variability_analysis` or parsimonious FBA before naming a single flux as the answer.
- **Reproducibility.** Pin the solver and the COBRApy version, and save the model state used for the result.

See `model-curation` for fixing a model and `gene-essentiality` for knockout screens.
