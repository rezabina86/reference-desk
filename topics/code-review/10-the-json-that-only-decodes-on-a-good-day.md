---
title: 10 · The JSON that only decodes on a good day
summary: A menu model and a getItemData() decoder that crash the app the first time the backend sends something slightly different — find why.
minutes: 20
group: Find the bug
sources:
- Glassdoor · DoorDash iOS — a getItemData() stub, "deserialize the JSON into native Swift objects" | https://www.glassdoor.com/Interview/DoorDash-Interview-RVW57524208.htm
- LeetCode Discuss · Swiggy iOS — "Why have I used a forced unwrap operator at one place" | https://leetcode.com/discuss/post/4558238/swiggy-ios-developer-rejected
- Apple · JSONDecoder — key, date and data decoding strategies | https://developer.apple.com/documentation/foundation/jsondecoder
---

*Shape: find the bug · Reported: DoorDash — fill in a `getItemData()` stub that deserialises JSON
into Swift objects; Swiggy — the candidate was asked to justify a single force unwrap · Verified:
the snippet crashes on the sample and the fix's tests pass, Swift 6.4*

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
Run against the JSON above, it dies on the first line of the decode: *'try!' expression
unexpectedly raised an error: DecodingError.keyNotFound … "storeId"*. That's only the first error.
Fixing them one at a time shows the rest, each hiding behind the one before (real output, trimmed
to the error type and path):

```text
1 as written                -> keyNotFound   'storeId'
2 + snake_case              -> typeMismatch  Expected Double.  Path: items[0].createdAt
3 + iso8601                 -> keyNotFound   'description'.     Path: items[1]
4 + optional description    -> valueNotFound Expected Double, found null.  Path: items[2].price
```

That's why it "works for some stores": a store whose items all have descriptions and prices gets
further than one that doesn't. By severity, the reported crash first:

1. **`try!` turns bad data into a crash (the reported bug).** Server data is input, and input can
   be wrong. `getItemData` must `throw`, and the screen must show an error. This is the Swiggy
   question: a force unwrap is only fine when failure means a programmer bug, never the network.
2. **snake_case keys, camelCase properties, no mapping.** The decoder looks for `storeId`; the JSON
   has `store_id`. Set `keyDecodingStrategy = .convertFromSnakeCase`, or write `CodingKeys`.
3. **The date decodes as a `Double`.** The default strategy reads seconds since 2001, so an ISO-8601
   string fails with "expected Double". Set `dateDecodingStrategy = .iso8601`.
4. **A field that's sometimes missing is non-optional.** Item 2 has no `description`, so the whole
   response fails. Make it `String?`.
5. **One bad element fails the whole array.** Item 3 has `"price": null`. Dropping an item that
   can't be sold is right; losing the whole menu isn't. Decode each element on its own and keep the
   ones that work.
6. **`data!` crashes on any network failure.** No connection means `data` is `nil`. The error and
   the HTTP status are ignored too, so a 500 with an HTML body goes straight to the decoder.
7. **`storeID` is pasted into the URL unescaped.** Since iOS 17, `URL(string:)` escapes a space
   instead of returning `nil`, so the `!` rarely fires now. But an id with `/` or `?` silently
   changes the path or adds a query (checked: `s/42?x=1` became a query). Use
   `appending(components:)`, which escapes each part.
8. **Data race on `self`.** The completion handler runs on a background queue and captures a
   non-`Sendable` view model. Swift 6.4 warns: *capture of 'self' with non-Sendable type
   'MenuViewModel' in a '@Sendable' closure*. Swift 5 mode says nothing. Make the view model
   `@MainActor`.
9. **No cancellation.** Switch stores quickly and the slower, older response can land last and
   overwrite the new menu. Keep the task and cancel it on the next `load`.
10. **Decoding runs on the main thread.** The parse sits inside `DispatchQueue.main.async`. A large
    menu drops frames. Decode in the callback, then hop to main with the result.
11. **Money as `Double`.** `12.99 + 4.50` prints `17.490000000000002` (checked). Totals drift and
    comparisons fail. Use `Decimal`, or integer cents from the server.
12. **`items` is publicly writable.** Any caller can replace the menu behind the view model's back.
    Make it `private(set)`.
13. **`Codable` where `Decodable` is enough.** Nothing encodes these types. Claiming `Encodable`
    promises a round trip nobody tests.
14. **Built-in dependencies.** `URLSession.shared` and a hard-coded host inside the method mean
    `load` can't be tested without the network. Inject a loader.
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
Same types, same `URLSession` and completion handler. Only the lines behind the findings change.

```swift
import Foundation

struct MenuResponse: Decodable {                        // key 13
    let storeId: String
    let items: [Lossy<MenuItem>]                        // key 5
}

struct MenuItem: Decodable {
    let itemId: Int
    let displayName: String
    let price: Decimal                                  // key 11
    let createdAt: Date
    let description: String?                           // key 4
}

/// Decodes one element; a bad one becomes nil instead of failing the array.
struct Lossy<T: Decodable>: Decodable {
    let value: T?
    init(from decoder: any Decoder) throws { value = try? T(from: decoder) }
}

@MainActor                                              // key 8
final class MenuViewModel {
    private(set) var items: [MenuItem] = []             // key 12
    var onUpdate: (() -> Void)?
    var onError: ((any Error) -> Void)?                 // key 1

    func load(storeID: String) {
        let url = URL(string: "https://api.example.com/stores")!
            .appending(components: storeID, "menu")     // key 7
        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            let result = Result {                       // keys 6, 10: checked and decoded off main
                guard let data, let http = response as? HTTPURLResponse,
                      (200..<300).contains(http.statusCode) else {
                    throw error ?? URLError(.badServerResponse)
                }
                return try MenuViewModel.getItemData(data)
            }
            DispatchQueue.main.async {
                switch result {
                case .success(let items): self?.items = items; self?.onUpdate?()
                case .failure(let error): self?.onError?(error)
                }
            }
        }.resume()
    }

    nonisolated static func getItemData(_ data: Data) throws -> [MenuItem] {   // key 1
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase                       // key 2
        decoder.dateDecodingStrategy = .iso8601                                   // key 3
        return try decoder.decode(MenuResponse.self, from: data).items.compactMap(\.value)
    }

    var total: Decimal {
        items.reduce(0) { $0 + $1.price }
    }
}
```

**Said out loud, not coded:** log the skipped items (keep the error, not just `nil`); cancel the
previous task when the store changes; `async`/`await` with a `MenuLoading` protocol so `load` is
testable; one `State` enum instead of two callbacks; integer cents from the backend.

Why each piece:

- **`.convertFromSnakeCase`** — the property names stay as they are; `store_id` becomes `storeId`,
  which is exactly what the model already says.
- **`Lossy`** — each element runs its own `init(from:)`, so a failure is caught there and the
  array still moves on to the next element.
- **Decode in the callback, then hop to main** — the parse runs on URLSession's queue, and only a
  `Sendable` `Result` crosses to the main thread. `getItemData` is `nonisolated static` so the
  background closure may call it.
- **`URL(string:)!` stays** — on a constant it can only fail through a typo, a programmer bug. The
  user's input goes through `appending(components:)`.
:::

::: Now write the tests
> "Good. Now write me a few tests — start with the response that crashed in production."

**What I'd test, and why**

1. **The response that crashed now decodes** — the right keys, dates and prices, and a total of
   exactly 17.49. The JSON from the bug report becomes a *fixture*: saved test input the test reads
   every time, so the crash can't quietly come back.
2. **The item with a `null` price is skipped** — one bad item must not sink the menu.
3. **A missing `description` decodes as `nil`** — the field really is optional.
4. **A response with no `store_id` throws** — the lossy decode is only for items. A broken page
   should still fail loudly, as an error and not a crash.

No seam needed: `getItemData` is a static function, so the fixture goes straight in. I wouldn't
test `URLSession` or `JSONDecoder` themselves; they are Apple's.

```swift
import Foundation
import Testing

/// The response from the bug report, kept as a fixture.
let sampleMenu = Data("""
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
""".utf8)

struct MenuDecodingTests {
    @Test func theResponseThatCrashedDecodes() throws {
        let items = try MenuViewModel.getItemData(sampleMenu)

        #expect(items.map(\.displayName) == ["Margherita", "Garlic bread"])
        #expect(items[0].createdAt == (try Date("2026-10-01T18:30:00Z", strategy: .iso8601)))
        #expect(items.reduce(0) { $0 + $1.price } == Decimal(string: "17.49"))
    }

    @Test func itemWithNullPriceIsSkipped() throws {
        let items = try MenuViewModel.getItemData(sampleMenu)

        #expect(items.map(\.itemId) == [1, 2])
    }

    @Test func missingDescriptionIsNil() throws {
        let items = try MenuViewModel.getItemData(sampleMenu)

        #expect(items[0].description == "Tomato, mozzarella, basil")
        #expect(items[1].description == nil)
    }

    @Test func responseWithoutStoreIDThrows() {
        let noStore = Data(#"{ "items": [] }"#.utf8)

        #expect(throws: DecodingError.self) { try MenuViewModel.getItemData(noStore) }
    }
}
```

Ran with Swift 6.4: 4 tests, all passed.
:::

::: What I'd ask next
- *"Why not just make every field optional?"* — Then the decode never fails, and every screen is
  full of `if let`. Optional should mean "the server legitimately leaves this out", not "I didn't
  check."
- *"The server sends dates with milliseconds — `2026-10-01T18:30:00.123Z`. Still fine?"* — With
  Swift 6.4's Foundation, `.iso8601` accepted it (I checked). Older OS versions have rejected
  fractional seconds with that strategy, so test on your minimum iOS, and fall back to `.custom`
  with `Date.ISO8601FormatStyle(includingFractionalSeconds: true)` if needed.
- *"Is `Decimal` from JSON always exact?"* — With Swift 6.4's Foundation, `12.99` decoded exactly,
  which is why the 17.49 check passes. Older Foundation versions went through `Double` first and
  gave `12.990000000000002`; there, compare in cents. Better still, have the backend send integer
  minor units (`1299`) plus a currency code, and the question goes away on every OS.
- *"How would you log the skipped items?"* — Make `Lossy` keep a `Result` instead of an optional,
  and log each failure's coding path. You'll notice when the backend starts sending broken items.
- *"When is a lossy decode the wrong call?"* — When a partial list is worse than none: a list of
  payment methods, a cart total, anything a user signs off on. Then fail loudly.
:::
