---
title: 29 · Koko Eating Bananas
summary: Find the slowest steady eating speed that still finishes every pile of bananas within a given number of hours.
group: Binary search
minutes: 25
sources:
- LeetCode 875 · Koko Eating Bananas | https://leetcode.com/problems/koko-eating-bananas/
- Swift standard library · Sequence.reduce(_:_:) | https://developer.apple.com/documentation/swift/sequence/reduce(_:_:)
---

*Medium*

There are several piles of bananas, given as a list of pile sizes, and a number of hours. Each hour, the eater picks one pile and eats up to k bananas from it, where k is a fixed speed they choose in advance. If the pile has fewer than k left, they finish it and wait out the rest of that hour — they never move to a second pile within an hour. Return the smallest whole-number speed k that finishes every pile within the hours given. The hours are always at least the number of piles, so some speed always works.

| Piles | Hours | Answer |
|---|---|---|
| `[5, 9, 4]` | `6` | `4` — 2 + 3 + 1 = 6 hours; speed 3 needs 2 + 3 + 2 = 7 |
| `[12, 7, 20]` | `3` | `20` — one hour per pile, so the biggest pile sets the speed; the edge case |
| `[8]` | `10` | `1` — plenty of time, the slowest speed works |

Constraints that matter: up to 10,000 piles, each up to a billion bananas, hours up to a billion. Trying every speed from 1 upward can take a billion steps, each scanning all piles; the target is O(n log m), where m is the largest pile.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct KokoEatingBananasTests {

    @Test(arguments: [
        ([5, 9, 4], 6, 4),
        ([12, 7, 20], 3, 20),
        ([8], 10, 1),
    ])
    func returnsTheSlowestSpeedThatFinishesInTime(piles: [Int], hours: Int, expected: Int) {
        #expect(minEatingSpeed(piles, hours) == expected)
    }

    // MARK: - Privates
    private func minEatingSpeed(_ piles: [Int], _ hours: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func minEatingSpeed(_ piles: [Int], _ hours: Int) -> Int {
    0 // your solution
}

let cases: [([Int], Int, Int)] = [
    ([5, 9, 4], 6, 4),
    ([12, 7, 20], 3, 20),
    ([8], 10, 1),
]
for (piles, hours, expected) in cases {
    let got = minEatingSpeed(piles, hours)
    print(got == expected ? "PASS" : "FAIL", piles, hours, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Binary search on the answer.** The cue is *"the minimum speed such that it finishes in time"*. Nothing in the input is sorted — but the answers to "does speed k work?" are: too slow, too slow, …, fast enough, fast enough. Any speed above a working speed also works. That one flip is what binary search finds.
:::

::: Approach
The answer lies between 1 banana per hour and the size of the biggest pile — eating faster than the biggest pile never saves an hour, because each pile takes at least one hour anyway. For any speed, the hours needed are easy to count: each pile takes its size divided by the speed, rounded up, and you add those up. So try the speed halfway through the range. If it finishes in time, the answer is that speed or a slower one; if not, the answer is faster. Halve the range until one speed is left.

Time O(n log m): about log₂ m guesses (30 for a billion), each adding up n piles. Space O(1).
:::

::: Swift solution
```swift
func minEatingSpeed(_ piles: [Int], _ hours: Int) -> Int {
    var low = 1
    var high = piles.max()!                       // eating the biggest pile in one hour always works

    while low < high {
        let speed = low + (high - low) / 2
        let needed = piles.reduce(0) { $0 + ($1 + speed - 1) / speed }   // whole hours, rounded up
        if needed <= hours {
            high = speed                          // fast enough: try slower
        } else {
            low = speed + 1                       // too slow
        }
    }
    return low
}
```

`(pile + speed - 1) / speed` is division rounded up, in integers: 9 bananas at speed 4 is (9 + 3) / 4 = 3 hours. `high = speed` keeps a working speed in range because it might be the answer; `low = speed + 1` drops a failing one for good.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (one pile of one banana, one pile of a billion in 2 hours, equal piles with hours equal to and one less than the total at speed 3, two piles of a billion in 3 hours), and 3,000 random cases with piles up to 30 checked against a brute force that tries every speed from 1 upward.
:::

::: Walk it through
**`[5, 9, 4]`, 6 hours** — the range is 1…9.

| low | high | speed | Hours needed | Action |
|---|---|---|---|---|
| 1 | 9 | 5 | 1 + 2 + 1 = 4 ≤ 6 | high = 5 |
| 1 | 5 | 3 | 2 + 3 + 2 = 7 > 6 | low = 4 |
| 4 | 5 | 4 | 2 + 3 + 1 = 6 ≤ 6 | high = 4 |
| 4 | 4 | — | low == high | return 4 |

**`[12, 7, 20]`, 3 hours** — three piles in three hours means one hour each, so only speed 20 works. The range is 1…20; every guess below 20 needs more than 3 hours and pushes `low` up, until `low` reaches 20. The answer is the top of the range, which is why the range must *include* the biggest pile.
:::

::: The Swift trap
**Round up with integers, not with `ceil`.** The textbook formula `ceil(Double(pile) / Double(speed))` needs Foundation, converts to floating point, and comes back as a `Double` you then convert again. It works for these sizes, but it's slower in the inner loop and invites `Int(…)` conversion mistakes. `(pile + speed - 1) / speed` stays in `Int` and is exact. On overflow: the hour total can reach 10,000 piles × a billion = 10¹³ at speed 1, which is fine for Swift's `Int` — 64 bits on every current Apple platform — but would overflow a 32-bit `Int32`, and in Swift that's a crash, not a wrong answer.
:::

::: What they ask next
- **"Ship packages within D days: the smallest boat capacity."** → Same shape: the range is from the heaviest package to the total weight, and the check is a greedy pass that counts days.
- **"Split an array into k parts to minimise the largest part's sum."** → The same binary search on the answer, with a greedy "how many parts do I need at this limit" check.
- **"Can you narrow the starting range?"** → The lower end can start at the total divided by hours, rounded up — no speed below that can possibly fit — but it doesn't change the complexity.
:::
