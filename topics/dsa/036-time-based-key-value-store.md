---
title: 30 · Time Based Key-Value Store
summary: Build a key-value store that keeps every value a key has had over time and answers what the value was at any given moment.
group: Binary search
minutes: 25
sources:
- LeetCode 981 · Time Based Key-Value Store | https://leetcode.com/problems/time-based-key-value-store/
- Swift standard library · Dictionary.subscript(_:default:) | https://developer.apple.com/documentation/swift/dictionary/subscript(_:default:)-45arb
---

*Medium · G*

Design a store with two operations. `set(key, value, at: t)` records that the key held that value from time t on. `get(key, at: t)` returns the value the key held at time t: the value from the latest `set` whose time is at or before t. If the key was never set, or only set after t, return the empty string. Times passed to `set` only ever increase across calls.

The tests replay a list of operations — `"set lamp off 2"`, `"get lamp 5"` — and collect what each `get` returned.

| Operations | Gets return |
|---|---|
| set lamp off 2, set lamp on 7, get lamp 5, get lamp 7, get lamp 100 | `["off", "on", "on"]` |
| set door shut 10, get door 9, get window 10 | `["", ""]` — asked before the first set, and a key never set; the edge cases |
| set a x 1, set b y 2, get a 2, get b 1 | `["x", ""]` — each key keeps its own history |

Constraints that matter: up to 200,000 calls in total; times between 1 and 10⁷. Scanning a key's whole history on each `get` is O(n) per call; the target is O(1) for `set` and O(log n) for `get`.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct TimeBasedKeyValueStoreTests {

    @Test(arguments: [
        (["set lamp off 2", "set lamp on 7", "get lamp 5", "get lamp 7", "get lamp 100"], ["off", "on", "on"]),
        (["set door shut 10", "get door 9", "get window 10"], ["", ""]),
        (["set a x 1", "set b y 2", "get a 2", "get b 1"], ["x", ""]),
    ])
    func returnsTheLatestValueAtOrBeforeTheAskedTime(operations: [String], expected: [String]) {
        #expect(run(operations) == expected)
    }

    // MARK: - Privates
    /// Replays "set key value time" and "get key time", and returns what each "get" returned.
    private func run(_ operations: [String]) -> [String] {
        var store = TimeMap()
        var results: [String] = []
        for operation in operations {
            let parts = operation.split(separator: " ").map(String.init)
            if parts[0] == "set" {
                store.set(parts[1], parts[2], at: Int(parts[3])!)
            } else {
                results.append(store.get(parts[1], at: Int(parts[2])!))
            }
        }
        return results
    }
}

private struct TimeMap {
    mutating func set(_ key: String, _ value: String, at timestamp: Int) {}
    func get(_ key: String, at timestamp: Int) -> String { "" }
}
```

In a playground:

```swift
struct TimeMap {
    mutating func set(_ key: String, _ value: String, at timestamp: Int) {} // your solution
    func get(_ key: String, at timestamp: Int) -> String { "" }
}

func run(_ operations: [String]) -> [String] {
    var store = TimeMap()
    var results: [String] = []
    for operation in operations {
        let parts = operation.split(separator: " ").map(String.init)
        if parts[0] == "set" {
            store.set(parts[1], parts[2], at: Int(parts[3])!)
        } else {
            results.append(store.get(parts[1], at: Int(parts[2])!))
        }
    }
    return results
}

let cases: [([String], [String])] = [
    (["set lamp off 2", "set lamp on 7", "get lamp 5", "get lamp 7", "get lamp 100"], ["off", "on", "on"]),
    (["set door shut 10", "get door 9", "get window 10"], ["", ""]),
    (["set a x 1", "set b y 2", "get a 2", "get b 1"], ["x", ""]),
]
for (operations, expected) in cases {
    let got = run(operations)
    print(got == expected ? "PASS" : "FAIL", operations, "→", got, "expected", expected)
}
```

The placeholder `get` returns the empty string, so it already passes the second case.
:::

::: Pattern and cue
**Dictionary of sorted histories, plus binary search.** The cues are *"times only increase"* and *"the latest one at or before t"*. Increasing times mean each key's history is already sorted just by appending, and "latest at or before" is the last entry before the first one that's too late — a binary search.
:::

::: Approach
Keep a dictionary from each key to its history: a list of (time, value) pairs. A `set` appends to the end of that key's list; since times only grow, the list stays sorted with no extra work. A `get` looks up the key's list (no list means the empty string) and binary searches it for the first entry whose time is *after* the asked time. The entry just before that one is the answer; if there's none before it, the key had no value yet, so return the empty string.

Time O(1) amortised per `set` (an append), O(log h) per `get`, where h is the length of that key's history. Space O(n) for everything ever set.
:::

::: Swift solution
```swift
struct TimeMap {
    private var history: [String: [(timestamp: Int, value: String)]] = [:]

    mutating func set(_ key: String, _ value: String, at timestamp: Int) {
        history[key, default: []].append((timestamp, value))     // timestamps arrive increasing
    }

    func get(_ key: String, at timestamp: Int) -> String {
        guard let entries = history[key] else { return "" }
        var low = 0
        var high = entries.count                  // first entry with a timestamp > the asked one
        while low < high {
            let mid = low + (high - low) / 2
            if entries[mid].timestamp <= timestamp {
                low = mid + 1
            } else {
                high = mid
            }
        }
        return low == 0 ? "" : entries[low - 1].value
    }
}
```

The search finds the first entry that is too late (an upper bound), and the answer is the one before it. Searching for "the last entry ≤ t" directly also works, but the off-by-one is easier to get right this way. `high` starts at `entries.count`, not `count - 1`, because "every entry is early enough" is a valid outcome.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, three more (a `get` with no `set` at all, a key set three times and read before, at, between and after each time, the same value set twice), and 1,000 random sequences of 30 operations over three keys checked against a linear scan of everything set so far.
:::

::: Walk it through
**set lamp off 2, set lamp on 7, then three gets**

After the sets, `history["lamp"]` is `[(2, off), (7, on)]`.

| get at | low / high steps | First too-late index | Answer |
|---|---|---|---|
| 5 | mid 1: 7 > 5, high = 1; mid 0: 2 ≤ 5, low = 1 | 1 | entry 0: `off` |
| 7 | mid 1: 7 ≤ 7, low = 2 | 2 | entry 1: `on` |
| 100 | mid 1: 7 ≤ 100, low = 2 | 2 | entry 1: `on` |

**set door shut 10, get door 9, get window 10** — for `door` at 9: mid 0, 10 > 9, high = 0. The first too-late index is 0, nothing comes before it, so the answer is `""`. For `window`, there's no history at all and the `guard` returns `""` before searching.
:::

::: The Swift trap
**Copy the history out and append, and every `set` becomes O(n).** A natural first draft is `var list = history[key] ?? []; list.append(entry); history[key] = list`. While `list` and the dictionary both hold the array, it has two owners, so the `append` copies all of it before adding one entry — copy-on-write doing its job, at the cost of turning a 200,000-call run quadratic. `history[key, default: []].append(entry)` mutates the stored array in place, with no copy. The same applies to any "dictionary of arrays" in Swift: mutate through the subscript, don't read-modify-write.
:::

::: What they ask next
- **"Timestamps can arrive out of order."** → Appending no longer keeps the list sorted: insert at the binary-searched position (O(h) for the shift), or sort lazily before the first `get` after a `set`.
- **"Many reads of the same key at the latest time."** → Also keep the latest value per key in a second dictionary, making the common case O(1).
- **"Make it safe to use from several threads."** → Turn it into an `actor` (calls become `await`), or keep the struct inside one; the value-type design means no shared mutable state leaks out.
:::
