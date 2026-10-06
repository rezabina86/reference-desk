---
title: 24 · Daily Temperatures
summary: For each day in a list of temperatures, count how many days you'd wait for a strictly warmer one.
group: Stack
minutes: 25
sources:
- LeetCode 739 · Daily Temperatures | https://leetcode.com/problems/daily-temperatures/
- Swift standard library · Array.last | https://developer.apple.com/documentation/swift/array/last
---

*Medium*

You get the daily temperatures for a run of days, one integer per day. For every day, work out how many days later the first strictly warmer day comes. If no later day is warmer, the answer for that day is 0. Return the answers as a list of the same length. A day with the *same* temperature doesn't count as warmer.

| Temperatures | Answer |
|---|---|
| `[70, 68, 72, 71, 75]` | `[2, 1, 2, 1, 0]` |
| `[80, 70, 60]` | `[0, 0, 0]` — only getting colder |
| `[50, 50, 51]` | `[2, 1, 0]` — equal isn't warmer; the edge case |

Constraints that matter: up to 100,000 days, temperatures between 30 and 100. Looking ahead from every day is O(n²), up to ten billion steps; the target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct DailyTemperaturesTests {

    @Test(arguments: [
        ([70, 68, 72, 71, 75], [2, 1, 2, 1, 0]),
        ([80, 70, 60], [0, 0, 0]),
        ([50, 50, 51], [2, 1, 0]),
    ])
    func returnsTheDaysUntilAStrictlyWarmerDay(temperatures: [Int], expected: [Int]) {
        #expect(dailyTemperatures(temperatures) == expected)
    }

    // MARK: - Privates
    private func dailyTemperatures(_ temperatures: [Int]) -> [Int] {
        []
    }
}
```

In a playground:

```swift
func dailyTemperatures(_ temperatures: [Int]) -> [Int] {
    [] // your solution
}

let cases: [([Int], [Int])] = [
    ([70, 68, 72, 71, 75], [2, 1, 2, 1, 0]),
    ([80, 70, 60], [0, 0, 0]),
    ([50, 50, 51], [2, 1, 0]),
]
for (temperatures, expected) in cases {
    let got = dailyTemperatures(temperatures)
    print(got == expected ? "PASS" : "FAIL", temperatures, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Monotonic stack.** The cue is *"for each element, the next one that is greater"*. Every day waits for something in the future; a warm day can answer many waiting days at once, and the ones it answers are always the most recent, coldest ones.
:::

::: Approach
Walk through the days in order, keeping a pile of days that are still waiting for a warmer one. When a new day arrives, look at the top of the pile: if that day was colder than today, today is its answer — record the gap in days and take it off the pile. Keep doing that until the top day is as warm as today or the pile is empty. Then put today on the pile to wait. Days left on the pile at the end never found a warmer day, so they keep the answer 0.

The pile is always ordered from warmest at the bottom to coldest at the top, because a colder day never stays below a warmer one — it gets answered and removed. Time O(n): every day is put on the pile once and taken off at most once, so the inner loop does at most n removals across the whole run. Space O(n): an only-colder run waits on the pile together.
:::

::: Swift solution
```swift
func dailyTemperatures(_ temperatures: [Int]) -> [Int] {
    var answer = [Int](repeating: 0, count: temperatures.count)
    var waiting: [Int] = []                       // indices of days still waiting, coldest on top

    for (day, temperature) in temperatures.enumerated() {
        while let colder = waiting.last, temperatures[colder] < temperature {
            waiting.removeLast()
            answer[colder] = day - colder
        }
        waiting.append(day)
    }
    return answer
}
```

The stack holds day *indices*, not temperatures: the answer is a distance, and the temperature is one subscript away. The `<` is strict on purpose — with `<=`, the first 50 in `[50, 50, 51]` would be answered by the second 50.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (empty list, one day, strictly rising, all equal), and 3,000 random lists of up to 15 days with many repeated temperatures, checked against a brute force that scans forward from every day.
:::

::: Walk it through
**`[70, 68, 72, 71, 75]`**

| Day | Temp | Pops (day: answer) | Waiting after (day:temp) |
|---|---|---|---|
| 0 | 70 | — | 0:70 |
| 1 | 68 | — | 0:70 1:68 |
| 2 | 72 | 1: 2−1 = 1, 0: 2−0 = 2 | 2:72 |
| 3 | 71 | — | 2:72 3:71 |
| 4 | 75 | 3: 1, 2: 2 | 4:75 |

Day 4 is left waiting and keeps 0. Answer `[2, 1, 2, 1, 0]`. Day 2 answers two days in one visit — that's what makes it linear.

**`[50, 50, 51]`** — day 0 waits. Day 1 is 50, not warmer than 50, so nothing pops; it waits on top. Day 2 is 51: it answers day 1 (gap 1), then day 0 (gap 2). Answer `[2, 1, 0]`.
:::

::: The Swift trap
**`while let` with a condition after the comma is the idiom — and it stops on the first false.** `while let colder = waiting.last, temperatures[colder] < temperature` unwraps the top and tests it in one line; when the stack is empty, `last` is `nil` and the loop ends without a crash. The common mistake is writing `while !waiting.isEmpty && temperatures[waiting.last!] < temperature`, which works but force-unwraps, or pushing temperatures instead of indices and then having no way to compute `day - colder`. Also: `[Int](repeating: 0, count:)` pre-fills the "never warmer" answer, so the days left on the stack need no clean-up pass.
:::

::: What they ask next
- **"Use O(1) extra space besides the answer."** → Walk from the right; for each day, jump forward using answers already computed (`j += answer[j]`) until a warmer day or a 0 is found. Still amortised O(n).
- **"Return the warmer temperature itself, not the wait."** → Same stack; record `temperature` instead of `day - colder`.
- **"Previous warmer day instead of next."** → Walk the same way, but pop every day that is *not* warmer than today (`<=`), then read the top: whatever remains is the previous warmer day, or none if the stack is empty.
:::
