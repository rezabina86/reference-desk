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
- Apple · JSONDecoder.KeyDecodingStrategy.convertFromSnakeCase — "avatar_url" becomes "avatarUrl" | https://developer.apple.com/documentation/foundation/jsondecoder/keydecodingstrategy/convertfromsnakecase
---

*Shape: review, then extend · Reported: Uber — "an app with the network request layer written
poorly… walk them through how you'd debug and improve"; Uber SE2 — an existing project to code-review
and fix · Verified: the snippet is clean in Swift 5 mode and has one error and two warnings in Swift 6
mode; the fix typechecks for iOS 18 and its client tests ran, Swift 6.4*

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
- The backend sends `avatar_url`. What key does `convertFromSnakeCase` turn that into?
- Which thread does `dataTask`'s completion handler run on, and who touches a `UILabel` there?
:::

::: How I'd debug it
Before fixing anything, I'd reproduce each report. Turn on the Main Thread Checker and open the
profile to catch report 3. Point the app at a proxy (Charles or Proxyman) and map `/users` to a 500
with an HTML body to reproduce report 2. Use the Network Link Conditioner on "100% Loss" to
reproduce report 1. Once the transport can be faked, each report becomes a failing test.
:::

::: The key — what I expect a senior to find
1. **`try!` crashes search during an outage (report 2).** `dataTask` treats any HTTP response as
   success: a 500 arrives with `error == nil` and an HTML body, and `try!` on decoding HTML traps.
   Use `try` and surface a decoding error.
2. **`avatarURL` never decodes from snake case.** `convertFromSnakeCase` turns `avatar_url` into
   `avatarUrl`, which doesn't match the property `avatarURL` — `keyNotFound`. So if the backend
   sends snake case, as the profile decoder assumes, the profile *always* fails, and search (which
   has no strategy at all) fails too — through `try!`, so it crashes on every result. Map the key
   with `CodingKeys` and use one decoder.
3. **`data!` is a second force unwrap.** It's only safe because `URLSession` happens to send data
   whenever `error` is nil. Unwrap it properly.
4. **UI updated off the main thread (report 3).** `URLSession.shared` calls its handler on a
   background queue, and the view controller sets `nameLabel.text` and stops the spinner from
   there. UIKit isn't thread-safe: late updates, flicker, a Main Thread Checker hit.
5. **The query isn't encoded.** Since the iOS 17 SDK, `URL(string:)` percent-encodes a space
   instead of returning `nil`, but `&` and `=` are valid, so searching `tom&admin=true` sends a
   second parameter. Build the URL with `append(queryItems:)`.
6. **`print` logs the full error in release builds.** The error includes the URL — a user id or a
   search for someone's name — in the device log. Drop it, or use `Logger` with private values.
7. **`var userID = 0`.** Forget to set it and the screen quietly loads user 0, someone else's
   profile. Make it optional and fail loudly in debug.
8. **Strong `self`, no cancellation.** The handler keeps the controller alive until the request
   ends, and nothing stops the request when the user leaves. Capture `[weak self]`.
9. **The spinner spins forever (report 1).** `if let error { print; return }` returns without
   calling `completion`, and so does `guard let data else { return }`. A completion handler must be
   called exactly once, on every path.
10. **No HTTP status check.** A 404, 401 or 500 goes straight into the decoder. Read the status
    code first.
11. **`(User?, Error?)` and lost errors.** `try?` turns any failure into `(nil, nil)` — "no user
    and no error", a state that should be impossible. The UI can't tell "offline" from "server
    down". Use `async throws` (or `Result`).
12. **No timeout or retry.** The default timeout is 60 seconds of spinner, and a single 503 during
    a deploy fails the screen. Set a shorter timeout and retry what is transient.
13. **Singleton and hard-coded `URLSession.shared`.** Nothing can be faked, so none of this can be
    tested. Without default main-actor isolation, `static let shared` on this non-`Sendable` class
    is also a compile error in Swift 6 mode (verified). Inject the transport; mark the class
    `final` and `Sendable`.
14. **A `JSONDecoder` built per call.** The two methods already disagree on key strategy. Build one
    decoder, once.
15. **Duplicate request code.** Every new endpoint copies the bugs. One generic `get` fixes them in
    one place.
16. **Style.** Neither class is `final`, and `baseURL` is an internal `String` built by `+`.
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
either return a value or throw on every path; the compiler checks it. And a `Task` started from a
view controller runs on the main actor — "always on the main thread" — so the result lands on main
without anyone remembering to hop.
:::

::: The fix
```swift
struct User: Codable, Equatable {
    let id: Int
    let name: String
    let avatarURL: URL
    enum CodingKeys: String, CodingKey { case id, name, avatarURL = "avatar_url" }   // key 2
}

enum APIError: Error, Equatable { case transport(URLError.Code), badStatus(Int), decoding }

final class APIClient: Sendable {                                          // keys 13, 16
    typealias Transport = @Sendable (URLRequest) async throws -> (Data, URLResponse)
    static let shared = APIClient()

    private let baseURL = URL(string: "https://api.example.com")!
    private let decoder = JSONDecoder()                                    // key 14
    private let transport: Transport
    private let retryDelay: Duration

    init(transport: @escaping Transport = { try await URLSession.shared.data(for: $0) },
         retryDelay: Duration = .seconds(1)) {
        self.transport = transport
        self.retryDelay = retryDelay
    }

    func fetchUser(id: Int) async throws -> User {                          // keys 9, 11
        try await get(baseURL.appending(path: "users/\(id)"))
    }

    func searchUsers(matching query: String) async throws -> [User] {       // key 5
        try await get(baseURL.appending(path: "users")
            .appending(queryItems: [URLQueryItem(name: "q", value: query)]))
    }

    private func get<T: Decodable>(_ url: URL, attempt: Int = 1) async throws -> T {   // key 15
        let request = URLRequest(url: url, timeoutInterval: 15)                       // key 12
        do {
            let data: Data, response: URLResponse
            do { (data, response) = try await transport(request) }
            catch let error as URLError { throw APIError.transport(error.code) }
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            guard (200..<300).contains(status) else { throw APIError.badStatus(status) }   // key 10
            do { return try decoder.decode(T.self, from: data) }
            catch { throw APIError.decoding }                                         // keys 1, 3
        } catch let error as APIError where attempt < 3 && error.isWorthRetrying {    // key 12
            try await Task.sleep(for: retryDelay * attempt)                           // 1 s, then 2 s
            return try await get(url, attempt: attempt + 1)
        }
    }
}

extension APIError {
    var isWorthRetrying: Bool {
        switch self {
        case .badStatus(let code): code >= 500
        case .transport(let code): code == .timedOut || code == .networkConnectionLost
        case .decoding: false
        }
    }
}

class ProfileViewController: UIViewController {
    @IBOutlet var nameLabel: UILabel!
    @IBOutlet var spinner: UIActivityIndicatorView!
    var userID: Int?                                                        // key 7

    override func viewDidLoad() {
        super.viewDidLoad()
        guard let userID else { return assertionFailure("Set userID before showing the screen") }
        spinner.startAnimating()
        Task { [weak self] in                                               // keys 4, 8
            do {
                let user = try await APIClient.shared.fetchUser(id: userID)
                self?.nameLabel.text = user.name
            } catch {
                self?.nameLabel.text = "Something went wrong"               // key 6: no print
            }
            self?.spinner.stopAnimating()                                   // key 9
        }
    }
}
```

**Said out loud, not coded:** jitter on the backoff, so a million phones don't retry at the same
instant; retry only idempotent requests (a `GET`, not a "send money" `POST` without an idempotency
key); cancel the task in the controller when the screen goes away; typed throws and a view model
with a state enum; `@concurrent` on `get` if the project runs async functions on the caller's actor
by default, so decoding stays off main.

Why each piece:

- **The transport closure with a default is the one seam.** Production uses `URLSession.shared`;
  tests pass a fake that returns any status and body.
- **Status check before decoding.** The line the original was missing: 2xx goes to the decoder,
  anything else becomes `.badStatus` with the code kept.
- **Retry only what is transient.** A 5xx, a timeout or a dropped connection may work a moment
  later; a 404 or a bad body won't. The wait doubles each time (1 s, then 2 s).
- **The controller keeps its outlets and its shape.** `Task` inherits the main actor from
  `viewDidLoad`, so the labels are set on main with no `DispatchQueue.main.async`.
:::

::: Now write the tests
> "Good. Now write me the tests you'd want before this merges — the crash, the retry, and the
> search."

**What I'd test, and why**

1. **The profile decodes `avatar_url`.** The bug that made every profile fail, pinned first.
2. **A 500 is retried, then reported as `badStatus(500)`.** This is the search crash: an HTML error
   page never reaches the decoder, and the retry stops after three tries.
3. **A 404 is not retried.** Retrying something that won't change just makes the user wait.
4. **503, then 200, succeeds on the second attempt.** The retry actually rescues a blip.
5. **The search query is encoded.** `&` and `=` must not turn into extra parameters.

I wouldn't test `URLSession` itself, or the view controller — its outlets need a storyboard, and
its logic is now three lines.

**The seam.** A *seam* is a place where the test can swap a real part for a fake. Here it's the
`transport` closure: the fake below replays canned answers (any status, any body) and records each
request, so nothing touches the network. A zero `retryDelay` keeps the retries instant.

```swift
import Foundation
import Testing

/// Plays back canned replies in order (the last one repeats) and records every request.
actor FakeTransport {
    private var replies: [(status: Int, body: String)]
    private(set) var requests: [URLRequest] = []

    init(_ replies: (status: Int, body: String)...) { self.replies = replies }

    func data(for request: URLRequest) async throws -> (Data, URLResponse) {
        requests.append(request)
        let reply = replies.count > 1 ? replies.removeFirst() : replies[0]
        let response = HTTPURLResponse(url: request.url!, statusCode: reply.status,
                                       httpVersion: nil, headerFields: nil)!
        return (Data(reply.body.utf8), response)
    }
}

let ada = #"{"id": 1, "name": "Ada", "avatar_url": "https://example.com/ada.png"}"#

func makeClient(_ transport: FakeTransport) -> APIClient {
    APIClient(transport: { try await transport.data(for: $0) }, retryDelay: .zero)
}

struct APIClientTests {
    @Test func profileDecodesTheSnakeCaseAvatarURL() async throws {
        let client = makeClient(FakeTransport((200, ada)))

        let user = try await client.fetchUser(id: 1)

        #expect(user.avatarURL == URL(string: "https://example.com/ada.png"))
    }

    @Test func serverErrorIsRetriedThenReportedAsBadStatus() async {
        // Given a server that always answers 500 with an HTML page
        let transport = FakeTransport((500, "<html>Oops</html>"))
        let client = makeClient(transport)

        // When / Then: it never reaches the decoder, and it tried three times
        await #expect(throws: APIError.badStatus(500)) { try await client.searchUsers(matching: "ada") }
        #expect(await transport.requests.count == 3)
    }

    @Test func notFoundIsNotRetried() async {
        let transport = FakeTransport((404, ""))
        let client = makeClient(transport)

        await #expect(throws: APIError.badStatus(404)) { try await client.fetchUser(id: 1) }
        #expect(await transport.requests.count == 1)
    }

    @Test func serviceUnavailableThenOKSucceedsOnTheSecondAttempt() async throws {
        let transport = FakeTransport((503, ""), (200, ada))
        let client = makeClient(transport)

        let user = try await client.fetchUser(id: 1)

        #expect(user.name == "Ada")
        #expect(await transport.requests.count == 2)
    }

    @Test func searchQueryIsEncoded() async throws {
        let transport = FakeTransport((200, "[]"))
        let client = makeClient(transport)

        _ = try await client.searchUsers(matching: "tom & admin=true")

        let request = try #require(await transport.requests.first)
        #expect(request.url?.absoluteString == "https://api.example.com/users?q=tom%20%26%20admin%3Dtrue")
    }
}
```

Ran with Swift 6.4: 5 tests, all passed.
:::

::: What I'd ask next
- *"How do you add an auth token, and refresh it when it expires?"* — An `actor TokenStore` the client
  asks for a token before each request. On a 401, refresh once and retry; the actor makes sure ten
  concurrent 401s trigger one refresh, not ten.
- *"Why not retry inside the transport?"* — The transport doesn't know which requests are idempotent
  or which statuses are transient for this API. Keep it dumb; put policy in the client.
- *"How would you test the backoff delays themselves?"* — Inject the sleep (a `Clock`, or a small
  `sleep(for:)` closure) and assert the delays it was asked for.
- *"A user searches for `c++`. What reaches the server?"* — `URLQueryItem` leaves `+` alone, and
  many servers read `+` in a query as a space, so they see `c  `. Percent-encode `+` as `%2B` yourself.
- *"The product wants offline support."* — Cache the last good response on disk keyed by URL, show it
  with a "last updated" label, and refresh in the background. Don't fake it with long timeouts.
- *"Would you still keep a completion-handler API?"* — Only as a thin wrapper for old callers:
  start a `Task`, await `fetchUser(id:)`, and call `completion(.success(user))` or
  `completion(.failure(error))` — on main, exactly once. New code uses `async`.
:::
