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
candidate writes that storing tokens in the keychain wasn't the end of the conversation · Security
framework — the fix typechecks against the iOS SDK (iOS 18 target) in Swift 6 mode with zero warnings; the
login logic was compiled and run with Swift 6.4 against a fake HTTP client and an in-memory
keychain; the real keychain calls were checked by hand*

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
1. **`try!` on the response.** A 200 with an unexpected body — a maintenance page, a changed field
   name — crashes the app on the login screen. Decode with `try` and show an error.
2. **UI state written from a background queue.** The completion handler runs on `URLSession`'s
   queue and sets `isLoggedIn` and `errorMessage`, which drive the UI. That's a data race and
   wrong-thread UI. Swift 6 mode warns (verified: *capture of 'self' with non-Sendable type
   'LoginViewModel' in a '@Sendable' closure*); Swift 5 mode says nothing.
3. **"Remember me" stores the password itself, in plain text.** `UserDefaults` is an unencrypted
   plist in the app's container. It goes into unencrypted backups, and anyone with the backup or a
   jailbroken phone reads it. Never store the password at all — remembering the user means keeping
   the *session token*, and that belongs in the keychain.
4. **The token in `UserDefaults`.** Same plist, same problem: whoever reads it is logged in as the
   user, with no password needed.
5. **Clear-text HTTP, enabled app-wide.** `http://` sends the email and password readable to anyone
   on the same café Wi-Fi. `NSAllowsArbitraryLoads` switches off App Transport Security (Apple's
   HTTPS-only default) for every request in the app, and has to be justified in App Review.
   Delete it and use `https://`.
6. **The password in the URL.** Even over HTTPS, URLs end up in server access logs, proxy and CDN
   logs and crash reports. Credentials go in the request body. It's also a user-visible bug:
   verified, `URLComponents` leaves `+` as is — `password=p@ss+w0rd%26x` — and many servers decode
   `+` in a query as a space, so users with a `+` in their password can't log in.
7. **The token in the avatar URL.** Same leak, plus the URL becomes a key in `URLCache` on disk and
   is often logged by image loaders. Send it in an `Authorization` header.
8. **The password logged.** `NSLog` writes to the system log, which a connected Mac can read in
   Console and which ends up in sysdiagnose files. It also treats the string as a format: verified,
   a password of `x%dy%@z` was logged as `x0y(null)z`. Don't log credentials; for other personal
   data, `Logger` with `privacy: .private`.
9. **Error messages reveal who has an account.** "No account exists" versus "Wrong password" lets
   anyone test a list of emails — *account enumeration*. The 404 message also puts the email on
   screen. One message for both: "Email or password is incorrect."
10. **No protection against hammering.** Nothing stops five quick taps sending five requests, and
    there's no handling of a server's rate limit (`429 Too Many Requests` with `Retry-After`). The
    user gets no "try again in a minute"; the server sees a brute-force pattern.
11. **Logout leaves the user half logged in.** The token stays in memory in `token`, so
    `avatarURL()` keeps working; the remembered email and password stay in `UserDefaults` and are
    filled in on next launch for whoever picks up the phone. The server is never told either.
12. **Failures are silent.** No network, no data: `guard … else { return }`. The button does
    nothing and the user taps again.
13. **The password stays in memory after login.** Clear the field once it has been used.
14. **Untestable.** `UserDefaults.standard` and `URLSession.shared` are reached for directly; none
    of the above can be checked in a unit test.
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
```swift
import Foundation
import Security

protocol KeychainStoreType: Sendable {
    func set(_ data: Data, for account: String) throws
    func data(for account: String) throws -> Data?
    func remove(_ account: String) throws
}

struct KeychainError: Error, Equatable {
    let status: OSStatus
}

struct KeychainStore: KeychainStoreType {
    let service: String

    func set(_ data: Data, for account: String) throws {
        let attributes: [CFString: Any] = [
            kSecValueData: data,
            // Readable after the first unlock since boot, so a background refresh works while the
            // phone is locked. ThisDeviceOnly: never synced, never restored onto another phone.
            kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
        ]
        var status = SecItemUpdate(query(account) as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            let item = query(account).merging(attributes) { _, new in new }
            status = SecItemAdd(item as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw KeychainError(status: status) }
    }

    func data(for account: String) throws -> Data? {
        var request = query(account)
        request[kSecReturnData] = true
        request[kSecMatchLimit] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(request as CFDictionary, &result)
        switch status {
        case errSecSuccess: return result as? Data
        case errSecItemNotFound: return nil
        default: throw KeychainError(status: status)
        }
    }

    func remove(_ account: String) throws {
        let status = SecItemDelete(query(account) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError(status: status)
        }
    }

    private func query(_ account: String) -> [CFString: Any] {
        [kSecClass: kSecClassGenericPassword,
         kSecAttrService: service,
         kSecAttrAccount: account]
    }
}
```

```swift
protocol HTTPClient: Sendable {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

enum LoginOutcome: Equatable, Sendable {
    case success(token: String)
    case invalidCredentials
    case rateLimited(retryAfterSeconds: Int)
    case failed
}

struct AuthService: Sendable {
    private let baseURL: URL
    private let http: any HTTPClient

    init(baseURL: URL, http: any HTTPClient) {
        precondition(baseURL.scheme == "https", "Credentials only travel over HTTPS")
        self.baseURL = baseURL
        self.http = http
    }

    func login(email: String, password: String) async throws -> LoginOutcome {
        var request = URLRequest(url: baseURL.appending(path: "v1/login"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["email": email, "password": password])

        let (data, response) = try await http.send(request)
        switch response.statusCode {
        case 200:
            struct Body: Decodable { let token: String }
            return .success(token: try JSONDecoder().decode(Body.self, from: data).token)
        case 401, 404:
            return .invalidCredentials          // same answer whether or not the email exists
        case 429:
            let wait = response.value(forHTTPHeaderField: "Retry-After").flatMap(Int.init) ?? 30
            return .rateLimited(retryAfterSeconds: wait)
        default:
            return .failed
        }
    }
}

@MainActor
final class SessionStore {
    private(set) var token: String?
    private let keychain: any KeychainStoreType
    private let account = "session-token"

    init(keychain: any KeychainStoreType) {
        self.keychain = keychain
        token = (try? keychain.data(for: account)).map { String(decoding: $0, as: UTF8.self) }
    }

    /// "Remember me" keeps the token in the keychain; otherwise it lives in memory only.
    func start(token: String, remember: Bool) throws {
        self.token = token
        if remember {
            try keychain.set(Data(token.utf8), for: account)
        } else {
            try keychain.remove(account)
        }
    }

    func end() {
        token = nil
        try? keychain.remove(account)
    }

    func authorized(_ request: URLRequest) -> URLRequest {
        var request = request
        if let token { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        return request
    }
}

@MainActor
final class LoginViewModel {
    enum State: Equatable {
        case idle, submitting, loggedIn
        case failed(String)
        case lockedOut(until: Date)
    }

    var email = ""
    var password = ""
    var rememberMe = false
    private(set) var state: State

    private let auth: AuthService
    private let session: SessionStore
    private let now: () -> Date

    init(auth: AuthService, session: SessionStore, now: @escaping () -> Date) {
        self.auth = auth
        self.session = session
        self.now = now
        state = session.token == nil ? .idle : .loggedIn
    }

    var canSubmit: Bool {
        if case .lockedOut(let until) = state, now() < until { return false }
        return state != .submitting && !email.isEmpty && !password.isEmpty
    }

    func login() async {
        guard canSubmit else { return }                    // no double submit
        state = .submitting
        let email = email.trimmingCharacters(in: .whitespacesAndNewlines)
        do {
            switch try await auth.login(email: email, password: password) {
            case .success(let token):
                try session.start(token: token, remember: rememberMe)
                password = ""
                state = .loggedIn
            case .invalidCredentials:
                state = .failed("Email or password is incorrect.")
            case .rateLimited(let seconds):
                state = .lockedOut(until: now().addingTimeInterval(TimeInterval(seconds)))
            case .failed:
                state = .failed("Couldn't sign in. Please try again.")
            }
        } catch {
            state = .failed("Couldn't reach the server. Check your connection.")
        }
    }

    func logout() {
        session.end()
        password = ""
        state = .idle
    }
}
```

The `NSAllowsArbitraryLoads` entry is deleted from `Info.plist`.

Run with a fake `HTTPClient` that answers 404, 401, 429 (`Retry-After: 60`), then 200, an
in-memory `KeychainStoreType`, and a clock the test moves by hand (real output):

```text
unknown email -> failed("Email or password is incorrect.")
wrong password -> failed("Email or password is incorrect.")
rate limited -> lockedOut(until: 1970-01-01 00:01:00 +0000) | canSubmit: false
61 s later canSubmit: true
success -> loggedIn | password cleared: true
requests sent: 4
last request: POST https://api.example.com/v1/login
body: {"password":"p@ss+w0rd&x","email":"Ana+Bank@Example.com"}
keychain: ["session-token": "t-123"]
authorized header: Bearer t-123
after logout -> token: nil | keychain: [:] | idle
```

The success case was two `login()` calls fired at once — a double tap. Four replies, four
requests: the second tap sent nothing.

Why each piece:

- **`KeychainStoreType`** — the view model never sees `SecItem…`, and tests swap in an in-memory
  store. `SecItemUpdate` then `SecItemAdd` means saving twice updates instead of failing with
  `errSecDuplicateItem`.
- **`AfterFirstUnlockThisDeviceOnly`** — a token refresh can run in the background while the phone
  is locked. If nothing in the app touches the token in the background, choose
  `WhenUnlockedThisDeviceOnly`: a stolen locked phone then can't read it at all. `ThisDeviceOnly`
  either way, because a session should never follow a backup onto another device.
- **Only the token is remembered** — the password is never written anywhere and is cleared from
  memory after use. Without "remember me" the token lives in memory and is gone on relaunch.
- **HTTPS enforced at the seam, credentials in a JSON body** — no clear-text, nothing in a URL, and
  `+` survives.
- **One message for 401 and 404** — the screen can no longer tell an attacker which emails exist.
- **`lockedOut(until:)`** — the server decides the limit; the app shows it and disables the button.
  The injected `now` is how the test skipped 61 seconds.
- **`submitting` blocks a second request**, and every failure shows a message.
- **`@MainActor`** — all state the UI reads changes on main.
- **`logout()` clears memory and keychain** — `authorized(_:)` adds nothing after logout.
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
