---
title: 87 · Number of 1 Bits
summary: Given a non-negative whole number, say how many of the digits in its binary form are 1.
group: Bit manipulation
minutes: 15
sources:
- LeetCode 191 · Number of 1 Bits | https://leetcode.com/problems/number-of-1-bits/
- Swift standard library · BinaryInteger.nonzeroBitCount | https://developer.apple.com/documentation/swift/binaryinteger/nonzerobitcount
---

*Easy · G*

You get a non-negative integer. Write it in binary — only 0s and 1s, each position worth twice the one to its right — and count how many of the digits are 1. That count is also called the number's *Hamming weight* or *population count*.

| Number | Binary | Answer |
|---|---|---|
| `13` | `1101` | `3` |
| `128` | `10000000` | `1` — a power of two has a single 1 |
| `2147483647` | thirty-one 1s | `31` — the largest 32-bit signed value |

Constraints that matter: the number is between 1 and 2³¹ − 1, so it fits in 31 bits. Any loop over the bits is already O(1) — at most 31 steps — so the interesting question is how *few* steps you can take: one per 1, not one per bit.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct NumberOf1BitsTests {

    @Test(arguments: [
        (13, 3),
        (128, 1),
        (2_147_483_647, 31),
    ])
    func countsTheOnesInTheBinaryForm(number: Int, expected: Int) {
        #expect(hammingWeight(number) == expected)
    }

    // MARK: - Privates
    private func hammingWeight(_ n: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func hammingWeight(_ n: Int) -> Int {
    0 // your solution
}

let cases: [(Int, Int)] = [
    (13, 3),
    (128, 1),
    (2_147_483_647, 31),
]
for (number, expected) in cases {
    let got = hammingWeight(number)
    print(got == expected ? "PASS" : "FAIL", number, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Clear the lowest 1 until nothing is left: `n & (n - 1)`.** The cue is *"number of 1 bits"* / *"binary representation"*. Each application of `n & (n - 1)` switches off exactly one 1 — the rightmost — so the number of steps until `n` reaches 0 is the answer.
:::

::: Approach
Say the honest answer first: Swift already has this, `n.nonzeroBitCount`, and it compiles to one machine instruction. Then do it by hand, which is what the question is testing. The obvious way looks at the last bit (`n & 1`), adds it to a count, and shifts the number right by one, until the number is 0 — one step per bit. The better way uses the fact that subtracting 1 from a number flips its rightmost 1 to 0 and the 0s after it to 1s; AND-ing that with the original wipes out the rightmost 1 and leaves every other bit alone. Count how many times you can do that before the number is 0.

Time O(number of 1s) — at most 31 steps here, so O(1) either way. Space O(1).
:::

::: Swift solution
```swift
func hammingWeight(_ n: Int) -> Int {
    var remaining = UInt(bitPattern: n)   // unsigned: no sign bit to drag along
    var count = 0
    while remaining != 0 {
        remaining &= remaining - 1        // clears the lowest 1
        count += 1
    }
    return count
}
```

`remaining - 1` can't underflow: the loop only runs while `remaining` is not 0. Reading the bits as `UInt` makes the function also correct for a negative input, where it counts all 64 bits of the two's-complement form, as `nonzeroBitCount` does.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (0, 1, 6, `Int.max` with 63, −1 with 64, `Int.min` with 1), 3,000 random values up to 2³¹ − 1 checked against counting the `"1"`s in `String(n, radix: 2)`, and 3,000 random values over the whole `Int` range checked against `nonzeroBitCount`.
:::

::: Walk it through
**`13`** — binary `1101`

| Step | remaining | remaining − 1 | AND | count |
|---|---|---|---|---|
| 1 | `1101` | `1100` | `1100` | 1 |
| 2 | `1100` | `1011` | `1000` | 2 |
| 3 | `1000` | `0111` | `0000` | 3 |

Three steps for three 1s; the 0 in position 1 is never visited. The shift-by-one loop would take four steps, one per bit.

**`128`** — `10000000`. Minus 1 is `01111111`; the AND is 0 after one step. Answer 1. The shifting loop needs eight steps for the same answer.
:::

::: The Swift trap
**Shifting a negative `Int` right never reaches zero.** The textbook loop, `while n != 0 { count += n & 1; n >>= 1 }`, is fine for the inputs here, but feed it a negative number and it hangs: `>>` on a signed type copies the sign bit in from the left, so −1 shifted right is still −1, forever. The `n & (n - 1)` loop on a signed `Int` has its own failure: it walks a negative number down to `Int.min`, and `Int.min - 1` overflows and traps. Both are why the solution converts to `UInt(bitPattern:)` first — or to `UInt32(truncatingIfNeeded:)` when the problem says "unsigned 32-bit", which the older version of this problem does.
:::

::: What they ask next
- **"Is there a constant-time version without a loop?"** → `nonzeroBitCount`, a hardware popcount. By hand: add bits in parallel pairs, then nibbles, then bytes with masks like `0x5555…` and `0x3333…` — the "SWAR" popcount.
- **"Called millions of times?"** → A 256-entry table of counts per byte, then add the counts of the 8 bytes. Or just `nonzeroBitCount`.
- **"Hamming distance between two numbers?"** → The count of 1s in `a ^ b` — the positions where they differ.
:::
