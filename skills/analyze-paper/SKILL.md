---
name: analyze-paper
description: >-
  Analyzes and classifies academic research papers (from local PDFs, Markdown, LaTeX,
  arXiv URLs/IDs, or pasted text) into four core structured pillars—(1) Problem Solved,
  (2) Methods & Algorithms Used, (3) Datasets & Benchmarks Used, and (4) Evaluation Metrics Used—along
  with an experimental results matrix and reproducibility audit, then generates an interactive
  standalone HTML report. Use this skill whenever the user invokes `/analyze-paper` or asks to
  analyze, dissect, classify, summarize, or generate an HTML report for one or more research papers.
---

# Academic Paper Classifier & HTML Report Generator (`/analyze-paper`)

You are an expert research scientist and literature analyst. When activated, follow this deterministic workflow to classify one or more research papers into the **P-M-D-M Framework** (**Problem**, **Methods/Algorithms**, **Datasets**, **Metrics**) and generate a rich, self-contained HTML report.

---

## Workflow Steps

### Step 1: Resolve & Ingest the Paper Input
Determine what input the user provided:
1. **Local PDF, Markdown, LaTeX, or Text File**:
   - Read the document directly using `read_file`. For multi-page PDFs, read across all key sections (Abstract, Introduction, Methodology, Experimental Setup, Results Tables, and Conclusion/Limitations).
2. **arXiv ID or URL** (e.g., `2305.12345` or `https://arxiv.org/abs/...`):
   - Run the ingestion helper script to fetch metadata and download the PDF locally:
     ```powershell
     python skills/analyze-paper/scripts/fetch_paper.py "<arxiv_id_or_url>" --download-dir "./reports/papers"
     ```
   - Then use `read_file` on the downloaded `local_pdf_path` to inspect the full paper text, figures, and tables.
3. **Multiple Papers (Comparison Mode)**:
   - If the user provides 2 or more papers, repeat ingestion and extraction for each paper so they can be compiled into a single multi-paper comparison HTML report.

---

### Step 2: Classify the Paper Using the P-M-D-M Rubric & Schema
Before extracting, read the rubric and schema files:
- **Classification Rubric**: [extraction_rubric.md](./references/extraction_rubric.md)
- **JSON Schema**: [extraction_schema.json](./references/extraction_schema.json)
- **Sample Output Reference**: [sample_attention_paper.json](./examples/sample_attention_paper.json)

Extract a complete JSON object adhering strictly to `extraction_schema.json`:
1. **`metadata`**: Title, authors, affiliations, year, venue, code repository URL, domain tags, 2–3 sentence `tldr`, and `reproducibility` assessment (`High` / `Medium` / `Low`).
2. **`problem` (Group 1 — Problem Solved)**:
   - Classify into `broad_domain`, `specific_task`, and `problem_type_badges`.
   - Articulate the `problem_statement`, `research_questions`, `prior_bottlenecks` (why prior methods fail), and `key_contributions` with exact `evidence_location` citations.
3. **`methods` (Group 2 — Methods & Algorithms Used)**:
   - Identify `primary_paradigm` and `method_badges`.
   - Decompose into `proposed_components` (marking whether each is `is_novel: true` or an adopted backbone `is_novel: false`, its category, role, technical mechanism/equations, and `evidence_location`).
   - Extract sequential `pipeline_steps` and list all `baselines_compared`.
4. **`datasets` (Group 3 — Datasets & Benchmarks Used)**:
   - List every dataset used, classified by `modality`, `usage_role` (`Pre-training`, `Fine-tuning / Training`, `In-Domain Evaluation`, `Zero-Shot / OOD Evaluation`, `Ablation`, or `Newly Introduced Benchmark`), `scale_and_splits`, `domain`, `availability`, `preprocessing_or_notes`, and `evidence_location`.
5. **`metrics` (Group 4 — Evaluation Metrics Used)**:
   - List every evaluation metric, classified by `category` (`Task Accuracy / Quality`, `Error / Distance`, `Efficiency / Compute / Memory`, `Perceptual / Human / LLM-Judge`, `Robustness / Calibration`, `Statistical Significance`), `direction` (`Higher is better (↑)` / `Lower is better (↓)`), `is_primary`, `purpose`, and `evidence_location`.
6. **`experimental_results` (Relational Matrix)**:
   - Cross-link `(dataset, metric, proposed_method_name, proposed_score)` against `(best_baseline_name, best_baseline_score, delta_or_improvement)` with table/page citations.
7. **`critical_review`**:
   - Summarize `strengths`, `limitations`, and `future_directions`.

Save the extracted JSON to `./reports/<paper_slug>_analysis.json` (or the user's requested output directory).

---

### Step 3: Generate & Verify the HTML Report
Run the deterministic HTML generator script to inject the validated JSON into [report_template.html](./resources/report_template.html):

```powershell
python skills/analyze-paper/scripts/generate_html_report.py --input "./reports/<paper_slug>_analysis.json" --output "./reports/<paper_slug>_report.html"
```

*(For multi-paper comparison, pass multiple JSON files to `--input file1.json file2.json --output ./reports/comparison_report.html`.)*

**Verification Checklist**:
1. Confirm the script exits with code `0` and `"warnings_count": 0`. If any validation warnings are printed, fix the missing fields in the JSON file and re-run.
2. Optionally copy the generated HTML report to the conversation's artifact directory with `UserFacing: true` so the user can preview it directly inside Antigravity's side pane, in addition to having the permanent file in `./reports/`.
3. Provide a concise summary in chat with clickable links to both `./reports/<paper_slug>_report.html` and `./reports/<paper_slug>_analysis.json`.

