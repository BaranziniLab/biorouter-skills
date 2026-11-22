---
name: biomedical-imaging-pathology
description: Handle radiology and pathology images for research, from reading, inspecting and de-identifying DICOM with pydicom and finding public cancer imaging in NCI Imaging Data Commons, to whole-slide image tiling, tissue masks, stain normalisation and multiplex quantification with Histolab and PathML. Use for DICOM metadata or pixel data, CT, MR or PET series, IDC cohorts and downloads, H&E or IHC whole-slide images, tile datasets for deep learning, or OMERO image servers.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/pydicom, skills/imaging-data-commons, skills/pathml, skills/histolab)"
---

# Biomedical Imaging and Pathology

Medical images are data with obligations attached: patient identifiers in headers and burned
into pixels, per-collection licences, and acquisition parameters that change what the pixels
mean. This skill handles those before any analysis. The four guides under `references/` are
adapted from K-Dense Scientific Agent Skills (see `LICENSE-UPSTREAM`).

## Choose the path

| Task | Use | Guide |
| --- | --- | --- |
| Read, inspect, convert or write DICOM; transfer syntaxes and compression; multi-frame pixel data; private tags; de-identification review | pydicom with the pixel plugins the guide pins | `references/pydicom.md` |
| Find and download public cancer imaging (TCIA collections, CT, MR, PET, slide microscopy), query metadata with SQL, check licences and citations | NCI Imaging Data Commons through IDCAgent or `idc-index` | `references/imaging-data-commons.md` |
| Inspect whole-slide images, build tissue masks, extract tiles (random, grid, score-based), normalise H&E stains | Histolab with OpenSlide | `references/histolab.md` |
| Whole-slide pipelines with QC, h5path storage, multiplex immunofluorescence (CODEX, Vectra) quantification, cell graphs, HoVer-Net or HACTNet inference | PathML | `references/pathml.md` |
| Images held on a lab OMERO server | OMEROAgent, when installed and configured for that server | none |

Route elsewhere for:

- Fluorescence and light microscopy (cell segmentation, tracking, intensity measurement):
  `microscopy-image-analysis`.
- Neuro MRI organised as BIDS, and DICOM-to-BIDS conversion: `bids-neuroimaging`.
- Imaging mass cytometry: the `imaging-mass-cytometry` bundle.
- Training or evaluating classifiers on extracted tiles or features: `scientific-machine-learning`,
  or `clinical-ai-modeling` when the model predicts a clinical outcome.

## Protected health information comes first

Local clinical DICOM and slide files from a hospital are protected health information until
shown otherwise.

1. Work only on data the person is authorised to use, inside the environment approved for it.
   Do not upload clinical images to external services, including public model endpoints.
2. De-identify with a documented profile (the DICOM PS3.15 Basic Application Level
   Confidentiality Profile is the usual baseline): remove or replace identifying elements,
   handle dates consistently, regenerate UIDs with a recorded mapping, and remove private tags
   unless they are known to be safe (`references/pydicom/scripts/anonymize_dicom.py`,
   `references/pydicom/scripts/uid_mapping_validator.py`).
3. Headers are not the whole story: check for burned-in annotations on ultrasound, screen
   captures and secondary captures, and for labels and macro images in whole-slide files.
4. Audit the result, then have a person review it; automated de-identification is a draft
   (`references/pydicom/scripts/deidentification_audit.py`).

## Public data has licences too

IDC collections carry individual licences (mostly CC BY, some non-commercial) and citation
requirements. Before using a collection, read its licence and DOI from IDC, record them in the
project, and cite the collection and IDC itself in any output. The IDC guide's licensing
section (`references/imaging-data-commons/references/licensing_and_citation.md`) shows how.

## Image analysis rules

- **Know the physical scale.** Pixel spacing and slice thickness for radiology, microns per
  pixel and magnification for slides. Analyses that mix scans or slides at different spacing
  must resample deliberately.
- **Intensities need context.** CT uses Hounsfield units after applying rescale slope and
  intercept; MR intensities are not standardised across scanners; stain colour varies by lab,
  so normalise before comparing slides and validate the normalisation visually.
- **Split by patient, not by tile or slice.** Tiles from one slide or slices from one scan are
  not independent; a random tile split leaks the patient into the test set.
- **Keep provenance.** Record series and SOP instance UIDs (or slide ids), the tiling
  parameters and the mask settings for every derived dataset.

## In Biorouter

- IDCAgent, when installed, connects to the official hosted IDC MCP server for search and
  metadata, with no account needed; this skill holds the method and licence rules it follows.
- Run pydicom, Histolab and PathML with the Developer shell; OpenSlide and the Java tools PathML
  needs are native dependencies, so check the guide's installation section first. PathML itself
  is GPL-2.0 licensed, which matters if the project will redistribute code that imports it.
- Large tile datasets and their storage layout: `scientific-data-engineering`; GPU inference on
  Wynton: `ucsf-hpc`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/pydicom.md` | Datasets and sequences, UIDs and transfer syntaxes, pixel data and frames, compression, DICOM JSON, de-identification, helper CLIs |
| `references/imaging-data-commons.md` | IDC data model and index tables, SQL patterns, downloads, viewers, DICOMweb, BigQuery, licences and citations |
| `references/histolab.md` | Slide management, tissue masks, tile extraction strategies, filters and stain normalisation |
| `references/pathml.md` | Slide loading and tiling, preprocessing and QC, h5path, multiparametric imaging, graphs, model inference |
