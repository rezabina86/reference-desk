---
title: 76 · Maximum Product Subarray
summary: Find the largest product you can get by multiplying a run of neighbouring numbers in an array that may hold negatives and zeros.
group: 1-D dynamic programming
minutes: 25
sources:
- LeetCode 152 · Maximum Product Subarray | https://leetcode.com/problems/maximum-product-subarray/
---

*Medium · G*

You get an array of integers — positive, negative or zero. Choose a stretch of **consecutive** entries, at least one long, and multiply them together. Return the largest product any such stretch can give.

| Numbers | Answer |
|---|---|
| `[-2, 3, -4]` | `24` — the whole array: two negatives cancel |
| `[3, -1, 4]` | `4` — the `4` alone; any stretch holding the −1 is negative |
| `[-3]` | `-3` — the only stretch there is |

Constraints that matter: between 1 and 20,000 numbers, each between −10 and 10, and every stretch's product fits in a 32-bit integer. Checking every stretch is O(n²); the target is one pass, O(n) time and O(1) space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MaximumProductSubarrayTests {

    @Test(arguments: [
        ([-2, 3, -4], 24),
        ([3, -1, 4], 4),
        ([-3], -3),
    ])
    func returnsTheLargestProductOfAConsecutiveRun(numbers: [Int], expected: Int) {
        #expect(maxProduct(numbers) == expected)
    }

    // MARK: - Privates
    private func maxProduct(_ numbers: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func maxProduct(_ numbers: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([-2, 3, -4], 24),
    ([3, -1, 4], 4),
    ([-3], -3),
]
for (numbers, expected) in cases {
    let got = maxProduct(numbers)
    print(got == expected ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming carrying two values — the largest and the smallest product ending here.** The cue is *"consecutive"* plus *"largest product"* with *"negative"* numbers allowed. For sums, the best run ending here needs only the best run ending one step earlier (Kadane's algorithm). For products, a negative number flips the order: the *most negative* run so far, times a negative, becomes the largest. So each position carries both extremes.
:::

::: Approach
Subproblem: the largest and the smallest product of a run that ends exactly at position i. Recurrence: both are found among three candidates — the number at i alone, the previous largest times it, and the previous smallest times it.

Walk the array once. At each number, work out the three candidates: start a fresh run with just this number, or extend the previous best run, or extend the previous worst run. The largest of the three is the new best-ending-here, the smallest is the new worst-ending-here. A zero resets both to 0, and the "start fresh" candidate lets the next number begin again. Keep the largest best-ending-here ever seen as the answer.

Time O(n): constant work per number. Space O(1): three running values.
:::

::: Swift solution
```swift
func maxProduct(_ numbers: [Int]) -> Int {
    var high = numbers[0]   // largest product of a run ending here
    var low = numbers[0]    // smallest (most negative) product of a run ending here
    var best = numbers[0]
    for number in numbers.dropFirst() {
        (high, low) = (
            max(number, high * number, low * number),
            min(number, high * number, low * number)
        )
        best = max(best, high)
    }
    return best
}
```

`max` and `min` in Swift take any number of arguments, so the three candidates fit in one call each. The tuple is what keeps `low` from being computed with the *new* `high` (see the trap). The statement promises at least one number; `numbers[0]` relies on it.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (`[0, -2]`, `[-2, 0, -1]`, a zero between negatives, `[2, 2, -2, -2]`, `[-1, -1]`, and the trap's `[2, -5, -2, -4, 3]`), and 3,000 random arrays of small numbers with plenty of zeros and negatives, checked against a brute force over every stretch.
:::

::: Walk it through
**`[-2, 3, -4]`**

| Number | Candidates (alone, high×n, low×n) | high | low | best |
|---|---|---|---|---|
| −2 | start | −2 | −2 | −2 |
| 3 | 3, −6, −6 | 3 | −6 | 3 |
| −4 | −4, −12, 24 | 24 | −12 | 24 |

Answer 24. The winning run comes from `low`: at the 3, the most negative run (−6) looked useless, and the −4 turned it into the answer.

**`[-2, 0, -1]`** — after −2, both are −2. The 0 makes every candidate 0, so high = low = 0 and best = 0. The −1 offers −1, 0, 0: high stays 0, low becomes −1. Answer 0 — the zero itself is the best stretch.
:::

::: The Swift trap
**Two separate assignment lines compute `low` from the new `high`.** Written as

```swift
high = max(number, high * number, low * number)
low = min(number, high * number, low * number)   // uses the high you just changed
```

the second line multiplies by the updated `high`. On `[-2, 3, -4]` that makes `low` at the 3 equal min(3, 9, −6) = −6 — right by luck — but on `[2, -5, -2, -4, 3]` it reports 480 — a product no stretch has — instead of 24. The tuple assignment evaluates both right-hand sides with the old values before assigning, so no temporary is needed. If you prefer separate lines, save `let previousHigh = high` first and say why.

Overflow doesn't bite here because the statement bounds every product to 32 bits and Swift's `Int` is 64-bit. On unbounded input it would, and a run of nineteen 10s already passes `Int.max` and traps — `multipliedReportingOverflow(by:)` is the tool if asked.
:::

::: What they ask next
- **"Why not just the largest product ending here, like Kadane for sums?"** → Because a negative turns the smallest into the largest; one value forgets the run that a later negative would rescue.
- **"Do it without tracking the minimum."** → Take the best of all prefix products and all suffix products, restarting at each zero: an odd count of negatives always leaves either a prefix or a suffix with an even count.
- **"Return the stretch, not the product."** → Track where the current high and low runs started (reset on "start fresh") and record start and end whenever best improves.
:::
