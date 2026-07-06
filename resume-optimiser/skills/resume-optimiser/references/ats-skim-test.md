# Pass 3 — ATS / Skim Test

Act as two readers in sequence against the Pass 2 rewrite:

1. **ATS parser** — check for anything that breaks automated parsing:
   tables/columns/text boxes, headers/footers holding key info, non-standard
   section titles, images or icons standing in for text, unusual date
   formats, missing standard section headers (Experience, Education, Skills).
2. **Hiring manager skimming ~200 resumes** — for each section, judge
   honestly whether it would get read fully, skimmed, or skipped in a ~10
   second pass. Common skip triggers: dense unbroken paragraphs, the most
   relevant bullet buried below less relevant ones, weak opening verbs,
   no visual hierarchy.

Output format:

```
ATS Parsing Issues:
- <issue, or "none found">

Section-by-Section Skim Verdict:
- <section name>: <would read fully | would skim | would skip> — <why>
```

Then rewrite only the sections marked "would skip" or "would skim" so they
survive both readers — strongest, most relevant point first, concrete over
vague, no fabricated content. Leave sections already marked "would read
fully" untouched.
