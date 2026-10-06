---
title: Binary search — the idea
summary: How to spot a problem where each check can rule out half of what's left, and the two loop shapes that cover almost every version of it.
group: Binary search
minutes: 9
sources:
- Swift standard library · Collection.firstIndex(of:) | https://developer.apple.com/documentation/swift/collection/firstindex(of:)
- swift-algorithms · partitioningIndex(where:) | https://github.com/apple/swift-algorithms/blob/main/Guides/Partition.md
---

## When to reach for it

- **"Sorted"** anywhere in the statement, together with "find", "position" or "insert".
- **"O(log n)"** as the required running time — almost nothing else gives it.
- **Rotated or shifted** sorted data: still sorted in two pieces.
- **"The minimum speed / capacity / size such that…"** — you can't search the input, but you can search the *answer*, if checking one candidate is easy.
- **"The latest value at or before time t"** — a sorted history and a lookup by timestamp.

## The idea in plain words

Think of guessing a number between 1 and 100 when you're told "higher" or "lower" after each guess. The smart first guess is 50: whatever the reply, half the numbers are gone. Then 25 or 75, and so on. Seven guesses settle any number up to 128; twenty settle any number up to a million.

That only works because the replies are reliable in one direction: if 50 is too low, everything below 50 is too low as well. Sorted data gives you that for free. So does any yes/no question whose answer flips once and stays flipped — "can I finish the bananas eating this fast?" is "no, no, no, …, yes, yes, yes" as the speed rises. Binary search finds the place where the answers flip.

The hard part is never the idea. It's the boundaries: whether the right end is included, whether the middle is kept or discarded, and when the loop stops. Picking one template and sticking to it removes that guesswork.

## The template in Swift

```swift
/// The first index whose value is >= target in a sorted array; `sorted.count` if there is none.
func lowerBound(_ sorted: [Int], _ target: Int) -> Int {
    var low = 0
    var high = sorted.count                  // the answer is always somewhere in low...high
    while low < high {
        let mid = low + (high - low) / 2     // no overflow, and mid < high
        if sorted[mid] < target {
            low = mid + 1                    // mid is too small: the answer is to its right
        } else {
            high = mid                       // mid might be the answer: keep it
        }
    }
    return low
}

/// The smallest value in `range` for which `works` is true. `works` must be
/// false, false, …, true, true across the range, and true at its upper end.
func smallestWorking(in range: ClosedRange<Int>, _ works: (Int) -> Bool) -> Int {
    var low = range.lowerBound
    var high = range.upperBound
    while low < high {
        let mid = low + (high - low) / 2
        if works(mid) {
            high = mid
        } else {
            low = mid + 1
        }
    }
    return low
}
```

Both loops keep one promise — the answer lies in `low...high` — and stop when the range is a single spot. The classic "find this exact value" loop (`while low <= high`, return as soon as `mid` matches) is the same idea with a closed range; the problems use whichever reads more clearly.

## Variations

- **Exact match in a sorted array.** Compare the middle with the target and drop the half that can't hold it. → Binary Search.
- **Sorted, but rotated.** One of the two halves around the middle is always properly sorted; check whether the target lies inside that half, and drop the other one. Or find where the rotation happens, which is the same as finding the minimum. → Search in Rotated Sorted Array, Find Minimum in Rotated Sorted Array.
- **Search the answer, not the array.** The answer is a number in a known range, and "does this value work?" is cheap to check and flips once. → Koko Eating Bananas.
- **Last entry at or before a key.** A sorted history and the upper-bound shape: find the first entry *after* the key, step back one. → Time Based Key-Value Store.

## Complexity

O(log n) comparisons: each step halves the range, and a range of n halves to one spot in about log₂ n steps (20 for a million, 30 for a billion). Space O(1) for the loop. When searching an answer range instead of an array, the cost is O(log(range) × cost of one check) — for Koko, log of the largest pile times one pass over the piles.

## Swift traps

- **The standard library has no binary search.** `firstIndex(of:)` and `contains(_:)` are linear scans, O(n) — fine to mention as the brute force, never the answer. `partitioningIndex(where:)` exists, but in the swift-algorithms package, which a shared interview editor won't have. Write the loop.
- **`(low + high) / 2` traps instead of wrapping.** Swift's `Int` arithmetic stops the program on overflow where C silently wraps. Array indices never get near `Int.max`, but answer-space searches can (a range up to `Int.max`); `low + (high - low) / 2` is safe everywhere, so use it by habit.
- **An `ArraySlice` keeps its parent's indices.** Recursing on `numbers[mid...]` is tempting, but the slice starts at index `mid`, not 0, so `slice[0]` traps and `slice.count / 2` isn't its middle. Use `slice.startIndex` and `slice.endIndex`, or pass `low` and `high` instead of slicing.
- **Sorting first costs O(n log n).** If the input isn't already sorted, sorting it to binary search once is slower than one linear scan. Binary search pays off when the data is given sorted, or when you'll search many times.

## The problems in this topic

- [26 · Binary Search](#/dsa/binary-search) — Easy
- [27 · Search in Rotated Sorted Array](#/dsa/search-in-rotated-sorted-array) — Medium
- [28 · Find Minimum in Rotated Sorted Array](#/dsa/find-minimum-in-rotated-sorted-array) — Medium
- [29 · Koko Eating Bananas](#/dsa/koko-eating-bananas) — Medium
- [30 · Time Based Key-Value Store](#/dsa/time-based-key-value-store) — Medium
