---
name: social-science-text-as-data
description: Measure concepts in large text collections for social-science and health research, from corpus construction and preprocessing through dictionaries, supervised classifiers, topic models (STM, BERTopic), embeddings and text scaling to large language model annotation, with every measure validated against human-coded labels and its provenance kept. Use for coding speeches, news, social media, clinical or patient free text, open-ended survey answers or documents at scale, sentiment or stance, topic discovery, or checking whether an automated text measure is valid.
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite, no upstream text copied)"
---

# Social Science Text as Data

Text methods turn words into numbers, and the numbers are only as good as the evidence that they
measure what the paper says they measure. This skill makes validation part of every pipeline.
It is written for Biorouter and copies no upstream text; its traceability rules follow the same
pattern as `claim-evidence-integrity`: every measured value points back to the text it came from.

## Define the measurement task

Write down, before any modelling:

- **The concept** (stance on a policy, mention of a symptom, populist rhetoric, topic of a
  complaint) and a written definition with examples and counterexamples.
- **The unit**: document, paragraph, sentence, post, speaker turn. Results change with the unit.
- **The task type**: discovery (what themes exist), measurement (how much of a known concept),
  or prediction (which documents belong to a class).
- **The corpus and its frame**: what population of texts it represents, how it was collected,
  what is missing (deleted posts, paywalled articles, non-English text), and the dates covered.

## Choose the method

| Task | Methods | R | Python |
| --- | --- | --- | --- |
| Known concept, clear vocabulary | Dictionary or lexicon, validated on a labelled sample | `quanteda.dictionaries`, `tidytext` | custom lists, spaCy matchers |
| Known concept, nuanced language | Supervised classifier trained on human labels | `quanteda.textmodels`, `tidymodels` | scikit-learn, fine-tuned Transformers |
| Known concept, few labels | Zero- or few-shot LLM annotation, validated on a gold set | API clients | API clients, `transformers` |
| Unknown themes | Topic models with covariates; embedding-based clustering | `stm` | BERTopic, sentence-transformers plus clustering |
| Positions on a scale (left to right, for or against) | Text scaling (Wordfish, Wordscores), or supervised scaling | `quanteda.textmodels` | custom, or embeddings with anchors |
| Similarity, framing, semantic change | Word and sentence embeddings | `text2vec`, `conText` | gensim, sentence-transformers |

Prefer the simplest method that validates. A dictionary that agrees with human coders as well as
a fine-tuned model is easier to explain and reproduce.

## Build the gold standard first

1. Write a **codebook** for the concept (definition, decision rules, examples).
2. Sample documents for labelling **at random from the analysis corpus** (stratify if the concept
   is rare), separate from any examples used to design prompts or features.
3. Have **two or more people label independently**; report agreement (Krippendorff's alpha or
   Cohen's kappa) and resolve disagreements by discussion recorded in the codebook.
4. Hold out part of the gold set as a **final test set** that no model or prompt is tuned on.

## Validate every measure

- **Against the gold set**: precision, recall and F1 per class (and per subgroup of documents
  where errors could differ: source, time period, language variety, dialect), with intervals.
- **Face validity**: read the top-scoring and borderline documents for each class or topic; a
  topic is not named until its top documents are read, not just its top words.
- **Convergent and predictive validity**: does the measure move with things it should (known
  events, other measures, expert ratings)?
- **Stability**: topic models and clustering vary with seeds and the number of topics; compare
  runs and report the choice of K with held-out likelihood, coherence and exclusivity, plus
  interpretability.
- **Preprocessing sensitivity**: stemming, stop words, n-grams and frequency cut-offs change
  results; show the main result under reasonable alternatives.

## Large language model annotation

- Use a model approved for the data: patient text or other sensitive material only through a
  private, institutionally hosted model, never a public endpoint.
- Pin the exact model and version, the prompt (in a versioned file), temperature (usually 0) and
  the output schema; store raw responses with the document ids.
- Validate on the held-out gold set exactly as for any classifier, and report agreement with
  humans beside agreement between humans.
- Watch for systematic errors (dialect, sarcasm, long documents, negation) and for the model
  echoing words from the prompt. Re-validate whenever the model or prompt changes.
- Quotes or spans an LLM extracts must be checked verbatim against the source text.

## Traceability

Keep a table linking every document id to its source, collection date, preprocessing version and
each derived measure, so any number in a figure can be traced to the texts behind it. Store
labelled data, codebook, prompts and model outputs with the project; `replication-package-audit`
checks that the pipeline reruns. Respect copyright and platform terms when storing and sharing
text; share ids and derived measures when the text itself cannot be shared.

## Reporting

Describe the corpus and its frame, the unit, preprocessing, the method and its settings, the gold
standard (size, sampling, coders, agreement), validation results per class, sensitivity analyses,
and limitations of coverage. Interpret results at the level the validation supports.

## Related skills

- `qualitative-thematic-analysis` for close reading and interpretive coding of smaller corpora,
  and for building the codebook.
- `scientific-machine-learning` for classifier training and evaluation mechanics, and
  `hugging-science-resource-discovery` for choosing pretrained models.
- `statistical-modeling-bayes` or `econometrics-toolkit` for downstream models that use the text
  measures as variables, with measurement error carried through.
- `claim-evidence-integrity` for checking that statements in the paper match the measured results.
