---
name: bids-neuroimaging
description: Plan and audit BIDS neuroimaging datasets, derivatives, validation, metadata, and reproducible preprocessing. Use when users mention BIDS, fMRI, MRI, EEG/MEG/iEEG, DICOM conversion, dataset_description.json, participants.tsv, or neuroimaging derivatives.
user-invocable: true
license: Apache-2.0
---

# BIDS Neuroimaging

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills BIDS/neuroimaging patterns, rewritten under Apache-2.0.

## When to Use

Use this skill when work touches the Brain Imaging Data Structure or neuroimaging dataset organization. Pair with `biomedical-imaging-pathology` for DICOM/PACS and image QC, and with `neurophysiology-analysis` for EEG/MEG/iEEG signal analysis.

## Intake

Collect:

- Modality: MRI/fMRI/dMRI, PET, EEG, MEG, iEEG, or multimodal.
- Source data format and conversion path.
- Dataset scope: raw BIDS, derivatives, or both.
- Subject/session/task/run structure.
- Required metadata sidecars and privacy constraints.
- Intended pipeline: fMRIPrep, MRIQC, QSIPrep, MNE-BIDS, custom workflow, or archive deposit.

## BIDS Audit

Check:

- `dataset_description.json`, `participants.tsv`, README, CHANGES, and license files.
- Subject/session folder naming.
- Modality-specific filenames and entities.
- JSON sidecars for acquisition parameters, task metadata, channels, electrodes, events, and coordinate systems.
- Derivative `dataset_description.json` and source provenance.
- Defacing/de-identification and protected metadata removal.

## Validation Workflow

1. Run or plan `bids-validator` before analysis.
2. Separate warnings from errors and explain which affect inference.
3. Preserve conversion logs and DICOM/source provenance.
4. Check slice timing, phase encoding, intended-for fields, events timing, and channel metadata.
5. Confirm derivatives do not overwrite raw data.

## Quality Gates

Do not treat a dataset as analysis-ready unless:

1. Validation status is reported.
2. Known validator warnings are triaged.
3. Subject/session/task/run counts match expectations.
4. Metadata needed by the preprocessing tool is present.
5. Privacy/de-identification status is explicit.

## Output Shape

Return: dataset map, validation findings, required fixes, preprocessing route, and archive/readiness status.
