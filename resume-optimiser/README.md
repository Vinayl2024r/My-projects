# Resume Optimiser Skill

A Claude Code skill that tailors a resume to a specific job description in
three passes: score & gap analysis, XYZ-formula rewrite, then an ATS /
hiring-manager skim test.

## Install

Copy the `skills/resume-optimiser` directory into your project's
`.claude/skills/`, or install with:

```bash
npx skills add <this-repo>/resume-optimiser --skill resume-optimiser
```

## Usage

In Claude Code, share your resume and the target job description, then run:

```
/resume-optimiser
```

Each pass is shown to you before the next one runs, so you can correct course
early. The skill never invents experience, metrics, or job history that
isn't in your actual resume, and it never submits or sends anything on your
behalf — it only produces text for you to review.

## Directory Structure

```
resume-optimiser/
├── SKILL.md                    # skill definition (3-pass workflow)
└── references/
    ├── match-scoring.md        # Pass 1 — recruiter scoring rubric
    ├── xyz-rewrite.md          # Pass 2 — rewrite formula and rules
    └── ats-skim-test.md        # Pass 3 — ATS/skim checklist
```
