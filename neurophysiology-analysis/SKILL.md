---
name: neurophysiology-analysis
description: Analyse extracellular electrophysiology and physiological signals, from Neuropixels spike sorting and unit curation with SpikeInterface and Kilosort4 to ECG, heart-rate variability, EDA, respiration, PPG, EMG and EEG features with NeuroKit2, and conversion to Neurodata Without Borders (NWB). Use for spike sorting, drift correction, quality metrics, peak detection, HRV, event-locked epochs, multimodal signal alignment, or packaging recordings for DANDI.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/neurokit2, skills/neuropixels-analysis, skills/nwb-conversion)"
---

# Neurophysiology Analysis

Recorded signals carry their acquisition history: sampling rate, filters, clock, reference and
channel map. This skill keeps that history attached while signals become features, units and
shareable files. The three guides under `references/` are adapted from K-Dense Scientific Agent
Skills (MIT; see `LICENSE-UPSTREAM`).

## Identify the recording

Collect before processing:

- **Modality and device**: Neuropixels 1.0 or 2.0 (SpikeGLX or Open Ephys), other silicon
  probes, ECG, PPG, EDA, respiration, EMG, EOG or scalp EEG.
- **Sampling rate and units** for every stream, read from the file headers, plus any hardware
  filters already applied.
- **Clocks**: which device timestamps each stream, and the sync pulses or TTL events that tie
  them together.
- **Events**: stimulus onsets, trial structure and behaviour logs, with their own timebase.
- **Subject and session metadata** needed later for NWB (species, age, sex, session start time
  with time zone, experimenter, protocol).

## Choose the path

| Task | Use | Guide |
| --- | --- | --- |
| Load, preprocess, motion-correct and spike-sort Neuropixels or other probe recordings; quality metrics; curation; export to Phy | SpikeInterface with Kilosort4 (or a CPU sorter), UnitRefine for model-based curation | `references/neuropixels-analysis.md` |
| ECG peaks and HRV, EDA tonic and phasic decomposition, respiration rate and RSA, PPG, EMG onsets, EOG blinks, complexity indices | NeuroKit2 | `references/neurokit2.md` |
| Convert sessions to NWB with metadata and timestamps; validate with NWB Inspector before DANDI upload | NeuroConv and PyNWB | `references/nwb-conversion.md` |

The NWB guide's tested converter covers planar two-photon TIFF imaging plus behavioural
position CSV; other streams use the same NeuroConv pattern with the interface for that format,
and must be validated the same way.

Route elsewhere for:

- MRI, fMRI, and EEG/MEG datasets organised as BIDS: `bids-neuroimaging`.
- Forecasting future values of a physiological series: `general-time-series-forecasting`.
- Statistical comparison of extracted features across groups: `statistical-modeling-bayes`.
- Decoding or classification from neural features: `scientific-machine-learning`.

## Spike sorting rules

1. Look at the raw traces and the probe geometry before sorting; bad channels and noise bands
   are easier to see than to infer from metrics.
2. Apply preprocessing in a fixed, logged order (phase-shift correction for multiplexed
   Neuropixels ADCs, band-pass,
   bad-channel removal, common reference) and estimate drift before sorting; correct it if the
   drift map shows movement.
3. Record the sorter name, version and full parameters with the output; Kilosort4 results are
   not comparable across versions without that.
4. Curate with explicit, pre-stated thresholds (for example ISI violation ratio, presence
   ratio, amplitude cutoff, SNR) and keep the metric table. Model-based or visual curation is a
   second pass for borderline units, not a replacement for metrics.
5. Report how many units passed each criterion; "good units" without the criteria is not
   reproducible.

## Physiological signal rules

1. Inspect the raw signal and its sampling rate before cleaning
   (`references/neurokit2/scripts/inspect_signal.py`); a resampled or clipped signal changes every
   downstream index.
2. Keep cleaning, peak detection and artefact correction as separate, logged steps, and keep
   corrected peak indices so HRV can be recomputed.
3. HRV metrics depend on recording length: compare time-domain metrics only across equal
   durations, and do not report low-frequency power from windows shorter than about two
   minutes.
4. Epochs need a stated baseline window and an event table whose times share the signal's clock
   (`references/neurokit2/scripts/plan_epochs.py`).
5. These analyses are research measurements, not diagnosis. Do not interpret an individual's
   ECG or EEG clinically.

## Sharing

Convert to NWB with complete subject and session metadata, run NWB Inspector and fix every
critical and best-practice violation before upload to DANDI. Raw data layout and versioning
(DataLad for DANDI datasets) are covered in `scientific-data-engineering`.

## In Biorouter

Run pipelines with the Developer shell in a pinned environment. Kilosort4 needs an NVIDIA GPU:
use `ucsf-hpc` for a Wynton GPU job, and `gpu-compute-optimization` if a custom step is slow.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/neuropixels-analysis.md` | Loading, preprocessing, motion correction, Kilosort4, quality metrics, curation (threshold, UnitRefine, visual), export |
| `references/neurokit2.md` | ECG and HRV, EDA, RSP, PPG, EMG, EOG, EEG, epochs and events, complexity, signal processing |
| `references/nwb-conversion.md` | NeuroConv and PyNWB conversion, timebase alignment, schema validation, NWB Inspector, round-trip checks |
