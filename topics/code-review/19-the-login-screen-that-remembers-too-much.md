---
title: 19 · The login screen that remembers too much
summary: A login view model with a "remember me" switch that stores far more than it should, in the wrong places — review it.
minutes: 20
group: Review this PR
sources:
- LeetCode Discuss · PhonePe iOS — "how to share keychain data b/w apps" | https://leetcode.com/discuss/interview-experience/1422835/
- Medium · candidate story — "I stored auth tokens in Keychain. My interviewer showed me why that wasn't enough" | https://medium.com/@saiprasanthamuluru/i-stored-auth-tokens-in-keychain-my-interviewer-showed-me-why-that-wasnt-enough-2d28ef5a9dd2
- Apple · Restricting keychain item accessibility | https://developer.apple.com/documentation/security/restricting-keychain-item-accessibility
---

*Shape: review this PR · Reported: PhonePe asked how to share keychain data between apps; a
candidate writes that storing tokens in the keychain wasn't the end of the conversation ·
Verified: the fix's login logic run against a fake server and token store, Swift 6.4*

> "A teammate added 'remember me' to the login screen. It works, QA signed it off, and it's
> going out on Thursday. Review it before it does."

```swift
import Foundation

struct LoginResponse: Decodable {
    let token: String
}

final class LoginViewModel {
    var email = ""
    var password = ""
    var rememberMe = false
    var errorMessage: String?
    var isLoggedIn = false
    private var token: String?

    init() {
        let defaults = UserDefaults.standard
        if defaults.bool(forKey: "rememberMe") {
            email = defaults.string(forKey: "email") ?? ""
            password = defaults.string(forKey: "password") ?? ""
        }
        token = defaults.string(forKey: "authToken")
        isLoggedIn = token != nil
    }

    func login() {
        NSLog("Logging in \(email) with password \(password)")
        var components = URLComponents(string: "http://api.example.com/v1/login")!
        components.queryItems = [
            URLQueryItem(name: "email", value: email),
            URLQueryItem(name: "password", value: password),
        ]
        var request = URLRequest(url: components.url!)
        request.httpMethod = "POST"

        URLSession.shared.dataTask(with: request) { data, response, _ in
            guard let data, let http = response as? HTTPURLResponse else { return }
            switch http.statusCode {
            case 200:
                let token = try! JSONDecoder().decode(LoginResponse.self, from: data).token
                self.token = token
                UserDefaults.standard.set(token, forKey: "authToken")
                if self.rememberMe {
                    UserDefaults.standard.set(true, forKey: "rememberMe")
                    UserDefaults.standard.set(self.email, forKey: "email")
                    UserDefaults.standard.set(self.password, forKey: "password")
                }
                self.isLoggedIn = true
            case 404:
                self.errorMessage = "No account exists for \(self.email)."
            case 401:
                self.errorMessage = "Wrong password for \(self.email)."
            default:
                self.errorMessage = "Something went wrong."
            }
        }.resume()
    }

    func avatarURL() -> URL {
        URL(string: "https://api.example.com/v1/me/avatar?token=\(token ?? "")")!
    }

    func logout() {
        UserDefaults.standard.removeObject(forKey: "authToken")
        isLoggedIn = false
    }
}
```

And in the same PR, `Info.plist`, so the `http://` URL works:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

::: A hint, if you're stuck
- Follow the password from the text field. List every place it ends up — memory, disk, logs,
  the network, other people's servers.
- Do the same for the token.
- Read the two error messages as an attacker with a list of email addresses would.
- What happens when the user taps "Log in" five times quickly? What happens after logout?
:::

::: The key — what I expect a senior to find
1. **`try!` on the response.** A 200 with an unexpected body — a maintenance page, a renamed
   field — crashes the app on the login screen. Decode with `try` and show an error.
2. **UI state written from a background queue.** The completion handler runs on `URLSession`'s
   queue and sets `isLoggedIn` and `errorMessage`, which drive the UI. That's a data race and
   wrong-thread UI. Swift 6 mode warns (*capture of 'self' with non-Sendable type
   'LoginViewModel' in a '@Sendable' closure*); Swift 5 mode says nothing. Make the class
   `@MainActor` and use `async`/`await`.
3. **"Remember me" stores the password itself, in plain text.** `UserDefaults` is an unencrypted
   plist in the app's container. It goes into backups, and anyone with the backup or a jailbroken
   phone reads it. `init` fills it back into the field on every launch, and `logout()` never
   deletes it. Never store the password; remembering the user means keeping the *token*.
4. **The token in `UserDefaults`.** Same plist, same problem: whoever reads it is logged in as the
   user, no password needed. It belongs in the keychain.
5. **Clear-text HTTP, enabled app-wide.** `http://` sends the email and password readable to anyone
   on the same café Wi-Fi. `NSAllowsArbitraryLoads` switches off App Transport Security (Apple's
   HTTPS-only default) for every request in the app. Delete it and use `https://`.
6. **The password in the URL.** Even over HTTPS, URLs end up in server, proxy and CDN logs and in
   crash reports. Credentials go in the request body. It's also a user-visible bug: `URLComponents`
   leaves `+` as is (`password=p@ss+w0rd%26x`), and many servers read `+` in a query as a space.
7. **The token in the avatar URL.** Same leak, plus the URL becomes a `URLCache` key on disk and
   image loaders often log it. The token is also pasted in unencoded, so a `+` or `&` in it breaks
   the URL. Send it in an `Authorization` header.
8. **The password logged.** `NSLog` writes to the system log, which a connected Mac reads in
   Console and which lands in sysdiagnose files. It also treats the string as a format: a password
   of `x%dy%@z` was logged as `x0y(null)z`. Don't log credentials at all.
9. **Error messages reveal who has an account.** "No account exists" versus "Wrong password" lets
   anyone test a list of emails — *account enumeration*. One message for both: "Email or password
   is incorrect."
10. **The password stays in memory after login.** It sits in `password` for as long as the screen
    lives. Clear it as soon as the request is built.
11. **No protection against hammering.** Five quick taps send five requests, and a server's rate
    limit (`429 Too Many Requests`) gets "Something went wrong." Block a second submit while one is
    in flight.
12. **Logout leaves the user half logged in.** The token stays in memory in `token`, so
    `avatarURL()` keeps working, and the server is never told.
13. **Failures are silent.** No network, no data: `guard … else { return }`. The button does
    nothing and the user taps again.
14. **The error never clears.** `errorMessage` is set on a failure and never reset, so a retry that
    succeeds still shows the old error under a logged-in screen.
15. **Unticking "remember me" forgets nothing.** Log in once with it on, once with it off: the
    first login's data stays stored. Unticking has to delete what was saved.
16. **`isLoggedIn` trusts any stored token.** A token from months ago, already expired, makes the
    app look logged in until the first request fails. The fix keeps this; say what you'd add (below).
17. **Untestable.** `UserDefaults.standard` and `URLSession.shared` are reached for directly, so
    none of the above can be checked in a unit test.
:::

::: The idea behind it
Every secret has a *blast radius*: the set of places it can be read from. A good login flow keeps
that set as small as possible.

A password is the worst secret to leak. People reuse it on other sites, so leaking it hurts the
user far beyond your app. So the app should touch it for as short a time as it can: read it from
the field, send it once, forget it.

A *token* is a stand-in the server hands back. It proves you logged in without repeating the
password. It can be limited — it can expire, and the server can cancel it. That's why "remember
me" should keep the token, never the password.

Where to keep it? `UserDefaults` is a settings file, not a safe. The *keychain* is the system's
encrypted store for small secrets. Each item has an *accessibility class* — the rule for when the
system unlocks it:

- **WhenUnlocked** — only while the phone is unlocked.
- **AfterFirstUnlock** — after the first unlock since the phone was switched on, even when it's
  locked again. Background work needs this.
- **ThisDeviceOnly** — added to either: the item is never moved to a new phone through a backup.

Think of a hotel. The password is your passport: show it once at the desk, then put it away. The
token is the key card: it opens your room, expires when you check out, and the desk can cancel it.
You keep the card in the room safe, not on the lobby table.
:::

::: The fix
Same class, same properties. `login()` becomes `async`, the token moves to the keychain behind one
protocol, and the `NSAllowsArbitraryLoads` entry is deleted from `Info.plist`.

```swift
import Foundation

struct LoginResponse: Decodable {
    let token: String
}

protocol TokenStore {                    // key 4: the one new seam; the app passes a keychain store
    func token() -> String?
    func set(_ token: String) throws
    func remove()
}

@MainActor                                                    // key 2
final class LoginViewModel {
    var email = ""
    var password = ""
    var rememberMe = false
    var errorMessage: String?
    var isLoggedIn = false
    private var token: String?
    private var isSubmitting = false                          // key 11
    private let session: URLSession
    private let tokenStore: TokenStore

    init(session: URLSession = .shared, tokenStore: TokenStore) {   // key 17
        self.session = session
        self.tokenStore = tokenStore
        email = UserDefaults.standard.string(forKey: "email") ?? ""   // key 3: never the password
        token = tokenStore.token()
        isLoggedIn = token != nil
    }

    func login() async {
        guard !isSubmitting else { return }                   // key 11: one request per tap burst
        isSubmitting = true
        defer { isSubmitting = false }
        errorMessage = nil                                    // key 14
        var request = URLRequest(url: URL(string: "https://api.example.com/v1/login")!)   // key 5
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONEncoder().encode(["email": email, "password": password])  // key 6
        password = ""                                         // key 10

        do {
            let (data, response) = try await session.data(for: request)
            switch (response as? HTTPURLResponse)?.statusCode {
            case 200:
                let token = try JSONDecoder().decode(LoginResponse.self, from: data).token  // key 1
                try remember(token)
                self.token = token
                isLoggedIn = true
            case 401, 404:
                errorMessage = "Email or password is incorrect."                // key 9
            default:
                errorMessage = "Couldn't sign in. Please try again."
            }
        } catch {
            errorMessage = "Couldn't sign in. Please try again."               // key 13
        }
    }

    func avatarRequest() -> URLRequest {                      // key 7
        var request = URLRequest(url: URL(string: "https://api.example.com/v1/me/avatar")!)
        if let token { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        return request
    }

    func logout() {
        tokenStore.remove()                                   // key 12
        for key in ["authToken", "rememberMe", "email", "password"] {
            UserDefaults.standard.removeObject(forKey: key)
        }
        token = nil
        isLoggedIn = false
    }

    private func remember(_ token: String) throws {
        if rememberMe {
            try tokenStore.set(token)                         // key 3, 4: only the token
            UserDefaults.standard.set(email, forKey: "email")
        } else {
            tokenStore.remove()                               // key 15: unticking forgets
            UserDefaults.standard.removeObject(forKey: "email")
        }
    }
}
```

Why each piece:

- **"Remember me" now means "stay signed in".** The original filled in the email *and* password.
  The fix keeps the token, and still pre-fills the email — an email isn't a secret. The password
  is never written anywhere.
- **`TokenStore` is the one new seam.** The view model never sees `SecItem…`, and tests pass a
  dictionary. The `URLSession` was already a dependency; it's now passed in, with `.shared` as the
  default.
- **`isSubmitting` with `defer`.** The flag is set before the first `await`, so a second tap on the
  main actor sees it and returns; `defer` resets it on every path out.

**Said out loud, not coded:** the keychain store is about ten lines — a generic-password query
(`kSecClass`, service, account), `SecItemDelete` then `SecItemAdd` with
`kSecAttrAccessibleWhenUnlockedThisDeviceOnly` (delete first, or a second save fails with
`errSecDuplicateItem`), and `SecItemCopyMatching` to read; honour `429` and `Retry-After`; revoke
the token on the server at logout; check the token's expiry before trusting `isLoggedIn`;
`AfterFirstUnlock` if a background refresh needs the token; `Logger` with `privacy: .private` for
other personal data.
:::

::: Now write the tests
> "Good. Now write me the tests that would have stopped this PR — the security ones first."

**What I'd test, and why**

1. **A 401 and a 404 show the same message** — the leak the review led with: the screen must not
   tell anyone which emails have an account.
2. **A double tap sends one request** — two `login()` calls at once, one request on the wire.
3. **"Remember me" stores only the token** — the token lands in the store, the password field is
   cleared, and nothing is written to `UserDefaults` under `password` or `authToken`.
4. **The credentials go in a JSON `POST` body, not the URL** — the URL is exactly the HTTPS
   endpoint with no query, and the body decodes to the email and password, `+` and `&` intact.
5. **Logout forgets the session** — the store is empty, the remembered email is gone, and the
   avatar request no longer carries an `Authorization` header.

I wouldn't unit-test the real keychain store. It is a thin wrapper over Apple's `SecItem` calls,
and the real keychain needs a signed app. One test in the app target, or a check by hand, covers it.

**The seam.** `TokenStore` gets an in-memory fake. For the network I don't add a protocol: the test
gives the view model a `URLSession` whose configuration routes every request to a `URLProtocol`
subclass — a fake server inside URLSession that answers with canned status codes and records each
request. The suite is `.serialized` because that fake keeps one shared log.

```swift
import Foundation
import Synchronization
import Testing

/// A fake server inside URLSession: answers with canned status codes and records each request.
final class StubServer: URLProtocol {
    struct Log { var statuses: [Int] = []; var requests: [URLRequest] = []; var bodies: [Data] = [] }
    static let log = Mutex(Log())

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        // Inside URLProtocol the body arrives as a stream, not as httpBody.
        let body = request.httpBodyStream.map { stream in
            stream.open(); defer { stream.close() }
            var data = Data(), buffer = [UInt8](repeating: 0, count: 1024)
            while case let n = stream.read(&buffer, maxLength: buffer.count), n > 0 { data.append(buffer, count: n) }
            return data
        } ?? Data()
        let status = Self.log.withLock { log in
            log.requests.append(request); log.bodies.append(body)
            return log.statuses.isEmpty ? 500 : log.statuses.removeFirst()
        }
        let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Data(#"{"token":"t-123"}"#.utf8))
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

/// The real keychain is Apple's code and needs a signed app; a dictionary stands in for it.
final class InMemoryTokenStore: TokenStore {
    var stored: String?
    func token() -> String? { stored }
    func set(_ token: String) throws { stored = token }
    func remove() { stored = nil }
}

@MainActor
@Suite(.serialized)   // one StubServer log, shared
struct LoginViewModelTests {
    let store = InMemoryTokenStore()

    func makeViewModel(answering statuses: Int...) -> LoginViewModel {
        StubServer.log.withLock { $0 = StubServer.Log(statuses: statuses) }
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubServer.self]
        let viewModel = LoginViewModel(session: URLSession(configuration: configuration), tokenStore: store)
        viewModel.email = "ana@example.com"
        viewModel.password = "p@ss+w0rd&x"
        return viewModel
    }

    @Test
    func unknownEmailAndWrongPasswordLookTheSame() async {
        let viewModel = makeViewModel(answering: 404, 401)

        await viewModel.login()
        let unknownEmail = viewModel.errorMessage
        viewModel.password = "another try"
        await viewModel.login()

        #expect(unknownEmail == "Email or password is incorrect.")
        #expect(viewModel.errorMessage == unknownEmail)
    }

    @Test
    func doubleTapSendsOneRequest() async {
        let viewModel = makeViewModel(answering: 200, 200)

        async let firstTap: Void = viewModel.login()
        async let secondTap: Void = viewModel.login()
        _ = await (firstTap, secondTap)

        #expect(StubServer.log.withLock { $0.requests.count } == 1)
        #expect(viewModel.isLoggedIn)
    }

    @Test
    func rememberMeStoresOnlyTheToken() async {
        let viewModel = makeViewModel(answering: 200)
        viewModel.rememberMe = true

        await viewModel.login()

        #expect(store.stored == "t-123")
        #expect(viewModel.password.isEmpty)
        #expect(UserDefaults.standard.string(forKey: "password") == nil)
        #expect(UserDefaults.standard.string(forKey: "authToken") == nil)
    }

    @Test
    func credentialsGoInAJSONPostBodyNotTheURL() async throws {
        let viewModel = makeViewModel(answering: 401)

        await viewModel.login()

        let (request, body) = try #require(StubServer.log.withLock { log in
            log.requests.first.map { ($0, log.bodies[0]) }
        })
        #expect(request.url?.absoluteString == "https://api.example.com/v1/login")
        #expect(request.httpMethod == "POST")
        #expect(request.value(forHTTPHeaderField: "Content-Type") == "application/json")
        let sent = try JSONDecoder().decode([String: String].self, from: body)
        #expect(sent == ["email": "ana@example.com", "password": "p@ss+w0rd&x"])
    }

    @Test
    func logoutForgetsTheSession() async {
        let viewModel = makeViewModel(answering: 200)
        viewModel.rememberMe = true
        await viewModel.login()

        viewModel.logout()

        #expect(!viewModel.isLoggedIn)
        #expect(store.stored == nil)
        #expect(UserDefaults.standard.string(forKey: "email") == nil)
        #expect(viewModel.avatarRequest().value(forHTTPHeaderField: "Authorization") == nil)
    }
}
```

One thing that trips people up: inside a `URLProtocol`, the request's body arrives as
`httpBodyStream`, not `httpBody`, so the fake reads the stream.

Ran with Swift 6.4: 5 tests, all passed.
:::

::: What I'd ask next
- *"How would two of our apps share the login?"* — The PhonePe question. Put both apps in the same
  *keychain access group* (the Keychain Sharing capability, same team ID) and set
  `kSecAttrAccessGroup` on the item. Both apps read the same token. Apps from different teams
  can't share keychain items.
- *"Is the keychain enough?"* — The Medium story's point. The keychain protects the token at rest
  on this device. It doesn't stop a stolen token being replayed from elsewhere. Keep access tokens
  short-lived with a refresh token, revoke on logout, and for high-value actions bind the session to
  the device — a key in the Secure Enclave or App Attest.
- *"Does the keychain survive deleting the app?"* — Often yes: keychain items can outlive the app.
  Store an "installed" flag in `UserDefaults` (which is deleted with the app) and, on a fresh
  install, wipe the keychain items before reading them.
- *"Face ID for 'remember me'?"* — Add a `SecAccessControl` with `.biometryCurrentSet` to the item.
  The system then shows Face ID when the item is read; you never handle the biometric yourself.
- *"What should logout also do?"* — Call the server to revoke the token, clear cookies and
  `URLCache`, and drop any per-user caches, so the next person sees nothing of the last.
:::
