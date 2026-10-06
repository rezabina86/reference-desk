---
title: 37 · LRU Cache
summary: Design a fixed-size key-value store where reads and writes are constant time and, when full, it drops the entry that was used longest ago.
group: Linked list
minutes: 30
sources:
- LeetCode 146 · LRU Cache | https://leetcode.com/problems/lru-cache/
- The Swift Programming Language · Weak and Unowned References | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/#Resolving-Strong-Reference-Cycles-Between-Class-Instances
- Apple · NSCache | https://developer.apple.com/documentation/foundation/nscache
---

*Medium · G*

Build a cache type that holds at most `capacity` entries, each an integer key with an integer value. `get(key)` returns the key's value, or −1 if it isn't there. `put(key, value)` stores the value, replacing any old value for that key. Both count as *using* the key. When `put` adds a new key to a cache that is already full, it first throws out the key that was used longest ago. Both operations must run in constant average time.

| Capacity | Calls | What the `get`s return |
|---|---|---|
| 2 | put(1, 10), put(2, 20), get(1), put(3, 30), get(2), get(3), put(1, 11), get(1) | `10, −1, 30, 11` — adding 3 evicts 2, because 1 was just read |
| 1 | put(5, 50), put(6, 60), get(5), get(6) | `−1, 60` |
| 2 | put(1, 1), put(2, 2), put(1, 100), put(3, 3), get(2), get(1), get(3) | `−1, 100, 3` — updating 1 counts as using it |

Constraints that matter: capacity from 1 to 3,000, up to 200,000 calls. O(1) for both operations rules out scanning for the oldest entry and rules out an array you remove from the front.

The tests drive the type with a list of calls and compare what the `get`s return.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct LRUCacheTests {

    enum Call: Sendable {
        case put(Int, Int)
        case get(Int)
    }

    @Test(arguments: [
        (2, [Call.put(1, 10), .put(2, 20), .get(1), .put(3, 30), .get(2), .get(3), .put(1, 11), .get(1)], [10, -1, 30, 11]),
        (1, [Call.put(5, 50), .put(6, 60), .get(5), .get(6)], [-1, 60]),
        (2, [Call.put(1, 1), .put(2, 2), .put(1, 100), .put(3, 3), .get(2), .get(1), .get(3)], [-1, 100, 3]),
    ])
    func evictsTheLeastRecentlyUsedKey(capacity: Int, calls: [Call], expected: [Int]) {
        let cache = LRUCache(capacity: capacity)
        var results: [Int] = []
        for call in calls {
            switch call {
            case let .put(key, value): cache.put(key, value)
            case let .get(key): results.append(cache.get(key))
            }
        }
        #expect(results == expected)
    }

    // MARK: - Privates
    private final class LRUCache {
        init(capacity: Int) {}
        func get(_ key: Int) -> Int { -1 }
        func put(_ key: Int, _ value: Int) {}
    }
}
```

In a playground:

```swift
final class LRUCache {
    init(capacity: Int) {}
    func get(_ key: Int) -> Int { -1 } // your solution
    func put(_ key: Int, _ value: Int) {}
}

enum Call {
    case put(Int, Int)
    case get(Int)
}

let cases: [(Int, [Call], [Int])] = [
    (2, [.put(1, 10), .put(2, 20), .get(1), .put(3, 30), .get(2), .get(3), .put(1, 11), .get(1)], [10, -1, 30, 11]),
    (1, [.put(5, 50), .put(6, 60), .get(5), .get(6)], [-1, 60]),
    (2, [.put(1, 1), .put(2, 2), .put(1, 100), .put(3, 3), .get(2), .get(1), .get(3)], [-1, 100, 3]),
]
for (capacity, calls, expected) in cases {
    let cache = LRUCache(capacity: capacity)
    var got: [Int] = []
    for call in calls {
        switch call {
        case let .put(key, value): cache.put(key, value)
        case let .get(key): got.append(cache.get(key))
        }
    }
    print(got == expected ? "PASS" : "FAIL", "capacity", capacity, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Dictionary plus doubly linked list.** The cue is *"least recently used"* together with *"O(1)"*. Finding a key in O(1) needs a dictionary; keeping entries in order of use, and moving one to the front or dropping the last in O(1), needs a list where each entry knows both its neighbours.
:::

::: Approach
Keep the entries in a chain ordered by use: the most recently used at the front, the one used longest ago at the back. Each entry links to the one before and the one after it, so it can be taken out of the middle without walking the chain. Next to the chain, a dictionary maps each key to its entry. A read looks the key up, unhooks its entry and puts it back at the front. A write to an existing key does the same after changing the value. A write of a new key into a full cache first unhooks the entry at the back and deletes its key from the dictionary — which is why each entry also stores its key — and then adds the new entry at the front. Two placeholder entries, one at each end of the chain, mean "unhook" and "add at the front" never have to check for an empty chain.

Time O(1) average for both: one dictionary operation and a fixed number of link changes. Space O(capacity).
:::

::: Swift solution
```swift
final class LRUCache {
    private final class Node {
        let key: Int
        var value: Int
        weak var prev: Node?          // weak: next is the owning direction
        var next: Node?
        init(key: Int, value: Int) { self.key = key; self.value = value }
    }

    private let capacity: Int
    private var nodes: [Int: Node] = [:]
    private let head = Node(key: 0, value: 0)    // placeholder before the most recent
    private let tail = Node(key: 0, value: 0)    // placeholder after the least recent

    init(capacity: Int) {
        self.capacity = capacity
        head.next = tail
        tail.prev = head
    }

    func get(_ key: Int) -> Int {
        guard let node = nodes[key] else { return -1 }
        moveToFront(node)
        return node.value
    }

    func put(_ key: Int, _ value: Int) {
        if let node = nodes[key] {
            node.value = value
            moveToFront(node)
            return
        }
        if nodes.count == capacity, let oldest = tail.prev, oldest !== head {
            unlink(oldest)
            nodes[oldest.key] = nil
        }
        let node = Node(key: key, value: value)
        nodes[key] = node
        insertAtFront(node)
    }

    private func unlink(_ node: Node) {
        node.prev?.next = node.next
        node.next?.prev = node.prev
    }

    private func insertAtFront(_ node: Node) {
        node.next = head.next
        node.prev = head
        head.next?.prev = node
        head.next = node
    }

    private func moveToFront(_ node: Node) {
        unlink(node)
        insertAtFront(node)
    }
}
```

The node stores its own `key` so eviction can delete the dictionary entry: the chain tells you *which* node is oldest, and only the node can tell you which key that was.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (capacity 1 with repeated puts of one key, updating the oldest key so a different one is evicted, a get of a missing key not changing the order, 10,000 puts into capacity 3, reading every key in reverse order before evicting), 300 random call sequences of 500 calls checked against an array-based cache, and a deinit count showing every node is freed when the cache is — which fails if `prev` is made strong.
:::

::: Walk it through
**Capacity 2: put(1, 10), put(2, 20), get(1), put(3, 30), get(2), get(3), put(1, 11), get(1)** — the chain is written most recent first.

| Call | Chain after | Returns |
|---|---|---|
| put(1, 10) | `1` | — |
| put(2, 20) | `2, 1` | — |
| get(1) | `1, 2` | 10 |
| put(3, 30) | full: evict the back, 2 → `3, 1` | — |
| get(2) | `3, 1` | −1 |
| get(3) | `3, 1` | 30 |
| put(1, 11) | update and move: `1, 3` | — |
| get(1) | `1, 3` | 11 |

**Capacity 1: put(5, 50), put(6, 60), get(5), get(6)** — the second put finds the cache full and evicts 5, the only entry; the placeholders keep the chain valid while it's briefly empty. `get(5)` is −1, `get(6)` is 60.
:::

::: The Swift trap
**Strong `prev` and strong `next` is a memory leak.** Each pair of neighbours would point at each other strongly — a reference cycle — so when the cache itself is released, ARC frees the dictionary but not a single node. Nothing crashes and every test still passes; the leak only shows in Instruments or a deinit counter. Make one direction non-owning: `next` owns, `prev` doesn't. `weak var prev` is the safe default: if the node it points at goes away, it becomes `nil`. `unowned var prev` also works, because while a node is in the chain its predecessor is always alive, and it skips weak-reference bookkeeping; but read it after that predecessor is freed and the app traps. Say that trade-off out loud, then pick `weak` unless the interviewer pushes on speed.
:::

::: What they ask next
- **"Where would you use this in an iOS app?"** → An image or thumbnail cache in a scrolling list, keyed by URL. Mention `NSCache`: thread-safe and evicts under memory pressure, but it doesn't promise LRU order, so you'd still build this when the order matters, and protect it with an `actor` or a lock once more than one thread touches it.
- **"Make it thread-safe."** → Wrap it in an `actor` so calls are serialised, or guard both methods with a lock (`Mutex` from the Synchronization module, iOS 18+); the linked list itself can't be shared lock-free.
- **"Evict by total byte size instead of entry count."** → Store each entry's cost, keep a running total, and evict from the back in a loop until the new entry fits.
:::
