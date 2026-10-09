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
concurrency issues and race conditions; TikTok — threads, GCD and race conditions · Verified: part 1
is rejected in Swift 6 mode, part 2 compiles; the fix and its tests ran with Swift 6.4*

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
The reported bug comes first. Against a fake auth server that rotates refresh tokens, part 1 with
two requests refreshed twice and logged the user out; the actor with three requests refreshed
three times and logged out twice.

1. **Check-then-act race: two refreshes (the reported bug).** Both requests check "is the token
   expired?", both see yes, both refresh. Nothing records that a refresh is already running.
2. **The second refresh destroys the session.** With rotation, the first refresh spends `r0`. The
   second sends the same `r0` and is rejected — and real auth servers often treat that reuse as
   theft and revoke the whole session. The user did nothing wrong.
3. **The actor doesn't fix it (part 2).** An actor runs one *piece* of code at a time, but it lets
   go at every `await`. While caller 1 waits for the network, callers 2 and 3 enter, see the same
   expired token, and start their own refreshes. The data race is gone; the logic race isn't.
   Fix: store the in-flight refresh `Task` and make later callers wait on it.
4. **`refresher` is implicitly unwrapped.** If nobody sets it before the first request, the app
   crashes. Pass it in through `init`.
5. **Data race on `tokens`.** It's read on whatever thread calls `withValidToken` and written on
   whatever queue the refresher calls back on. Unsynchronised reads and writes of a struct holding
   strings can tear or crash. Swift 6 mode refuses part 1 (*static property 'shared' is not
   concurrency-safe*); Swift 5 mode compiles it with no warning.
6. **Callbacks on the wrong thread.** `completion` and `onLogout` run on the refresher's queue. The
   caller will update UI from them, and `onLogout` will present a login screen — off the main
   thread.
7. **Logout during a refresh brings the user back.** Nothing stops a refresh that finishes after
   logout from writing new tokens. On a shared device that's a privacy bug.
8. **Logout fires once per failed request.** Two failures, two `onLogout` calls — two login screens,
   two analytics events. Logout must happen once.
9. **Any failure logs out.** Offline, a timeout or a 500 also clears the tokens. Only a rejected
   refresh token means "log in again"; a network error means "try later".
10. **No tokens still calls the server.** `tokens?.refresh ?? ""` sends an empty refresh token, a
    request that can only fail. With no tokens, fail at once with "logged out".
11. **No expiry margin.** `expiresAt > Date()` passes a token with one second left; it expires on
    the way to the server and the request gets a 401. Refresh a little early.
12. **No timeout.** If the refresher never calls back, every request waiting for a token hangs
    forever. Put a deadline on the refresh.
13. **Untestable and too open.** A singleton, `Date()` read directly, and `tokens` and `refresher`
    writable by anyone: no test can control time or swap the server, and any code can overwrite
    the session.
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
I fix part 2, because that's where the candidate ended up. Same actor, same names; the changes
are the in-flight task, the empty-token guard and the margin.

```swift
struct Tokens: Sendable {                                   // a Task can only return Sendable values
    let access: String
    let refresh: String
    let expiresAt: Date
}

enum SessionError: Error {
    case loggedOut
}

actor NaiveSession {
    private var tokens: Tokens?
    private var refreshTask: Task<Tokens, any Error>?          // key 1, 3: "a refresh is running"
    private let refresher: any TokenRefreshing

    init(tokens: Tokens?, refresher: any TokenRefreshing) {
        self.tokens = tokens
        self.refresher = refresher
    }

    func validAccessToken() async throws -> String {
        if let refreshTask {                                    // key 3: join the one in flight
            return try await refreshTask.value.access
        }
        guard let tokens else { throw SessionError.loggedOut } // key 10: no "" refresh token
        if tokens.expiresAt.timeIntervalSinceNow > 30 {         // key 11: refresh 30 s early
            return tokens.access
        }
        let task = Task { try await refresher.refresh(using: tokens.refresh) }
        refreshTask = task                                      // key 1: stored before any await
        defer { refreshTask = nil }                             // only the caller that started it
        do {
            let newTokens = try await task.value
            self.tokens = newTokens
            return newTokens.access
        } catch {
            self.tokens = nil                                   // key 8: one logout, not one per caller
            throw error
        }
    }
}
```

**Said out loud, not coded:** an injected clock instead of the real one; `logOut()` that cancels
the task, plus a check after the `await` so a late refresh can't log the user back in (key 7);
separate "refresh token rejected" from "network down" (key 9); a timeout (key 12); one logout event
for the app to observe; retry once on a 401.

Why each piece:

- **The task is stored before the first `await`.** Between creating it and storing it there is no
  suspension point, so no other caller can slip in and start a second refresh.
- **Only the caller that started the refresh writes the result and clears the task.** Callers that
  join just return the task's value. A caller that arrives after the network answered but before
  the starter resumes still finds the task and gets its finished result at once. Writing the tokens
  and clearing the task happen with no `await` between them, so nobody can see the task gone but the
  old tokens still there.
- **Clearing on failure** means a failed refresh isn't cached, so the next call says "logged out"
  instead of re-throwing an old error forever.

I checked the reentrancy claim beyond the tests: 500 rounds of 40 callers arriving before, during
and after the refresh, against a server that rejects reused tokens — one refresh per round, every
caller got the new token.
:::

::: Now write the tests
> "Good. This one logged people out in production. Write me the tests that make sure it never
> does again."

**What I'd test, and why**

1. **Concurrent callers share one refresh.** Three requests hit an expired token at once; the
   server sees `r0` exactly once, all three get `a1`, and a call after it finished needs no new
   refresh. This is the morning-logout bug, so it goes first.
2. **A fresh token needs no refresh.** The happy path must not touch the server.
3. **The margin.** A token with 20 seconds left is refreshed early. Delete the margin and this fails.
4. **A rejected refresh fails every caller and logs out.** All three get the error, the next call
   says `loggedOut`, and the server isn't asked again.

**The seam.** The refresher is already passed in, so the test passes a *fake* auth server. It
records the refresh tokens it is sent and holds each refresh open until the test answers — with a
continuation, not a sleep. The margin test uses the real clock: 20 seconds against a 30-second
margin can't flip during a test run.

```swift
import Foundation
import Testing

/// A fake auth server: records each refresh token it is sent, and holds every refresh open
/// until the test answers.
@MainActor
final class FakeRefresher: TokenRefreshing {
    private(set) var usedRefreshTokens: [String] = []
    private var pending: [CheckedContinuation<Tokens, Error>] = []

    func refresh(using refreshToken: String) async throws -> Tokens {
        usedRefreshTokens.append(refreshToken)
        return try await withCheckedThrowingContinuation { pending.append($0) }
    }

    func answer(_ result: Result<Tokens, Error>) {
        pending.forEach { $0.resume(with: result) }
        pending.removeAll()
    }
}

/// Gives other tasks a turn, a fixed number of times, until the condition holds. No clocks.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () async -> Bool) async {
    for _ in 0..<maxYields {
        if await condition() { return }
        await Task.yield()
    }
}

struct RefreshRejected: Error {}

let expired = Tokens(access: "a0", refresh: "r0", expiresAt: Date() - 60)
let fresh = Tokens(access: "a1", refresh: "r1", expiresAt: Date() + 3600)

@MainActor
struct SessionTests {

    @Test
    func concurrentCallersShareOneRefresh() async throws {
        // Given an expired token, and three requests needing it at once
        let refresher = FakeRefresher()
        let session = NaiveSession(tokens: expired, refresher: refresher)
        let callers = (0..<3).map { _ in Task { try await session.validAccessToken() } }
        await waitUntil { !refresher.usedRefreshTokens.isEmpty }
        for _ in 0..<1_000 { await Task.yield() }   // give the other callers turns to reach the session

        // When the one refresh comes back
        refresher.answer(.success(fresh))

        // Then all three get the new token, r0 was spent once, and a later call needs no refresh
        for caller in callers {
            #expect(try await caller.value == "a1")
        }
        #expect(try await session.validAccessToken() == "a1")
        #expect(refresher.usedRefreshTokens == ["r0"])
    }

    @Test
    func freshTokenNeedsNoRefresh() async throws {
        let refresher = FakeRefresher()
        let session = NaiveSession(tokens: fresh, refresher: refresher)

        #expect(try await session.validAccessToken() == "a1")
        #expect(refresher.usedRefreshTokens == [])
    }

    @Test
    func tokenInsideTheMarginIsRefreshedEarly() async throws {
        // Given a token with 20 seconds left, inside the 30-second margin
        let refresher = FakeRefresher()
        let almostExpired = Tokens(access: "a0", refresh: "r0", expiresAt: Date() + 20)
        let session = NaiveSession(tokens: almostExpired, refresher: refresher)

        // When a request asks for it
        let caller = Task { try await session.validAccessToken() }
        await waitUntil { !refresher.usedRefreshTokens.isEmpty }
        refresher.answer(.success(fresh))

        // Then it was refreshed before it could die on the way to the server
        #expect(try await caller.value == "a1")
        #expect(refresher.usedRefreshTokens == ["r0"])
    }

    @Test
    func rejectedRefreshFailsEveryCallerAndLogsOut() async throws {
        // Given three requests waiting on one refresh
        let refresher = FakeRefresher()
        let session = NaiveSession(tokens: expired, refresher: refresher)
        let callers = (0..<3).map { _ in Task { try await session.validAccessToken() } }
        await waitUntil { !refresher.usedRefreshTokens.isEmpty }
        for _ in 0..<1_000 { await Task.yield() }

        // When the server rejects the refresh token
        refresher.answer(.failure(RefreshRejected()))

        // Then every caller gets that error, and the next call is told it's logged out
        for caller in callers {
            await #expect(throws: RefreshRejected.self) { try await caller.value }
        }
        await #expect(throws: SessionError.loggedOut) { try await session.validAccessToken() }
        #expect(refresher.usedRefreshTokens == ["r0"])
    }
}
```

A test can't see inside the actor, so in the two three-caller tests it can't know for certain that
every caller has joined before the refresh returns. It gives them a fixed number of turns first.
That's enough: with the join removed, both tests fail.

Ran with Swift 6.4: 4 tests, all passed.
:::

::: What I'd ask next
- *"How would you add logout?"* — `logOut()` cancels the task, clears it and the tokens. Then every
  caller must check after its `await` that the session wasn't logged out meanwhile, or a refresh that
  lands late writes tokens back. And a refresher that honours cancellation makes waiters throw
  `CancellationError`, so map that to `loggedOut`.
- *"A request with a 'valid' token comes back 401. Now what?"* — The server says it's dead. Add
  `invalidate(token:)`: if the current access token is the one that failed, drop it so the next
  call refreshes, then retry that request once. Comparing the token avoids throwing away a newer
  one another caller just got.
- *"Should a network error log the user out?"* — No. Throw it and keep the tokens; only a
  rejection of the refresh token itself (`invalid_grant`) means log in again.
- *"Why is actor reentrancy a feature, not a bug?"* — A non-reentrant actor that awaits another
  actor that awaits the first deadlocks. SE-0306 chose reentrancy and the rule "don't trust state
  across an `await`."
- *"How do you test this deterministically?"* — A fake refresher that counts calls and suspends
  until the test releases it (a continuation, not a sleep). Start N callers as separate tasks,
  release, assert one call and N identical tokens.
- *"Where would the logout screen be triggered?"* — Not in the session. It throws `loggedOut`;
  one observer (an `AsyncStream` of session events, or the app's root coordinator) reacts once.
:::
