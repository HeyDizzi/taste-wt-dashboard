# Low-lift activation — vetted talent → active projects, this week

## The move: a 48-hour concierge matching sprint

No build. Use data already in hand:

1. **Target list (ready today):** 364 accepted experts with zero deals, plus 137 `idle`
   profiles. Rank by: specialization match to the 12 open positions, rating (avg 3–4 scale
   already scored), rate fit to position range, stated hours available.
2. **Match against live demand:** 12 open positions + 4 auto-generated supply requests
   already sitting in the portal. The specialization enum is shared on both sides — the
   shortlist is a filter, not a project.
3. **Personal outreach, not blast:** top 3–5 bench candidates per open position get a named,
   project-specific invite from a recruiter ("you, this project, this rate, reply yes").
   Everything about the message is already in the data: name, specialization, portfolio score.
4. **Hard 7-day loop:** invites expire (the board currently carries 198 invites at
   `pending` indefinitely — the anti-pattern this replaces). No reply → next candidate.

## Why this beats the alternatives for immediacy

- Marketplace-standard fixes (matching algorithm, availability calendar, self-serve board)
  are all "Next"-phase builds. The sprint is the manual version of all three and generates
  their spec.
- Demand is the binding constraint for only part of the bench: 12 positions won't absorb 364
  people. The sprint therefore also produces the **first real split of the dormant pool** —
  "no matching demand exists" vs "offered and declined" — which have opposite fixes and are
  currently indistinguishable (the #1 instrumentation gap).

## Measured by

VAR (see `02-north-star.md`) and one sprint-local number: invites sent → accepted within 7
days. Baseline for comparison already known: of 855 lifetime deals, 208 accepted / 235
rejected / 198 still pending.
