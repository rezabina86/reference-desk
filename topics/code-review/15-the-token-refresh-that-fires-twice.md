---
title: 15 · The token refresh that fires twice
summary: A session manager that logs users out at random when two requests need a fresh token at once — find the race, then find it again after it's "fixed" with an actor.
minutes: 20
group: Find the bug
sources:
- LeetCode Discuss · Snapchat iOS — "Design a class and solve concurrency issues and race conditions" | https://leetcode.com/discuss/interview-experience/1144400/
- LeetCode Discuss · TikTok iOS — threads, GCD, deadlocks, race conditions | https://leetcode.com/discuss/interview-experience/5550559/
- SE-0306 · Actors — actor-isolated functions are reentrant at every await | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0306-actors.md
---

*Shape: find the bug, in two parts · Reported: Snapchat — design a class and solve its
concurrency issues and race conditions; TikTok — threads, GCD and race conditions · Compiled and
run with Swift 6.4: part 1 is rejected in Swift 6 mode and was run in Swift 5 mode; part 2 and the
fix compile in Swift 6 mode with zero warnings and were run against a fake auth server*

> "Support tickets say users get logged out at random, usually right after opening the app in the
> morning. Our backend rotates refresh tokens — each one works once. Here's the session manager.
> What's going on?"

**Part 1** — what's in the app today:

```swift
import Foundation

struct Tokens {
    let access: String
    let refresh: String
    let expiresAt: Date
}

protocol TokenRefresher {
    func refresh(using refreshToken: String,
                 completion: @escaping (Result<Tokens, Error>) -> Void)
}

final class SessionManager {
    static let shared = SessionManager()

    var tokens: Tokens?
    var refresher: TokenRefresher!
    var onLogout: (() -> Void)?

    func withValidToken(_ completion: @escaping (String?) -> Void) {
        if let tokens, tokens.expiresAt > Date() {
            completion(tokens.access)
            return
        }
        refresher.refresh(using: tokens?.refresh ?? "") { result in
            switch result {
            case .success(let newTokens):
                self.tokens = newTokens
                completion(newTokens.access)
            case .failure:
                self.tokens = nil
                self.onLogout?()
                completion(nil)
            }
        }
    }
}
```

**Part 2** — once you've found it, the candidate's fix: "make it an actor, actors can't race."

```swift
protocol TokenRefreshing: Sendable {
    func refresh(using refreshToken: String) async throws -> Tokens
}

actor NaiveSession {
    private var tokens: Tokens?
    private let refresher: any TokenRefreshing

    init(tokens: Tokens?, refresher: any TokenRefreshing) {
        self.tokens = tokens
        self.refresher = refresher
    }

    func validAccessToken() async throws -> String {
        if let tokens, tokens.expiresAt > Date() {
            return tokens.access
        }
        let newTokens = try await refresher.refresh(using: tokens?.refresh ?? "")
        tokens = newTokens
        return newTokens.access
    }
}
```

::: A hint, if you're stuck
- In the morning the access token has expired. The app opens and the feed, profile and inbox all
  load at once. Walk through what each request sees.
- The refresh token works once. What happens to the second refresh that uses it?
- An actor runs one piece of code at a time. Is "one at a time" the same as "one whole function
  at a time"? What happens at `await`?
:::

::: The key — what I expect a senior to find
I ran both against a fake auth server that rotates refresh tokens and takes 50 ms to answer.
Part 1, two requests at once, three runs in Swift 5 mode (real output, one run shown):

```text
refresh #1 with r0: ok -> a1
feed got token: a1
refresh #2 with r0: rejected (already used)
LOGGED OUT
profile got token: nil
refresh calls: 2
```

Part 2, the actor, three requests at once in Swift 6 mode:

```text
actor, no in-flight task:
  refresh #1 with r0: ok -> a1
  refresh #3 with r0: rejected, already used
  feed: a1
  refresh #2 with r0: rejected, already used
  inbox: failed -> log out
  profile: failed -> log out
  refresh calls: 3
```

1. **Check-then-act race: two refreshes.** Both requests check "is the token expired?", both
   see yes, both refresh. Nothing records that a refresh is already running. This is the
   morning-logout bug.
2. **The second refresh destroys the session.** With rotation, the first refresh spends `r0`. The
   second sends the same `r0`, the server rejects it — and in real auth servers that reuse is
   often treated as theft, so the whole session is revoked. The user did nothing wrong.
3. **Data race on `tokens`.** It's read on whatever thread calls `withValidToken` and written on
   whatever queue the refresher calls back on. Unsynchronised reads and writes of a struct with
   strings can tear or crash. Swift 6 refuses part 1 — verified: *static property 'shared' is not
   concurrency-safe*. In Swift 5 mode it compiles with no warning.
4. **The actor doesn't fix it (part 2).** An actor runs one *piece* of code at a time, but it lets
   go at every `await`. While caller 1 waits for the network, callers 2 and 3 enter, see the same
   expired token, and start their own refreshes. Three calls, two logouts. The data race is gone;
   the logic race isn't.
5. **Logout fires once per failed request.** Two failures, two `onLogout` calls — two login
   screens pushed, two analytics events. Logout must happen once.
6. **Any failure logs out.** Offline, a timeout or a 500 also clears the tokens. Only a rejected
   refresh token means "log in again"; a network error means "try later".
7. **No expiry margin.** `expiresAt > Date()` passes a token with one second left; it expires on
   the way to the server and the request gets a 401. Refresh a little early.
8. **Logout during a refresh brings the user back.** Nothing stops a refresh that finishes after
   logout from writing new tokens. That's a privacy bug on a shared device.
9. **Untestable design.** A singleton, an implicitly unwrapped `refresher`, and `Date()` read
   directly mean no test can control time or swap the server.
:::

::: The idea behind it
A *race condition* is a bug where the result depends on the order two things happen in. The
classic shape is *check-then-act*: "if there's no milk, buy milk." Two flatmates read the note at
the same time, both see no milk, both go to the shop. Each step was right. The pair was wrong.

A lock or an actor stops two people reading the note at the *exact* same instant. That fixes
*data races* — two threads touching the same memory at once. It doesn't fix the milk.

Actors have a property called *reentrancy*. When an actor method hits `await`, it pauses and
the actor is free to run other calls. This is deliberate: it stops actors deadlocking while they
wait on each other. But it means anything you checked before an `await` may be false after it.
Between "the token is expired" and "here's the new token" there's a network call, and three other
callers can get in.

The fix is to leave a note on the fridge: "I'm already at the shop." In code, the note is the
in-flight `Task` itself. The first caller creates it and stores it before its first `await`.
Everyone who arrives later finds it and waits for *that* task's result instead of starting
another. When it finishes, the note comes down.
:::

::: The fix
```swift
enum SessionError: Error {
    case loggedOut
}

actor Session {
    private var tokens: Tokens?
    private var refreshTask: Task<Tokens, any Error>?
    private let refresher: any TokenRefreshing
    private let now: @Sendable () -> Date
    private let leeway: TimeInterval = 30

    init(tokens: Tokens?, refresher: any TokenRefreshing, now: @escaping @Sendable () -> Date) {
        self.tokens = tokens
        self.refresher = refresher
        self.now = now
    }

    func validAccessToken() async throws -> String {
        let task: Task<Tokens, any Error>
        if let refreshTask {
            task = refreshTask                  // a refresh is already running: join it
        } else {
            guard let tokens else { throw SessionError.loggedOut }
            if tokens.expiresAt.timeIntervalSince(now()) > leeway {
                return tokens.access
            }
            task = Task { [refresher] in
                try await refresher.refresh(using: tokens.refresh)
            }
            refreshTask = task                  // stored BEFORE the first await
        }

        do {
            let newTokens = try await task.value
            if refreshTask == task {            // first caller back applies the result
                tokens = newTokens
                refreshTask = nil
            }
            guard tokens?.access == newTokens.access else {
                throw SessionError.loggedOut    // logOut() ran while we were waiting
            }
            return newTokens.access
        } catch {
            if refreshTask == task {            // the refresh itself failed
                tokens = nil
                refreshTask = nil
            }
            throw error
        }
    }

    func logOut() {
        refreshTask?.cancel()
        refreshTask = nil
        tokens = nil
    }
}
```

The same harness, run against the fix (real output):

```text
actor + shared refresh task:
  refresh #1 with r0: ok -> a1
  inbox: a1
  profile: a1
  feed: a1
  refresh calls: 1
again, token now fresh:
  feed: a1
  profile: a1
  inbox: a1
  refresh calls: 1
refresh rejected:
  inbox: failed -> log out
  profile: failed -> log out
  feed: failed -> log out
  refresh calls: 1
  next call: loggedOut
log out mid-refresh:
   failed: loggedOut | failed: loggedOut
   next call: loggedOut
```

The last case used a refresher that ignores cancellation and still returns new tokens after
logout. Both waiting callers got `loggedOut`, and the session stayed logged out.

Why each piece:

- **`refreshTask` stored before the first `await`** — this is the whole fix. Between creating the
  task and storing it there is no suspension point, so no other caller can slip in.
- **Joining callers `await task.value`** — every caller gets the same tokens, or the same error.
  One network call, however many requests arrive.
- **"First caller back applies the result"** — whoever resumes first writes the tokens and clears
  the task; the rest see it's already done. No `defer` that a late caller could run at the wrong
  moment.
- **Clearing on failure** — a failed refresh doesn't stay cached, so the next call doesn't
  re-throw an old error forever. Here it also means logged out; see the second question below.
- **The logout check after the `await`** — reentrancy again. `logOut()` can run while callers
  wait. Comparing against the current `tokens` stops a late refresh from logging the user back in.
- **`leeway` and an injected `now`** — refresh 30 seconds early so tokens don't die in flight, and
  a test can move time forward without sleeping.
- **An actor, not a lock** — the compiler checks every access to `tokens`; a lock is a convention
  someone eventually forgets.
:::

::: Now write the tests
> "Good. This one logged people out in production. Write me the tests that make sure it never
> does again."

What I'd test, and why:

1. **Concurrent callers share one refresh.** Three requests hit an expired token at once; the
   server sees `r0` exactly once and all three get `a1`. This is the morning-logout bug, so it
   goes first.
2. **A fresh token needs no refresh.** The happy path must not touch the server at all.
3. **The leeway.** A token with 20 seconds left is refreshed early. Delete the leeway and this
   fails.
4. **A rejected refresh fails every caller and logs out once.** All three waiting callers get the
   error, the next call says `loggedOut`, and the server isn't asked again.
5. **`logOut()` during a refresh stays logged out.** The server answers after logout; the waiting
   caller and the next one both get `loggedOut`. That's the shared-device privacy bug.

**The seam.** Both things the session depends on are passed in. The refresher is a *fake* auth
server: it records which refresh token it was sent and holds each refresh open until the test
answers, with a continuation rather than a sleep. And `now` is a function, so the tests pin the
time to one fixed "morning" instead of reading the real clock. Nothing waits on real time, so the
tests behave the same on every run — they're *deterministic*.

```swift
import Foundation
import Testing

/// A fake auth server: it records every refresh and holds it until the test answers.
@MainActor
final class ControlledRefresher: TokenRefreshing {
    private(set) var usedRefreshTokens: [String] = []
    private var pending: [CheckedContinuation<Tokens, Error>] = []
    private var waiters: [(count: Int, resume: CheckedContinuation<Void, Never>)] = []

    func refresh(using refreshToken: String) async throws -> Tokens {
        usedRefreshTokens.append(refreshToken)
        for waiter in waiters where usedRefreshTokens.count >= waiter.count { waiter.resume.resume() }
        waiters.removeAll { usedRefreshTokens.count >= $0.count }
        return try await withCheckedThrowingContinuation { pending.append($0) }
    }

    func waitForRefreshes(_ count: Int) async {
        if usedRefreshTokens.count >= count { return }
        await withCheckedContinuation { waiters.append((count, $0)) }
    }

    func succeed(with tokens: Tokens) {
        pending.forEach { $0.resume(returning: tokens) }
        pending.removeAll()
    }

    func reject(with error: Error) {
        pending.forEach { $0.resume(throwing: error) }
        pending.removeAll()
    }
}

struct RefreshRejected: Error, Equatable {}

let morning = Date(timeIntervalSince1970: 1_000_000)
let expired = Tokens(access: "a0", refresh: "r0", expiresAt: morning - 60)
let fresh = Tokens(access: "a1", refresh: "r1", expiresAt: morning + 3600)

@MainActor
struct SessionTests {

    @Test
    func concurrentCallersShareOneRefresh() async throws {
        // Given an expired token and three requests needing it at once
        let refresher = ControlledRefresher()
        let session = Session(tokens: expired, refresher: refresher, now: { morning })
        let callers = (0..<3).map { _ in Task { try await session.validAccessToken() } }
        await refresher.waitForRefreshes(1)
        for _ in 0..<200 { await Task.yield() }   // let the other callers reach the session

        // When the one refresh comes back
        refresher.succeed(with: fresh)

        // Then all three get the new token, and r0 was spent exactly once
        for caller in callers {
            #expect(try await caller.value == "a1")
        }
        #expect(refresher.usedRefreshTokens == ["r0"])
    }

    @Test
    func freshTokenNeedsNoRefresh() async throws {
        // Given a token valid for another hour
        let refresher = ControlledRefresher()
        let session = Session(tokens: fresh, refresher: refresher, now: { morning })

        // When a request asks for it
        let token = try await session.validAccessToken()

        // Then it comes straight from the session
        #expect(token == "a1")
        #expect(refresher.usedRefreshTokens == [])
    }

    @Test
    func tokenInsideTheLeewayIsRefreshedEarly() async throws {
        // Given a token with 20 seconds left (less than the 30-second leeway)
        let refresher = ControlledRefresher()
        let almostExpired = Tokens(access: "a0", refresh: "r0", expiresAt: morning + 20)
        let session = Session(tokens: almostExpired, refresher: refresher, now: { morning })

        // When a request asks for a token
        let caller = Task { try await session.validAccessToken() }
        await refresher.waitForRefreshes(1)
        refresher.succeed(with: fresh)

        // Then it is refreshed before it can die on the way to the server
        #expect(try await caller.value == "a1")
        #expect(refresher.usedRefreshTokens == ["r0"])
    }

    @Test
    func rejectedRefreshFailsEveryCallerAndLogsOut() async throws {
        // Given three requests waiting on one refresh
        let refresher = ControlledRefresher()
        let session = Session(tokens: expired, refresher: refresher, now: { morning })
        let callers = (0..<3).map { _ in Task { try await session.validAccessToken() } }
        await refresher.waitForRefreshes(1)
        for _ in 0..<200 { await Task.yield() }

        // When the server rejects the refresh token
        refresher.reject(with: RefreshRejected())

        // Then every caller gets that error
        for caller in callers {
            await #expect(throws: RefreshRejected.self) { try await caller.value }
        }
        // And the session is logged out, without trying again
        await #expect(throws: SessionError.loggedOut) { try await session.validAccessToken() }
        #expect(refresher.usedRefreshTokens == ["r0"])
    }

    @Test
    func logOutDuringARefreshStaysLoggedOut() async throws {
        // Given a refresh in flight
        let refresher = ControlledRefresher()
        let session = Session(tokens: expired, refresher: refresher, now: { morning })
        let caller = Task { try await session.validAccessToken() }
        await refresher.waitForRefreshes(1)

        // When the user logs out, and the server answers anyway
        await session.logOut()
        refresher.succeed(with: fresh)

        // Then the waiting request is told it's logged out, and so is the next one
        await #expect(throws: SessionError.loggedOut) { try await caller.value }
        await #expect(throws: SessionError.loggedOut) { try await session.validAccessToken() }
    }
}
```

A test can't see inside the actor, so in the two three-caller tests it can't know for certain that
every caller has joined before the refresh returns. It gives them a fixed number of turns first.
That's enough: with the join removed (each caller starting its own refresh), the first test fails.

Ran with Swift 6.4: 5 tests, all passed.
:::

::: What I'd ask next
- *"A request with a 'valid' token comes back 401. Now what?"* — The server says it's dead. Add
  `invalidate(token:)`: if the current access token is the one that failed, drop it so the next
  call refreshes, then retry that request once. Comparing the token avoids throwing away a newer
  one another caller just got.
- *"Should a network error log the user out?"* — No. Throw it and keep the tokens; only a
  rejection of the refresh token itself (`invalid_grant`) means log in again. The fix clears on
  any error to stay short — in production, split the error types.
- *"Why is actor reentrancy a feature, not a bug?"* — A non-reentrant actor that awaits another
  actor that awaits the first deadlocks. SE-0306 chose reentrancy and the rule "don't trust state
  across an `await`."
- *"How do you test this deterministically?"* — A fake refresher that counts calls and suspends
  until the test releases it (a continuation, not a sleep), fire N concurrent callers with a task
  group, release, assert one call and N identical tokens.
- *"Where would the logout screen be triggered?"* — Not in the session. It throws `loggedOut`;
  one observer (an `AsyncStream` of session events, or the app's root coordinator) reacts once.
:::
