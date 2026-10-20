---
title: The shape of the round
summary: How a session runs as a simulated 45-minute interview, what is graded, and how each question chapter is laid out.
minutes: 7
sources:
- weeeBox · Mobile System Design (the public exercise set and its grading criteria) | https://github.com/weeeBox/mobile-system-design
- System Design Handbook · Mobile system design interview | https://www.systemdesignhandbook.com/guides/mobile-system-design-interview/
- ByteByteGo · A framework for mobile system design interviews | https://bytebytego.com/courses/mobile-system-design-interview/a-framework-for-mobile-sd-interviews
---

At senior level this is usually the deciding round. What's graded is how you run 45 minutes, out
loud, while someone interrupts you.

The chapters are also meant to be **learned from**, and readable by someone who doesn't code. They
stay short on purpose: each opens with a **Words used in this chapter** glossary, and every
component is its job in one or two plain sentences, its interface, and the one or two choices
behind it.

Every question is written to be **performed, not read**. The prompt is at the top; the answer is
behind collapsed sections in the order a real round unfolds, including the interviewer's own lines.

## The 45 minutes

| Clock | Phase | What happens |
|---|---|---|
| 0:00–0:02 | The prompt | You repeat it back and say how you'll spend the time |
| 0:02–0:07 | Clarify | You ask; they answer; you state your assumptions |
| 0:07–0:12 | Scope | Out of scope **first**, then 3–5 features, then the non-functional ones that matter |
| 0:12–0:24 | High level | Say the idea · list the parts · sketch them · one line each · trace the key flows |
| 0:24–0:40 | Deep dives | They pick a component and push |
| 0:40–0:45 | Follow-ups and recap | Whatever they still want to probe, then the whole design in 60 seconds |

About 30 working minutes. Running out of time before the deep dive is the most common way a strong
candidate fails.

## How to run a session

1. **Timer on, standing, out loud, sketching** on paper or an iPad. Nothing open in front of you.
2. At each phase boundary, move on whether or not you're finished. That discipline *is* the skill.
3. When the 45 minutes are up, open the sections one at a time and mark each **clean**, **partial**
   or **missed**. Then work through the question bank: read each question, answer it out loud,
   and only then open the answer. Finish with the scorecard section.
<!--private-->4. Everything marked missed goes in the progress log and comes back later as a recall prompt.<!--/private--><!--public-->4. Keep the misses somewhere. A section you skip twice is a gap, not an oversight, and the second time is when it is worth reading up on.<!--/public-->

## What is actually graded

The public exercise set these prompts are drawn from publishes its criteria, and they are not what
candidates expect: clear communication and active listening · thoughtful requirement clarification ·
practical trade-off analysis · **honestly acknowledging the limits of your knowledge** · balancing
engineering quality against business timelines.

Only one line is about the design. In practice:

**Scoping out loud.** Three features done properly beat eight named. *"Offline editing is out of
scope for this pass"* is a positive signal.

**Trade-offs, not choices.** Every box arrives with the alternative you rejected and the condition
under which you'd switch.

**Staying client-side.** The classic failure is drifting into sharding and QPS. You're sizing a
cache and reasoning about what happens on a train with no signal.

**Naming the smaller version.** *"For a single screen, `AsyncImage` and `NSCache` are enough;
here's when they stop being enough"* reads as senior. Building a pipeline for a settings screen
does not.

**Saying what you don't know**, then reasoning about it anyway.

**Talking, not coding.** A design round doesn't ask you to write code. The furthest it goes is an
interface: a protocol, a model's fields, an endpoint. Mechanisms (the load-more guard, an
optimistic like) are explained as steps, in words, with a diagram when there's a race. The chapters
do the same: Swift appears only as interfaces, never as an implementation.

## The high-level design, in the order you say it

Twelve minutes, the same five steps every time.

1. **Say the idea (1 min).** Four sentences in plain words, before any box.
2. **List what you need (2 min).** The parts in drawing order, named by **what they do** ("feed
   repository", "image loader"), one job each. Write the list on the side of the board.
3. **Sketch them (4 min).** Three frames, one card per item on the list, arrows last.
4. **One line each (4 min).** Point at each card and say its job in one line. Say interfaces only
   for the domain protocols, the use case and the model; the interviewer will ask for two or three
   more if they want them. Nine cards with full interfaces in four minutes is 25 seconds each, and
   nobody manages that.
5. **Trace the key flows (1–2 min).** The main read and each important write (open the feed; like
   a post) across the cards.

## The parts, and the one rule for each

A board with twenty boxes doesn't read as thorough. It reads as someone who can't tell what matters.
**At most nine cards.** The promises the domain writes (protocols) are drawn as small chips above
the card that keeps them, and don't count.

Every card is exactly one of these roles, and its name ends with the role:

| Role | In plain words | Never |
|---|---|---|
| **View** | Draws one view state, passes taps on | Decides anything |
| **View model** | Owns this screen's state and turns data into one view state | Talks to the network or disk; holds what another screen shows |
| **Use case** | Carries out one user intent that has a product rule | Exists just to pass a call through |
| **Repository** | The one owner of one kind of data; turns the server's format into the app's | Combines other repositories |
| **Composite** | Reads two repositories and combines them into one model | Owns a source or writes anything |
| **Store** | In-memory state several screens show at once | Holds a rule, or saves to disk |
| **Database** | Saves records on the device | Calls the network |
| **Client** | Calls endpoints and returns the server's format | Knows the app's models |
| **Engine** | One long-running background job (sync, sending a queue) | Answers a screen's reads |
| **Policy** | A pure rule as a function | Does any I/O |

Three words get confused most often. A **store** is never a database. A **repository** never
returns the server's raw format; a type that does is a client. A **composite** only reads.

**A use case exists when the action has a product rule a product manager could state without
naming HTTP or storage:** "only the latest tap counts", "never charge twice", "a read marker only
moves forward". Delivery mechanics (retry with the same ID, drain a queue oldest-first, back off)
belong to the data part that owns the source. Loading a page has no rule, so it gets no use case.

**The one-blank test.** For every card, finish *"This card changes when ___"* with one phrase: the
screen's design, the screen's behaviour, a product rule, an endpoint, a storage schema, a
connection's lifecycle, how two sources combine, what several screens share, or a platform API. If
you need "and", split the card. Five smells point to a split:

1. It does I/O **and** holds UI state.
2. It owns a source **and** combines sources.
3. Its protocol hands out another source's data or events.
4. It only forwards calls. Delete it.
5. A hidden helper has state, I/O or a lifecycle. Then it's a part, not a helper. Only pure
   helpers (a mapper, a formatter) hide inside a card.

A few more rules every chapter follows:

- **Optimistic state lives with whoever owns what's shown.** One screen: the view model. Several
  screens: the store. The rule for sending writes lives in the use case either way.
- **A shared store goes on the first sketch only when the prompt puts the same state on several
  screens** (a cart badge and a cart screen). Otherwise it's a "grow later" step.
- **A protocol is shaped by its caller.** If two callers need different halves of one type, it
  keeps two small promises.
- **Name the endpoints** as `GET /feed`, `POST /posts/{id}/like`: on the card, in the idea, in the
  contract.
- **Separate required from later.** Required for the prompt, production considerations, optional
  follow-ups. Grow only when the interviewer asks.
- **On the board:** cards are the role in bold and the type name under it; arrows read
  `request → reply` in three words at most; dashed "implements" arrows point **up** at the
  protocol; blue presentation, purple domain, green data, orange network, grey dashed for something
  reused.

## Saying why those parts

Every one of these rounds reaches *"why these types and not one big one?"*. That question asks
whether you can justify a boundary, and SOLID is the vocabulary, used as reasons rather than names:

- **Single responsibility**: the one-blank test above. Different reasons to change, different types.
- **Open–closed**: new behaviour arrives as a new conformance, not another `if`.
- **Liskov**: the contract is behavioural. Each protocol says whether it throws or returns
  "unknown", what happens if the caller cancels (a write that must land still lands), and which
  thread it runs on. Every conformance must keep it.
- **Interface segregation**: a protocol shaped by its caller, so a fake needs one method, not twelve.
- **Dependency inversion**: the domain writes the protocols, the data layer keeps them, and the
  concrete types are injected at the start of the app. That's what makes the interesting race
  testable.

The caveat worth saying in the room: pushed too far, SOLID produces thirty one-method types.
*"I split where the reasons to change differ, not per noun."*

## The checklist to touch, briefly, in every answer

Data flow and ownership of state · networking (pagination, retry, cancellation) · caching (tiers,
keys, eviction) · offline behaviour and the write queue · concurrency (what's on the main actor, how
duplicate work is avoided) · memory and performance · metrics, feature flags, testing and rollout,
one sentence each.

## How each chapter is laid out

Visible: the prompt, the clock, and **what the question is really testing**. Then, collapsed: a
**Words used in this chapter** glossary, and the answer:

1. The interviewer answers your clarifying questions
2. Requirements and scope: what you should have said
3. The idea, in 30 seconds, before you draw anything
4. What we need: the parts in drawing order, with role, type name, layer and one job
5. The sketch, and how to draw it on your own board
6. Each component: its **job**, its **interface** (with what it promises on failure and
   cancellation), the choices behind it, and "why these parts, and no more"
7. Key flows through the sketch: one sequence diagram per main read or write
8. The server contract: endpoints and payloads
9–11. Deep dives, each opened by the line the interviewer would actually use
12. Failure modes, production and scale
13. Question bank: every area they can push on, each answer hidden behind its question, with a
    follow-up chain per area, because real rounds drill down rather than jump around
14. Scorecard: mark yourself 0, 1 or 2
15. The 60-second recap

You did it right if all four are true: you named out-of-scope first, every choice carried a rejected
alternative and a switch condition, you stayed client-side, and you could answer at least two
follow-ups before opening them. The question bank is the real test of the last one: an area where
you can't answer the first question out loud is the area to study next.
