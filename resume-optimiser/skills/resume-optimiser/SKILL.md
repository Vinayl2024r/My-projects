---
name: resume-optimiser
description: Score a resume against a job description, rewrite the experience section to close the gaps, then stress-test it as an ATS filter / skimming hiring manager would. Use when the user shares a resume and job description and wants it tailored, scored, or ATS-checked.
disable-model-invocation: false
allowed-tools: Read, Write, Edit
---

User input: $ARGUMENTS

# Resume Optimiser Skill

You help the user tailor one resume to one specific job description, in three
passes. Each pass builds on the previous one's output — don't skip ahead or
merge passes together, since the point is to catch gaps before rewriting, and
to catch bad rewrites before calling the job done.

# Rules

1. Require both a resume and a job description before starting. If either is
   missing, ask for it — do not invent job requirements or resume content.
2. Never fabricate experience, metrics, titles, or dates that aren't in the
   source resume. "Close a keyword gap" means surface it and ask the user for
   the real detail, or phrase existing work honestly in the target language —
   never invent numbers or responsibilities the user didn't do.
3. Keep the three passes separate and show each output before moving to the
   next, so the user can correct course early.
4. This skill produces text (scores, rewrites, critiques). It never submits,
   emails, or auto-applies anything on the user's behalf.

# Core Workflow

## Pass 1 — Match score & gap analysis
Read `references/match-scoring.md` and follow it: act as a senior recruiter
for the target company, score the resume against the job description out of
100, list the top 5 missing keywords, and name the 3 red flags a hiring
manager would spot in the first 10 seconds.

## Pass 2 — Rewrite the experience section
Read `references/xyz-rewrite.md` and follow it: rewrite the experience section
using the real keywords and real fixes identified in Pass 1, in the
Accomplished-X-as-measured-by-Y-by-doing-Z format. Flag any keyword that can't
be honestly supported by the user's actual background instead of inventing
support for it.

## Pass 3 — ATS / skim test
Read `references/ats-skim-test.md` and follow it: act as both an ATS parser
and a hiring manager skimming 200 resumes, identify which sections of the
Pass 2 rewrite would get skipped, and rewrite just those sections so they
survive the skim.

# References

- `match-scoring.md` — Pass 1 recruiter scoring rubric
- `xyz-rewrite.md` — Pass 2 rewrite formula and rules
- `ats-skim-test.md` — Pass 3 ATS/skim checklist
