---
title: 05 · A cache for any type
summary: A generic cache built on a protocol with an associated type — review it, then make it safe for account data.
minutes: 25
group: Review, then extend
sources:
- Glassdoor · Revolut Senior iOS — "given a protocol with associated type, code a cache system for that type" | https://www.glassdoor.ie/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Glassdoor · Revolut Senior iOS — pair-programming task on caching | https://www.glassdoor.com/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Apple · Mutex (Synchronization) | https://developer.apple.com/documentation/synchronization/mutex
- Apple · NSCache | https://developer.apple.com/documentation/foundation/nscache
---

*Shape: review, then extend · Reported: Revolut asked for exactly this cache, by protocol with an
associated type · Verified: the snippet only warns in Swift 6 mode; the fix builds clean and its
tests pass, Swift 6.4*

> "Here's a cache a teammate wrote. It's called from several places at once. Review it — then
> tell me what you'd change before we put account data in it."

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
- What happens to the cache when the user logs out?
- A transfer changes one account's balance. How do you make the cache forget just that account?
- What stops this cache from growing forever, or from showing this morning's balance tonight?
:::

::: The key — what I expect a senior to find
1. **Data race.** `Dictionary` isn't thread-safe. Concurrent writes can corrupt it or crash
   during a resize. Swift 6.4 only *warns* at the call site (*main actor-isolated let 'cache' can
   not be referenced from a nonisolated context* — top-level code runs on the main actor). Treat
   that warning as an error. Fix: guard the dictionary with a lock.
2. **No way to clear it.** On logout the previous user's accounts must go — a privacy bug in a
   banking app. Add `removeAll()`.
3. **No way to forget one account.** After a transfer, the old balance keeps showing until the
   app restarts. Add `removeValue(for:)`.
4. **No size limit.** The cache grows forever; on a phone that ends in a memory-pressure kill.
5. **No response to memory warnings.** `NSCache` evicts under pressure for free; a dictionary
   doesn't.
6. **No expiry.** A balance cached at 9:00 is shown at 17:00 as if current.
7. **`Double` for a balance.** Binary floating point can't hold 0.10 exactly. Use `Decimal`.
8. **`Cache` can't be `Sendable`.** `Account` is fine — a struct of `Sendable` fields is
   `Sendable` on its own. But `Cache<Value>` puts no limit on `Value`, so the compiler can't prove
   the cache is safe to share across threads. Require `Cacheable: Sendable` (and a `Sendable` key),
   then the locked class can be `Sendable` without `@unchecked`.
9. **The key is fixed by the value.** Each value names its own key, so there's one way to look a
   type up. You can't cache accounts by IBAN in one place and by id in another, or key by something
   the value doesn't carry, like a request URL. A `Cache<Key, Value>` is more flexible.
10. **A global instance.** `let cache` at the top level is hard to swap in tests and easy to forget
    on logout. Inject it.
11. **No load-once.** Once it sits in front of the network, ten screens that miss the same account
    fire ten requests. Keep the running load per key and let later callers wait for it.
:::

::: The idea behind it
A cache is a small, fast memory of answers you've already fetched, so you don't fetch them again.
Three questions make one safe: who can touch it at the same time, how long an answer stays true,
and when it must forget.

Swift's `Dictionary` isn't safe to change from two threads at once. That's a *data race*, and it
can corrupt memory or crash. A *lock* fixes it: only one thread can hold it at a time, so only one
thread touches the dictionary at a time. `Mutex` (Synchronization, iOS 18+) wraps the value it
protects, so you can't reach the dictionary without taking the lock.

An *actor* is the other answer: an object that lets one caller in at a time, enforced by the
compiler. But every call into an actor needs `await`, and this cache is called from plain,
synchronous code. A lock keeps the call sites as they are.

For account data, "when it must forget" matters most: everything on logout, and one account when
its balance changes.
:::

::: The fix
```swift
import Synchronization

protocol Cacheable: Sendable {                                  // key 8
    associatedtype Key: Hashable & Sendable
    var cacheKey: Key { get }
}

final class Cache<Value: Cacheable>: Sendable {                 // key 8
    private let storage = Mutex<[Value.Key: Value]>([:])         // key 1: one thread at a time

    func insert(_ value: Value) {
        storage.withLock { $0[value.cacheKey] = value }
    }

    func value(for key: Value.Key) -> Value? {
        storage.withLock { $0[key] }
    }

    func removeValue(for key: Value.Key) {                      // key 3: after a transfer
        storage.withLock { $0[key] = nil }
    }

    func removeAll() {                                          // key 2: on logout
        storage.withLock { $0.removeAll() }
    }
}

struct Account: Cacheable {
    let id: String
    let balance: Decimal                                        // key 7
    var cacheKey: String { id }
}

let cache = Cache<Account>()
DispatchQueue.concurrentPerform(iterations: 1_000) { i in
    cache.insert(Account(id: "\(i)", balance: Decimal(i)))
}
```

**Said out loud, not coded:** a count limit (or `NSCache` with `countLimit`, which also evicts
on memory warnings); expiry with an injected clock; load-once for many callers; injecting the cache
instead of a global; a `Cache<Key, Value>`; an actor instead of the lock if every caller is async.

Why each piece:

- **A `Mutex`, not an actor** — the call site is synchronous (`concurrentPerform` can't `await`),
  so a lock keeps every caller unchanged. Below iOS 18, `OSAllocatedUnfairLock` or `NSLock` does
  the same job.
- **`Sendable` without `@unchecked`** — `Mutex` is `Sendable` when what it holds is, which is why
  the protocol now requires it. The compiler checks the claim, and the call-site warning goes away.
- **Keep the lock short** — each `withLock` does one dictionary operation. Never call out (to a
  loader, a callback) while holding it.
:::

::: Now write the tests
> "Good. Account data goes in this tomorrow. Write me the tests that would let you sleep tonight."

**What I'd test, and why**

1. **Many threads, no lost writes.** 1,000 inserts from many threads at once, across 10 accounts;
   all 10 must be there. That's the data race. Without the lock this test crashes rather than
   failing politely — a crash is still a red test.
2. **`removeAll()` empties the cache** — the logout privacy bug.
3. **`removeValue(for:)` drops only that account** — the stale balance after a transfer, and the
   check that it doesn't take the other accounts with it.

I wouldn't test `Mutex` or `Dictionary` themselves — that's Apple's code.

**The seam.** None needed: the cache has no dependencies, so the tests use it directly.

```swift
import Foundation
import Testing

struct CacheTests {

    @Test func concurrentInsertsKeepEveryKey() {
        // Given 1,000 inserts from many threads at once, across 10 accounts
        let cache = Cache<Account>()
        DispatchQueue.concurrentPerform(iterations: 1_000) { i in
            cache.insert(Account(id: "\(i % 10)", balance: Decimal(i)))
        }

        // Then all 10 accounts are there
        for id in 0..<10 {
            #expect(cache.value(for: "\(id)")?.id == "\(id)")
        }
    }

    @Test func removeAllEmptiesTheCacheOnLogout() {
        let cache = Cache<Account>()
        cache.insert(Account(id: "a", balance: 10))
        cache.insert(Account(id: "b", balance: 20))

        cache.removeAll()

        #expect(cache.value(for: "a") == nil)
        #expect(cache.value(for: "b") == nil)
    }

    @Test func removeValueDropsOnlyThatAccount() {
        // Given two cached accounts
        let cache = Cache<Account>()
        cache.insert(Account(id: "a", balance: 10))
        cache.insert(Account(id: "b", balance: 20))

        // When a transfer changes account a
        cache.removeValue(for: "a")

        // Then a is gone and b stays
        #expect(cache.value(for: "a") == nil)
        #expect(cache.value(for: "b")?.balance == 20)
    }
}
```

Ran with Swift 6.4: 3 tests, all passed.
:::

::: What I'd ask next
- *"Why not just use `NSCache`?"* — A good default for objects: thread-safe, evicts under memory
  pressure, has `countLimit`. But keys and values must be classes (wrap them), and it can evict at
  any time with no expiry policy — fine for images, wrong when you need a predictable lifetime.
- *"Now make it load missing values, once, for many callers."* — Keep a `[Key: Task<Value, Error>]`
  of running loads. A caller that finds one awaits it instead of starting its own; the entry is
  removed when the load ends, so a failure isn't cached. That makes the cache async, so it becomes
  an actor — and because an actor lets other callers in at every `await` (*reentrancy*), the
  running-load table is exactly what stops a second download.
- *"The user logs out while a load is running. What happens?"* — The load finishes and puts the
  old account back. Cancel running loads in `removeAll()` and drop any result that started before
  the clear (a generation counter does it).
- *"Make it survive app restarts."* — `Codable` values in the caches directory, or SwiftData;
  never persist account data unencrypted, and clear it on logout.
:::
