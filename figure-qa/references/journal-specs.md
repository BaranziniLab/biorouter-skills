<!-- Translated from Chinese for Biorouter from Haojae/scipilot-figure-skill references/journal_specs.md (MIT, commit 43098ddb9e6a). Changes: translated to English; references to scipilot's setup_style.py replaced with plain matplotlib settings. Journal rules change: confirm against the journal's current author guide. See LICENSE-UPSTREAM. -->

# Journal figure specifications

A summary of the hard requirements major journals set for submitted figures. **Check the target journal before plotting**: note the column width, font size, DPI, preferred font and preferred vector format, then open matplotlib (or ggplot2).

## Contents

- [Nature journals](#nature-journals)
- [Science](#science)
- [IEEE](#ieee)
- [Elsevier journals](#elsevier-journals)
- [PNAS](#pnas)
- [Chinese core journals](#chinese-core-journals)
- [Quick comparison](#quick-comparison)
- [Installing Chinese fonts](#installing-chinese-fonts)

---

## Nature journals

Covers *Nature*, *Nature Methods*, *Nature Communications*, *Nature Machine Intelligence* and the other Nature titles.

| Item | Requirement |
|---|---|
| Single column | **89 mm ≈ 3.5 in** |
| Double column | **183 mm ≈ 7.2 in** |
| Maximum height | 247 mm ≈ 9.7 in (no more than one page) |
| Font size | labels and ticks 5 to 7 pt, never below 5 pt |
| Preferred font | **Helvetica or Arial** (sans serif) |
| Preferred vector | **EPS**, PDF, AI |
| Raster | TIFF or PNG, **at least 300 DPI**; colour figures in RGB; line art at least 600 DPI |
| Line width | 0.25 to 1 pt (matplotlib's default 1 pt is on the heavy side; 0.6 is suggested) |
| Colour | RGB; colour-blind safe; avoid red against green |
| Panel labels | **a, b, c** (lower case, bold, top left) |

**Pitfall**: Nature insists that figures are made at final size; the submission system checks font sizes in millimetres.

Reference: [Nature formatting guide](https://www.nature.com/nature/for-authors/formatting-guide)

---

## Science

| Item | Requirement |
|---|---|
| Single column | **55 mm ≈ 2.2 in** (very narrow) |
| 1.5 columns | **120 mm ≈ 4.7 in** |
| Double column | **183 mm ≈ 7.2 in** |
| Font size | 5 to 7 pt |
| Preferred font | **Helvetica or Arial** |
| Preferred vector | PDF, EPS, AI |
| Raster | TIFF or PNG, **at least 300 DPI**; 600 suggested for line and grid figures |
| Panel labels | **A, B, C** (upper case, bold, top left) |

**Pitfall**: the single column is very narrow (2.2 in). Squeezing all the data into it flattens the figure; 1.5 columns is usually the better choice.

---

## IEEE

Covers *Transactions on PAMI*, *Transactions on Image Processing* and conferences such as CVPR and ICCV.

| Item | Requirement |
|---|---|
| Single column | **3.5 in ≈ 88.9 mm** |
| Double column | **7.16 in ≈ 181.9 mm** |
| Font size | 8 to 10 pt |
| Preferred font | **Times New Roman** (serif); Helvetica or Arial are acceptable inside figures |
| Preferred vector | PDF, EPS |
| Raster | **600 DPI** (line art), 300 DPI (photographs and grayscale) |
| Readable in black and white | **Explicitly required**: categories in colour figures must stay distinguishable in grayscale |
| Panel labels | (a) (b) (c), lower case in parentheses |

**Pitfall**: IEEE is strict about **black-and-white readability**, because conference proceedings are often printed in black and white. Encoding every category three times (line style, marker and colour) is a must.

Reference: [IEEE Author Center, graphics](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-graphics-for-your-article/)

---

## Elsevier journals

Covers *Cell*, *Neuron*, *Cell Reports* and most Elsevier journals.

| Item | Requirement |
|---|---|
| Single column | **90 mm ≈ 3.54 in** |
| 1.5 columns | 140 mm ≈ 5.5 in |
| Double column | **190 mm ≈ 7.48 in** |
| Font size | 7 to 9 pt |
| Preferred font | Helvetica or Arial (sans serif) |
| Preferred vector | EPS, PDF |
| Raster | **300 DPI (colour and grayscale)**; line art 1000 DPI |
| Panel labels | (A) (B) (C), upper case in parentheses |
| Colour | RGB; colour-blind safe |

Reference: [Elsevier artwork guidelines](https://www.elsevier.com/authors/policies-and-guidelines/artwork-and-media-instructions)

---

## PNAS

| Item | Requirement |
|---|---|
| Single column | **8.7 cm ≈ 3.42 in** |
| 1.5 columns | **11.4 cm ≈ 4.5 in** |
| Double column | **17.8 cm ≈ 7.0 in** |
| Font size | 6 to 8 pt |
| Preferred font | Helvetica, Arial or Times (serif and sans serif both accepted) |
| Preferred vector | PDF, EPS |
| Raster | 300 DPI (colour), 600 DPI (black and white) |
| Panel labels | (A) (B) (C) |

---

## Chinese core journals

Applies to the *Science China* series, *Acta Physica Sinica*, the *National Medical Journal of China*, EI-indexed core journals and Chinese CCF B and C journals. **The journal's own author instructions decide**; what follows are the common conventions.

| Item | Common requirement |
|---|---|
| Single column | **8 cm ≈ 3.15 in** |
| Double column | **17 cm ≈ 6.7 in** |
| Font size | Chinese size 6 (≈ 8 pt) or small 5 (≈ 9 pt) |
| Font | **SimSun for Chinese, Times New Roman for Latin text and numbers**, mixed |
| Vector | EPS, PDF (some accept TIFF) |
| Raster | **at least 600 DPI** (line art), 300 DPI (photographs) |
| Colour | some journals accept only black and white; always read the author instructions |
| Panel labels | (a) (b) (c), or (甲) (乙) (丙), as in the journal's examples |

**Pitfall 1**: after upload, EPS previews from Chinese journals often show empty boxes. Use a serif CJK font (SimSun or Noto Serif CJK) for Chinese text and save as PDF rather than EPS (EPS handles TrueType Chinese fonts poorly).

**Pitfall 2**: numbers, variable names and units **must** use Times New Roman (a Latin serif font), not the Chinese SimSun; this is a typesetting rule.

---

## Quick comparison

| Journal | Single column (in) | Double column (in) | Font size (pt) | Preferred font | DPI | Preferred vector |
|---|---|---|---|---|---|---|
| Nature | 3.5 | 7.2 | 5–7 | Helvetica/Arial | 300+ | EPS/PDF |
| Science | 2.2 | 7.2 | 5–7 | Helvetica/Arial | 300+ | PDF/EPS |
| IEEE | 3.5 | 7.16 | 8–10 | Times | 600 | PDF/EPS |
| Elsevier | 3.54 | 7.48 | 7–9 | Helvetica/Arial | 300+ | EPS/PDF |
| PNAS | 3.42 | 7.0 | 6–8 | Helvetica/Times | 300+ | PDF/EPS |
| Chinese core | 3.15 | 6.7 | 8–9 | SimSun + TNR | 600 | PDF |

---

## Installing Chinese fonts

Look for a sans-serif CJK font in this order:

```
Noto Sans CJK SC  >  Source Han Sans SC  >  SimHei  >  Microsoft YaHei
```

and, for SimSun-style serif text:

```
Noto Serif CJK SC  >  Source Han Serif SC  >  SimSun  >  STSong
```

If none is installed, install one rather than accept empty boxes:

### Linux

```bash
# Debian / Ubuntu
sudo apt install fonts-noto-cjk fonts-noto-cjk-extra

# Fedora / RHEL / CentOS
sudo dnf install google-noto-sans-cjk-fonts google-noto-serif-cjk-fonts

# Then rebuild matplotlib's font cache
python -c "import matplotlib.font_manager; matplotlib.font_manager._load_fontmanager(try_read_cache=False)"
```

### macOS

```bash
# Recommended: Homebrew Cask
brew install --cask font-noto-sans-cjk-sc font-noto-serif-cjk-sc

# Or download from Google Fonts or Adobe
# https://fonts.google.com/noto/specimen/Noto+Sans+SC
```

macOS already ships PingFang SC, Heiti SC and Songti SC, which are enough.

### Windows

1. Download `Noto_Sans_CJK_SC.zip` from https://github.com/notofonts/noto-cjk/releases
2. Unzip it, select all the `.otf` and `.ttf` files, right-click and choose **Install for all users**
3. Restart Python, **or** delete matplotlib's cache:
   ```bash
   python -c "import matplotlib; print(matplotlib.get_cachedir())"
   # delete the fontlist*.json files in that folder
   ```

Windows already ships SimHei, SimSun and Microsoft YaHei, which are enough at a minimum.

### Checking

```bash
python -c "import matplotlib.font_manager as fm; print(sorted({f.name for f in fm.fontManager.ttflist if 'CJK' in f.name or 'Song' in f.name or 'Hei' in f.name}))"
```

This should list the CJK fonts available. If the list is empty, the cache has not been rebuilt: clear it as above and try again.

---

## Submission checking tools by journal

- **Nature**: the submission system checks DPI, size and font size automatically
- **IEEE**: [IEEE PDF eXpress](https://ieee-pdf-express.org/) checks that PDF fonts are embedded
- **Elsevier**: the submission system's PDF builder regenerates the PDF
- **arXiv**: lenient, but EPS or PDF files with unembedded fonts preview as boxes
