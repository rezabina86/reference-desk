---
title: Two pointers — the idea
summary: Two positions walking through one array, usually toward each other, so that every step rules something out for good.
group: Two pointers
minutes: 8
sources:
- Swift standard library · MutableCollection.swapAt(_:_:) | https://developer.apple.com/documentation/swift/mutablecollection/swapat(_:_:)
- Swift standard library · String.Index | https://developer.apple.com/documentation/swift/string/index
---

Most brute-force answers to array problems look at every pair of positions: O(n²). Two pointers is the observation that, for some problems, a single comparison tells you which of the two positions can never be part of the answer — so you drop it and move on, and the pairs collapse into one pass.

## When to reach for it

- The input is **sorted**, or sorting it doesn't lose anything the answer needs.
- The statement asks for a **pair** or a **triplet** with some sum or score.
- It says **"in place"** or **"constant extra memory"**.
- It compares the **front with the back**: palindromes, reversing, mirrored checks.
- The score of a pair depends on the **distance between them** and on the **smaller** of the two.
- There are only **two or three distinct values** to separate.

## The idea in plain words

Picture two people searching a shelf of books arranged by price for two that together cost exactly 30 euros. One starts at the cheap end, one at the expensive end. They add up their two prices. Too little? The cheap person steps up — the cheap book can't reach 30 even paired with the dearest book on the shelf, so it is out for good. Too much? The other person steps down, for the mirrored reason. Every step throws away one book, and they meet in the middle after one walk along the shelf.

That is the whole trick: **each comparison eliminates one end**. Your job in an interview is to say *why* the end you drop can't be in the answer. If you can't say it, the two pointers are probably wrong for this problem.

## The template in Swift

```swift
// Shape 1: from both ends inward (sorted pairs, palindromes, containers).
func pairIndices(in sorted: [Int], summingTo target: Int) -> (Int, Int)? {
    var left = 0
    var right = sorted.count - 1          // -1 for an empty array: the loop just doesn't run
    while left < right {                  // stop when they meet: every candidate has been ruled in or out
        let sum = sorted[left] + sorted[right]
        if sum == target { return (left, right) }
        if sum < target {
            left += 1                     // too small: the left value can't reach the target with anything
        } else {
            right -= 1                    // too big: the right value overshoots with anything
        }
    }
    return nil
}

// Shape 2: same direction, a reader and a writer (filtering in place).
func removeDuplicates(_ sorted: inout [Int]) -> Int {
    guard !sorted.isEmpty else { return 0 }
    var write = 1                         // everything before `write` is the finished result
    for read in 1..<sorted.count where sorted[read] != sorted[write - 1] {
        sorted[write] = sorted[read]
        write += 1
    }
    return write                          // the new logical length
}
```

## Variations

- **Opposite ends, one decision per step.** Compare the two values and move one end. Valid Palindrome (skip what doesn't count, then compare), Two Sum II (move by the sum), Container With Most Water and Trapping Rain Water (move the lower wall).
- **Fix one, then two pointers on the rest.** Sort, loop over the first value, and run shape 1 on everything to its right. That is 3Sum, and 4Sum is one more loop. Sorting also lines up duplicates so they can be skipped.
- **Three pointers partitioning in place.** Two boundaries for the finished zones and one scanner in the unsorted middle: Sort Colors, the Dutch national flag.
- **Reader and writer, same direction.** One pointer reads every element, the other marks where the next kept element goes. Removing duplicates or a value from an array in place.

## Complexity

O(n) time: each step moves at least one pointer, and the pointers can only cover the array once between them. O(1) extra space: a few indices. When the problem needs a sort first, the sort dominates at O(n log n) — and `sorted()` returns a copy, so say whether you count that O(n).

## Swift traps

- **A `String` has no integer subscript.** `Array(text)` gives `[Character]` with `Int` indices at an O(n) cost; walking `String.Index` values with `index(after:)` and `index(before:)` is O(1) extra. `text.index(text.startIndex, offsetBy: i)` inside a loop is O(i) per call and makes the pass O(n²).
- **`swap(&a[i], &a[j])` doesn't compile** — two overlapping accesses to one array. Use `a.swapAt(i, j)`, which is also fine when `i == j`.
- **"In place" means `inout`.** A function parameter is a constant copy; changing a local `var` changes nothing the caller sees.
- **`Int` traps on overflow.** Adding the two ends of an array can overflow even when the answer fits; `addingReportingOverflow` is the honest guard.
- **A slice keeps its parent's indices.** An `ArraySlice` starts at `startIndex`, not 0; start pointers from `startIndex` if the function takes a slice.

## The problems in this topic

- [11 · Valid Palindrome](#/dsa/valid-palindrome) — Easy
- [12 · Two Sum II — Input Array Is Sorted](#/dsa/two-sum-ii-input-array-is-sorted) — Medium
- [13 · 3Sum](#/dsa/3sum) — Medium
- [14 · Container With Most Water](#/dsa/container-with-most-water) — Medium
- [15 · Sort Colors](#/dsa/sort-colors) — Medium
- [16 · Trapping Rain Water](#/dsa/trapping-rain-water) — Hard, optional
