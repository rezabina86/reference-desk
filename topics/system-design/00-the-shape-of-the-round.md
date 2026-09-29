---
title: The shape of the round
summary: How a session runs as a simulated 45-minute interview, what is graded, and how each question chapter is laid out.
minutes: 6
sources:
- weeeBox · Mobile System Design (the public exercise set and its grading criteria) | https://github.com/weeeBox/mobile-system-design
- System Design Handbook · Mobile system design interview | https://www.systemdesignhandbook.com/guides/mobile-system-design-interview/
---

At senior level this is usually the round that decides the outcome, and it is the one where knowing
the material and passing come apart most often. What's graded is how you run 45 minutes, out loud,
while someone interrupts you.

So every question here is written to be **performed, not read**. The prompt is at the top; the
whole answer is behind collapsed sections, in the order a real round unfolds — including the
interviewer's own lines: how they'd answer your clarifying questions, which component they'd pick
to go deep on, and what they'd push on next.

## The 45 minutes

| Clock | Phase | What happens |
|---|---|---|
| 0:00–0:02 | The prompt | You repeat it back and say how you'll spend the time |
| 0:02–0:07 | Clarify | You ask; they answer; you state your assumptions |
| 0:07–0:12 | Scope | Out of scope **first**, then 3–5 features, then the non-functional ones that matter |
| 0:12–0:24 | High level | The boxes, the flow, the contract, the types and why those types |
| 0:24–0:40 | Deep dives | They pick a component and push |
| 0:40–0:45 | Follow-ups and recap | Rapid fire, then the whole design in 60 seconds |

About 30 working minutes. Running out of time before the deep dive is the most common way a strong
candidate fails.

## How to run a session

1. **Timer on, standing, out loud, sketching** on paper or an iPad. Nothing open in front of you.
2. At each phase boundary, move on whether or not you're finished. That discipline *is* the skill.
3. When the 35 minutes are up, open the sections one at a time and mark each **clean**, **partial**
   or **missed**. Finish with the scorecard section.
<!--private-->4. Everything marked missed goes in the progress log and comes back later as a recall prompt.<!--/private--><!--public-->4. Keep the misses somewhere. A section you skip twice is a gap, not an oversight, and the second time is when it is worth reading up on.<!--/public-->

## What is actually graded

The public exercise set these prompts are drawn from publishes its criteria, and they are not what
candidates expect: clear communication and active listening · thoughtful requirement clarification ·
practical trade-off analysis · **honestly acknowledging the limits of your knowledge** · balancing
engineering quality against business timelines.

Read that list again. Only one line is about the design. The rest is about how you behave while
producing it. In practice that means:

**Scoping out loud.** Three features done properly beat eight named. *"Offline editing is out of
scope for this pass"* is a positive signal.

**Trade-offs, not choices.** Every box arrives with the alternative you rejected and the condition
under which you'd switch.

**Staying client-side.** The classic failure is drifting into sharding and QPS. You're sizing a
cache and reasoning about what happens on the U-Bahn with no signal.

**Naming the smaller version.** Saying *"for a single screen, `AsyncImage` and `NSCache` are
enough — here's when they stop being enough"* reads as senior. Building a pipeline for a settings
screen does not.

**Saying what you don't know**, then reasoning about it anyway.

## Components, and saying why those components

Every one of these rounds reaches *"why these types and not one big one?"*. That question is asking
whether you can justify a boundary, and the useful vocabulary for it is SOLID — used as reasons,
not names:

- **Single responsibility** — say what would make each type change. Different reasons, different types.
- **Open–closed** — new behaviour arrives as a new conformance, not as another `if` in the coordinator.
- **Liskov** — the contract is behavioural: every conformance must cancel, throw and be callable
  concurrently the same way, or callers written against the protocol break.
- **Interface segregation** — if a test double needs twelve methods to test one, the protocol is too fat.
- **Dependency inversion** — depend on protocols, inject the concrete types at the composition root.
  This is what makes the interesting race testable at all.

And the caveat worth saying in the room: SOLID came from class hierarchies; on iOS half of it lands
as value types and protocol witnesses, and pushed too far it produces thirty one-method types.
*"I split where the reasons to change differ, not per noun."*

## The checklist to touch, briefly, in every answer

Data flow and ownership of state · networking (protocol, pagination, retry, cancellation) · caching
(tiers, keys, eviction, invalidation) · offline behaviour and the mutation queue · concurrency
(what's on the main actor, how duplicate work is avoided) · memory and performance · observability,
feature flags, testing and rollout — one sentence each is enough for the last group.

## How each chapter is laid out

Visible: the prompt, the clock, and **what the question is really testing** — the framing, not the
answer. Then, collapsed:

1. The interviewer answers your clarifying questions
2. Requirements and scope — what you should have said
3. The design, on the whiteboard — a real diagram
4. The types, and the reasons behind them (SOLID, out loud)
5. API and data model
6–8. Deep dives, each opened by the line the interviewer would actually use
9. Failure modes and 10×
10. Rapid fire — the follow-ups
11. Scorecard — mark yourself, 0 / 1 / 2
12. The 60-second recap

You did it right if all four are true: you named out-of-scope first, every choice carried a rejected
alternative and a switch condition, you stayed client-side, and you could answer at least two
follow-ups before opening them.
