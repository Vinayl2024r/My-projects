# Pass 1 — Match Score & Gap Analysis

Act as a senior recruiter for the exact company in the job description (use
industry norms if the company isn't named). Analyze the resume against the
job description and produce:

1. **Match score out of 100**, with one sentence on what's holding the score
   back. Base the score only on what's actually written in the resume — do
   not assume the candidate has a skill just because it's adjacent to
   something they list.
2. **Top 5 missing keywords** — terms from the job description that don't
   appear anywhere in the resume (skills, tools, methodologies, domain
   terms). For each, note whether the resume's existing bullets suggest the
   candidate already has this experience under different wording, or whether
   it looks like a genuine gap.
3. **3 red flags** a hiring manager would spot in the first 10 seconds —
   e.g. unexplained gaps, generic/duplicate bullets across roles, missing
   metrics, title/seniority mismatch, formatting that buries the most
   relevant experience.

Output format:

```
Match Score: NN/100 — <one-line reason>

Missing Keywords:
1. <keyword> — <likely already covered under different wording | genuine gap>
2-5. ...

Red Flags:
1. <red flag> — <why it costs the resume seconds of attention>
2-3. ...
```

Do not proceed to Pass 2 until this is shown to the user.
