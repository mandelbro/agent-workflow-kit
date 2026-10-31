# Worked Example — `/tdd-pair auto specs/rate-limiter.md`

A full autonomous run on a token-bucket rate limiter, showing the Zod gate at each boundary, one rejection/retry, and one escalation. Compressed for illustration.

**The spec (contract Zod reviews against):**

```markdown
# Token-Bucket Rate Limiter — spec

## What is it?
Per-key token bucket for throttling. Canonical use: cap a client to N req/s.

## Public API
  try_acquire(key: str, tokens: int = 1) -> bool   # True if allowed, False if throttled
  __init__(capacity: int, refill_per_sec: float, clock: Callable[[], float])

## Design Decisions
- Per-key buckets in a dict; created lazily on first access.
- Lazy refill from timestamps — NO background timers.
- Clock is injected (testability).

## Error States
- capacity <= 0 or refill_per_sec <= 0 → ValueError at construction.
- tokens < 1 → ValueError.
- tokens > capacity → always False (never satisfiable), not an error.

## Test Plan
1. fresh key with full bucket allows up to `capacity` immediate acquires
2. (capacity+1)th immediate acquire returns False
3. tokens refill at refill_per_sec after elapsed time
4. refill never exceeds capacity
5. ValueError on capacity<=0, refill<=0, tokens<1
6. tokens > capacity returns False without consuming

## Out of Scope
- Distributed/shared state (single-process only). Concurrency: deferred.
```

**Step 1 — invoke.** `/tdd-pair auto specs/rate-limiter.md`. No existing `tdd-state.json`, spec has a real Test Plan + Public API + Error States → contract is reviewable, proceed.

**Step 2 — batching plan + Zod plan review:**

```
Batch 1 "Capacity & consumption"   → tests 1, 2, 6   (core happy/boundary path)
Batch 2 "Refill over time"         → tests 3, 4       (the clock-driven behavior)
Batch 3 "Construction validation"  → test 5          (error states)
```

Autonomous gate, phase=`plan` → dispatch Zod: *"Review this batching against the spec — coverage, cohesion, atomicity."* Zod returns `Verdict: Approve with Concerns` (concern: "test 6 is a boundary of batch 2's refill logic as much as batch 1's consumption — acceptable as placed"). → `zod_approved`, write state:

```json
{ "version": 1, "mode": "autonomous", "spec_path": "specs/rate-limiter.md",
  "max_review_rounds": 3, "current_batch_id": 1, "current_phase": "red",
  "implementation_plan": { "batches": [
    { "id": 1, "name": "Capacity & consumption", "tests": ["1","2","6"],
      "status": "in_progress", "phase": "red", "review_rounds": 0 },
    { "id": 2, "name": "Refill over time", "tests": ["3","4"], "status": "pending", "phase": "red", "review_rounds": 0 },
    { "id": 3, "name": "Construction validation", "tests": ["5"], "status": "pending", "phase": "red", "review_rounds": 0 } ] },
  "history": [ {"event": "started_auto"}, {"event": "plan_approved"} ] }
```

**Step 3 — Batch 1 Red.** Write failing tests for 1, 2, 6. Run suite → 3 fail (no implementation yet). `review_rounds → 1`, `zod_review_started (red, 1)`, dispatch Zod with the red criteria + *"review against the spec, not the code; watch for assertions calibrated to nonexistent code."*

Zod returns `Verdict: Request Changes`: *"Test 6 asserts `try_acquire('k', 6)` is False for capacity=5 — correct — but also asserts the bucket still holds 5 tokens afterward by reaching into `limiter._buckets['k']`. That couples the test to private state; the spec's contract is the boolean return. Assert a subsequent `try_acquire('k', 5)` succeeds instead."* → `zod_rejected (round 1)`, `review_rounds (1) < 3` → apply the change, re-run, re-dispatch.

Round 2: Zod returns `Verdict: Approve`. → `zod_approved`, `batch_red_complete`, `current_phase → green`.

**Step 4 — Batch 1 Green.** Implement minimum code (dict of buckets, lazy create, decrement on acquire — no refill yet beyond what tests 1/2/6 need). Tests pass, lint/typecheck clean. Refactor scan: "none recommended — 18 lines, flat." `review_rounds → 1`, dispatch Zod with green criteria.

Zod returns `Verdict: Approve with Concerns`: *"Matches Design Decisions; lazy dict creation is correct. Concern (non-blocking): `tokens` default isn't validated here — but test 5 / batch 3 owns construction validation, so deferral is correct, not a gap."* → `zod_approved`, concern logged to `notes`, no refactor needed → `current_phase → done` for the refactor step, `batch_green_complete`.

**Step 5 — Batch advancement.** Batch 1 `completed`. `current_batch_id → 2`, `current_phase → red`, `batch_advanced`. Commit is NOT made autonomously — it's queued for the human. Re-enter Red Phase for batch 2.

**Step 6 — escalation example (Batch 2 Red).** Tests 3, 4 are the clock-driven refill. Suppose the spec is ambiguous: it says "refill at refill_per_sec" but doesn't state whether refill is continuous (fractional tokens accrue) or whole-token. The test author picks continuous; Zod rejects *"spec test 4 ('refill never exceeds capacity') only constrains the ceiling — fractional accrual is an unstated assumption; test 3's expected value at t=0.5s depends on it. This is a contract gap, not a test bug."* Round 2: revise to whole-token, Zod rejects *"now test 3 at t=0.5s with refill=2/s expects 1 token, but whole-token flooring is equally unstated — same gap, opposite guess."* Round 3: same impasse.

`review_rounds (3) >= max_review_rounds` → **escalate.** Batch 2 `status → blocked`, Zod's finding written to `notes`, `escalated_to_human`, state persisted, **a `PushNotification` fires** (the run was unattended; this is the moment it needs you), and the loop STOPS:

```
[push] tdd-pair blocked: batch 2 "Refill over time" — spec ambiguity on token
       refill (continuous vs whole-token), needs your call. /tdd-pair resume

⏸  Autonomous run paused — batch 2 "Refill over time" blocked after 3 Zod rounds.
   Impasse: the spec doesn't define whether token refill is continuous (fractional)
   or whole-token. Tests 3 and 4 can't be made deterministic without this decision.
   Zod's finding is in tdd-state.json notes. Resolve the spec ambiguity, then:
     /tdd-pair resume   → (retry autonomously | take over manually | abort)
```

This is the system working as designed: three rounds proved the disagreement is a **contract ambiguity**, not a fixable code defect — exactly the case a human must settle. The human edits the spec ("refill is continuous; fractional tokens accrue"), runs `/tdd-pair resume`, picks *Resume autonomous (retry from red)*, and the loop continues with `review_rounds` reset.

**Interactive contrast:** the same run with `/tdd-pair start` is identical except each `dispatch Zod` is instead an `AskUserQuestion` to you — you'd have caught the refill ambiguity at the red gate yourself. The autonomous run reaches the same conclusion without you, and only pulls you in when it genuinely needs a decision.
