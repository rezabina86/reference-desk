---
title: 70 · Maximum Subarray
summary: Find the largest total you can get by adding up a run of consecutive numbers from a list that may contain negatives.
group: Greedy
minutes: 25
sources:
- LeetCode 53 · Maximum Subarray | https://leetcode.com/problems/maximum-subarray/
- The Swift Programming Language · Overflow Operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/#Overflow-Operators
---

*Medium · G*

You get a list of whole numbers, some of which may be negative. Choose a run of one or more **consecutive** numbers and add them up. Return the largest total any such run can have. The run can't be empty, so when every number is negative, the answer is the least negative one.

| Numbers | Answer |
|---|---|
| `[-3, 4, -1, 2, -5, 3]` | `5` — the run `4, -1, 2` |
| `[-4, -2, -7]` | `-2` — the run is just `-2` |
| `[7]` | `7` |

Constraints that matter: up to 100,000 numbers, each between −10,000 and 10,000, and at least one number. Adding up every run is O(n²); the target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MaximumSubarrayTests {

    @Test(arguments: [
        ([-3, 4, -1, 2, -5, 3], 5),
        ([-4, -2, -7], -2),
        ([7], 7),
    ])
    func returnsTheLargestSumOfAConsecutiveRun(numbers: [Int], expected: Int) {
        #expect(maxSubArray(numbers) == expected)
    }

    // MARK: - Privates
    private func maxSubArray(_ numbers: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func maxSubArray(_ numbers: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([-3, 4, -1, 2, -5, 3], 5),
    ([-4, -2, -7], -2),
    ([7], 7),
]
for (numbers, expected) in cases {
    let got = maxSubArray(numbers)
    print(got == expected ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Greedy running best — Kadane's algorithm.** The cue is *"largest sum"* of a *consecutive* run, with *negatives* allowed. At each number, the best run that ends right there either continues the best run that ended one step earlier, or starts fresh at this number — whichever is bigger.
:::

::: Approach
Walk along the list carrying one number: the best total of a run that ends at the current position. For each new number, ask whether the run so far helps or hurts. If the run so far has a positive total, adding the new number to it beats starting over; if its total is negative or zero, it only drags things down, so drop it and start a new run at this number. Keep a second number for the best total seen anywhere, and update it after every step.

Time O(n): one pass with constant work per number. Space O(1): two variables.
:::

::: Swift solution
```swift
func maxSubArray(_ numbers: [Int]) -> Int {
    var current = numbers[0]
    var best = numbers[0]
    for number in numbers.dropFirst() {
        current = max(number, current + number)  // extend the run, or start over here
        best = max(best, current)
    }
    return best
}
```

Both variables start at the first number, not at 0. Starting `best` at 0 is the classic bug: it reports 0 for `[-4, -2, -7]`, a total no non-empty run has.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (a single zero, all positive, a big negative between two positives, a value near `Int.min` that would trap with an `Int.min` start), and 3,000 random lists checked against a brute force that adds up every run.
:::

::: Walk it through
**`[-3, 4, -1, 2, -5, 3]`**

| Number | Extend: current + number | Restart: number | Current | Best |
|---|---|---|---|---|
| −3 | — | — | −3 | −3 |
| 4 | 1 | 4 | 4 | 4 |
| −1 | 3 | −1 | 3 | 4 |
| 2 | 5 | 2 | 5 | 5 |
| −5 | 0 | −5 | 0 | 5 |
| 3 | 3 | 3 | 3 | 5 |

Answer 5, the run `4, -1, 2`. At the 4, the run so far (−3) only hurts, so the run restarts.

**`[-4, -2, -7]`** — current goes −4, then max(−2, −6) = −2, then max(−7, −9) = −7. Best stays at −2.
:::

::: The Swift trap
**Starting from `Int.min` crashes instead of being wrong.** A common way to "handle all negatives" is `var current = Int.min, best = Int.min` and then loop over every number. The first step computes `current + number` = `Int.min + (-4)`, which is below the smallest `Int`. In C or Java that silently wraps to a huge positive number; Swift checks every arithmetic operation and stops the program with an overflow error. Start both values at `numbers[0]` and loop over `dropFirst()`, as above — that needs no sentinel at all. (The wrapping operator `&+` exists, but wrapping here would give a wrong answer, not a right one.)
:::

::: What they ask next
- **"Return where the run starts and ends."** → Track a `start` index that resets to `i` whenever you restart, and copy it with `i` into `bestStart`, `bestEnd` whenever `best` improves.
- **"Do it with divide and conquer."** → Best run is in the left half, the right half, or crosses the middle (best suffix of the left + best prefix of the right). O(n log n) — worse than Kadane, but it's the follow-up some interviewers want.
- **"Largest product instead of sum."** → A negative times a negative flips sign, so carry both the largest and the smallest product ending here; at each number, the new largest is the max of the number, largest × number and smallest × number.
:::
