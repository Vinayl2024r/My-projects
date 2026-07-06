# Pass 2 — XYZ Rewrite

Rewrite the resume's experience section to naturally include the missing
keywords from Pass 1 and remove the red flags, using the XYZ formula for
every bullet:

> Accomplished **X** as measured by **Y** by doing **Z**.

Rules:

- **X** (the accomplishment) and **Z** (how it was done) must come from what
  the candidate actually did — pull from the existing resume content, don't
  invent projects or responsibilities.
- **Y** (the metric) must be a number already in the resume, or one the
  candidate can plausibly estimate from what's written (e.g. team size, time
  saved, scope). If no metric exists and none can be reasonably inferred,
  write the bullet without a fabricated number rather than making one up —
  flag it for the user to fill in instead.
- Work missing keywords in only where they honestly describe something the
  candidate already did. If a keyword from Pass 1 has no real support in the
  resume, list it separately as "not addressed — requires new experience or
  user input" rather than forcing it into a bullet.
- Fix the red flags from Pass 1 directly: dedupe repeated bullets across
  roles, address gaps with a one-line honest explanation if the user
  provides one, and reorder so the most relevant bullets lead each role.

Output the full rewritten experience section, followed by a short list of any
keywords that couldn't be honestly addressed and why.

Do not proceed to Pass 3 until this is shown to the user.
