---
title: 8 · Product of Array Except Self
summary: For each position in a list of whole numbers, return the product of all the other numbers, without using division.
group: Prefix sums
minutes: 25
sources:
- LeetCode 238 · Product of Array Except Self | https://leetcode.com/problems/product-of-array-except-self/
- The Swift Programming Language · Overflow Operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/#Overflow-Operators
---

*Medium · G*

You get an array of integers. Build a new array of the same length where each position holds the product of every number in the input **except** the one at that position. You may not use division. Zeros and negatives can appear.

| Numbers | Answer |
|---|---|
| `[2, 3, 4, 5]` | `[60, 40, 30, 24]` — e.g. position 1 is 2 × 4 × 5 |
| `[3, 0, 2]` | `[0, 6, 0]` — only the position holding the zero escapes it |
| `[0, 5, 0]` | `[0, 0, 0]` — two zeros make every product zero |

Constraints that matter: between 2 and 100,000 numbers, each between −30 and 30, and every product of a run of them fits in a 32-bit integer. Target O(n) time, and as a follow-up O(1) extra space, where the output array doesn't count as extra.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ProductOfArrayExceptSelfTests {

    @Test(arguments: [
        ([2, 3, 4, 5], [60, 40, 30, 24]),
        ([3, 0, 2], [0, 6, 0]),
        ([0, 5, 0], [0, 0, 0]),
    ])
    func multipliesEverythingButTheEntryAtEachPosition(numbers: [Int], expected: [Int]) {
        #expect(productExceptSelf(numbers) == expected)
    }

    // MARK: - Privates
    private func productExceptSelf(_ numbers: [Int]) -> [Int] {
        []
    }
}
```

In a playground:

```swift
func productExceptSelf(_ numbers: [Int]) -> [Int] {
    [] // your solution
}

let cases: [([Int], [Int])] = [
    ([2, 3, 4, 5], [60, 40, 30, 24]),
    ([3, 0, 2], [0, 6, 0]),
    ([0, 5, 0], [0, 0, 0]),
]
for (numbers, expected) in cases {
    let got = productExceptSelf(numbers)
    print(got == expected ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Prefix and suffix products.** The cue is *"all the other numbers except the one at that position"*: everything except position i is everything to its **left** times everything to its **right**. Both of those are running totals, of products instead of sums, one built from the front and one from the back. *"Without division"* is what rules out the shortcut of dividing the total by each number.
:::

::: Approach
Make two passes. In the first pass, go left to right and write into each position the product of everything before it; the first position gets 1, because nothing comes before it. In the second pass, go right to left carrying a running product of everything after the current position, starting at 1, and multiply it into each position before folding that position's own number into the running product. After both passes, each position holds (everything to its left) × (everything to its right), which is exactly the product of all the others.

Time O(n): two passes. Space O(1) beyond the output: the left products live in the output array itself and the right products in a single variable.
:::

::: Swift solution
```swift
func productExceptSelf(_ numbers: [Int]) -> [Int] {
    var result = Array(repeating: 1, count: numbers.count)

    var leftProduct = 1
    for index in numbers.indices {
        result[index] = leftProduct          // everything before index
        leftProduct *= numbers[index]
    }

    var rightProduct = 1
    for index in numbers.indices.reversed() {
        result[index] *= rightProduct        // times everything after index
        rightProduct *= numbers[index]
    }
    return result
}
```

In both loops the order of the two lines is the whole trick: use the running product first, then fold in the current number, so a position never multiplies by itself.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (two numbers, one number, negatives, a single zero at the front, all ones), and 3,000 random arrays with values from −5 to 5, many with zeros, checked against an O(n²) brute force that multiplies everything except each position.
:::

::: Walk it through
**`[2, 3, 4, 5]`**

| Index | Left product written | Right product multiplied in | Result |
|---|---|---|---|
| 0 | 1 | 3 × 4 × 5 = 60 | 60 |
| 1 | 2 | 4 × 5 = 20 | 40 |
| 2 | 2 × 3 = 6 | 5 | 30 |
| 3 | 2 × 3 × 4 = 24 | 1 | 24 |

The first pass fills the second column top to bottom; the second pass fills the third column bottom to top.

**`[3, 0, 2]`** — the left products are `[1, 3, 0]`, the right products `[0, 2, 1]`; multiplied position by position that is `[0, 6, 0]`. The zero needs no special handling: it lands in every product except its own.
:::

::: The Swift trap
**The division shortcut crashes in Swift, it doesn't just fail.** Multiplying everything and then dividing by each number is the idea most people have first, and the statement forbids it for a reason: with a zero in the array, `total / 0` is a **runtime trap** in Swift, not a wrong value or an infinity, and handling it means counting zeros as special cases. Explain the shortcut, say why it breaks, and write the two passes.

The quieter one: the constraints promise every product fits in 32 bits. Without that promise, Swift's `*` traps on overflow where C would silently wrap. If the interviewer drops the guarantee, say what you'd want instead: `multipliedReportingOverflow(by:)` to detect it, or `&*` only if wrapped values are acceptable.
:::

::: What they ask next
- **"Can you do it without the extra output array?"** → The output is required, so O(1) extra is already the floor. The point of the follow-up is to put the left products in the output and keep the right ones in one variable.
- **"Now return the sum of all others."** → Total once, then `total − numbers[i]`; subtraction has no division-by-zero problem, so no passes are needed.
- **"The array changes, with many queries afterwards."** → Keep a segment tree of products: O(log n) per update and per query.
:::
