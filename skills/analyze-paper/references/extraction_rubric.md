# Academic Paper Extraction & Classification Rubric (P-M-D-M Framework)

This rubric governs how the agent extracts, classifies, and verifies information from research papers for the `/analyze-paper` skill.

---

## Core Anti-Hallucination & Grounding Principles

1. **Strict Evidence Citations**:
   - Every item in `problem`, `methods`, `datasets`, `metrics`, and `experimental_results` **must** carry an `evidence_location` string pointing to the exact section, page, table, figure, or equation in the source paper (e.g., `"Section 3.2, Eq. 5, p. 4"` or `"Table 2, p. 7"`).
2. **Explicit vs. Inferred Distinction**:
   - If a detail (such as dataset split size or compute hardware) is not stated in the paper, explicitly record `"Not specified in paper"` rather than guessing from common benchmarks.
3. **Canonical Naming + Paper Alias**:
   - When a paper uses an abbreviated name for a dataset or metric, include both the canonical name and abbreviation (e.g., `"ImageNet-1K (ILSVRC 2012)"`, `"Peak Signal-to-Noise Ratio (PSNR)"`).

---

## Pillar 1: Problem Classification (`problem`)

Classify the problem along three dimensions:
1. **Hierarchy**:
   - `broad_domain`: Top-level research area (e.g., `Computer Vision`, `Natural Language Processing`, `Machine Learning Theory`, `Distributed Systems`, `Computational Biology`, `Robotics`, `Quantitative Finance`).
   - `specific_task`: Concrete task solved (e.g., `Monocular Depth Estimation`, `Retrieval-Augmented Generation`, `Byzantine Fault-Tolerant Consensus`).
2. **Problem Type Badges (`problem_type_badges`)**:
   Assign 1–4 taxonomy badges that characterize *what kind* of research problem this is:
   - `New Task / Problem Formulation`: Introduces a previously unstudied task.
   - `Accuracy / SOTA Push`: Improves predictive quality on an established task.
   - `Efficiency / Latency / Memory`: Reduces compute, parameters, or runtime complexity.
   - `Generalization / OOD / Robustness`: Addresses domain shift, adversarial noise, or scarcity.
   - `New Benchmark / Dataset Creation`: Curates a new evaluation suite or corpus.
   - `Theoretical / Empirical Analysis`: Explains why existing phenomena occur.
   - `Interpretability / Safety / Alignment`: Improves trustworthiness, fairness, or controllability.
3. **Gap Analysis (`prior_bottlenecks` & `key_contributions`)**:
   - Clearly contrast *why prior methods fail* (`prior_bottlenecks`) against *what this paper contributes* (`key_contributions`).

---

## Pillar 2: Methods & Algorithms Classification (`methods`)

Separate the paper's **Proposed Components** from **Adopted Backbones** and **Compared Baselines**:

1. **Primary Paradigm (`primary_paradigm`)**:
   - Identify the overarching algorithmic family (e.g., `Transformer / Sparse Attention`, `Latent Diffusion`, `Reinforcement Learning (PPO/GRPO)`, `Graph Neural Network`, `Mixed-Integer Linear Programming`, `Statistical Causal Inference`).
2. **Component Breakdown (`proposed_components`)**:
   Break the methodology into modular sub-components and classify each into a `category`:
   - `Core Architecture / Model Design`
   - `Objective / Loss Function / Regularizer`
   - `Training / Optimization Strategy`
   - `Data Augmentation / Synthesis Pipeline`
   - `Inference / Decoding / Search Algorithm`
   - `Theoretical Bound / Formulation`
   - Set `is_novel: true` for contributions introduced by the authors and `is_novel: false` for existing pre-trained backbones or standard modules they build upon.
3. **End-to-End Pipeline (`pipeline_steps`)**:
   - Extract 3–6 sequential steps describing how data flows from input to final output so the HTML report can render a visual architecture timeline.

---

## Pillar 3: Datasets Classification (`datasets`)

Capture **every** dataset, corpus, simulator, or synthetic environment used:

1. **Modality (`modality`)**:
   - `Text / Natural Language`, `Source Code`, `Image`, `Video`, `3D / Point Cloud`, `Audio / Speech`, `Tabular / Time-Series`, `Graph / Molecular`, `Multimodal (Vision-Language)`, `Interactive Simulation / Environment`.
2. **Usage Role (`usage_role`)**:
   - `Pre-training`: Used to learn general representations.
   - `Fine-tuning / Training`: Used for supervised or RL training of the main model.
   - `In-Domain Evaluation`: Primary test split matching the training distribution.
   - `Zero-Shot / OOD Evaluation`: Held-out dataset testing transfer or out-of-distribution generalization.
   - `Ablation`: Used specifically to isolate component behavior.
   - `Newly Introduced Benchmark`: Created and released by this paper.
3. **Availability (`availability`)**:
   - `Public / Open`, `Restricted / Credentialed`, `Proprietary / Private`, `Synthetic / Generated`, or `Unspecified`.

---

## Pillar 4: Metrics Classification (`metrics`)

Classify all quantitative and qualitative evaluation criteria:

1. **Category (`category`)**:
   - `Task Accuracy / Quality`: e.g., Accuracy, F1, mAP, mIoU, BLEU, ROUGE, Pass@k, NDCG.
   - `Error / Distance`: e.g., RMSE, MAE, Perplexity, FID, LPIPS, Chamfer Distance.
   - `Efficiency / Compute / Memory`: e.g., FLOPs, Throughput (tokens/sec, FPS), Latency (ms), Peak VRAM (GB), Parameter Count.
   - `Perceptual / Human / LLM-Judge`: e.g., Elo rating, Win-rate vs. GPT-4, MOS (Mean Opinion Score), User Study preference.
   - `Robustness / Calibration`: e.g., Expected Calibration Error (ECE), Adversarial Accuracy, AUROC on OOD.
   - `Statistical Significance`: e.g., $p$-value, Wilcoxon signed-rank test, Cohen's $\kappa$.
2. **Directionality (`direction`)**:
   - Always label whether `Higher is better (↑)`, `Lower is better (↓)`, or `Target value / Neutral (↔)`.
3. **Primary vs. Secondary (`is_primary`)**:
   - Mark the 1–3 headline metrics that drive the paper's main claim as `is_primary: true`.

---

## Relational Mapping: Experimental Results (`experimental_results`)

To avoid isolated lists, link the 4 pillars together by extracting the key rows from the paper's main experimental tables:
- Map `(proposed_method_name, dataset, metric) -> proposed_score` alongside `(best_baseline_name, best_baseline_score)` and compute or quote the `delta_or_improvement` (e.g., `"+2.8% mAP"`, `"-35% latency"`).

