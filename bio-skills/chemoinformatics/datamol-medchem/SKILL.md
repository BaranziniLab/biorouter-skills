---
name: chemoinformatics-datamol-medchem
description: Use Datamol and MedChem for medicinal chemistry preprocessing, standardization, scaffold handling, salt/tautomer cleanup, rule-based filtering, library curation, and molecule set inspection. Use when RDKit workflows need production-grade compound hygiene before descriptors, QSAR, docking, or screening.
tool_type: python
primary_tool: datamol
user-invocable: false
license: Apache-2.0
---

# Datamol and MedChem Compound Hygiene

Use this before modeling or docking when molecules arrive from vendor libraries, SDF files, SMILES tables, or assay exports.

## Required Checks

- Parse failures and invalid valence.
- Duplicate structures after canonicalization.
- Salt/solvent stripping policy.
- Tautomer and charge normalization.
- Stereochemistry retention or removal policy.
- Assay-incompatible molecules: metals, mixtures, polymers, extreme molecular weight.
- PAINS/reactive/toxicophore flags when appropriate.

## Workflow

1. Read molecules with Datamol/RDKit and keep original IDs.
2. Standardize structures in a reversible, logged step.
3. Deduplicate by canonical SMILES or InChIKey.
4. Apply project-specific filters rather than a generic "druglike" filter.
5. Export both kept and rejected molecules with reasons.
6. Hand off curated molecules to descriptors, QSAR, docking, or similarity search.

## Output Contract

Return counts for input, parsed, standardized, deduplicated, filtered, and retained molecules. Never drop compounds silently.

## Related Skills

- `chemoinformatics/molecular-io`
- `chemoinformatics/molecular-descriptors`
- `chemoinformatics/virtual-screening`
