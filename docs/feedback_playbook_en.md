# PrimeVarClass - Feedback Playbook

## Purpose

Feedback turns real use into product evidence and translational impact. Each session should answer: did the tool help, save time, generate actionable hypotheses, and preserve scientific safety?

## When to record feedback

- After batch screening.
- After reviewing a difficult case.
- After comparison with human curation.
- After a laboratory or translational committee meeting.
- Whenever there is an error, confusion, delay, unexpected result, or scientific disagreement.

## Minimum fields

- `session_id`: unique session identifier.
- `study_name`: associated study or benchmark.
- `operator_name`: responsible user.
- `role`: user role.
- `confidence_score`: confidence from 0 to 5.
- `actionability_score`: practical usefulness from 0 to 5.
- `time_saved_minutes`: estimated time saved.
- `adoption_recommendation`: `recommended`, `conditional`, or `not_recommended`.
- `incident_level`: `none`, `low`, `medium`, or `high`.
- `notes`: free-text comments.

## Recommended scale

- 0: did not help or created risk.
- 1: helped very little and had high uncertainty.
- 2: useful in a narrow context.
- 3: useful, but requires careful review.
- 4: very useful and understandable.
- 5: excellent, actionable, and low-friction.

## How to interpret

- High confidence and high actionability indicate UX and scientific maturity.
- Low confidence with high actionability indicates potential, but weak explainability.
- Low actionability with high confidence may mean the result is correct but not decision-relevant.
- `medium` or `high` incidents should block public rollout until reviewed.
- Time saved without scientific quality is not enough for real impact.

## Useful note example

```text
The ranking prioritized BRCA1 p.Cys61Gly consistently with rarity and MAVE evidence.
The explanation was clear for the senior team, but the student asked for a definition of gnomAD AF.
Estimated time saved: 25 minutes. No incident.
```

## How to use negative feedback

Negative feedback is backlog:

- Confusing term: add it to the glossary.
- Hard-to-find button: revise visual hierarchy.
- Result without evidence: improve annotation or gap messaging.
- Recurrent error: add validation or preflight.
- Scientific disagreement: create a test case and record the exception.

## Safety rule

Positive feedback does not replace external validation. It measures usefulness and experience; scientific validity still depends on independent benchmarking, audit, human review, and experimental confirmation.

