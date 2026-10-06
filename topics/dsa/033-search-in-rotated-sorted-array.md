---
title: 27 · Search in Rotated Sorted Array
summary: Find a target in a list of distinct numbers that was sorted and then shifted around in a circle, in logarithmic time.
group: Binary search
minutes: 25
sources:
- LeetCode 33 · Search in Rotated Sorted Array | https://leetcode.com/problems/search-in-rotated-sorted-array/
- Swift standard library · ArraySlice | https://developer.apple.com/documentation/swift/arrayslice
---

*Medium · G*

You get a list of distinct integers that was sorted ascending and then rotated: some number of entries were taken off the front and put on the back, in order. So `[2, 5, 9, 15, 18]` might arrive as `[15, 18, 2, 5, 9]`. You don't know how far it was rotated — possibly not at all. Return the index of a target, or −1 if it isn't there, in O(log n) time.

| Numbers | Target | Answer |
|---|---|---|
| `[15, 18, 2, 5, 9]` | `5` | `3` |
| `[15, 18, 2, 5, 9]` | `16` | `-1` — falls between 15 and 18, but isn't there |
| `[3, 1]` | `1` | `1` — two entries, so the middle is also the left end; the edge case |

Constraints that matter: up to 5,000 numbers, all distinct. A linear scan is O(n); the statement demands O(log n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct SearchInRotatedSortedArrayTests {

    @Test(arguments: [
        ([15, 18, 2, 5, 9], 5, 3),
        ([15, 18, 2, 5, 9], 16, -1),
        ([3, 1], 1, 1),
    ])
    func returnsTheIndexOfTheTargetInARotatedList(numbers: [Int], target: Int, expected: Int) {
        #expect(search(numbers, target) == expected)
    }

    // MARK: - Privates
    private func search(_ numbers: [Int], _ target: Int) -> Int {
        -1
    }
}
```

In a playground:

```swift
func search(_ numbers: [Int], _ target: Int) -> Int {
    -1 // your solution
}

let cases: [([Int], Int, Int)] = [
    ([15, 18, 2, 5, 9], 5, 3),
    ([15, 18, 2, 5, 9], 16, -1),
    ([3, 1], 1, 1),
]
for (numbers, target, expected) in cases {
    let got = search(numbers, target)
    print(got == expected ? "PASS" : "FAIL", numbers, target, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Binary search on a half that is known to be sorted.** The cues are *"sorted … rotated"* and *"O(log n)"*. Cut a rotated list anywhere and at least one of the two halves is in normal sorted order — the break can only be on one side. A sorted half can answer "is the target inside me?" with two comparisons.
:::

::: Approach
Keep two markers at the ends of the part still worth searching, and look at the middle entry. If it's the target, done. Otherwise, work out which half is in order: if the left end is no bigger than the middle, the left half is sorted; if not, the right half is. For the sorted half, check whether the target lies between its two ends. If it does, search that half; if not, the target can only be in the other half. Repeat until found or the markers cross.

Time O(log n): every step discards half. Space O(1).
:::

::: Swift solution
```swift
func search(_ numbers: [Int], _ target: Int) -> Int {
    var low = 0
    var high = numbers.count - 1

    while low <= high {
        let mid = low + (high - low) / 2
        if numbers[mid] == target { return mid }

        if numbers[low] <= numbers[mid] {                 // left half low...mid is sorted
            if numbers[low] <= target, target < numbers[mid] {
                high = mid - 1
            } else {
                low = mid + 1
            }
        } else {                                          // right half mid...high is sorted
            if numbers[mid] < target, target <= numbers[high] {
                low = mid + 1
            } else {
                high = mid - 1
            }
        }
    }
    return -1
}
```

The `<=` in `numbers[low] <= numbers[mid]` is the line that matters: when only two entries are left, `low` and `mid` are the same index, and that one-entry left half has to count as sorted. With `<`, `[3, 1]` searching for 1 goes the wrong way.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (empty list, one entry found and missed, an unrotated list, the largest value just before the break, a three-entry rotation), and 5,000 random rotations of random sorted lists checked against `firstIndex(of:)`.
:::

::: Walk it through
**`[15, 18, 2, 5, 9]`, target 5**

| low | high | mid | Values low / mid / high | Sorted half | Target inside? | Action |
|---|---|---|---|---|---|---|
| 0 | 4 | 2 | 15 / 2 / 9 | right (15 > 2) | 2 < 5 ≤ 9, yes | low = 3 |
| 3 | 4 | 3 | 5 / 5 / 9 | — | found | return 3 |

**`[3, 1]`, target 1** — low 0, high 1, mid 0. `numbers[0]` is 3, not the target. `3 <= 3`, so the left half (just index 0) is treated as sorted; is 1 at least 3 and below 3? No, so low = 1. Now low = high = mid = 1: found, return 1. With a strict `<`, the code would treat the right half as sorted, ask whether 1 is in `3 < t ≤ 1`, say no, and set high = −1 — reporting −1 for a target that's there.
:::

::: The Swift trap
**Recursing on slices keeps the old indices.** A tidy-looking recursive version calls itself on `numbers[low...mid]` or `numbers[(mid + 1)...]`. An `ArraySlice` shares its parent's indices: the slice `numbers[3...]` starts at index 3, so `slice[0]` traps and `slice.count / 2` is not its middle. The answer you return would also be an index into the original array, which is actually what you want — but only if every access uses `slice.startIndex`, `slice.endIndex` and `slice.index(...)`. Passing `low` and `high` as here avoids the whole question. And as always, `numbers.firstIndex(of:)` is O(n): the brute force, not the answer.
:::

::: What they ask next
- **"The list may contain duplicates."** → When `numbers[low] == numbers[mid] == numbers[high]`, you can't tell which half is sorted; shrink both ends by one and continue. The worst case becomes O(n), and you should say so.
- **"Do it in two passes instead."** → First find the index of the minimum (problem 28), which splits the list into two sorted runs, then do a plain binary search in the run whose range contains the target.
- **"How far was it rotated?"** → The index of the minimum is the rotation amount.
:::
