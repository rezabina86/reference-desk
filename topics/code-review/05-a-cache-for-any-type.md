---
title: 05 · A cache for any type
summary: A generic cache built on a protocol with an associated type — review it, then build the version you'd ship.
minutes: 30
group: Review, then extend
sources:
- Glassdoor · Revolut Senior iOS — "given a protocol with associated type, code a cache system for that type" | https://www.glassdoor.ie/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Glassdoor · Revolut Senior iOS — pair-programming task on caching | https://www.glassdoor.com/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Apple · NSCache | https://developer.apple.com/documentation/foundation/nscache
---

*Shape: review, then extend · Reported: Revolut asked for exactly this cache, by protocol with an
associated type · Compiled in Swift 6 mode: Swift 6.2 rejected the snippet, Swift 6.4
only warns; the fix compiles with Swift 6.4 in Swift 6 mode and was run*

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

::: A hint, if you're stuck
- Several callers at once: what does a `Dictionary` do when two threads write to it together?
- What stops this cache from growing forever, or from showing this morning's balance tonight?
- Ten callers ask for the same missing key at the same moment. How many network calls?
- What happens to the cache when the user logs out?
:::

::: The key
1. **Data race.** `Dictionary` isn't thread-safe; concurrent writes can corrupt it or crash during
   a resize. In Swift 6 mode, Swift 6.2 refused to compile the call site; Swift 6.4 only warns
   (*capture of 'cache' with non-Sendable type*) — both verified. Treat that warning as an error.
   (On a one-core test machine the
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

::: The idea behind it
A cache is a small, fast memory of answers you've already fetched, so you don't fetch them again.
Three questions make one safe: who can touch it at the same time, how big it may grow, and how long
an answer stays true.

Swift's `Dictionary` isn't safe to change from two threads at once. That's a *data race*, and it
can corrupt memory or crash. An *actor* fixes it: an actor is an object that lets only one caller
inside at a time, and the compiler enforces that.

Actors have one catch, called *reentrancy*. Whenever the actor waits (`await`), it lets the next
caller in. So "check the cache, wait for the network, store the answer" isn't one unbroken step — a
second caller can slip in during the wait, see nothing cached, and start the same download. The fix
is to remember the download that's already running and let later callers wait for that one.

A count limit and an expiry time stop it growing forever or serving stale data. And `removeAll` on
logout — which also stops downloads that are still running — keeps one user's data from reaching
the next.
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
    private let now: @Sendable () -> ContinuousClock.Instant

    init(countLimit: Int = 100, lifetime: Duration = .seconds(60),
         now: @escaping @Sendable () -> ContinuousClock.Instant = { .now }) {
        self.countLimit = countLimit
        self.lifetime = lifetime
        self.now = now
    }

    func insert(_ value: Value) {
        let key = value.cacheKey
        storage[key] = Entry(value: value, expiry: now() + lifetime)
        order.removeAll { $0 == key }
        order.append(key)
        while order.count > countLimit {
            storage[order.removeFirst()] = nil
        }
    }

    func value(for key: Value.Key) -> Value? {
        guard let entry = storage[key] else { return nil }
        guard entry.expiry > now() else {
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
- **`ContinuousClock`, read through an injected `now`** — it keeps counting while the device
  sleeps, so expiry is wall-time honest; `Date` can jump when the user changes the clock. The app
  uses the default (`ContinuousClock.now`); a test passes a clock it moves by hand.
- **The in-flight dictionary** — this is the reentrancy fix. Every `await` lets another caller into
  the actor; without the stored task, the second caller would see "not cached" and start its own
  load.
- **`generation` and the cancel in `removeAll()`** — the same reentrancy, seen from logout. A load
  that started before `removeAll()` finishes after it; without the check it would put the previous
  user's account straight back into the cache it was just cleared from. Cancelling stops the
  network work; the generation check covers a `load` that ignores cancellation.
:::

::: Now write the tests
> "Good. Account data goes in this tomorrow. Write me the tests that would let you sleep tonight."

What I'd test, and why:

1. **Many callers, one load.** Ten callers ask for the same missing key while the load is still
   running; the loader must run once and all ten get the same account. That's the reentrancy fix,
   and the bug a reviewer can't see by reading.
2. **The count limit evicts the oldest.** Insert three into a cache of two; the first one goes.
3. **Expiry.** At 59 seconds the entry is there; at 60 it's gone. Without this test, a balance
   from this morning is one refactor away from showing tonight.
4. **A failed load isn't cached.** The loader throws once; the next caller loads again and gets
   the value.
5. **`removeAll()` during a load.** The user logs out while a load is running and the load
   returns anyway. The caller must not get the old account, and the cache must stay empty. That's
   the privacy bug from the review.

I wouldn't test `Dictionary` or the actor itself — the compiler already guarantees one caller at a
time.

**The seam.** Two things are passed in, so the test controls them. The loader is a *fake*: a
small stand-in that counts its calls and holds each load open until the test says succeed or
fail, so the test decides when the "network" answers. The clock is the other. The first version
of the fix created `ContinuousClock` inside the actor; I changed it to take a `now` function
(default `ContinuousClock.now`) so a test can move time by hand. Then expiry is tested in
microseconds, not by waiting a minute.

```swift
import Synchronization
import Testing

struct Account: Cacheable, Equatable {
    let id: String
    let balance: Int
    var cacheKey: String { id }
}

/// A clock the test moves by hand, so expiry needs no waiting.
final class TestTime: Sendable {
    private let start = ContinuousClock.now
    private let elapsed = Mutex<Duration>(.zero)

    func now() -> ContinuousClock.Instant { start + elapsed.withLock { $0 } }
    func advance(by duration: Duration) { elapsed.withLock { $0 += duration } }
}

/// A fake loader: it counts calls and suspends each one until the test releases it.
@MainActor
final class ControlledLoader {
    private(set) var calls = 0
    private var pending: [CheckedContinuation<Account, Error>] = []
    private var waiters: [(count: Int, resume: CheckedContinuation<Void, Never>)] = []

    func load() async throws -> Account {
        calls += 1
        for waiter in waiters where calls >= waiter.count { waiter.resume.resume() }
        waiters.removeAll { calls >= $0.count }
        return try await withCheckedThrowingContinuation { pending.append($0) }
    }

    func waitForCalls(_ count: Int) async {
        if calls >= count { return }
        await withCheckedContinuation { waiters.append((count, $0)) }
    }

    func succeed(with account: Account) {
        pending.forEach { $0.resume(returning: account) }
        pending.removeAll()
    }

    func fail(with error: Error) {
        pending.forEach { $0.resume(throwing: error) }
        pending.removeAll()
    }
}

struct LoadFailed: Error {}

@MainActor
struct CacheTests {

    @Test
    func concurrentCallersForOneKeyTriggerOneLoad() async throws {
        // Given ten callers asking for the same missing key while the load is still running
        let cache = Cache<Account>()
        let loader = ControlledLoader()
        let callers = (0..<10).map { _ in
            Task { try await cache.value(for: "a1") { try await loader.load() } }
        }
        await loader.waitForCalls(1)
        for _ in 0..<200 { await Task.yield() }   // let the other callers reach the cache

        // When the one load finishes
        loader.succeed(with: Account(id: "a1", balance: 50))

        // Then every caller got the same account from a single load
        for caller in callers {
            #expect(try await caller.value == Account(id: "a1", balance: 50))
        }
        #expect(loader.calls == 1)
    }

    @Test
    func countLimitEvictsTheOldest() async {
        // Given a cache that holds two accounts
        let cache = Cache<Account>(countLimit: 2)

        // When a third is inserted
        await cache.insert(Account(id: "a", balance: 1))
        await cache.insert(Account(id: "b", balance: 2))
        await cache.insert(Account(id: "c", balance: 3))

        // Then the oldest is gone and the newer two stay
        #expect(await cache.value(for: "a") == nil)
        #expect(await cache.value(for: "b") == Account(id: "b", balance: 2))
        #expect(await cache.value(for: "c") == Account(id: "c", balance: 3))
    }

    @Test
    func entryExpiresAfterItsLifetime() async {
        // Given an account cached with a 60-second lifetime
        let time = TestTime()
        let cache = Cache<Account>(lifetime: .seconds(60), now: time.now)
        await cache.insert(Account(id: "a", balance: 1))

        // When 59 seconds pass, it is still there
        time.advance(by: .seconds(59))
        #expect(await cache.value(for: "a") == Account(id: "a", balance: 1))

        // When the minute is up, it is gone
        time.advance(by: .seconds(1))
        #expect(await cache.value(for: "a") == nil)
    }

    @Test
    func failedLoadIsNotCachedAndTheNextCallerRetries() async throws {
        // Given a load that fails
        let cache = Cache<Account>()
        let loader = ControlledLoader()
        let first = Task { try await cache.value(for: "a1") { try await loader.load() } }
        await loader.waitForCalls(1)
        loader.fail(with: LoadFailed())
        await #expect(throws: LoadFailed.self) { try await first.value }

        // When the next caller asks
        let second = Task { try await cache.value(for: "a1") { try await loader.load() } }
        await loader.waitForCalls(2)
        loader.succeed(with: Account(id: "a1", balance: 7))

        // Then it loads again and gets the value
        #expect(try await second.value == Account(id: "a1", balance: 7))
        #expect(loader.calls == 2)
    }

    @Test
    func removeAllDuringALoadDoesNotCacheTheOldValue() async {
        // Given a load for the previous user's account still running
        let cache = Cache<Account>()
        let loader = ControlledLoader()
        let caller = Task { try await cache.value(for: "a1") { try await loader.load() } }
        await loader.waitForCalls(1)

        // When the user logs out, and then the load returns anyway
        await cache.removeAll()
        loader.succeed(with: Account(id: "a1", balance: 999))

        // Then the caller doesn't get the old account, and the cache stays empty
        await #expect(throws: CancellationError.self) { try await caller.value }
        #expect(await cache.value(for: "a1") == nil)
    }
}
```

One honest note on the first test. A test can't see inside the actor, so it can't know for
certain that all ten callers have arrived before the load finishes. It gives them a fixed number
of turns first, then releases the load. A caller that still arrived late would find the account
cached, so a correct fix never fails this test. With the in-flight dictionary removed, the
callers that are waiting each start their own load, and it fails.

Ran with Swift 6.4: 5 tests, all passed.
:::

::: What I'd ask next
- *"Why not just use `NSCache`?"* — Good default for objects: thread-safe, evicts under memory
  pressure. But keys must be `AnyObject` (wrap them), values must be classes, and it can evict at
  any time with no expiry policy — fine for images, wrong when you need predictable lifetime.
- *"Where's the bug if `load` throws?"* — Nothing is cached and the in-flight entry is removed by
  `defer`, so the next caller retries. Say whether you'd want a short negative cache.
- *"Make it survive app restarts."* — Codable values written to the caches directory, or SwiftData;
  never persist sensitive data unencrypted, and clear it on logout.
- *"Why `now` as a closure and not a `Clock`?"* — It's the smallest seam that makes expiry
  testable: the test hands in a time it moves by hand (see the tests above). A generic `C: Clock`
  parameter also works and lets you inject a test clock that can sleep, but it makes every use
  site spell out the clock type — more ceremony than a cache needs.
:::
