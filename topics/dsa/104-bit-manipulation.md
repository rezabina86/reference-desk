---
title: Bit manipulation — the idea
summary: Read a whole number as the row of 1s and 0s the machine stores, and answer questions about it with a few operators that work on all those digits at once.
group: Bit manipulation
minutes: 10
sources:
- The Swift Programming Language · Advanced Operators | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/advancedoperators/
- Swift standard library · BinaryInteger.nonzeroBitCount | https://developer.apple.com/documentation/swift/binaryinteger/nonzerobitcount
---

Bit questions are short, and they look like tricks. They aren't, once you can see the number the way the computer stores it: as a row of switches, each on or off. Then "count the 1s", "find the missing value" and "is this a power of two" become questions about switches, and a handful of operators flip or compare all of them in one step.

## When to reach for it

- *"binary representation"*, *"number of 1 bits"*, *"set bits"*, *"Hamming"*
- *"without using + or −"*, *"without extra space"* on an integer problem
- *"every element appears twice except one"*, *"the missing number"* — pairs that cancel
- *"power of two"*, *"reverse the bits"*, *"32-bit unsigned integer"*
- *"all subsets"* of a small set — each subset is a number whose bits say in or out

## The idea in plain words

We write numbers with ten digits, and each position is worth ten times the one to its right: 305 is 3 hundreds, 0 tens and 5 ones. Binary is the same with only two digits, 0 and 1, and each position worth **twice** the one to its right: 1, 2, 4, 8, 16, and so on. So 13 is 8 + 4 + 1, written `1101` — one 8, one 4, no 2, one 1. Each of those digits is a **bit**, and position 0 is the rightmost.

Now picture a row of light switches, one per bit. The bit operators work on every switch at the same time:

Take 12 (`1100`) and 10 (`1010`):

- `a & b` — **AND**: a bit is 1 where both are 1. `12 & 10` is `1000`, 8.
- `a | b` — **OR**: a bit is 1 where either is 1. `12 | 10` is `1110`, 14.
- `a ^ b` — **XOR**: a bit is 1 where they differ. `12 ^ 10` is `0110`, 6.
- `~a` — **NOT**: flips every switch.
- `a << k` — **shift left**: every bit moves k places left, which doubles the number k times. `12 << 1` is 24.
- `a >> k` — **shift right**: every bit moves k places right and the last ones fall off, which halves it k times, rounding down. `12 >> 2` is 3.

Two facts do most of the work:

- **XOR cancels pairs.** `x ^ x` is 0 and `x ^ 0` is `x`, in any order. XOR a list together and every value that appears twice disappears.
- **`n & (n - 1)` removes the lowest 1.** Subtracting 1 turns the rightmost 1 into a 0 and every 0 to its right into a 1: `1100 − 1 = 1011`. AND the two and everything from that rightmost 1 down becomes 0: `1100 & 1011 = 1000`. Repeat until the number is 0 and you have counted its 1s, one step per 1 — not one per bit. And a positive `n` with `n & (n - 1) == 0` had exactly one 1: it's a power of two.

## The template in Swift

```swift
/// Is the bit at `position` (0 = the rightmost) a 1?
func isBitSet(_ value: Int, at position: Int) -> Bool {
    value & (1 << position) != 0
}

func settingBit(_ value: Int, at position: Int) -> Int { value | (1 << position) }
func clearingBit(_ value: Int, at position: Int) -> Int { value & ~(1 << position) }
func flippingBit(_ value: Int, at position: Int) -> Int { value ^ (1 << position) }

/// Count the 1s by looking at the last bit and shifting it away.
func onesByShifting(_ value: UInt) -> Int {
    var remaining = value
    var count = 0
    while remaining != 0 {
        count += Int(remaining & 1)
        remaining >>= 1
    }
    return count
}

/// `value & (value - 1)` removes the lowest 1. `&-` because 0 - 1 traps on an unsigned type.
func clearingLowestOne(_ value: UInt) -> UInt {
    value & (value &- 1)
}

/// A power of two has exactly one 1.
func isPowerOfTwo(_ value: Int) -> Bool {
    value > 0 && value & (value - 1) == 0
}

/// XOR of a list: pairs cancel, the odd one out is what remains.
func loneValue(_ values: [Int]) -> Int {
    values.reduce(0, ^)
}
```

## Variations

1. **Count or test bits.** Walk the bits with `& 1` and `>> 1` (one step per bit), or strip them with `n & (n - 1)` (one step per 1).
2. **Reuse smaller answers.** A number's bits are its half's bits plus its last bit: `ones(i) == ones(i >> 1) + (i & 1)`. That turns "count for every number up to n" into one pass.
3. **XOR to cancel.** Pair every value with its partner — the same value elsewhere in the list, or the index it should sit at — and XOR everything; what survives is the unpaired one.
4. **Bits as a set.** An `Int` is 64 yes/no flags: bit k on means "item k is in". Looping a mask from 0 to 2ⁿ − 1 lists every subset of n items.

## Complexity

The operators themselves are O(1): one machine instruction on a 64-bit word. A loop over bits is O(number of bits) — 32 or 64, a constant — and the `n & (n - 1)` loop is O(number of 1s). Over an array or a range of n values, multiply by n. Space is O(1) apart from any output.

## Swift traps

- **`nonzeroBitCount` is the real answer — and then they want the loop.** `13.nonzeroBitCount == 3`, compiled to a single popcount instruction; `trailingZeroBitCount` and `leadingZeroBitCount` are there too. In production code and as a step inside a bigger problem, use them. When counting bits *is* the problem, say "in production, `nonzeroBitCount`", then write the loop: that's what's being tested.
- **`Int` is 64 bits, and negative numbers are mostly 1s.** On every current Apple platform `Int` is `Int64`. Negatives use two's complement: −1 is 64 ones. Problems written for C's 32-bit `uint32_t` say "unsigned 32-bit"; in Swift, convert with `UInt32(truncatingIfNeeded: n)` to see the same 32 bits, or `UInt(bitPattern: n)` for all 64.
- **`>>` on a signed number copies the sign bit in.** `-8 >> 1` is −4, and `-1 >> 1` is still −1, so a "shift until zero" loop on a negative `Int` never ends. Unsigned types shift zeros in.
- **Arithmetic traps on overflow; the `&` operators wrap.** `Int.max + 1` and `UInt(0) - 1` crash. `&+`, `&-` and `&*` wrap around instead, the way C does. The bit operators `&`, `|`, `^`, `~` never overflow. Shifts are safe too: Swift's shifts by too many places give 0 (or −1 for a negative), where C's are undefined.
- **Precedence is not C's.** Swift ranks `<<` and `>>` above `*`, and `&` with `*` — above `+` and above `==`. So `x & 1 == 1` means `(x & 1) == 1`, which C gets wrong; but `a + b & c` means `a + (b & c)`, which is the opposite of C and Java. When porting a formula, add the parentheses.

## The problems in this topic

- [87 · Number of 1 Bits](#/dsa/number-of-1-bits) — Easy
- [88 · Counting Bits](#/dsa/counting-bits) — Easy
- [89 · Missing Number](#/dsa/missing-number) — Easy
