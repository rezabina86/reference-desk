---
title: 00 · How the live-coding round works
summary: The five shapes the iOS technical round actually takes at Uber, Doctolib, GetYourGuide, SumUp, Babbel, Revolut and others — what you're given, how long you get, and what the interviewer is scoring.
minutes: 15
group: Start here
sources:
- Uber · iOS onsite (2025) — an iOS debugging round on a broken app: async, main thread, races | https://medium.com/@ios-interview/uber-ios-interview-experience-questions-sunnyvale-ca-e0900c806cbb
- Uber · iOS developer, São Paulo (2024) — "iOS specialization": code review plus a live feature | https://www.jointaro.com/interviews/companies/uber/experiences/ios-developer-sao-paulo-sao-paulo-august-1-2024-no-offer-positive-90b310a5/
- Uber · mobile onsite — build a city weather app in the round | https://www.1point3acres.com/interview/thread/1032404
- Doctolib · Senior Mobile Engineer iOS posting — recruiter, pair programming, mobile app design, behavioural | https://builtin.com/job/senior-mobile-engineer-ios-xfm/3639313
- GetYourGuide · iOS senior reports — 48-hour take-home (tour reviews with pagination); pair coding on an existing codebase | https://www.glassdoor.com/Interview/GetYourGuide-IOS-Senior-Developer-Interview-Questions-EI_IE695237.0,12_KO13,33.htm
- SumUp · How we hire — technical assessment, team interview, bar raiser; candidates report "coding task or live task" | https://www.sumup.com/careers/how-we-hire/
- Babbel · The recruitment process — 7-day take-home + 90 min review, or 60 min live coding with instructions sent in advance | https://www.babbel.com/en/magazine/the-recruitment-process-at-babbel
- Revolut · Android and iOS loop — 2–3 sequential tasks, each stressing the last design; concurrency and tests expected | https://ophyai.com/blog/company-guides/revolut-android-ios-interview
- Dojo · iOS live-coding senior interview — migrate a shipped screen to a new async client; no AI tools | https://github.com/dojo-engineering/ios-live-coding-senior-interview
- Race Condition · Live-coding exercises — 45 minutes, build from an API, image caching as a hidden requirement | https://racecondition.software/blog/live-challenges/
---

*Written from the interviewer's side of the table. Every claim about a company comes from candidate
reports or the company's own hiring page, linked above. Processes change by team, level and year, so
ask your recruiter which shape you'll get. They'll usually tell you.*

## The five shapes

| Shape | What you get | Time | Reported at |
|---|---|---|---|
| **A · Fix the broken app** | A small app that builds but misbehaves: async bugs, UI off the main thread, a race | 45–60 min | Uber onsite ("iOS debugging") |
| **B · Build it from nothing** | An API (or a fake), a screenshot or two, an empty project | 45–60 min | Uber (weather app, image search; UI in code, no storyboards), SumUp (live task against a weather API), most "live task" options |
| **C · Review it, then extend it** | An existing project you've never seen; review it, then add a feature with the interviewer | 60 min | Uber São Paulo (code review + live feature), GetYourGuide (pair coding on an existing codebase), Doctolib (pair programming), Dojo (migrate a shipped screen) |
| **D · Requirements that keep coming** | One task, then a second and a third, each stressing what you built first | 60–120 min | Revolut (cache → download → thread safety → tests) |
| **E · Defend your take-home, then change it** | Your own take-home, reviewed live by two engineers; then "now switch to the paged endpoint" | 60–90 min | Babbel (90 min with two seniors), SumUp ("why did you do this or that"), GetYourGuide (reviews with pagination), Trade Republic, Rightmove |

Some companies let you choose. Babbel and SumUp both offer a take-home or a live session. Babbel
sends the instructions and the structure of the live session *before* the call, so read them and set up
the project in advance.

## The rules you'll be given

- **Your machine, your Xcode, screen shared.** The interviewer watches and answers questions about the
  requirements. Some use an online editor that can't run code (reported at GetYourGuide); then the review
  is the whole point.
- **No AI assistants.** Dojo says so in writing, and other reports repeat it. Turn off Copilot and
  Xcode's predictive completion before the call.
- **Documentation is usually fine.** Searching for an API you can't remember costs minutes. Practise
  until you don't need to.
- **UIKit or SwiftUI is your choice**, unless they say otherwise. One Uber round asked for UIKit in code
  with no storyboards.
- **80% done loses to 100% done.** In build rounds, a candidate who finishes every requirement beats a
  candidate with a nicer architecture and a missing screen. Scope down early and out loud.

## What's scored in every shape

| Signal | What it looks like |
|---|---|
| **Reads before acting** | Reads the whole compiler error, the console, the brief, and says what they think before changing anything |
| **Asks the question that changes the code** | "Two currencies — one total each?", "Does pending count?", "Is the list paged?" |
| **Finds the cause, not the symptom** | Removes the `append`, rather than calling `removeDuplicates()` on the result |
| **Covers the states** | Loading, empty, error, no results, cancelled — not only the happy path |
| **Modern and correct concurrency** | Main-actor UI, no stray GCD hops, cancellation treated as normal |
| **Testable on purpose** | Injects the service early, because the last ten minutes are tests |
| **Talks the whole time** | No thirty-second silences; says what they're checking and why |

## What sinks the round

- Ten minutes in, it still doesn't build, and you can't say why.
- You fix the symptom, and the interviewer's next requirement breaks it again.
- You build the feature before asking what it means.
- Nothing is injectable, so the "now test it" part has nothing to stand on.
- In a build round, you polish one screen and never reach the second.

## The rounds

Each round is a real project in `LiveCodingLab`: a small app that's broken in realistic ways. You fix it, add a
feature on top of your fixes, and test it. Each is labelled with the shape and the companies whose reports it copies.

| Round | Shape | Flavour of | What breaks, and what you add |
|---|---|---|---|
| 01 · The transactions that don't add up | C | Uber São Paulo, GetYourGuide, Doctolib | A name clash with SwiftUI, rows that don't open, refresh that doubles the list → merchant search and a spend total |
| 02 · The driver who drives backwards | A | Uber's iOS debugging round | A Swift 6 build error, a frozen screen, an ETA that jumps back up, tracking that never stops → an "almost here" banner and Cancel ride |
| 03 · The reviews that won't stop loading | C | GetYourGuide, Rightmove | A cancelled request shown as an error, a whole-number rating, an end of list that wipes the screen → a cursor endpoint and a star filter |
| 04 · The photo from another row | D | Revolut | UIKit: a crash on launch, wrong photos in reused cells, triple downloads → shared in-flight downloads, then a memory cap |
| 05 · The flag that was never off | C | Dojo | A live unfinished feature, a toggle that doesn't stick, tests that pass in one order only → migrate to an async flag client that can fail |
| 06 · The basket that charges twice | C | Uber São Paulo, fintech reviews | Money in `Double`, stale totals, negative quantities, a double charge → promotion codes, where every rule needs a question first |
