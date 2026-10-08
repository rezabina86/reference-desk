---
title: 00 · How the code-review round works
summary: What the interviewer is scoring when they hand you a Swift snippet, and the order to say things in.
minutes: 15
group: Start here
sources:
- Glassdoor · Delivery Hero Senior iOS — retain-cycle scenarios, small snippets | https://www.glassdoor.com/Interview/Delivery-Hero-Senior-IOS-Developer-Interview-Questions-EI_IE504556.0,13_KO14,34.htm
- Glassdoor · Revolut Senior iOS — escaping closures, GCD, cache with associated type | https://www.glassdoor.com/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Glassdoor · DoorDash iOS — debug a threading error in a sample project | https://www.glassdoor.com/Interview/DoorDash-IOS-Developer-Interview-Questions-EI_IE813073.0,8_KO9,22.htm
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
| **Find the bug** | A small project or screen that misbehaves | Whether you reason before you poke |
| **Review, then extend** | A review, then "now add X" on the same code | Whether your fix holds up when the code has to grow |

Delivery Hero, Revolut and European fintech scale-ups have all been reported using at least one
of these. At one fintech, a Senior iOS candidate had the round stopped after ten minutes for finding too few issues — so treat
volume and speed as part of the bar.

## The order to say things in

Severity first. If you start with naming, I assume you can't see the rest.

1. **Crashes** — force unwraps, `try!`, out-of-range indexes, deadlocks.
2. **Data races and wrong-thread UI** — shared mutable state, UI touched off the main actor.
3. **Security and privacy** — secrets in UserDefaults, personal data in URLs or logs.
4. **Leaks** — retain cycles, timers, observers, tasks that outlive their owner.
5. **User-visible bugs** — stale results, wrong cell content, missing error and empty states.
6. **Testability and architecture** — singletons, dependencies built inside, logic in the view.
7. **Performance** — work in `body`, decoding on main, no reuse, unbounded growth.
8. **Style** — naming, access control, `final`, dead code.

## How to say each one

One sentence each, in three parts: **what** it is, **why** it matters to the user or the team,
**the fix**. "`onSelect` captures `self` strongly and is stored on `self`, so the screen never
deallocates — capture `[weak self]`." Then move on. Don't rewrite the code unless I ask; the list
is the deliverable.

## The first sixty seconds

Read the whole thing silently once. Then say in one sentence what the code is trying to do. It
shows me you read it before you judged it, and it often surfaces the biggest problem: the code
doing the wrong job in the wrong place.

## How I score it

| | Fail | Pass | Strong |
|---|---|---|---|
| Volume in 10 min | Under 6 | 10–14 | 15+ |
| Order | Style first | Severity mostly right | Severity first, grouped |
| Explanations | Names the smell | Says why it breaks | Says why and the fix, briefly |
| Threading | Misses it | Finds main-thread UI | Finds the race and the stale-result bug |
| Tone | "This is bad" | Neutral | Reads like a review you'd want to receive |

## The chapters in this section

Each chapter is one snippet in the shape interviewers actually use, and the chapters are grouped
by shape. The snippet is visible; everything else is collapsed, so you can try first. Timer on, out
loud, then open.

How to use a chapter:

1. **Read the prompt and the snippet.** Say out loud what the code is trying to do.
2. **Set a timer** — ten minutes for a review, five for a print puzzle — and list what you find.
3. **Stuck?** Open *A hint, if you're stuck*. It nudges without giving the answer away.
4. **Check yourself** against *The key* (or *Answers*). Count what you found, and in what order.
5. **Read *The idea behind it*** for anything you missed. It explains the concept from scratch,
   in plain words, so it sticks.
6. **Read the fix.**
7. **Write the tests.** Many rounds end with "good — now write a few unit tests for your fix".
   Write yours before opening *Now write the tests*, then compare which behaviours you covered.
   (Print puzzles have no fix, so they skip this step.)
8. **Answer *What I'd ask next*** out loud before opening it.

To run the snippets with autocomplete, make an iOS **App** project in Xcode with a unit-test
target, and add one file per chapter. Paste the snippet, wrap code you want to run in
`#Playground { … }` (`import Playgrounds`, Xcode 26 or later), pick an iPhone simulator, and open
the canvas (⌥⌘↩). A standalone `.swift` file or a macOS target won't work for UIKit snippets: they
build for the Mac, where `import UIKit` fails with "No such module".

Every chapter names the interview where its question was reported, or says plainly that it wasn't.
Foundation-only snippets and fixes were compiled and run with Swift 6 (each chapter names the exact
version); UIKit, SwiftUI and Core Data ones are marked: their fixes typecheck against the iOS SDK,
but their runtime behaviour was checked by hand.
