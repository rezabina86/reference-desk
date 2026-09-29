---
title: 3 · Top K Frequent Elements
summary: Given a list of numbers and a count k, return the k values that appear most often.
minutes: 25
sources:
- LeetCode 347 · Top K Frequent Elements | https://leetcode.com/problems/top-k-frequent-elements/
- Swift standard library · Array.prefix(_:) | https://developer.apple.com/documentation/swift/array/prefix(_:)
- Swift Collections · Heap | https://github.com/apple/swift-collections
---

*Medium · G*

You get an array of integers and a number k. Count how often each distinct value appears, and return the k values with the highest counts. The answer is always unique — there is never a tie at the cut-off — and it can come back in any order.

| Numbers | k | Answer |
|---|---|---|
| `[4, 4, 4, 7, 7, 9]` | `2` | `[4, 7]` — 4 appears three times, 7 twice |
| `[6]` | `1` | `[6]` — one value, one answer |
| `[-1, -1, 3, 3, 3, 8]` | `2` | `[3, -1]` — negatives count like any other value |

Constraints that matter: up to 100,000 numbers; k is between 1 and the number of distinct values. Sorting the counts gets you an answer in O(n log n). The follow-up you should expect is "can you beat O(n log n)?" Because order is free, the Xcode test sorts your answer before comparing.

::: Pattern and cue
**Hash map to count, then a bucket by frequency.** The first cue is *"how often each value appears"* — that is counting, and counting is `dict[value, default: 0] += 1`. The second cue is *"the k … with the highest"* — a top-k selection. The textbook tool for top-k is a heap of size k, but there is a sharper observation here: a count can never be larger than n. So the counts themselves can be used as array positions, and no comparison-based sort is needed at all.
:::

::: Approach
First, walk the numbers once and count each value in a dictionary. Then make a row of n + 1 empty buckets, one for each possible count from 0 to n, and drop each value into the bucket that matches its count. Finally, walk the buckets from the highest count down, collecting values until you have k of them.

Time O(n): one pass to count, one pass over the distinct values to fill buckets, one pass down the buckets. Space O(n) for the dictionary and the buckets.

The alternatives, so you can say why not: sorting the distinct values by count is O(d log d) for d distinct values — fine, and easier to write correctly, so it is a sound first answer. A min-heap of size k is O(n log k), the right tool when the numbers arrive as a stream and you can't hold them all.
:::

::: Swift solution
```swift
func topKFrequent(_ numbers: [Int], _ k: Int) -> [Int] {
    var countByValue: [Int: Int] = [:]
    for number in numbers {
        countByValue[number, default: 0] += 1
    }

    // buckets[c] holds every value that appears exactly c times.
    var buckets = Array(repeating: [Int](), count: numbers.count + 1)
    for (value, count) in countByValue {
        buckets[count].append(value)
    }

    var result: [Int] = []
    for count in stride(from: numbers.count, through: 1, by: -1) {
        for value in buckets[count] {
            result.append(value)
            if result.count == k { return result }
        }
    }
    return result
}
```

The sort-based version, which is a perfectly good first answer before you optimise:

```swift
func topKFrequentSorted(_ numbers: [Int], _ k: Int) -> [Int] {
    var countByValue: [Int: Int] = [:]
    for number in numbers { countByValue[number, default: 0] += 1 }
    return Array(countByValue.sorted { $0.value > $1.value }.prefix(k).map(\.key))
}
```

Verified with `swift test` on Swift 6.2.3 in Swift 6 mode: the three examples above plus five more — every value the same (`[5, 5, 5]`, k 1), k equal to the number of distinct values (`[1, 2, 3]`, k 3), a close race where 2 appears four times and 0 three times (k 1), negatives and zero together (k 3), and counts of 1, 2 and 3 where the walk must stop after two values.
:::

::: Walk it through
**`[4, 4, 4, 7, 7, 9]`, k = 2**

| Step | State |
|---|---|
| Count | `4: 3, 7: 2, 9: 1` |
| Buckets (0…6) | `[3] = [4]`, `[2] = [7]`, `[1] = [9]`, the rest empty |
| Walk from 6 down | 6, 5, 4 empty · 3 → take 4 · 2 → take 7, now 2 values, stop |

Answer `[4, 7]`.

**`[6]`, k = 1** — count `6: 1`, buckets has two slots, `[1] = [6]`. The walk starts at 1, takes 6, stops. Nothing special needed; the `numbers.count + 1` size is exactly what makes a count of n fit.
:::

::: The Swift trap
**There is no `Heap` in the standard library.** The answer most people have memorised — "min-heap of size k" — is not writable in a shared editor without `swift-collections`, and writing a heap from scratch eats half your 20 minutes. Say the heap answer and its O(n log k), then write the bucket version or the sort. Saying *why* you aren't writing the heap is a senior signal, not a gap.

Smaller one, in the sort version: `prefix(k)` on an array returns an `ArraySlice`, not an `Array`, and a slice keeps its parent's indices — a slice that starts at position 3 has `startIndex == 3`, so `slice[0]` traps. Wrap it in `Array(...)` before returning or indexing.

And if there were ties at the cut-off, dictionary iteration order is randomised per process, so which tied value you return would change between runs. This problem rules ties out; say you noticed.
:::

::: What they ask next
- **"The numbers arrive as a stream too big for memory."** → Keep the counts (or an approximate counter such as Count-Min Sketch if even that's too big) and a min-heap of size k; each update is O(log k).
- **"Return them ordered, most frequent first."** → The bucket walk already produces that order; the sort version too. State the tie-break rule you'd use if ties were allowed — say, smaller value first.
- **"Top k most frequent words, ties broken alphabetically."** → Same count, then sort by `(count descending, word ascending)`. The bucket trick still works if you sort inside each bucket.
:::
