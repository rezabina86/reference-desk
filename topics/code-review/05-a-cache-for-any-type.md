---
title: 05 · A cache for any type
summary: A generic cache built on a protocol with an associated type — review it, then build the version you'd ship.
minutes: 30
sources:
- Glassdoor · Revolut Senior iOS — "given a protocol with associated type, code a cache system for that type" | https://www.glassdoor.ie/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Glassdoor · Revolut Senior iOS — pair-programming task on caching | https://www.glassdoor.com/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Apple · NSCache | https://developer.apple.com/documentation/foundation/nscache
---

*Shape: review, then extend · Reported: Revolut asked for exactly this cache, by protocol with an
associated type · Compiled with Swift 6.2: the snippet fails in Swift 6 mode, the fix passes and
was run*

> "Here's a cache a teammate wrote. It's called from several places at once. Review it — then tell
> me what you'd change before we put account data in it."

```swift
protocol Cacheable {
    associatedtype Key: Hashable
    var cacheKey: Key { get }
}

final class Cache<Value: Cacheable> {
    private var storage: [Value.Key: Value] = [:]

    func insert(_ value: Value) {
        storage[value.cacheKey] = value
    }

    func value(for key: Value.Key) -> Value? {
        storage[key]
    }
}

struct Account: Cacheable {
    let id: String
    let balance: Double
    var cacheKey: String { id }
}

let cache = Cache<Account>()
DispatchQueue.concurrentPerform(iterations: 1_000) { i in
    cache.insert(Account(id: "\(i)", balance: Double(i)))
}
```

::: The key
1. **Data race.** `Dictionary` isn't thread-safe; concurrent writes can corrupt it or crash during
   a resize. Swift 6 refuses to compile the call site — verified. (On a one-core test machine the
   race didn't visibly misbehave, which is the point: races pass tests and crash in production.)
2. **No size limit.** The cache grows forever; on a phone that ends in a memory-pressure kill.
3. **No expiry.** A balance cached at 9:00 is shown at 17:00 as if current.
4. **No response to memory warnings.** `NSCache` evicts on pressure for free; a dictionary doesn't.
5. **No in-flight deduplication.** Ten screens asking for the same account miss together and fire
   ten network requests.
6. **No way to clear it.** On logout the previous user's accounts must go — a privacy bug in a
   banking app.
7. **`Double` for a balance.** Use `Decimal`.
8. **`Cacheable` isn't `Sendable`**, so values can't safely cross threads under Swift 6.
:::

::: The version I'd ship (Swift 6, verified)
```swift
protocol Cacheable: Sendable {
    associatedtype Key: Hashable & Sendable
    var cacheKey: Key { get }
}

actor Cache<Value: Cacheable> {

    private struct Entry {
        let value: Value
        let expiry: ContinuousClock.Instant
    }

    private var storage: [Value.Key: Entry] = [:]
    private var order: [Value.Key] = []                 // oldest first
    private var inFlight: [Value.Key: Task<Value, Error>] = [:]
    private var generation = 0                          // bumped by removeAll()
    private let countLimit: Int
    private let lifetime: Duration
    private let clock = ContinuousClock()

    init(countLimit: Int = 100, lifetime: Duration = .seconds(60)) {
        self.countLimit = countLimit
        self.lifetime = lifetime
    }

    func insert(_ value: Value) {
        let key = value.cacheKey
        storage[key] = Entry(value: value, expiry: clock.now + lifetime)
        order.removeAll { $0 == key }
        order.append(key)
        while order.count > countLimit {
            storage[order.removeFirst()] = nil
        }
    }

    func value(for key: Value.Key) -> Value? {
        guard let entry = storage[key] else { return nil }
        guard entry.expiry > clock.now else {
            storage[key] = nil
            order.removeAll { $0 == key }
            return nil
        }
        return entry.value
    }

    /// Returns the cached value, or loads it once even if many callers ask at the same time.
    func value(for key: Value.Key,
               orLoad load: @escaping @Sendable () async throws -> Value) async throws -> Value {
        if let cached = value(for: key) { return cached }
        let started = generation
        let task: Task<Value, Error>
        if let running = inFlight[key] {
            task = running
        } else {
            task = Task { try await load() }
            inFlight[key] = task
        }
        // Only clear our own entry: after removeAll() a newer load may own this key.
        defer { if inFlight[key] == task { inFlight[key] = nil } }
        let value = try await task.value
        // Cleared (logout) while this ran: don't cache or return the previous user's data.
        guard generation == started else { throw CancellationError() }
        insert(value)
        return value
    }

    func removeAll() {
        inFlight.values.forEach { $0.cancel() }
        inFlight.removeAll()
        storage.removeAll()
        order.removeAll()
        generation += 1
    }
}
```

What the run showed: 1,000 concurrent inserts across 10 keys with a limit of 3 kept exactly 3;
an entry read after its lifetime came back `nil`; 50 concurrent callers for the same missing key
triggered **one** load and all got the same value.

Why each piece:

- **Actor, not a lock** — the compiler enforces exclusive access; with a lock it's a convention.
  A `Mutex` (Synchronization, iOS 18+) is the right switch if callers can't be `async`.
- **`order` array for eviction** — evicts oldest-inserted. Removing from an array is O(n), which is
  fine at a limit of 100; at thousands of entries, swap in a doubly linked list plus dictionary for
  O(1) true LRU.
- **`ContinuousClock`** — keeps counting while the device sleeps, so expiry is wall-time honest;
  `Date` can jump when the user changes the clock.
- **The in-flight dictionary** — this is the reentrancy fix. Every `await` lets another caller into
  the actor; without the stored task, the second caller would see "not cached" and start its own
  load.
- **`generation` and the cancel in `removeAll()`** — the same reentrancy, seen from logout. A load
  that started before `removeAll()` finishes after it; without the check it would put the previous
  user's account straight back into the cache it was just cleared from. Cancelling stops the
  network work; the generation check covers a `load` that ignores cancellation.
:::

::: What I'd ask next
- *"Why not just use `NSCache`?"* — Good default for objects: thread-safe, evicts under memory
  pressure. But keys must be `AnyObject` (wrap them), values must be classes, and it can evict at
  any time with no expiry policy — fine for images, wrong when you need predictable lifetime.
- *"Where's the bug if `load` throws?"* — Nothing is cached and the in-flight entry is removed by
  `defer`, so the next caller retries. Say whether you'd want a short negative cache.
- *"Make it survive app restarts."* — Codable values written to the caches directory, or SwiftData;
  never persist sensitive data unencrypted, and clear it on logout.
- *"How do you test expiry without waiting a minute?"* — Inject the clock (a `Clock` protocol
  generic, or a test clock) instead of creating `ContinuousClock` inside.
:::
