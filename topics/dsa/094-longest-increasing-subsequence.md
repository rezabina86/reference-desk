---
title: 79 · Longest Increasing Subsequence
summary: Find how many numbers you can keep from an array, in their original order, so that each kept number is strictly bigger than the one before.
group: 1-D dynamic programming
minutes: 25
sources:
- LeetCode 300 · Longest Increasing Subsequence | https://leetcode.com/problems/longest-increasing-subsequence/
- Swift Algorithms · partitioningIndex(where:) | https://github.com/apple/swift-algorithms/blob/main/Guides/Partition.md
---

*Medium · G*

You get an array of integers. Cross out any numbers you like, keeping the rest in their original order, so that what's left goes **strictly upward** — each number bigger than the one before it. The kept numbers don't need to be next to each other. Return the largest number of entries you can keep.

| Numbers | Answer |
|---|---|
| `[2, 8, 3, 7, 1, 9, 4]` | `4` — 2, 3, 7, 9 |
| `[9, 1, 4, 2, 3]` | `3` — 1, 2, 3 |
| `[5, 5, 5]` | `1` — equal numbers don't count as going up |

Constraints that matter: between 1 and 2,500 numbers, each between −10⁴ and 10⁴. There are 2ⁿ ways to choose what to keep; the O(n²) DP below is accepted, and O(n log n) is the usual follow-up.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LongestIncreasingSubsequenceTests {

    @Test(arguments: [
        ([2, 8, 3, 7, 1, 9, 4], 4),
        ([9, 1, 4, 2, 3], 3),
        ([5, 5, 5], 1),
    ])
    func returnsTheLengthOfTheLongestStrictlyRisingSelection(numbers: [Int], expected: Int) {
        #expect(lengthOfLIS(numbers) == expected)
    }

    // MARK: - Privates
    private func lengthOfLIS(_ numbers: [Int]) -> Int {
        0
    }
}
```

In a playground:

```swift
func lengthOfLIS(_ numbers: [Int]) -> Int {
    0 // your solution
}

let cases: [([Int], Int)] = [
    ([2, 8, 3, 7, 1, 9, 4], 4),
    ([9, 1, 4, 2, 3], 3),
    ([5, 5, 5], 1),
]
for (numbers, expected) in cases {
    let got = lengthOfLIS(numbers)
    print(got == expected ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming, looking back at every earlier position.** The cue is *"subsequence"* — keep items in order but skip freely — plus *"longest"*. Fix where the chosen sequence ends, and its best length depends only on the best sequences that end at earlier, smaller numbers. Unlike the stairs, the previous step can be *any* earlier position, so each box looks back at all of them.
:::

::: Approach
Subproblem: the length of the longest rising sequence that **ends at** position i. Recurrence: that length = 1 + the largest such length at any earlier position whose number is smaller than the number at i (or just 1 if there is none).

Give every position a starting length of 1 — the number on its own. Go through the positions from left to right; for each one, look at every earlier position holding a smaller number and see whether stepping from there makes a longer sequence. The answer is the largest length anywhere, because the best sequence can end at any position, not necessarily the last.

Time O(n²): each position looks back at all earlier ones. Space O(n): one length per position.
:::

::: Swift solution
```swift
func lengthOfLIS(_ numbers: [Int]) -> Int {
    var longestEndingAt = [Int](repeating: 1, count: numbers.count)
    for index in numbers.indices {
        for earlier in 0..<index where numbers[earlier] < numbers[index] {
            longestEndingAt[index] = max(longestEndingAt[index], longestEndingAt[earlier] + 1)
        }
    }
    return longestEndingAt.max() ?? 0
}
```

The subproblem says "ends at i", which is why the answer is `max()` over the whole list rather than its last entry. The strict `<` is what makes `[5, 5, 5]` answer 1.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (one number, strictly falling, a rising run of negatives, a longer mixed array), and 3,000 random arrays with many repeats checked against a brute force over every subset. The O(n log n) version below was verified on the same cases.
:::

::: Walk it through
**`[2, 8, 3, 7, 1, 9, 4]`**

| Index | Number | Smaller numbers earlier (their lengths) | Longest ending here |
|---|---|---|---|
| 0 | 2 | — | 1 |
| 1 | 8 | 2 (1) | 2 |
| 2 | 3 | 2 (1) | 2 |
| 3 | 7 | 2 (1), 3 (2) | 3 |
| 4 | 1 | — | 1 |
| 5 | 9 | 2 (1), 8 (2), 3 (2), 7 (3), 1 (1) | 4 |
| 6 | 4 | 2 (1), 3 (2), 1 (1) | 3 |

Answer 4, found at index 5 — not at the last index, which holds 3.

**`[5, 5, 5]`** — no earlier number is strictly smaller, so every length stays 1. Answer 1.
:::

::: The Swift trap
**The fast version needs a binary search the standard library doesn't have.** The O(n log n) follow-up keeps `tails`, where `tails[k]` is the smallest number that can end a rising sequence of length k + 1, and for each number finds the first tail that is ≥ it. `tails.firstIndex { $0 >= number }` compiles and is correct — and it's a linear scan, so the "fast" version is quietly O(n²) again. The binary search lives in swift-algorithms (`partitioningIndex(where:)`), which isn't available in a shared editor, so write it:

```swift
func lengthOfLISFast(_ numbers: [Int]) -> Int {
    var tails: [Int] = []
    for number in numbers {
        var low = 0, high = tails.count
        while low < high {                       // first tail >= number
            let mid = (low + high) / 2
            if tails[mid] < number { low = mid + 1 } else { high = mid }
        }
        if low == tails.count { tails.append(number) } else { tails[low] = number }
    }
    return tails.count
}
```

Searching for `>=` rather than `>` is what keeps the sequence strictly increasing: an equal number replaces its twin instead of extending past it. And `tails` is not itself a valid sequence — only its length is meaningful; say that before the interviewer asks.
:::

::: What they ask next
- **"Do it in O(n log n)."** → The `tails` array above: each number either extends the longest sequence or lowers the smallest possible ending of some length, found by binary search.
- **"Return the sequence itself."** → In the O(n²) version, store for each index the earlier index it extended from, then follow those links back from the index with the largest length.
- **"Count how many longest sequences there are (LeetCode 673)."** → Carry a count alongside each length: when an earlier position gives a longer length, copy its count; when it ties, add its count.
:::
