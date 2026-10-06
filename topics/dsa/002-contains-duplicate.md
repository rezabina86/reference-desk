---
title: 1 · Contains Duplicate
summary: Given a list of whole numbers, say whether any value appears in it more than once.
group: Arrays and hashing
minutes: 15
sources:
- LeetCode 217 · Contains Duplicate | https://leetcode.com/problems/contains-duplicate/
- Swift standard library · Set | https://developer.apple.com/documentation/swift/set
---

*Easy · G*

You get an array of integers. Return `true` if at least one value shows up in two or more positions, and `false` if every value is different. You only have to say *whether* a repeat exists, not which value or where.

| Numbers | Answer |
|---|---|
| `[4, 9, 2, 9]` | `true` — 9 appears twice |
| `[7, 3, 1]` | `false` — all different |
| `[0, 0]` | `true` — the smallest input that can repeat |

Constraints that matter: up to 100,000 numbers, each between −10⁹ and 10⁹. Comparing every pair is O(n²), about five billion comparisons at the top size. The target is O(n) time.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ContainsDuplicateTests {

    @Test(arguments: [
        ([4, 9, 2, 9], true),
        ([7, 3, 1], false),
        ([0, 0], true),
    ])
    func reportsWhetherAnyValueAppearsTwice(numbers: [Int], expected: Bool) {
        #expect(containsDuplicate(numbers) == expected)
    }

    // MARK: - Privates
    private func containsDuplicate(_ numbers: [Int]) -> Bool {
        false
    }
}
```

In a playground:

```swift
func containsDuplicate(_ numbers: [Int]) -> Bool {
    false // your solution
}

let cases: [([Int], Bool)] = [
    ([4, 9, 2, 9], true),
    ([7, 3, 1], false),
    ([0, 0], true),
]
for (numbers, expected) in cases {
    let got = containsDuplicate(numbers)
    print(got == expected ? "PASS" : "FAIL", numbers, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Hash set.** The cue is *"appears more than once"*: for every value you need to ask "have I seen this before?", and the data structure that answers that in constant time is a set. It is the smallest problem in the topic, and the one every other problem here builds on.
:::

::: Approach
Read the numbers from left to right, keeping a set of the values seen so far. For each number, try to add it to the set. If it was already there, you have found a repeat and can stop at once with `true`. If you reach the end without that happening, every value was different, so the answer is `false`.

Time O(n): one pass, and each set insert is O(1) on average. Space O(n): when there is no repeat, the set ends up holding every value.

The other answer worth naming: sort the array and check neighbours. That is O(n log n) time but needs no extra set if you may sort in place, which is the trade an interviewer may push you towards.
:::

::: Swift solution
```swift
func containsDuplicate(_ numbers: [Int]) -> Bool {
    var seen = Set<Int>()
    for number in numbers {
        if !seen.insert(number).inserted {
            return true                      // already there: stop at the first repeat
        }
    }
    return false
}
```

`insert` returns a pair, and its `inserted` part is `false` when the value was already in the set. So one hash both checks and records, and the loop can stop as soon as a repeat appears.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (empty, a single number, negatives with a repeat, a repeat at the very end of a long array, `Int.min` and `Int.max` side by side), and 3,000 random arrays checked against a brute force that compares every pair.
:::

::: Walk it through
**`[4, 9, 2, 9]`**

| Number | Set before | Inserted? | Result |
|---|---|---|---|
| 4 | `{}` | yes | go on |
| 9 | `{4}` | yes | go on |
| 2 | `{4, 9}` | yes | go on |
| 9 | `{4, 9, 2}` | no | return `true` |

**`[7, 3, 1]`** — each insert succeeds, the loop ends, and the answer is `false`. The set holds all three values at the end, which is the O(n) space worst case.
:::

::: The Swift trap
**The one-liner is correct, but it never stops early.** `Set(numbers).count != numbers.count` is the answer many people write first, and it is fine to say. It always builds the whole set, though, even when the repeat is in the first two positions; the loop with `insert(_:).inserted` stops there. The slower trap is checking with `seen.contains(number)` and then calling `seen.insert(number)`: that hashes each value twice, and it is easy to forget the insert altogether.

If the interviewer makes it generic over `Hashable` and passes `Double`s, say this out loud: `Double.nan` is not equal to itself, so `Set([Double.nan, .nan])` holds **two** elements and a duplicate NaN is never reported.
:::

::: What they ask next
- **"Do it with O(1) extra memory."** → Sort in place (`numbers.sort()`) and compare each value with its neighbour. O(n log n) time, and the caller's array changes, so say that.
- **"Is there a repeat within k positions of each other?"** → Keep a set of only the last k values: insert the new one, and remove the one that just fell k positions behind. O(n) time, O(k) space.
- **"Return the value that repeats."** → Return `number` instead of `true` at the point where the insert fails.
:::
