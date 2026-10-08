---
title: 10 · The JSON that only decodes on a good day
summary: A menu model and a getItemData() decoder that crash the app the first time the backend sends something slightly different — find why.
minutes: 15
group: Find the bug
sources:
- Glassdoor · DoorDash iOS — a getItemData() stub, "deserialize the JSON into native Swift objects" | https://www.glassdoor.com/Interview/DoorDash-Interview-RVW57524208.htm
- LeetCode Discuss · Swiggy iOS — "Why have I used a forced unwrap operator at one place" | https://leetcode.com/discuss/post/4558238/swiggy-ios-developer-rejected
- Apple · JSONDecoder — key, date and data decoding strategies | https://developer.apple.com/documentation/foundation/jsondecoder
---

*Shape: find the bug · Reported: DoorDash — fill in a `getItemData()` stub that deserialises JSON
into Swift objects; Swiggy — the candidate was asked to justify a single force unwrap · Compiled
and run with Swift 6.4: the snippet is rejected in Swift 6 mode, compiles cleanly in Swift 5 mode
and crashes on the sample; the fix compiles in Swift 6 mode with zero warnings and was run against
the same JSON*

> "This is the menu screen's model. It worked in the demo. In production it crashes on launch for
> some stores and not others. Here's the code, and here's a real response from one of the stores
> that crashes. Find out why — then tell me everything else you'd change."

```json
{
  "store_id": "s-42",
  "items": [
    { "item_id": 1, "display_name": "Margherita", "price": 12.99,
      "created_at": "2026-10-01T18:30:00Z", "description": "Tomato, mozzarella, basil" },
    { "item_id": 2, "display_name": "Garlic bread", "price": 4.50,
      "created_at": "2026-10-01T18:31:00Z" },
    { "item_id": 3, "display_name": "Tiramisu", "price": null,
      "created_at": "2026-10-01T18:32:00Z", "description": "Mascarpone, coffee" }
  ]
}
```

```swift
import Foundation

struct MenuResponse: Codable {
    let storeId: String
    let items: [MenuItem]
}

struct MenuItem: Codable {
    let itemId: Int
    let displayName: String
    let price: Double
    let createdAt: Date
    let description: String
}

final class MenuViewModel {
    var items: [MenuItem] = []
    var onUpdate: (() -> Void)?

    func load(storeID: String) {
        let url = URL(string: "https://api.example.com/stores/\(storeID)/menu")!
        URLSession.shared.dataTask(with: url) { data, _, _ in
            DispatchQueue.main.async {
                self.items = self.getItemData(data!)
                self.onUpdate?()
            }
        }.resume()
    }

    func getItemData(_ data: Data) -> [MenuItem] {
        let response = try! JSONDecoder().decode(MenuResponse.self, from: data)
        return response.items
    }

    var total: Double {
        items.reduce(0) { $0 + $1.price }
    }
}
```

::: A hint, if you're stuck
- Read the JSON keys, then read the property names. Does anything tell the decoder how to get
  from one to the other?
- What type does `JSONDecoder` expect a `Date` to be by default? It isn't a string.
- Look at all three items. Which fields are always there, and which aren't?
- If item 3 is bad, should the user lose items 1 and 2?
:::

::: The key — what I expect a senior to find
I ran the snippet against the JSON above. In Swift 5 mode it compiles cleanly and dies on the
first line of the decode:

```text
Fatal error: 'try!' expression unexpectedly raised an error: DecodingError.keyNotFound:
Key 'storeId' not found in keyed decoding container. Debug description: No value associated
with key CodingKeys(stringValue: "storeId", intValue: nil) ("storeId").
```

That's only the first error. Fixing them one at a time with a `do`/`catch` harness shows the rest,
each hiding behind the one before (real output, trimmed to the error type and path):

```text
1 as written                -> keyNotFound   'storeId'
2 + snake_case              -> typeMismatch  Expected Double.  Path: items[0].createdAt
3 + iso8601                 -> keyNotFound   'description'.     Path: items[1]
4 + optional description    -> valueNotFound Expected Double, found null.  Path: items[2].price
```

That's why it "works for some stores": a store whose items all have descriptions and prices
gets further than one that doesn't. The answer key, by severity:

1. **`try!` turns bad data into a crash.** Any decoding error kills the app. Data from a server is
   input, and input can be wrong; the function must `throw` and the screen must show an error.
   This is the Swiggy question: one force unwrap is only defensible when a failure means a
   programmer bug, never when it depends on the network.
2. **`data!` crashes on any network failure.** When the request fails, `data` is `nil`. The error
   and the HTTP status are both ignored too, so a 500 with an HTML body goes straight to the
   decoder.
3. **snake_case keys, camelCase properties, no mapping.** The synthesised coding keys are the
   property names, so the decoder looks for `storeId` and the JSON has `store_id`. Use explicit
   `CodingKeys`, or `keyDecodingStrategy = .convertFromSnakeCase` — not both on the same type.
4. **The date decodes as a `Double`.** The default `dateDecodingStrategy` is `.deferredToDate`,
   which reads a number of seconds since 2001. An ISO-8601 string fails with "expected Double".
   Set `.iso8601`.
5. **A field that's sometimes missing is declared non-optional.** Item 2 has no `description`, so
   the whole response fails. Make it `String?` (the synthesised decoder then uses
   `decodeIfPresent`) or give it a default in a custom `init(from:)`.
6. **One bad element fails the whole array.** Item 3 has `"price": null`. An item with no price
   can't be sold, so dropping it is right; losing the whole menu isn't. Decode each element
   separately and keep the ones that work — and log the ones that don't.
7. **Data race on `self`.** The completion handler runs on a background queue and captures the
   non-`Sendable` view model. Swift 6 rejects it — verified: *sending 'self' risks causing data
   races*. In Swift 5 mode it compiles with no warning at all.
8. **Decoding runs on the main thread.** The whole parse happens inside `DispatchQueue.main.async`.
   A menu of a few hundred items with nested options can take long enough to drop frames.
9. **Money as `Double`.** Binary floating point can't hold 12.99 exactly. Verified: `12.99 + 4.50`
   prints `17.490000000000002`. Totals drift and comparisons fail. Use `Decimal`, or integer cents
   from the server.
10. **Built-in dependencies.** `URLSession.shared` and a URL string inside the method mean nothing
    here can be tested without the network. `storeID` is also pasted into the path unescaped.
:::

::: The idea behind it
`Codable` is a contract. When you write `let price: Double`, you are promising the decoder that
every response will contain a key called exactly `price`, and that its value will be a number.
The decoder holds you to every word. If one promise breaks anywhere in the tree — one key, one
item, one `null` — the whole decode throws and you get nothing.

So the job is to write promises the server can actually keep. Three questions per field:

- **What is the key called on the wire?** That's what `CodingKeys` (a small enum that maps your
  property names to JSON keys) or a key strategy is for.
- **What shape is the value?** A date can be a string, a number of seconds, or milliseconds. You
  have to tell the decoder which.
- **Is it always there?** If not, it's an optional. That's not weakness; it's the truth.

Then decide what failure means. Some failures mean the whole response is useless — no store id.
Others mean one item is broken. Treat those differently. A *lossy* decode (one that skips bad
elements instead of failing) is a promise of "most of these will be fine."

Think of a customs officer checking a list of packages. A strict one rejects the whole lorry for
one torn label. A sensible one sets that box aside, writes it down, and lets the rest through.
:::

::: The fix
```swift
import Foundation

struct MenuItem: Decodable, Sendable, Identifiable {
    let id: Int
    let name: String
    let price: Decimal
    let createdAt: Date
    let description: String?

    private enum CodingKeys: String, CodingKey {
        case id = "item_id"
        case name = "display_name"
        case price
        case createdAt = "created_at"
        case description
    }
}

struct MenuPage: Decodable, Sendable {
    let storeID: String
    let items: [MenuItem]
    let skipped: [any Error]   // log these (they carry the coding path), don't show them

    private enum CodingKeys: String, CodingKey {
        case storeID = "store_id"
        case items
    }

    init(from decoder: any Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        storeID = try container.decode(String.self, forKey: .storeID)
        let results = try container.decode([Lossy<MenuItem>].self, forKey: .items).map(\.result)
        items = results.compactMap { try? $0.get() }
        skipped = results.compactMap { if case .failure(let error) = $0 { error } else { nil } }
    }
}

/// Decodes one array element without letting its failure sink the whole array.
struct Lossy<Wrapped: Decodable & Sendable>: Decodable, Sendable {
    let result: Result<Wrapped, any Error>

    init(from decoder: any Decoder) throws {
        result = Result { try Wrapped(from: decoder) }
    }
}

protocol MenuLoading: Sendable {
    func menu(storeID: String) async throws -> MenuPage
}

struct MenuService: MenuLoading {
    let session: URLSession
    let baseURL: URL

    func menu(storeID: String) async throws -> MenuPage {
        let url = baseURL.appending(components: "stores", storeID, "menu")
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try await Self.decode(data)
    }

    /// `@concurrent` = always off the caller's actor, so a big payload never decodes on main.
    @concurrent
    static func decode(_ data: Data) async throws -> MenuPage {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(MenuPage.self, from: data)
    }
}

@MainActor
final class MenuViewModel {
    enum State { case loading, loaded([MenuItem]), failed(any Error) }

    private(set) var state: State = .loading
    private let loader: any MenuLoading

    init(loader: any MenuLoading) { self.loader = loader }

    func load(storeID: String) async {
        do {
            state = .loaded(try await loader.menu(storeID: storeID).items)
        } catch {
            state = .failed(error)
        }
    }

    var total: Decimal {
        guard case .loaded(let items) = state else { return 0 }
        return items.reduce(0) { $0 + $1.price }
    }
}
```

Run against the same JSON through a fake `MenuLoading` that reads the file (real output):

```text
skipped: DecodingError.valueNotFound: Expected value of type NSDecimal. Path: items[2].price. Debug description: Cannot get value of type NSDecimal -- found null value instead
1 Margherita 12.99 2026-10-01 18:30:00 +0000 Tomato, mozzarella, basil
2 Garlic bread 4.5 2026-10-01 18:31:00 +0000 —
total: €17.49
```

Why each piece:

- **Explicit `CodingKeys`** — they also let the model use Swift names (`id`, `name`, `storeID`)
  instead of whatever the server chose. I picked them over `.convertFromSnakeCase` because that
  strategy turns `store_id` into `storeId`, not `storeID`.
- **`.iso8601`** — matches what the server actually sends.
- **`description: String?`** — states the truth: some items don't have one.
- **`Lossy` with a `Result`** — each element is decoded inside its own `init`, so a failure is
  caught there and the array's position still moves on. Keeping the error, not just dropping it,
  means you can log it and notice when the backend starts sending broken items.
- **`Decimal` for price** — the total is exactly 17.49.
- **`throws` everywhere, a `State` enum** — a bad response becomes an error screen, not a crash.
- **`@concurrent` on `decode`** — the parse runs on the global executor whatever the caller is.
  A plain `nonisolated async` function does that today, but with the newer "run on the caller's
  actor" default (Xcode 26's Approachable Concurrency setting) it would run on main.
- **`MenuLoading` protocol and an injected `URLSession`** — the view model is tested with a fake;
  that's exactly how this was run.
:::

::: What I'd ask next
- *"Why not just make every field optional?"* — Then the decode never fails, and every screen is
  full of `if let`. Optional should mean "the server legitimately leaves this out", not "I didn't
  check."
- *"The server sends dates with milliseconds — `2026-10-01T18:30:00.123Z`. Still fine?"* — On this
  Mac's Foundation, `.iso8601` accepted it (I checked). Older OS versions have rejected fractional
  seconds with that strategy, so test on your minimum iOS, and fall back to
  `.custom` with `Date.ISO8601FormatStyle(includingFractionalSeconds: true)` if needed.
- *"How would you test this without a server?"* — Commit the JSON as a test fixture and decode it
  in a Swift Testing `@Test`, including a fixture with a broken item. Cheaper and faster than any
  mock of `URLSession`.
- *"Is `Decimal` from JSON always exact?"* — On this Mac, `12.99` decoded exactly. If the backend
  can, send money as integer minor units (`1299`) plus a currency code, and the question goes away
  on every OS.
- *"When is a lossy decode the wrong call?"* — When a partial list is worse than none: a list of
  payment methods, a cart total, anything a user signs off on. Then fail loudly.
:::
