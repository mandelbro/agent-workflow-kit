---
name: tdd-pair
description: "TDD Loop Pairing Session orchestrator. Drives Ada's red→green→refactor cycle in test batches against a spec, with a per-project state file that survives session compaction. Each phase boundary is gated by either a human review (interactive mode) or an autonomous Zod review (autonomous mode). Subcommands: start <spec-path>, auto [--headless] <spec-path>, resume [--headless], status, end. The --headless variant never prompts and ends with a schema-validated JSON outcome."
disable-model-invocation: true
user-invocable: true
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, Agent, Task
---

# /tdd-pair — TDD Loop Pairing Session

You are operating as **Ada** (the pair-programming persona; use the `Ada` agent definition if one is installed, otherwise follow this file alone) in TDD Loop Pairing mode. This skill orchestrates the inner loop of the TDD-with-AI Workflow's step 6 ("Pipelined implementation"): turning a finalized spec into batched red/green/refactor cycles, with you in the typing role and an **auditor** in the review role at every phase boundary.

**Two modes, one engine.** The red→green→refactor state machine is identical regardless of who audits; only the *gate* at each phase boundary differs:

- **Interactive mode** (`start`) — the human is the auditor. Each phase boundary is an `AskUserQuestion`. Use when you want input into the process.
- **Autonomous mode** (`auto`) — the **Zod** reviewer agent is the auditor. Each phase boundary is a Zod review against the spec, with bounded retry and escalation to the human on impasse. Use for hands-off, contract-driven implementation (e.g. the Task Workflow System's implementation step).

See the **Gate Protocol** section for how the two gates resolve. Everything else — batching, state persistence, the phase flows — is shared.

**Headless variant.** `auto --headless` (and `resume --headless`) is autonomous mode for unattended runs such as `claude -p`. It never calls `AskUserQuestion` or `PushNotification`; wherever another flow says "STOP and surface", it ends the run with a JSON outcome instead. See **Headless Mode**.

**Subcommand input:** `$ARGUMENTS`

Parse the first whitespace-separated token of `$ARGUMENTS` to determine the subcommand. Remaining tokens are subcommand arguments. Supported subcommands: `start`, `auto`, `resume`, `status`, `end`. `auto` and `resume` accept a `--headless` flag anywhere in the arguments; strip it before reading the spec path. If no subcommand or an unknown one is given, print the help block at the bottom of this file and exit.

---

## State File

**Location:** `<cwd>/.claude/tdd-state.json` (per-project, survives reboots, gitignore-able)

**Schema (version 1):**

```json
{
  "version": 1,
  "mode": "interactive|autonomous",
  "headless": false,
  "spec_path": "<path relative to cwd>",
  "base_branch": "<default branch the session was started against, e.g. 'main' — optional, set by the pre-flight>",
  "started_at": "<ISO 8601 UTC>",
  "updated_at": "<ISO 8601 UTC>",
  "implementation_plan": {
    "summary": "<plain-English summary of the plan presented to the user>",
    "batches": [
      {
        "id": 1,
        "name": "<batch name, e.g. 'Input validation'>",
        "rationale": "<why these tests are batched together>",
        "tests": ["<test description 1>", "<test description 2>"],
        "status": "pending|in_progress|completed|blocked",
        "phase": "red|green|refactor|done",
        "review_rounds": 0,
        "notes": "<optional review feedback or refactor recommendations>"
      }
    ]
  },
  "max_review_rounds": 3,
  "current_batch_id": 1,
  "current_phase": "red",
  "history": [
    { "timestamp": "<ISO 8601 UTC>", "event": "<event name>", "details": "<...>" }
  ]
}
```

**State update protocol (ALWAYS follow):**

1. `Read` the file first to get the current state.
2. Modify the in-memory copy.
3. Update `updated_at` to current ISO 8601 UTC (use `date -u +%Y-%m-%dT%H:%M:%SZ`).
4. Append a `history` entry describing the change.
5. Write atomically: write to `<cwd>/.claude/tdd-state.json.tmp` first, then `mv` to the final path.

If `<cwd>/.claude/` does not exist, create it before writing. In a git repo, also make sure the state file never lands in a commit: append `.claude/tdd-state*` to the file reported by `git rev-parse --git-path info/exclude` if that line is not already there (a local exclude; never edit `.gitignore` for this).

**Event names for history:**
- `started` — `start` subcommand invoked (interactive mode)
- `started_auto` — `auto` subcommand invoked (autonomous mode)
- `plan_approved` — implementation plan approved (by user in interactive, by Zod in autonomous)
- `batch_red_started` / `batch_red_complete` — red phase boundaries
- `batch_green_started` / `batch_green_complete` — green phase boundaries
- `batch_refactor_started` / `batch_refactor_complete` — refactor phase boundaries
- `zod_review_started` — autonomous gate dispatched a Zod review (include phase + round)
- `zod_approved` — Zod returned Approve / Approve with Concerns
- `zod_rejected` — Zod returned Request Changes / Needs Discussion (include round + summary)
- `escalated_to_human` — autonomous gate exhausted `max_review_rounds`; paused for human
- `batch_advanced` — moved to next batch
- `resumed` — `resume` subcommand invoked
- `ended` — `end` subcommand invoked
- `aborted` — user explicitly abandoned the session
- `needs_info_stop` — headless run stopped because the spec is not a usable contract (include the gaps)
- `preflight_branch_check` — recorded the default-branch freshness check at session start (include branch, behind/ahead counts, decision)

---

## Session Pre-Flight: Default-Branch Freshness

Both `start` and `auto` run this **before any other step** (it gates session creation, like the spec-quality gate). It encodes a hard-won lesson: a TDD session's eventual commit/PR is only as clean as the base it started from. Starting on a stale branch — one behind the default, or whose base was already squash-merged — produces redundant commits, doc-drift reversions, and a confusing PR that has to be rebased at the end. Catch it at the start, not at PR time.

1. **Bail out cleanly if not version-controlled.** If `git rev-parse --git-dir` fails, report "not a git repo — skipping branch freshness check" and proceed straight to the subcommand's step 1. Everything below assumes a git repo.

2. **Identify the default branch.** `git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p'`; fall back to `git symbolic-ref --short refs/remotes/origin/HEAD` (strip the `origin/`), then to `main`. Call it `<default>`. Record it as `base_branch` in the state file (an optional top-level field).

3. **Fetch it (best-effort).** `git fetch origin <default> -q`. If the fetch fails (offline, no remote), WARN that freshness can't be verified and proceed — never block a session on the network.

4. **Assess the working branch** against `origin/<default>`:
   - `current = git branch --show-current`.
   - behind/ahead: `git rev-list --left-right --count origin/<default>...HEAD` (left = behind, right = ahead).
   - dirty tree: `git status --porcelain` non-empty.

5. **Decide** (this is the only place the two modes differ):
   - **Headless** (either of the next two bullets): never ask, never rebase, never create branches. On the default branch → end the run with `status: "blocked"` and `blocked_reason` recommending `git checkout -b <feature> origin/<default>`. Behind the default → proceed, and put the staleness in the outcome's `base_warning`. Not a git repo → proceed.
   - **On the default branch** (`current == <default>`): a TDD session should branch off the default, never commit onto it (Ada/CLAUDE.md). *Interactive:* `AskUserQuestion` → *Branch fresh from origin/<default>* (recommended), *Continue on <default> anyway*, *Cancel*. *Autonomous:* STOP and surface — recommend `git checkout -b <feature> origin/<default>`, let the human branch and re-invoke. Do not auto-create branches unattended.
   - **Behind the default** (behind > 0): the base is stale. *Interactive:* `AskUserQuestion` → *Rebase onto origin/<default> now* (recommended; abort with a stash/commit instruction if the tree is dirty), *Branch fresh from origin/<default>*, *Continue as-is (I'll rebase before the PR)*, *Cancel*. *Autonomous:* do NOT rebase unattended (it can conflict or rewrite history). Record the staleness in `base_branch` + a `preflight_branch_check` history entry, WARN prominently, and **proceed** — the session work (tests/code) isn't harmed by a stale base; commits are deferred to the human anyway. Repeat the warning in the final summary so the human rebases before opening the PR.
   - **Up to date** (behind == 0, on a feature branch): proceed silently.

6. **Record** a `preflight_branch_check` history entry (branch, behind/ahead, decision) when the state file is written. In autonomous mode, any staleness warning surfaced here MUST also appear in the completion/escalation summary — the human reads that to decide the PR base.

---

## Subcommand: `start <spec-path>`

**Goal:** Initialize a TDD Loop Pairing session from a finalized spec.

**Before step 1, run the [Session Pre-Flight: Default-Branch Freshness](#session-pre-flight-default-branch-freshness) above** so the session starts on a current base.

1. **Validate inputs:**
   - If `<spec-path>` is missing, ask the user to provide it.
   - Resolve to absolute path. If file does not exist, error and exit.
   - If `<cwd>/.claude/tdd-state.json` already exists, ask the user whether to abort the existing session, resume it (run `/tdd-pair resume` instead), or overwrite it.

2. **Read and analyze the spec:**
   - The spec should follow the six-section structure from Ada's TDD-with-AI Workflow: *What is it?*, *Public API*, *Design Decisions*, *Error States*, *Test Plan*, *Out of Scope*.
   - Focus on the **Test Plan** section to extract individual test cases.
   - If the spec lacks a clear Test Plan, surface this as a gap and ask the user whether to proceed with a less-structured spec or pause to add a Test Plan first.

3. **Identify test gaps:**
   - Cross-reference the Test Plan against the Public API and Error States sections.
   - Flag any public-API surface or error state that has no corresponding test.
   - Present gaps to the user as a numbered list. Ask whether to add tests to cover them before starting the loop.

4. **Generate the test batching plan:**
   - Group tests into batches following Ada's Test Batching Strategy:
     - Tests related to a single core functionality (input validation, success response, error handling, data model validation)
     - Tests related to a single security check (authentication, authorization, data protection)
     - Tests related to a single bug fix (specific error or issue)
   - Aim for batches of 3–5 tests where reasonable. Larger or smaller is acceptable when batch cohesion demands it.
   - For each batch, write a name and a one-sentence rationale.

5. **Present the implementation plan to the user:**
   - Show: spec path, gap analysis (if any), the full batched plan as a numbered list with rationale, total batches, total tests.
   - Use `AskUserQuestion` to get explicit approval. Options: *Approve as-is*, *Revise batches*, *Cancel*.
   - Do not write the state file or proceed until approved (or after the user dictates a revision and approves the revised plan).

6. **Write the state file:**
   - Initialize `version: 1`, `mode: "interactive"`, `spec_path`, `started_at`, `updated_at`, `implementation_plan`, `max_review_rounds: 3`, `current_batch_id: 1`, `current_phase: "red"`.
   - Append two `history` entries: `started` and `plan_approved`.
   - Write atomically per the State Update Protocol.

7. **Enter the red phase of batch 1:**
   - Hand off to the **Red Phase** flow below.

---

## Subcommand: `auto <spec-path>`

**Goal:** Run a fully autonomous TDD Loop Pairing session — identical to `start`, but every phase boundary is gated by a **Zod** review instead of a human prompt. This is the engine the Task Workflow System invokes for its implementation step.

**Before step 1, run the [Session Pre-Flight: Default-Branch Freshness](#session-pre-flight-default-branch-freshness) above** — in autonomous mode it pauses when on the default branch, and warns-but-proceeds (recording the warning for the final summary) when behind it.

**Steps 1–4 are identical to `start`** (validate inputs, read and analyze the spec, identify test gaps, generate the batching plan) — with these autonomous substitutions:

- **Step 1 (existing state file):** if `<cwd>/.claude/tdd-state.json` already exists, do NOT silently overwrite. Stop and report it; let the human decide (`resume`, `end`, or explicit overwrite). Autonomy never destroys in-progress state. (Headless: end with `status: "blocked"` and say so in `blocked_reason`.)
- **Step 2–3 (spec quality / test gaps):** the spec IS the contract Zod will review against, so its quality gates the whole run. If the spec lacks a usable **Test Plan**, or has **Public API**/**Error States** surfaces with no corresponding tests, treat this as a blocking gap: **pause and surface it to the human** rather than guessing. A weak contract makes Zod's review tautological — refuse to proceed on one. (Headless: end with `status: "needs_info"` and list every gap in `spec_gaps`; append `needs_info_stop`.)

5. **Plan review (Zod, not human):**
   - Run the **autonomous gate** (see Gate Protocol) with phase = `plan`: dispatch Zod to review the batching plan against the spec — coverage of Public API and Error States, batch cohesion, test atomicity, and whether each batch maps to spec requirements.
   - On `zod_approved`: append `plan_approved`, continue. On exhausted retries: `escalated_to_human`, pause.

6. **Write the state file:**
   - Initialize `version: 1`, `mode: "autonomous"`, `headless` (true when `--headless` was given), `spec_path`, `started_at`, `updated_at`, `implementation_plan`, `max_review_rounds: 3`, `current_batch_id: 1`, `current_phase: "red"`.
   - Append two `history` entries: `started_auto` and `plan_approved`.
   - Write atomically per the State Update Protocol.

7. **Run the loop to completion:**
   - Enter the **Red Phase** of batch 1 and proceed through the phase flows. In autonomous mode every "run the phase gate" step resolves to the **autonomous gate**.
   - Continue through all batches without stopping, EXCEPT:
     - **Escalation:** when the autonomous gate exhausts `max_review_rounds` on any phase, STOP, persist state with the batch marked `blocked`, and surface Zod's findings to the human (per the Gate Protocol). Do not advance past a blocked phase.
     - **Git commits:** still require explicit human approval (see Optional: Git Commit Between Batches). Autonomous mode does not commit unattended.
   - On completion of all batches, set `current_phase = "done"`, write state, and report a final summary (use the `status` output format). Suggest `/tdd-pair end`. Headless: the final message is the JSON outcome with `status: "done"`.

---

## Subcommand: `resume`

**Goal:** Pick up an in-progress TDD Loop Pairing session after compaction, /resume, or any other interruption.

1. **Locate state file:**
   - Read `<cwd>/.claude/tdd-state.json`. If absent, error: "No TDD pairing session in progress. Run `/tdd-pair start <spec-path>` to begin."

2. **Re-anchor on the spec:**
   - `Read` the file at `state.spec_path`. If missing or unreadable, surface this and ask the user how to proceed (point at a new spec path, or end the session).

3. **Summarize where we are:**
   - Show: `mode`, spec path, started_at, last `updated_at`, total batches, batches completed, current batch (id, name, phase, status), tests in the current batch.
   - Show the last 3–5 entries from `history` so the user can verify the session was tracking correctly.
   - If the current batch is `blocked` (autonomous escalation), show the Zod findings from `notes` that caused the escalation.

4. **Headless resume (`resume --headless`):** skip the confirmation below. Continue from the current phase; a `blocked` batch is reset to `in_progress` with `review_rounds: 0` and retried from red. Set `headless: true` in state. Gates are autonomous.

   **Confirm continuation with the user** (not headless):
   - Use `AskUserQuestion`. Options: *Resume from current phase*, *Restart current batch from red*, *Skip to next batch*, *Abort session*.
   - For a `blocked` autonomous batch, also offer: *Resume autonomous (retry from red)* and *Take over manually (switch to interactive for this batch)*. Resuming clears `blocked` → `in_progress` and resets `review_rounds: 0`.

5. **Append `resumed` to history**, update `updated_at`, write state.

6. **Branch to the appropriate phase flow** — gates resolve per the session's stored `mode` (interactive → `AskUserQuestion`; autonomous → Zod gate), unless the user chose *Take over manually*, which sets `mode = "interactive"` for the remainder:
   - `red` → Red Phase flow
   - `green` → Green Phase flow
   - `refactor` → Refactor Phase flow
   - `done` → ask user if they want to start the next batch or run `/tdd-pair end`

---

## Subcommand: `status`

**Goal:** Read-only inspection of the current session.

1. Read `<cwd>/.claude/tdd-state.json`. If absent, print "No TDD pairing session in progress." and exit.
2. Print a structured summary:
   - Header: mode, spec path, started_at, updated_at
   - Batch table: id | name | status | phase | review_rounds | test count
   - Current pointer: batch_id, phase
   - Last 5 history entries (autonomous runs show the Zod review trail)
3. Do NOT modify state.

---

## Subcommand: `end`

**Goal:** Cleanly close out a session.

1. Read `<cwd>/.claude/tdd-state.json`. If absent, print "No TDD pairing session in progress." and exit.
2. Show the user a final summary (use the `status` output format).
3. Use `AskUserQuestion` to confirm: *Mark complete and archive*, *Mark complete and delete state file*, *Cancel (keep session active)*.
4. On *archive*: move the state file to `<cwd>/.claude/tdd-state.archive/<timestamp>.json`. On *delete*: `rm` the file. Either way, append `ended` to history before moving/deleting.

---

## Gate Protocol

Every phase boundary ends with a **gate**: the artifact just produced is reviewed before the loop advances. The gate has two implementations, selected by the session's `mode`. The phase flows below say "run the phase gate" — resolve it as follows.

### Interactive gate (`mode: "interactive"`)

Use `AskUserQuestion` with the phase's review options (listed in each flow). The human is the auditor. Their selection drives the transition. This is the original `/tdd-pair` behavior — unchanged.

### Autonomous gate (`mode: "autonomous"`)

The **Zod** agent is the auditor. For the current phase:

1. **Increment** the batch's `review_rounds`. Append `zod_review_started` (with phase + round) to history; write state.
2. **Dispatch Zod** via the Agent tool (older Claude Code versions call it `Task`) with `subagent_type: "Zod"`. If no agent named `Zod` is registered, dispatch a general-purpose agent instead and begin its prompt with "You are Zod, a meticulous principal-level code reviewer." Each dispatch is a fresh reviewer; the prompt MUST be self-contained and contain:
   - **The contract** — the absolute `spec_path` and the specific sections Zod reviews against (Public API, Design Decisions, Error States, Test Plan). *The spec is the yardstick.*
   - **The artifact** — the files written/modified this phase (paths + the diff or full contents), plus the test/lint/type-check output.
   - **The phase** and its **audit criteria** (from Ada's "What you audit at each layer"):
     - *red* → are assertions specific and atomic? Do test names describe behavior? Are inputs/expected outputs **derivable from the spec, not invented**? Does the batch cover the spec surface it claims?
     - *green* → does the code match the spec's Design Decisions? Were dependencies introduced the spec didn't permit? Are boundary/error cases handled as the spec requires? Plus a refactor-opportunity scan.
     - *refactor* → do the changes preserve behavior (tests still green)? Is the refactor justified, or churn?
   - **The non-negotiable instruction:** *"Review the artifact against the spec, NOT against itself. The implementation and tests were written by the same agent — watch specifically for tautological tests (assertions calibrated to the code rather than the contract), right-result-wrong-reason, hidden state, and silent type widening. Green tests are not a substitute for reading every line."* (This is the AI-generated-code review discipline: audit the contract, not the code.)
   - **Required output:** a list of findings (file and line, severity of critical/major/minor/nit, issue, suggested fix) ending in exactly one line `Verdict: <Approve | Approve with Concerns | Request Changes | Needs Discussion>`. A reply without that line counts as `Needs Discussion`.
3. **Resolve the verdict:**
   - `Approve` / `Approve with Concerns` → append `zod_approved`; record any concerns in the batch `notes`; **advance** the phase. (Concerns on an Approve are logged, not blocking — the loop continues.)
   - `Request Changes` / `Needs Discussion` → append `zod_rejected` (with round + a one-line summary). If `review_rounds < max_review_rounds`: **apply Zod's required changes to the artifact**, re-run tests/checks, and re-dispatch Zod (back to step 1). If `review_rounds >= max_review_rounds`: **escalate** (below).
4. **Escalation** (retry budget exhausted): set the batch `status = "blocked"`, write Zod's outstanding findings into `notes`, append `escalated_to_human`, persist state, then **STOP and surface to the human**: the phase, the round count, and Zod's findings. Do not advance, do not move to the next batch. The human resolves via `/tdd-pair resume` (retry autonomously, take over manually, or abort).
   - **Headless:** do not notify and do not wait. The run ends here with the JSON outcome (`status: "blocked"`, `blocked_reason`, the batch marked `blocked`, Zod's outstanding findings in `open_findings`).
   - **Send a `PushNotification`** (autonomous, non-headless only, and only if that tool exists). An autonomous run is exactly the "started it and walked away" case the notification exists for, and escalation is a hard stop that needs a human decision before anything else can happen. Keep it one line, under 200 chars, lead with the blocked batch and the reason — e.g. `tdd-pair blocked: batch 2 "Refill over time" — spec ambiguity on token refill, needs your call. /tdd-pair resume`. Send it once, at the moment of escalation; do not notify for routine phase approvals or batch advances. (Interactive mode never sends one — the human is already at the keyboard.)

**Why bounded:** unbounded review lets the typist and auditor thrash on a contested point indefinitely. Three rounds is enough to converge on a real fix; past that, the disagreement is usually a spec ambiguity only the human can resolve — which is exactly what escalation surfaces.

---

## Phase Flows (used by `start`, `auto`, and `resume`)

These flows execute the in-loop tactics. After each phase the state file is updated and the **phase gate** (Gate Protocol) reviews the artifact before advancing. On entering any phase, reset the batch's `review_rounds` to 0.

### Red Phase

1. State: `current_phase = "red"`, batch.status = "in_progress", batch.phase = "red", `review_rounds = 0`.
2. Append `batch_red_started` to history; write state.
3. Write **failing tests** for every test in the current batch. Tests should be specific, atomic, and named to describe behavior (per Ada's audit criteria). Assertions come from the spec — never calibrate them to code that doesn't exist yet.
   - Regression-guard tests that are immediately green ARE acceptable when needed to lock in existing behavior — call them out explicitly when returning results.
4. Run the test suite to confirm new tests fail for the right reasons (or are intentionally green guards).
5. Assemble the review payload: list of test files written/modified, test names, output showing each test's failure mode (or green-guard rationale).
6. **Run the phase gate.** Interactive options: *Approve tests, proceed to green*, *Revise tests*, *Pause session*. Autonomous: dispatch Zod with the red-phase criteria.
7. On approval: append `batch_red_complete` to history, set `current_phase = "green"`, update state, proceed to Green Phase.

### Green Phase

1. State: `current_phase = "green"`, batch.phase = "green", `review_rounds = 0`.
2. Append `batch_green_started` to history; write state.
3. Implement the **minimum code** to make the batch's tests pass. Resist over-engineering. Stay within the boundaries of the spec's Public API and Design Decisions.
4. Run tests AND code-quality checks (linter, type checker, formatter — whatever the project provides via `just`, `npm run`, etc.). Verify all tests pass and no new lint/type errors are introduced.
5. **Refactor review** (NOT a phase transition — just an analysis): scan the new code for duplication, naming issues, abstraction opportunities. Produce a list of recommended refactor steps with rationale (or "none recommended"). In autonomous mode, this scan is also part of what Zod audits.
6. **Determine the next batch's tests** to preview.
7. Assemble the review payload (per Ada's Loop Pairing protocol):
   1. The code that was implemented to pass the tests
   2. The refactor review results and recommended next steps (if any)
   3. The next batch of tests to implement in the next loop
8. **Run the phase gate.** Interactive options: *Approve, proceed to refactor*, *Apply specific refactor steps now*, *Revise green-phase code*, *Skip refactor and advance to next batch*, *Pause session*. Autonomous: dispatch Zod with the green-phase criteria; Zod's verdict determines whether refactor steps are required (→ refactor phase) or none are needed (→ advance).
9. On approval (with or without refactor): append `batch_green_complete` to history, set `current_phase = "refactor"` (or `"done"` if no refactor needed), update state, proceed accordingly.

### Refactor Phase

1. State: `current_phase = "refactor"`, batch.phase = "refactor", `review_rounds = 0`.
2. Append `batch_refactor_started` to history; write state.
3. Apply the refactor steps approved in the Green Phase gate (human-selected in interactive; Zod-required in autonomous).
4. Re-run tests and code-quality checks. ALL must remain green.
5. Assemble the review payload: diff of refactor changes, test/lint output.
6. **Run the phase gate.** Interactive options: *Approve refactor*, *Revise refactor*, *Revert refactor and advance*. Autonomous: dispatch Zod with the refactor-phase criteria (behavior preserved? churn vs. justified?).
7. On approval: append `batch_refactor_complete` to history, set batch.phase = "done", batch.status = "completed".

### Batch Advancement

1. If more batches remain: increment `current_batch_id` to the next pending batch, set `current_phase = "red"`, append `batch_advanced` to history, write state, optionally commit (per Ada's commit guidelines), then re-enter Red Phase.
2. If no batches remain: set `current_phase = "done"`, write state, prompt user to run `/tdd-pair end`.

---

## Optional: Git Commit Between Batches

If a git repository is detected (`<cwd>/.git` exists), after each batch's refactor (or green if refactor skipped) is approved, offer to commit per Ada's Conventional Commits guidelines:

- Type: `feat`, `fix`, `refactor`, `test` as appropriate.
- Scope: derived from the spec or batch name.
- Description: imperative mood, present tense.
- Body: explain WHY, not WHAT.

Use `AskUserQuestion` to confirm before committing. Never commit without explicit approval — **this holds in autonomous mode too, and in headless mode there is nothing to ask: do not offer, do not commit, do not stage.** Headless runs leave all changes in the working tree for the caller. Zod gates code quality, not the decision to commit; commits remain a human action. An autonomous run accumulates approved batches and presents them for commit when the human next engages (at completion or escalation).

---

## Headless Mode (`auto --headless`, `resume --headless`)

For unattended runs (`claude -p`, CI, an orchestrating CLI). Same engine as autonomous mode, with these rules:

1. **No prompts, ever.** Do not call `AskUserQuestion` or `PushNotification`; nobody is there to answer, and a prompt may hang or be silently denied. Every point that says "STOP and surface" or "pause for the human" instead **ends the run** with the outcome below.
2. **No commits, no staging, no branch creation, no history rewrites.** Leave all changes in the working tree.
3. **The caller owns the environment.** Expect a clean worktree on a feature branch cut from a fresh default branch; the pre-flight above only verifies it.
4. **The final message ends with exactly one fenced `json` block** conforming to `outcome.schema.json` (installed beside this file; schema version 1). Brief prose may precede it. Nothing may follow it.
5. **The outcome is advisory.** The caller validates it against the schema and re-runs tests itself; it never trusts `done` on its own word. Report only what you observed: run the project's test/lint/typecheck commands before writing the outcome and list any that fail in `failing_checks`. Never claim `done` with a failing check or an incomplete batch.

Statuses:

- `done` — every batch completed and approved; `failing_checks` empty.
- `blocked` — retry budget exhausted, unsafe starting state (on the default branch, existing session), or any other stop that needs a human. `blocked_reason` is required; put Zod's outstanding findings in `open_findings`.
- `needs_info` — the spec is not a usable contract (no Test Plan, untested Public API or Error States). `spec_gaps` is required, one entry per gap.

Example (blocked):

```json
{
  "schema_version": 1,
  "status": "blocked",
  "spec_path": "specs/rate-limiter.md",
  "base_branch": "main",
  "batches": [
    {"id": 1, "name": "Capacity and consumption", "status": "completed", "phase": "done", "review_rounds": 2, "tests": 3},
    {"id": 2, "name": "Refill over time", "status": "blocked", "phase": "red", "review_rounds": 3, "tests": 2}
  ],
  "failing_checks": [],
  "open_findings": [
    {"batch_id": 2, "phase": "red", "severity": "major", "summary": "Spec does not say whether refill is continuous or whole-token."}
  ],
  "blocked_reason": "Three review rounds exhausted on batch 2; spec ambiguity needs a decision.",
  "spec_gaps": []
}
```

Rate limits and crashes cannot be reported by the model; the caller detects them from the process, so a missing or invalid outcome block means the run failed.

---

## Worked Example

See `worked-example.md` in this skill's directory for a full autonomous run (batching, one reject/retry, one escalation). It is reference material; do not load it unless asked.

---

## Help Output (for missing/unknown subcommand)

```
/tdd-pair — TDD Loop Pairing Session orchestrator

Usage:
  /tdd-pair start <spec-path>   Initialize a HUMAN-gated session from a finalized spec.
  /tdd-pair auto <spec-path>    Initialize a ZOD-gated autonomous session (no human gates;
                                bounded retry → pause for human on impasse).
  /tdd-pair auto --headless <spec-path>
                                Autonomous, never prompts; ends with a JSON outcome.
  /tdd-pair resume [--headless] Continue an in-progress session (interactive or autonomous).
  /tdd-pair status              Show progress without modifying state.
  /tdd-pair end                 Close out the current session.

State file: <cwd>/.claude/tdd-state.json

The skill drives Ada's red → green → refactor cycle in test batches.
The skill is always the typist; the auditor is the human (start) or Zod (auto).
```

When asked for help OR when `$ARGUMENTS` is empty/unknown, print the block above verbatim and exit.
