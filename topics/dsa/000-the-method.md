---
title: The method
summary: How to use this catalogue, how to talk while solving, and the cue that names each of the 18 topics.
group: Start here
minutes: 6
sources:
- Zalando · Technical interview for software engineers | https://jobs.zalando.com/en/blog/technical-interview-for-software-engineers
- Grind 75 | https://www.techinterviewhandbook.org/grind75
- Blind 75 (original list) | https://www.teamblind.com/post/New-Year-Gift---Curated-List-of-Top-75-LeetCode-Questions-to-Save-Your-Time-OaM1orEU
---

Nothing in a coding round rewards having seen the problem before as much as it rewards recognising which *kind* of problem it is. That is what this topic trains: the cue in the wording that names the pattern, then the pattern, then the code.

## What's here

**89 problems in 18 topics**, for anyone preparing for a coding interview. Each topic opens with a short primer: what the technique is, the words in a problem that point to it, a Swift template, and the traps. Then its problems, easiest first.

No public dataset says which problems are asked most. LeetCode's company tags are paywalled and noisy, and the famous lists are curated rather than measured. So the set is built from the evidence that does exist: the lists most candidates and interviewers share (Blind 75, Grind 75), the problems German loops have been documented asking by name, and two that recent Apple frequency lists keep naming.

Each chapter carries its reason in the tag line:

- **G** — in the Blind 75 / Grind 75 core
- **Z** — asked by name in a documented German loop (Zalando, Sixt, Delivery Hero, N26)

Most are medium, the bar at most companies outside FAANG. The few hard ones are marked **optional**.

## Every problem, in the same shape

- **The statement and examples**, visible.
- **Starter code and tests**: the function with an empty body and the examples as tests, in two versions — a Swift Testing file for an Xcode test target, and a plain version that runs in a playground. Copy one, make it pass.
- Then, collapsed until you've tried: the pattern and the cue, the approach in plain words, a Swift solution (compiled and tested), a walk-through, the Swift-specific trap, and the follow-ups interviewers ask next.

## How a session runs

Two problems, about 25 minutes each.

1. **Open Xcode or a playground, not the solution.** Paste the chapter's starter code and run it: the examples fail until you solve it.
2. **Solve it with the clock running, 20 minutes, out loud.**
3. **Open the approach and compare, 5 minutes.** Not just "did I get it" — did you name the pattern from the same cue?
4. **Stuck at 20 minutes: stop.** Read the approach, close it, and re-solve it cold at the start of the next DSA session. Grinding past 20 minutes teaches endurance, not recognition.

## How to talk while solving

Zalando publicly recommends a structure for its coding round, and it works everywhere. It's called **REACTO**:

| Step | What you say |
|---|---|
| **R**epeat | The problem back in your own words. Catches misreads before they cost ten minutes. |
| **E**xamples | One normal case and the edge cases: empty, one element, duplicates, negatives. |
| **A**pproach | The pattern *and its complexity* — before you type anything. |
| **C**ode | Narrate decisions, not keystrokes. |
| **T**est | Walk one example through your code by hand. |
| **O**ptimise | What you'd change with more time, and what it costs. |

The step candidates skip is **A**. Saying *"this is a sliding window, O(n) time, O(k) space"* before typing is worth more than a clean solution written in silence. <!--private-->It is also the 90-second test in this programme: if you can't name the pattern by then, that's what gets logged.<!--/private--><!--public-->Give yourself ninety seconds to name it. Past that, you are not recognising the pattern, you are deriving it — which is a different skill and a slower one.<!--/public-->

## The cue that names each topic

| Topic | The cue in the wording | Typical cost |
|---|---|---|
| Arrays and hashing | "find a pair", "seen before", "group by", "count occurrences" | O(n) time, O(n) space |
| Prefix sums | "sum of a range", "subarray sums to k", "product of everything else" | O(n) build, O(1) query |
| Two pointers | a **sorted** array, pairs or triplets, "in place", palindromes | O(n), O(1) |
| Sliding window | "contiguous subarray / substring", "longest / shortest with a condition" | O(n) |
| Stack | matching pairs, nesting, "next greater", evaluate an expression | O(n) |
| Binary search | sorted input, or "minimum value that makes X possible" | O(log n) |
| Linked list | pointer rewiring, cycles, "nth from the end" | O(n), O(1) |
| Trees | hierarchy, "depth", "level", "ancestor", BST ordering | O(n), O(h) stack |
| Tries | "prefix", "starts with", a dictionary of words | O(length of word) |
| Heap | "k largest / smallest / closest", "top k", merge k sorted, a running median | O(n log k) |
| Backtracking | "all combinations / permutations / subsets", a path through a grid | exponential, by nature |
| Graphs | grids, "connected", "islands", spreading, dependencies | O(V + E) |
| Intervals | start/end pairs, overlaps, "meeting rooms" | O(n log n) for the sort |
| Greedy | "can you reach", "maximum sum of a run", a local best choice that never needs undoing | O(n) |
| 1-D dynamic programming | "number of ways", "minimum cost", choices that overlap | O(n) or O(n·k) |
| 2-D dynamic programming | a grid of paths, two strings compared | O(m·n) |
| Matrix | rotate, spiral, mark rows and columns, in place | O(m·n) |
| Bit manipulation | "count the 1s", "the missing / single number", without extra space | O(n) or O(1) |

## Swift traps worth saying out loud

These are the ones an interviewer notices:

- `String` isn't randomly indexable. Convert with `Array(s)` first, and say that it costs O(n).
- `Array.removeFirst()` is O(n). A BFS queue needs an index cursor, not a shrinking array.
- There's no `Deque` or `Heap` in the standard library, and `swift-collections` won't exist in a shared editor.
- A doubly-linked list needs a `class` with `weak var prev`, or it leaks.
- `dict[key, default: 0] += 1` is the idiomatic counter.
- `Int` traps on overflow where C wraps.
- A tuple isn't `Hashable`. Use a small `struct` or `[Int]` as a set key.
