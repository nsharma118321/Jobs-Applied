# Jobs Applied

Tracks every role Nishant has applied to from the UK Data Scientist Sponsor Job Tracker.

- `index.json` — machine-readable list (title, company, applied date, original posting link, portal link, path to the saved JD file).
- One `<job_title>_<company>.md` file per application, containing the role details and the full job description as captured at the time it was marked applied (source postings often expire within days, so this is the durable record).

Entries are added by Claude whenever Nishant says "mark <role> as applied" in chat — the role is simultaneously removed from the open-roles tracker at [job-tracker-data](https://github.com/nsharma118321/job-tracker-data).
