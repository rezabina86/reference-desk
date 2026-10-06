---
title: 88 · Counting Bits
summary: For every whole number from 0 up to n, report how many 1s its binary form contains, in one list.
group: Bit manipulation
minutes: 15
sources:
- LeetCode 338 · Counting Bits | https://leetcode.com/problems/counting-bits/
- Swift standard library · stride(from:through:by:) | https://developer.apple.com/documentation/swift/stride(from:through:by:)
---

*Easy · G*

You get a non-negative integer n. Return an array of n + 1 entries where the entry at position i is the number of 1s in the binary form of i. Position 0 holds the answer for 0, position n the answer for n.

| n | Answer |
|---|---|
| `2` | `[0, 1, 1]` — 0, 1, 10 |
| `6` | `[0, 1, 1, 2, 1, 2, 2]` — up to 110 |
| `0` | `[0]` — just the number 0 |

Constraints that matter: n is between 0 and 100,000. Counting each number's bits separately is O(n log n); the target is O(n) — a constant amount of work per number — without `nonzeroBitCount`.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct CountingBitsTests {

    @Test(arguments: [
        (2, [0, 1, 1]),
        (6, [0, 1, 1, 2, 1, 2, 2]),
        (0, [0]),
    ])
    func listsTheNumberOfOnesForEveryValueUpToN(n: Int, expected: [Int]) {
        #expect(countBits(n) == expected)
    }

    // MARK: - Privates
    private func countBits(_ n: Int) -> [Int] {
        []
    }
}
```

In a playground:

```swift
func countBits(_ n: Int) -> [Int] {
    [] // your solution
}

let cases: [(Int, [Int])] = [
    (2, [0, 1, 1]),
    (6, [0, 1, 1, 2, 1, 2, 2]),
    (0, [0]),
]
for (n, expected) in cases {
    let got = countBits(n)
    print(got == expected ? "PASS" : "FAIL", n, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Build each answer from a smaller one you already have.** The cue is *"for every number from 0 to n"* — a whole table of answers, where each number is a smaller number with one more bit. Dropping a number's last bit (`i >> 1`) gives a number already in the table; add the bit you dropped (`i & 1`).
:::

::: Approach
Fill the list from 0 upwards. The count for 0 is 0. For any larger number, shift it right by one: that throws away its last binary digit and gives a number half its size, whose count is already in the list. The original number has exactly those 1s, plus one more if the digit thrown away was a 1 — that is, if the number is odd. So each entry is one lookup and one addition.

Time O(n): one constant-time step per number. Space O(1) beyond the output list.
:::

::: Swift solution
```swift
func countBits(_ n: Int) -> [Int] {
    var ones = [Int](repeating: 0, count: n + 1)
    for value in stride(from: 1, through: n, by: 1) {
        ones[value] = ones[value >> 1] + (value & 1)   // drop the last bit, then add it back
    }
    return ones
}
```

`value >> 1` is always smaller than `value`, so the entry it reads was filled in an earlier step. Another one-liner works the same way: `ones[value & (value - 1)] + 1` — the number with its lowest 1 removed, plus that 1.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, two more (n = 1 and n = 8, the first number with a fresh high bit), 300 random n up to 2,000 checked against counting `"1"`s in `String(i, radix: 2)` for every i, and n = 100,000 checked against `nonzeroBitCount`.
:::

::: Walk it through
**n = 6**

| value | binary | value >> 1 | its count | last bit | count |
|---|---|---|---|---|---|
| 0 | `0` | — | — | — | 0 |
| 1 | `1` | 0 | 0 | 1 | 1 |
| 2 | `10` | 1 | 1 | 0 | 1 |
| 3 | `11` | 1 | 1 | 1 | 2 |
| 4 | `100` | 2 | 1 | 0 | 1 |
| 5 | `101` | 2 | 1 | 1 | 2 |
| 6 | `110` | 3 | 2 | 0 | 2 |

Answer `[0, 1, 1, 2, 1, 2, 2]`.

**n = 0** — the list is created with one entry, 0, and the loop from 1 through 0 has nothing to do. Answer `[0]`.
:::

::: The Swift trap
**`for value in 1...n` crashes when n is 0.** It's the loop anyone writes first, and n = 0 is a legal input: `1...0` is a closed range whose start is after its end, and Swift stops with *"Range requires lowerBound <= upperBound"* instead of running zero times as a C `for` loop would. `stride(from: 1, through: n, by: 1)` is empty in that case; so is a `guard n > 0 else { return [0] }` in front of the range. A related surprise runs the other way: in Swift `&` binds like `*`, tighter than `+`, so `ones[value >> 1] + value & 1` happens to mean the right thing here — but it means `(… + value) & 1` in C and Java. Keep the parentheses.
:::

::: What they ask next
- **"Can you do it with `n & (n - 1)` instead?"** → `ones[i] = ones[i & (i - 1)] + 1`: the number with its lowest 1 cleared is smaller and already filled in.
- **"Why not `(0...n).map(\.nonzeroBitCount)`?"** → It's correct and O(n) with a hardware popcount, and the right production code. The question asks for the reuse idea, so offer both.
- **"Sum of all those counts without the list?"** → Count per bit position: bit k is 1 in exactly half of every block of 2^(k+1) consecutive numbers, plus a partial block at the end. O(log n).
:::
