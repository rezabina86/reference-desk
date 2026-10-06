---
title: Prefix sums — the idea
summary: Keep a running total as you walk an array, so the sum of any stretch becomes the difference of two numbers you already have.
group: Prefix sums
minutes: 8
sources:
- Swift Algorithms · reductions | https://github.com/apple/swift-algorithms/blob/main/Guides/Reductions.md
- The Swift Programming Language · Remainder Operator | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/basicoperators/#Remainder-Operator
---

Many array questions are about stretches: entries that sit next to each other, from some start to some end. Adding up every stretch from scratch is O(n²) stretches times their length. A running total makes every stretch's sum a single subtraction.

## When to reach for it

- *"sum of the range from i to j"*, especially when many ranges are asked about
- *"a stretch / subarray that adds up to k"*, *"how many subarrays sum to"*
- *"a multiple of k"*, *"divisible by k"* — the same, keyed by remainder
- *"everything except the one at this position"*, *"to the left of … and to the right of …"*
- **negatives or zeros** in the input, which rule out a sliding window

## The idea in plain words

Think of a car's odometer. To know how far you drove between the bakery and the station, you don't need the route: you read the odometer at both places and subtract. A prefix sum is an odometer for an array. Write down the running total after each entry once, and the total of any stretch is "reading at the end minus reading just before the start".

The second half of the idea is what makes it fast for "find a stretch" questions. If the reading now is R and you want a stretch that adds up to k, you need an *earlier* reading of exactly R − k. Keep the earlier readings in a dictionary and that is one lookup, not a search.

## The template in Swift

```swift
/// prefix[i] is the sum of the first i numbers, so prefix[0] == 0 and prefix.count == numbers.count + 1.
func prefixSums(_ numbers: [Int]) -> [Int] {
    var prefix = [0]
    prefix.reserveCapacity(numbers.count + 1)
    for number in numbers {
        prefix.append(prefix[prefix.count - 1] + number)
    }
    return prefix
}

/// Sum of numbers[start..<end] in O(1), from the table above.
func rangeSum(_ prefix: [Int], from start: Int, to end: Int) -> Int {
    prefix[end] - prefix[start]
}

/// Running total plus a set of earlier totals: does any stretch add up to exactly k?
func hasStretch(in numbers: [Int], summingTo k: Int) -> Bool {
    var earlierTotals: Set<Int> = [0]        // the empty prefix: nothing taken yet
    var total = 0
    for number in numbers {
        total += number
        if earlierTotals.contains(total - k) { return true }   // look first...
        earlierTotals.insert(total)                            // ...then record
    }
    return false
}
```

## Variations

1. **Range queries.** Build the table once in O(n), then answer every "sum from i to j" in O(1). Worth it when there are many queries on an array that doesn't change.
2. **Running total plus a dictionary.** One pass: the current total, and a dictionary of earlier totals holding whatever the question needs — a count (how many stretches), the first position (the longest stretch), or just membership.
3. **Keyed by remainder.** For "a multiple of k", two totals that leave the same remainder after dividing by k differ by a multiple of k, so the dictionary is keyed by remainder instead of by total.
4. **Prefix and suffix products.** The same idea with multiplication, from both ends: "everything except position i" is (everything left of i) × (everything right of i).

## Complexity

Building the table or doing the one-pass walk is O(n) time. A range query is O(1). Space is O(n) for the table or the dictionary of earlier totals, O(k) when keyed by remainder modulo k, and O(1) extra when the running value can live in one variable and the output array.

## Swift traps

- **Off by one.** The table has `numbers.count + 1` entries and starts with 0, so the sum of `numbers[start..<end]` is `prefix[end] - prefix[start]` with no `- 1` anywhere. The leading 0, and the matching "empty prefix" entry in the dictionary version, is what lets a stretch start at position 0.
- **There is no `scan` in the standard library.** `reduce` gives only the final total. Running totals come from a loop, or from `reductions` in the swift-algorithms package, which won't exist in a shared interview editor.
- **`Int` traps on overflow** where C wraps. Running totals of large values can overflow before any single value does; check the constraints and say so.
- **`%` keeps the sign of the left side.** `-4 % 6 == -4`. Keyed by remainder, normalise with `((x % k) + k) % k`, and remember `x % 0` traps.
- **Look first, then record.** Recording the current total before looking up lets an empty stretch match itself, which over-counts whenever k is 0.

## The problems in this topic

- [8 · Product of Array Except Self](#/dsa/product-of-array-except-self) — Medium
- [9 · Subarray Sum Equals K](#/dsa/subarray-sum-equals-k) — Medium
- [10 · Continuous Subarray Sum](#/dsa/continuous-subarray-sum) — Medium
