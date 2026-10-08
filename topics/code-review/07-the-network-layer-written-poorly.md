---
title: 07 · The network layer written poorly
summary: A completion-handler API client that crashes, hangs and updates UI off main — debug it, then rebuild it with async/await and retries.
minutes: 30
group: Review, then extend
sources:
- Blind · Uber iOS — "You get an app with the network request layer written poorly… walk them through how you'd debug and improve" | https://www.teamblind.com/post/uber-ios-interview-jzihjgct
- LeetCode Discuss · Uber SE2 iOS — "They gave an existing iOS Project… Code review & fix errors" | https://leetcode.com/discuss/interview-experience/738598/
- Apple · URL init(string:) — from iOS 17 it percent-encodes invalid characters instead of returning nil | https://developer.apple.com/documentation/foundation/url/init(string:)
- Apple · URLRequest timeoutInterval — the default is 60 seconds | https://developer.apple.com/documentation/foundation/urlrequest/timeoutinterval
- SE-0461 · Run nonisolated async functions on the caller's actor by default — and @concurrent | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0461-async-function-isolation.md
- SE-0413 · Typed throws | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0413-typed-throws.md
---

*Shape: review, then extend · Reported: Uber — "an app with the network request layer written
poorly… walk them through how you'd debug and improve"; Uber SE2 — an existing project to code-review
and fix · UIKit snippet typechecked against the iOS SDK (iOS 18 target): clean in Swift 5 mode, one error and two
warnings in Swift 6 mode. The fix is Foundation-only, compiled with Swift 6.4 in Swift 6 mode with
zero warnings, and run against a fake transport returning 200, 500 and garbage*

> "This is the networking layer of an app we inherited. Users report three things: the profile
> spinner sometimes spins forever, the app crashes on search when the backend has an outage, and
> sometimes the name appears late or the screen 'flickers'. Walk me through how you'd debug it.
> Then: we want retries for transient failures. Show me the version you'd ship."

```swift
import UIKit

struct User: Codable {
    let id: Int
    let name: String
    let avatarURL: URL
}

class APIClient {
    static let shared = APIClient()

    let baseURL = "https://api.example.com"

    func fetchUser(id: Int, completion: @escaping (User?, Error?) -> Void) {
        let url = URL(string: baseURL + "/users/\(id)")!
        URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                print("Request failed: \(error)")
                return
            }
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let user = try? decoder.decode(User.self, from: data!)
            completion(user, nil)
        }.resume()
    }

    func searchUsers(matching query: String, completion: @escaping ([User]) -> Void) {
        let url = URL(string: baseURL + "/users?q=" + query)!
        URLSession.shared.dataTask(with: url) { data, _, _ in
            guard let data = data else { return }
            let users = try! JSONDecoder().decode([User].self, from: data)
            completion(users)
        }.resume()
    }
}

class ProfileViewController: UIViewController {
    @IBOutlet var nameLabel: UILabel!
    @IBOutlet var spinner: UIActivityIndicatorView!
    var userID = 0

    override func viewDidLoad() {
        super.viewDidLoad()
        spinner.startAnimating()
        APIClient.shared.fetchUser(id: userID) { user, error in
            self.spinner.stopAnimating()
            if let user = user {
                self.nameLabel.text = user.name
            } else {
                self.nameLabel.text = "Something went wrong"
            }
        }
    }
}
```

::: A hint, if you're stuck
- Take each of the three user reports and trace one request through the code by hand. Which line
  runs for a timeout? For a 500 with an HTML error page? For a 200 with a valid body?
- `dataTask` only reports a *transport* failure in `error`. What does it hand you for a 500?
- Which thread does `dataTask`'s completion handler run on, and who touches a `UILabel` there?
- Ask what you would need to write a unit test for "a 500 shows an error". Can you, today?
:::

::: The key — what I expect a senior to find
1. **`try!` crashes search during an outage (report 2).** `dataTask` treats any HTTP response as
   success: a 500 arrives with `error == nil` and an HTML body. `try!` on decoding HTML traps. Use
   `try` and surface a decoding error instead.
2. **The spinner spins forever (report 1).** `if let error { print; return }` returns without
   calling `completion`, and so does `guard let data else { return }`. Every path through a
   completion-handler API must call the handler exactly once.
3. **UI updated off the main thread (report 3).** `URLSession`'s handlers run on its delegate
   queue — a background queue for `.shared`. The view controller sets `nameLabel.text` and stops the
   spinner from there. UIKit isn't thread-safe: late updates, flicker, or a Main Thread Checker hit.
4. **No HTTP status check.** A 404, 401 or 500 goes straight into the decoder. `try?` then turns it
   into `nil`, and the caller gets `(nil, nil)` — "no user and no error", a state that should be
   impossible. The status code is the first thing to read.
5. **Errors are thrown away.** `try?` and `print` lose the reason. The UI can't tell "offline" from
   "server down" from "your session expired", and the logs say nothing useful.
6. **The query isn't encoded.** With the iOS 17 SDK, `URL(string:)` percent-encodes invalid
   characters instead of returning `nil`, so a space no longer crashes. But `&` and `=` are valid,
   so searching `tom&admin=true` sends a second query parameter. Build URLs with `URLComponents` or
   `append(queryItems:)`. The `!` still crashes if `baseURL` ever comes from bad config.
7. **No cancellation.** Leave the screen and the request still runs and writes to a screen that's
   gone. Search typed quickly can show an older query's results last.
8. **No timeout or retry policy.** The default request timeout is 60 seconds of spinner. A single
   dropped packet or a 503 during a deploy fails the screen; nothing retries.
9. **`(User?, Error?)` instead of a result type.** Four combinations, two of them nonsense. Use
   `Result<User, APIError>`, or `async throws`.
10. **Singleton and hard-coded `URLSession.shared`.** Nothing can be faked, so none of the above can
    be tested. In Swift 6 mode `static let shared` on a non-`Sendable` class is a compile error —
    verified.
11. **`JSONDecoder` built on every call.** Cheap-ish, but the two methods already disagree:
    one converts snake case, the other doesn't. Configure one decoder once.
12. **Duplicate request code.** Every new endpoint copies the bugs. One generic `get` fixes them
    all in one place.
13. **Strong `self` in the completion.** The controller lives until the request ends. Minor here,
    but it's how a dismissed screen keeps doing work.

How I'd *debug* it before fixing anything: turn on the Main Thread Checker and reproduce report 3;
point the app at a proxy (Charles or Proxyman) and map the endpoint to a 500 with an HTML body to
reproduce report 2; use the Network Link Conditioner on "100% Loss" to reproduce report 1. Each
report becomes a failing test once the transport can be faked.
:::

::: The idea behind it
A network call has more outcomes than "worked" and "didn't". The request can fail to leave the
phone (no signal). It can reach a server that answers with an error *status* — a three-digit code
where 2xx means success and 5xx means the server broke. Or it can answer 200 with a body you can't
read. `URLSession` only calls the first one an error. The other two arrive looking like success, and
your code has to check.

A *completion handler* is a function you pass in, to be called later with the result. Its contract
is unwritten: call it once, on every path, on a known thread. Nothing enforces it, so it's easy to
forget a path — and then the caller waits forever.

`async/await` turns that unwritten contract into a compiled one. An `async throws` function must
either return a value or throw on every path; the compiler checks it. Cancellation flows down
automatically. And when the caller is marked `@MainActor` — "always runs on the main thread" — the
result lands on main without anyone remembering to hop.

Think of a parcel delivery. The courier reporting "delivered" isn't the same as you getting the
right thing in one piece. Someone still has to open the box.
:::

::: The version I'd ship
```swift
import Foundation

struct User: Codable, Sendable, Equatable {
    let id: Int
    let name: String
}

/// The one thing that touches the network. URLSession conforms; tests use a fake.
protocol HTTPTransport: Sendable {
    func data(for request: URLRequest) async throws -> (Data, URLResponse)
}

extension URLSession: HTTPTransport {
    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        try await data(for: request, delegate: nil)
    }
}

enum APIError: Error, Equatable {
    case invalidURL
    case offline
    case transport(URLError.Code)
    case badStatus(Int)
    case decoding(String)
    case cancelled
}

struct RetryPolicy: Sendable {
    var maxAttempts = 3
    var baseDelay: Duration = .milliseconds(300)

    func isTransient(_ error: APIError) -> Bool {
        switch error {
        case .badStatus(let code): code == 408 || code == 429 || (500...599).contains(code)
        case .transport(let code): [.timedOut, .networkConnectionLost].contains(code)
        default: false
        }
    }
}

final class APIClient: Sendable {
    private let baseURL: URL
    private let transport: HTTPTransport
    private let retry: RetryPolicy
    private let decoder: JSONDecoder   // configured once; immutable after init

    init(baseURL: URL, transport: HTTPTransport, retry: RetryPolicy = RetryPolicy()) {
        self.baseURL = baseURL
        self.transport = transport
        self.retry = retry
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder = decoder
    }

    func user(id: Int) async throws(APIError) -> User {
        try await get(path: "users/\(id)", query: [])
    }

    func searchUsers(matching query: String) async throws(APIError) -> [User] {
        try await get(path: "users", query: [URLQueryItem(name: "q", value: query)])
    }

    // @concurrent: always runs off the caller's actor, so decoding never lands on main.
    @concurrent
    private func get<T: Decodable & Sendable>(path: String,
                                              query: [URLQueryItem]) async throws(APIError) -> T {
        var url = baseURL.appending(path: path)
        if !query.isEmpty { url.append(queryItems: query) }   // encodes '&', spaces, emoji
        var request = URLRequest(url: url, timeoutInterval: 15)
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        var attempt = 1
        while true {
            do throws(APIError) {
                let data = try await send(request)
                do { return try decoder.decode(T.self, from: data) }
                catch { throw APIError.decoding(String(describing: error)) }
            } catch {
                guard attempt < retry.maxAttempts, retry.isTransient(error) else { throw error }
                // Exponential backoff with jitter: 300 ms, 600 ms, ... ± 50 %.
                let delay = retry.baseDelay * (1 << (attempt - 1)) * Double.random(in: 0.5...1.5)
                do { try await Task.sleep(for: delay) } catch { throw .cancelled }
                attempt += 1
            }
        }
    }

    private func send(_ request: URLRequest) async throws(APIError) -> Data {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await transport.data(for: request)
        } catch is CancellationError {
            throw .cancelled
        } catch let error as URLError {
            switch error.code {
            case .cancelled: throw .cancelled
            case .notConnectedToInternet: throw .offline
            default: throw .transport(error.code)
            }
        } catch {
            throw .transport(.unknown)
        }
        guard let http = response as? HTTPURLResponse else { throw .transport(.badServerResponse) }
        guard (200..<300).contains(http.statusCode) else { throw .badStatus(http.statusCode) }
        return data
    }
}

// The caller: a main-actor view model. No DispatchQueue.main.async anywhere.
@MainActor
final class ProfileViewModel {
    enum State: Equatable { case loading, loaded(String), failed(String) }

    private(set) var state: State = .loading
    private let api: APIClient
    private var loadTask: Task<Void, Never>?

    init(api: APIClient) { self.api = api }

    @discardableResult
    func load(userID: Int) -> Task<Void, Never> {
        loadTask?.cancel()
        state = .loading
        let task = Task {
            do throws(APIError) {
                let user = try await api.user(id: userID)
                state = .loaded(user.name)
            } catch .cancelled {
                return
            } catch {
                state = .failed(Self.message(for: error))
            }
        }
        loadTask = task
        return task   // handed back so a caller (or a test) can await it
    }

    func cancel() { loadTask?.cancel() }

    private static func message(for error: APIError) -> String {
        switch error {
        case .offline: "You're offline."
        case .badStatus, .transport: "The server didn't respond. Try again."
        default: "Something went wrong."
        }
    }
}
```

What the run against a fake transport printed (retry delay shortened to 1 ms for the test; the long
decoding message is cut short here):

```text
200 json       -> user: Ada | attempts: 1
500 html       -> error: badStatus(500) | attempts: 3
200 garbage    -> error: decoding("DecodingError.dataCorrupted: Data was …") | attempts: 1
503 then 200   -> user: Ada | attempts: 2
404            -> error: badStatus(404) | attempts: 1
offline        -> error: offline | attempts: 1
search URL    -> https://api.example.com/users?q=tom%20%26%20admin%3Dtrue | timeout: 15.0
view model    -> failed("The server didn\'t respond. Try again.")
```

The 500 is retried and then reported, never decoded. The garbage 200 becomes a decoding error, not
a crash. A 404 isn't retried — it won't change. The `&` in the search is encoded, and the timeout
is 15 seconds, not 60.

Why each piece:

- **`HTTPTransport` protocol** — the seam. `URLSession` conforms in production; the fake above
  returns any status and body. That's what made every user report testable. The extension method
  is needed because a default argument (`delegate: nil`) doesn't satisfy a protocol requirement.
- **`async throws(APIError)`** — every path must return or throw, so "spinner forever" can't
  compile. *Typed throws* (Swift 6) means the caller's `catch` sees an `APIError`, not `any Error`,
  and `switch`es over it with no casting.
- **Status check before decoding** — the line the original was missing. 2xx goes to the decoder;
  anything else becomes `.badStatus` with the code kept for logs and UI.
- **Retry only what is transient, with backoff and jitter** — 408, 429, 5xx, a timeout or a dropped
  connection may work a moment later; a 404 or a decoding error won't. *Backoff* means each wait
  doubles. *Jitter* means a random spread, so a million phones don't retry at the same instant and
  knock the recovering server over again. Only retry idempotent requests — a `GET` is safe to send
  twice; a "send money" `POST` is not without an idempotency key.
- **`@concurrent` on `get`** — since Swift 6.2 a project can turn on
  `NonisolatedNonsendingByDefault` (Xcode 26's "Approachable Concurrency" does), and then a plain
  `async` method runs on its *caller's* actor — decoding a big response on main. `@concurrent` says
  "always run on the background pool", whatever the build setting.
- **One decoder, built in `init`** — one configuration for every endpoint, and immutable, so sharing
  it across threads is safe.
- **`@MainActor` view model with a stored `Task`** — UI state is on main by construction, a new load
  cancels the old one, and a cancelled request writes nothing. `load` also returns the task, so a
  test can `await` it instead of guessing how long to wait.
:::

::: Now write the tests
> "Good. Now write me the tests you'd want before this merges — one for each of the three user
> reports, and the retry."

**What I'd test, and why**

1. **A 500 is retried, then reported as `badStatus(500)`** — this is the search crash. The test
   proves an HTML error page never reaches the decoder, and that the retry stops after three tries.
2. **A 404 is not retried** — retrying something that won't change just makes the user wait.
3. **A garbage 200 becomes a decoding error** — the other half of the crash: a bad body throws,
   it doesn't trap.
4. **503, then 200, succeeds on the second attempt** — the retry actually rescues a blip.
5. **The search query is encoded** — `&` and `=` must not turn into extra parameters. The same
   test checks the 15-second timeout.
6. **The view model ends in `.failed` with the right message** — the spinner-forever report. Every
   path has to land in a final state.

I wouldn't test `URLSession` itself or the real backoff timing — the first is Apple's code, and the
second is just numbers in `RetryPolicy`.

**The seam.** A *seam* is a place where the test can swap a real part for a fake. Here it is
`HTTPTransport`: the *fake* below replays canned answers (any status, any body) and records each
request, so nothing touches the network. The backoff really sleeps, so the tests pass a 1 ms
`baseDelay` through `RetryPolicy`. One gap I closed: `load(userID:)` started its `Task` and kept it
private, so a test could only guess when it had finished. It now returns the task (two lines,
shown in the fix above), and the test simply awaits it — *deterministic*, meaning it gives the same
result on every run, with no timing involved.

```swift
import Testing
import Foundation

/// A fake transport: plays back canned replies in order (the last one repeats)
/// and records every request it was sent.
actor FakeTransport: HTTPTransport {
    enum Reply: Sendable {
        case status(Int, String)
        case failure(URLError.Code)
    }

    private var replies: [Reply]
    private(set) var requests: [URLRequest] = []

    init(_ replies: Reply...) { self.replies = replies }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        requests.append(request)
        let reply = replies.count > 1 ? replies.removeFirst() : replies[0]
        switch reply {
        case .failure(let code):
            throw URLError(code)
        case .status(let code, let body):
            let response = HTTPURLResponse(url: request.url!, statusCode: code,
                                           httpVersion: nil, headerFields: nil)!
            return (Data(body.utf8), response)
        }
    }
}

let ada = #"{"id": 1, "name": "Ada"}"#

/// A 1 ms base delay keeps the real backoff, just fast.
func makeClient(_ transport: FakeTransport, maxAttempts: Int = 3) -> APIClient {
    APIClient(baseURL: URL(string: "https://api.example.com")!,
              transport: transport,
              retry: RetryPolicy(maxAttempts: maxAttempts, baseDelay: .milliseconds(1)))
}

struct APIClientTests {
    @Test func serverErrorIsRetriedThenReportedAsBadStatus() async {
        // Given a server that always answers 500 with an HTML page
        let transport = FakeTransport(.status(500, "<html>Oops</html>"))
        let client = makeClient(transport)

        // When / Then: it never reaches the decoder, and it tried three times
        await #expect(throws: APIError.badStatus(500)) { try await client.user(id: 1) }
        #expect(await transport.requests.count == 3)
    }

    @Test func notFoundIsNotRetried() async {
        let transport = FakeTransport(.status(404, ""))
        let client = makeClient(transport)

        await #expect(throws: APIError.badStatus(404)) { try await client.user(id: 1) }
        #expect(await transport.requests.count == 1)
    }

    @Test func garbageBodyBecomesADecodingErrorNotACrash() async {
        let transport = FakeTransport(.status(200, "not json"))
        let client = makeClient(transport)

        let error = await #expect(throws: APIError.self) { try await client.user(id: 1) }

        guard case .decoding = error else {
            Issue.record("Expected a decoding error, got \(String(describing: error))")
            return
        }
        #expect(await transport.requests.count == 1)
    }

    @Test func serviceUnavailableThenOKSucceedsOnTheSecondAttempt() async throws {
        let transport = FakeTransport(.status(503, ""), .status(200, ada))
        let client = makeClient(transport)

        let user = try await client.user(id: 1)

        #expect(user == User(id: 1, name: "Ada"))
        #expect(await transport.requests.count == 2)
    }

    @Test func searchQueryIsEncoded() async throws {
        let transport = FakeTransport(.status(200, "[]"))
        let client = makeClient(transport)

        _ = try await client.searchUsers(matching: "tom & admin=true")

        let request = try #require(await transport.requests.first)
        #expect(request.url?.absoluteString
                == "https://api.example.com/users?q=tom%20%26%20admin%3Dtrue")
        #expect(request.timeoutInterval == 15)
    }
}

@MainActor
struct ProfileViewModelTests {
    @Test func serverOutageEndsInFailedWithAFriendlyMessage() async {
        let transport = FakeTransport(.status(500, "<html>Oops</html>"))
        let viewModel = ProfileViewModel(api: makeClient(transport, maxAttempts: 1))

        await viewModel.load(userID: 1).value

        #expect(viewModel.state == .failed("The server didn't respond. Try again."))
    }

    @Test func successEndsInLoadedWithTheName() async {
        let transport = FakeTransport(.status(200, ada))
        let viewModel = ProfileViewModel(api: makeClient(transport))

        await viewModel.load(userID: 1).value

        #expect(viewModel.state == .loaded("Ada"))
    }
}
```

Ran with Swift 6.4: 7 tests, all passed.
:::

::: What I'd ask next
- *"How do you add an auth token, and refresh it when it expires?"* — An `actor TokenStore` the client
  asks for a token before each request. On a 401, refresh once and retry; the actor makes sure ten
  concurrent 401s trigger one refresh, not ten.
- *"Why not retry inside `HTTPTransport`?"* — The transport doesn't know which requests are idempotent
  or which statuses are transient for this API. Keep it dumb; put policy in the client.
- *"How would you test the backoff without waiting?"* — Inject the sleep (a `Clock`, or a small
  `sleep(for:)` closure) and assert the requested delays, as the harness did with a 1 ms base.
- *"The product wants offline support."* — Cache the last good response on disk keyed by URL, show it
  with a "last updated" label, and refresh in the background. Don't fake it with long timeouts.
- *"Would you still keep a completion-handler API?"* — Only as a thin wrapper for old callers:
  a `@MainActor` method that starts a `Task`, awaits `user(id:)` in a `do`/`catch` and calls
  `completion(.success(user))` or `completion(.failure(error))` — on main, exactly once. New code
  uses `async`.
:::
