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
| 0:12–0:24 | High level | Say the idea · list the components · sketch them · explain each · trace one request |
| 0:24–0:40 | Deep dives | They pick a component and push |
| 0:40–0:45 | Follow-ups and recap | Whatever they still want to probe, then the whole design in 60 seconds |

About 30 working minutes. Running out of time before the deep dive is the most common way a strong
candidate fails.

## How to run a session

1. **Timer on, standing, out loud, sketching** on paper or an iPad. Nothing open in front of you.
2. At each phase boundary, move on whether or not you're finished. That discipline *is* the skill.
3. When the 35 minutes are up, open the sections one at a time and mark each **clean**, **partial**
   or **missed**. Then work through the question bank: read each question, answer it out loud,
   and only then open the answer. Finish with the scorecard section.
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

**Talking, not coding.** A design round doesn't ask you to write code. The furthest it goes is an
interface: a protocol, a model's fields, an endpoint. Mechanisms (the load-more guard, request
dedupe, an optimistic like) are explained as steps, in words, with a diagram when there's a race.
So the chapters do the same: Swift appears only as interfaces, never as an implementation.

## The high-level design, in the order you say it

The twelve minutes of high-level design run in the same five steps every time. Each step makes the
next one easy to follow, which is what the interviewer is grading.

1. **Say the idea (1 min).** Four sentences in plain words, before any box. If they stop you here,
   they already know the shape of the answer.
2. **List what you need (2 min).** The components, in the order you'll draw them, one job each.
   Write the list on the side of the board.
3. **Sketch them (4 min).** Three frames, one card per item on the list, arrows last.
4. **Explain each one (4 min).** Point at each card: what it owns, why it exists, the choice inside it
   and the alternative you rejected. This is where "why MVVM?" gets answered.
5. **Trace one request (1 min).** One real flow across the cards, so they see them work together.

## Keep the whiteboard simple

A board with twenty boxes doesn't read as thorough. It reads as someone who can't tell which parts
matter, and it eats the minutes the deep dives need. The rules every chapter here follows:

- **Three layers for an app question.** *Presentation* (the view and the view model that owns the
  screen's state), *domain* (plain models and the protocol the view model depends on), *data* (the
  implementation that decides between network and disk). No use-case classes at this size: a
  `LoadNextPageUseCase` that only forwards a call is ceremony, and interviewers read it as such.
  A library question (an image loader, an analytics SDK) isn't an app, so it gets three layers of its
  own instead: *API* (what callers touch), *core* (the coordinator), *I/O* (loaders, caches, codecs).
- **About seven or eight cards**, at most three side by side. Something that lives inside another
  component (a cache the coordinator owns) is written inside that card. Anything reused from an
  earlier question is one dashed card, not its insides.
- **One colour per layer**, the same in every chapter and on your own board: blue for presentation
  or API, purple for domain or core, green for data or I/O, orange for anything that crosses the
  network, grey and dashed for something reused.
- **A card earns its place** only if you can say in one sentence what it owns that nothing else does.
- **Draw one protocol seam, not every one.** Show interface and implementation as separate cards
  only at the boundary that defines the architecture (usually the repository), with a dashed
  "implemented by" line to the data layer. That card is dependency inversion on the board. Then say
  it once: *"Everything else is behind a protocol too, for tests. I'm drawing the one that matters."*
- **Start simple, grow under pressure.** Every extra component (an outbox, a shared store, a
  socket) waits until the interviewer pushes on that area. Adding it then, with the reason, scores
  better than having drawn it at minute twelve.

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
3. The idea, in 30 seconds — what you say before drawing anything
4. What we need — the components, in drawing order, one job each
5. The sketch — the diagram, and how to draw it on your own board step by step
6. Each component, one at a time — what it owns, why, the choice inside it (SOLID, out loud)
7. One request through the sketch — a sequence diagram of one real flow
8. API and data model
9–11. Deep dives, each opened by the line the interviewer would actually use
12. Failure modes and 10×
13. Question bank — every area they can push on, grouped by the checklist above, each answer
    hidden behind its question, and a follow-up chain per area, because real rounds drill down
    rather than jump around
14. Scorecard — mark yourself, 0 / 1 / 2
15. The 60-second recap

You did it right if all four are true: you named out-of-scope first, every choice carried a rejected
alternative and a switch condition, you stayed client-side, and you could answer at least two
follow-ups before opening them. The question bank is the real test of the last one: an area where you
can't answer the first question out loud is the area to study next.
