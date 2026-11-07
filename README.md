# Antigravity Skills Repository (`my-agent-skill`)

A modular repository designed to house, develop, and distribute custom **Google Antigravity Skills**. Any skill located in `skills/<skill-name>` can be used directly within this workspace, or imported/installed as a **global skill** (available across all projects on your machine) or into any other **project workspace**.

---

## Repository Structure

```text
my-agent-skill/
├── .agents/
│   └── skills.json                # Registers ./skills/ so Antigravity discovers all skills here
├── skills/                        # All custom skills live here as clean modular packages
│   ├── analyze-paper/             # Academic paper classification & HTML report generator
│   │   ├── SKILL.md               # Main instructions & metadata
│   │   ├── references/            # Schemas, rubrics, anti-hallucination guides
│   │   ├── resources/             # HTML templates, assets
│   │   ├── scripts/               # Deterministic execution scripts (fetch, build report)
│   │   └── examples/              # Sample JSON extractions
│   └── session-tokens/            # Session Token In, Token Out & Token Cache analyzer
│       ├── SKILL.md               # Main instructions & metadata
│       ├── references/            # Token accounting & context window guide
│       ├── resources/             # Interactive HTML token dashboard template
│       └── scripts/               # Deterministic CLI & HTML report generator (check_tokens.py)
├── scripts/                       # Distribution & installation automation
│   ├── install-skill.ps1          # PowerShell installer (Windows)
│   └── install-skill.sh           # Bash installer (macOS / Linux)
├── reports/                       # Generated outputs and artifacts
└── README.md
```

---

## Adding New Skills to This Repo

When creating future skills, follow this standard pattern:

1. Create a new directory under `skills/`:
   ```text
   skills/<my-new-skill>/
   ├── SKILL.md            # Required: YAML frontmatter (name, description) + instructions
   ├── references/         # Optional: Schemas, rubrics, guides
   ├── resources/          # Optional: Templates, static assets
   ├── scripts/            # Optional: Deterministic helper scripts
   └── examples/           # Optional: Reference inputs/outputs
   ```
2. Because `.agents/skills.json` points to `"skills"`, Antigravity will **automatically discover** your new skill without needing any manual registration.

---

## How to Import & Use Skills

### Mode 1: Using Skills Locally in This Repository
You don't need to do anything! When Antigravity opens this workspace, it reads `.agents/skills.json` and automatically activates any skill inside `skills/` (e.g. `/analyze-paper`).

---

### Mode 2: Installing as a Global Skill (Available in ALL Projects)
To make one or all skills from this repository available across **every Antigravity project on your machine**:

#### Windows (PowerShell):
```powershell
# Install a specific skill globally
powershell -ExecutionPolicy Bypass -File .\scripts\install-skill.ps1 -Target global -SkillName analyze-paper

# Or install ALL skills from this repo globally
powershell -ExecutionPolicy Bypass -File .\scripts\install-skill.ps1 -Target global
```

#### macOS / Linux (Bash):
```bash
# Install a specific skill globally
./scripts/install-skill.sh --target global --skill-name analyze-paper

# Or install ALL skills from this repo globally
./scripts/install-skill.sh --target global
```

*Global destination: `~/.gemini/config/skills/<skill-name>`.*

---

### Mode 3: Importing into Another Specific Project Workspace
To install one or all skills into another project:

#### Windows (PowerShell):
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-skill.ps1 `
  -Target project `
  -ProjectPath "C:\path\to\your\other-project" `
  -SkillName analyze-paper
```

#### macOS / Linux (Bash):
```bash
./scripts/install-skill.sh --target project --project-path "/path/to/other-project" --skill-name analyze-paper
```

*Project destination: `<project-path>/.agents/skills/<skill-name>`.*

---

### Mode 4: Symlink / Inherit via `skills.json` (Zero-Copy Team Sharing)
If you prefer not to copy files and want your other project to reference this skill repo directly:
Add a `.agents/skills.json` file inside your other project:

```json
{
  "entries": [
    {
      "path": "d:/skill/my-agent-skill/skills"
    }
  ]
}
```
Any updates you make to skills in `my-agent-skill` will immediately reflect across all linked projects.

---

## Included Skills

### 1. `analyze-paper` (`/analyze-paper`)
- **Description**: Classifies academic research papers into 4 structured pillars: **Problem Solved**, **Methods & Algorithms Used**, **Datasets & Benchmarks**, and **Evaluation Metrics Used**, plus a **Results Matrix** and **Reproducibility Audit**. Generates an interactive standalone HTML report.
- **Input Formats**: Local PDF, Markdown, LaTeX, or direct arXiv URLs/IDs (e.g. `https://arxiv.org/abs/2305.18290`).
- **Detailed Documentation**: See [skills/analyze-paper/SKILL.md](file:///d:/skill/my-agent-skill/skills/analyze-paper/SKILL.md).

### 2. `session-tokens` (`/session-tokens`)
- **Description**: Checks and analyzes **Token In** (`input_tokens`), **Token Out** (`output_tokens`), and **Token Cache** (`cache_read_tokens`) for the current session, a specific conversation ID, or across all sessions. Computes cache hit rate (%), current & peak context window size, per-turn and per-step breakdowns, subagent usage, and generates an interactive HTML dashboard.
- **Detailed Documentation**: See [skills/session-tokens/SKILL.md](file:///d:/skill/my-agent-skill/skills/session-tokens/SKILL.md).
