---
title: 00 · How the code-review round works
summary: What the interviewer is scoring when they hand you a Swift snippet, the order to say things in, and how to fix and test without rewriting.
minutes: 15
group: Start here
sources:
- Glassdoor · Delivery Hero Senior iOS — retain-cycle scenarios, small snippets | https://www.glassdoor.com/Interview/Delivery-Hero-Senior-IOS-Developer-Interview-Questions-EI_IE504556.0,13_KO14,34.htm
- Glassdoor · Revolut Senior iOS — escaping closures, GCD, cache with associated type | https://www.glassdoor.com/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Glassdoor · DoorDash iOS — debug a threading error in a sample project | https://www.glassdoor.com/Interview/DoorDash-IOS-Developer-Interview-Questions-EI_IE813073.0,8_KO9,22.htm
- PracHub · Code review interview guide — production risk over preference, smallest fix | https://prachub.com/resources/code-review-interview-guide-how-to-find-bugs-and-explain-trade-offs
- Apple · Migrating a test from XCTest — XCTest and Swift Testing side by side | https://developer.apple.com/documentation/testing/migratingfromxctest
---

*Written from the interviewer's side of the table.*

When I hand a candidate a snippet, I'm not checking whether they know Swift. I'm checking whether
I'd trust them to review my team's pull requests on a Tuesday afternoon. That means three things:
do they find what would hurt users, do they find it fast, and can they explain it so the author
learns something.

## The four shapes it comes in

| Shape | What you're given | What I'm scoring |
|---|---|---|
| **Review this PR** | 40–80 lines of plausible production code | How many real problems, in what order |
| **What does this print?** | 10–20 lines of closures, queues or value types | Whether your mental model of Swift is exact |
| **Review, then extend** | A review, then "now add X" on the same code | Whether your fix holds up when the code has to grow |
| **Find the bug** | A small project or screen that misbehaves | Whether you reason before you poke |

Most review rounds end the same way, whatever the shape: *"Good. Now fix it."* and then *"Now
write a few tests."* Both have a section below.

Delivery Hero, Revolut and European fintech scale-ups have all been reported using at least one
of these. At one fintech, a Senior iOS candidate had the round stopped after ten minutes for
finding too few issues — so treat volume and speed as part of the bar.

## The ten minutes

| Time | What you do |
|---|---|
| 0:00–1:00 | Read it silently, top to bottom. Say in one sentence what the code is trying to do. |
| 1:00–6:00 | One pass top to bottom. Say each finding as you reach it, one sentence each. |
| 6:00–8:30 | Second pass with the checklist below, for what the first pass skipped. |
| 8:30–10:00 | Name the two or three you'd block the merge on, and the order you'd fix them. |

The first sentence matters. It shows I can trust you read before you judged, and it often surfaces
the biggest problem: the code doing the wrong job in the wrong place.

## The order to say things in

Severity first. If you start with naming, I assume you can't see the rest. If the prompt names a
bug ("QA says…"), confirm that one first in a sentence — then go by severity.

1. **Crashes** — force unwraps, `try!`, `as!`, out-of-range indexes, deadlocks.
2. **Data races and wrong-thread UI** — shared mutable state, UI touched off the main actor.
3. **Security and privacy** — secrets in UserDefaults, personal data in URLs or logs.
4. **Leaks** — retain cycles, timers, observers, tasks that outlive their owner.
5. **User-visible bugs** — stale results, wrong cell content, missing error and empty states.
6. **Testability and architecture** — singletons, dependencies built inside, logic in the view.
7. **Performance** — work in `body`, decoding on main, no reuse, unbounded growth.
8. **Style** — naming, access control, `final`, dead code.

## What to scan for

When the first pass runs dry, scan for these. Each one is a likely finding.

- `!`, `try!`, `as!`, `[i]` on an array you didn't just check
- `DispatchQueue.main.sync`, `global()`, a captured `indexPath` or `tag`
- `self` inside a stored closure, `Timer`, `NotificationCenter`, a delegate that isn't `weak`
- `.shared`, or an object built inside a method (`URLSession.shared`, `DateFormatter()`)
- `UserDefaults`, values put into a URL, `print` or `NSLog`
- `Double` for money, `==` on floating-point numbers, `Date()` read inline
- A cell without `prepareForReuse`, a task nobody cancels, a result written without checking it's still wanted
- Missing loading, error and empty states
- Hard-coded user-facing strings, an icon-only button without an accessibility label

## How to say each one

One or two sentences, in three parts: **what** it is, **why** it matters to the user or the team,
**the fix**. Then move on. Don't rewrite the code unless I ask; the list is the deliverable.

Here is what four findings sound like, said out loud:

> "This screen loads a feed and downloads a photo per cell. First, the reported bug: cells are
> reused, so a slow download for row 3 can land in the cell now showing row 40 — I'd cancel the
> download in `prepareForReuse`. Second, the timer holds the screen strongly and is only
> invalidated in `deinit`, which can never run, so every visit leaks a screen that keeps refreshing
> — invalidate it in `viewDidDisappear`. Third, `refresh` updates the table from whatever thread
> the API calls back on — hop to main. And a nit: `as!` on dequeue; fine for most teams, I'd just
> mention it. I'd block on the first three."

Say what's fine, too. "This part is good, I wouldn't touch it" is a valid review comment. Inventing
nits on good code scores negative.

## When I say "now fix it"

Fix only the lines behind the blocking findings. Keep the snippet's shape: UIKit stays UIKit, a
completion handler can stay a completion handler, the storyboard stays a storyboard. Add at most
one new seam — a protocol or a closure the tests can replace — and only if the tests need it.

Say the rest out loud: "I'd also move this to an actor and add a cache, but not in this diff." A
rewrite costs you the time you need for the tests, and makes me review code I never asked for.
Every chapter's fix ends with a **Said out loud, not coded** line for exactly this.

## When I say "now write a few tests"

Three is plenty: the bug you just fixed, one edge case, one regression. Use *fakes* — small
stand-ins for the real network or database that you control — so the test gives the same answer
every run. If you need a fake, that's the seam your fix should have added.

Ask which framework the team uses. Many teams are still on XCTest; these chapters use Swift Testing.
The mapping is short:

| Swift Testing | XCTest |
|---|---|
| `@Test func savesTheToken()` | `func testSavesTheToken()` inside an `XCTestCase` |
| `#expect(a == b)` | `XCTAssertEqual(a, b)` |
| `try #require(x)` | `try XCTUnwrap(x)` |
| `await confirmation { … }` | `expectation(description:)` + `await fulfillment(of:)` |

## When you don't know

Don't bluff. Say what you'd check and keep going: "I'm not sure this callback is delivered on main
— I'd check the docs. If it isn't, the fix is to hop to the main actor." A doubt written as a
question is still a valid review comment.

## How I score it

| | Fail | Pass | Strong |
|---|---|---|---|
| Volume in 10 min | Under 6 | 10–14 | 15+ |
| Order | Style first | Severity mostly right | Severity first, grouped |
| Explanations | Names the smell | Says why it breaks | Says why and the fix, briefly |
| Threading | Misses it | Finds main-thread UI | Finds the race and the stale-result bug |
| The fix | Rewrites the file | Fixes the bugs, some extra | Minimal diff, says the rest out loud |
| Tone | "This is bad" | Neutral | Reads like a review you'd want to receive |

## After this round: the take-home and the debrief

Many processes follow this round with a take-home and a debrief where engineers review *your* code.
Review your own submission with the same checklist before you send it. In the debrief, defend each
trade-off in one sentence, and have a ready answer to "what would you do with more time?".

## The chapters in this section

Each chapter is one snippet in the shape interviewers actually use, and the chapters are grouped
by shape. The snippet is visible; everything else is collapsed, so you can try first. Timer on, out
loud, then open.

How to use a chapter:

1. **Read the prompt and the snippet.** Say out loud what the code is trying to do.
2. **Set a timer** — ten minutes for a review, five for a print puzzle — and list what you find.
3. **Stuck?** Open *A hint, if you're stuck*. It nudges without giving the answer away.
   Find-the-bug chapters also have *How I'd debug it*: the steps before reading any fix.
4. **Check yourself** against *The key* (or *Answers*). Count what you found, and in what order.
5. **Read *The idea behind it*** for anything you missed. It explains the concept from scratch,
   in plain words, so it sticks.
6. **Write your fix, then read *The fix*.** Compare the size of yours with it.
7. **Write the tests,** then open *Now write the tests* and compare which behaviours you covered.
   (Print puzzles have no fix, so they skip this step.)
8. **Answer *What I'd ask next*** out loud before opening it.

To run the snippets with autocomplete, make an iOS **App** project in Xcode with a unit-test
target, and add one file per chapter. Paste the snippet, wrap code you want to run in
`#Playground { … }` (`import Playgrounds`, Xcode 26 or later), pick an iPhone simulator, and open
the canvas (⌥⌘↩). A standalone `.swift` file or a macOS target won't work for UIKit snippets: they
build for the Mac, where `import UIKit` fails with "No such module".

Every chapter names the interview where its question was reported, or says plainly that it wasn't.
Each header ends with what was verified: Foundation-only snippets, fixes and tests were run with
Swift 6.4; UIKit, SwiftUI and Core Data tests ran on the iOS Simulator, and anything only checked by
hand says so.
