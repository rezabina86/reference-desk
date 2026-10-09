---
title: 21 · The favourite that doesn't stick
summary: A list and a detail screen each with a favourite button that drift apart — review it, then fix it with one source of truth and persist it.
minutes: 25
group: Review, then extend
sources:
- LeetCode Discuss · Swiggy iOS — a favourite button on the detail screen "with a mirrored version on the first screen… all synchronized" | https://leetcode.com/discuss/post/4558238/swiggy-ios-developer-rejected
- Apple · Observation — the @Observable macro and withObservationTracking | https://developer.apple.com/documentation/observation
---

*Shape: review, then extend · Reported: Swiggy — a favourite button on the detail screen "with a
mirrored version on the first screen… all synchronized" · Verified: fix and tests run on the iOS
Simulator in Swift 6 mode (Swift 6.4)*

> "A list of restaurants, each with a heart. Tap a row, you get the detail screen, which also has a
> heart. QA says: favourite something on the detail screen, go back — sometimes the list is right,
> sometimes it isn't, and sometimes the *wrong* restaurant gets the heart. And after a refresh or a
> relaunch, favourites are gone. Review it. Then make favourites persist."

```swift
import UIKit

struct Restaurant: Decodable {
    let id: String
    let name: String
    var rating: Double
    var isFavourite: Bool
}

final class RestaurantListViewController: UITableViewController {
    var restaurants: [Restaurant] = []

    func sortByRating() {
        restaurants.sort { $0.rating > $1.rating }
        tableView.reloadData()
    }

    func reload(with fresh: [Restaurant]) {        // called by pull-to-refresh
        restaurants = fresh
        tableView.reloadData()
    }

    @objc func favouriteTapped(_ sender: UIButton) {
        restaurants[sender.tag].isFavourite.toggle()
        tableView.reloadRows(at: [IndexPath(row: sender.tag, section: 0)], with: .none)
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        let detail = RestaurantDetailViewController()
        detail.restaurant = restaurants[indexPath.row]
        detail.onFavouriteChanged = { isFavourite in
            self.restaurants[indexPath.row].isFavourite = isFavourite
            self.tableView.reloadRows(at: [indexPath], with: .none)
        }
        navigationController?.pushViewController(detail, animated: true)
    }
}

final class RestaurantDetailViewController: UIViewController {
    var restaurant: Restaurant!
    var onFavouriteChanged: ((Bool) -> Void)?
    private let favouriteButton = UIButton(type: .system)

    @objc func favouriteTapped() {
        restaurant.isFavourite.toggle()
        updateButton()
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if isMovingFromParent {
            onFavouriteChanged?(restaurant.isFavourite)
        }
    }

    private func updateButton() {
        let symbol = restaurant.isFavourite ? "heart.fill" : "heart"
        favouriteButton.setImage(UIImage(systemName: symbol), for: .normal)
    }
}
```

::: A hint, if you're stuck
- `Restaurant` is a struct. What exactly does `detail.restaurant = restaurants[indexPath.row]`
  hand to the detail screen?
- The callback remembers `indexPath`. What else can change the order of `restaurants` while the
  detail screen is open?
- Count the places that store "is pizza a favourite?". How many are there, and who keeps them equal?
- Where does `isFavourite` come from on a pull-to-refresh?
:::

::: The key — what I expect a senior to find
The data-source methods are left out of the snippet; I'd say out loud that I assume
`cellForRowAt` sets each heart's `tag` and image.

1. **The wrong restaurant gets the heart — or a crash.** QA's bug, and the worst one. The callback
   captured `indexPath` when the row was tapped. If the array changes while the detail is open — a
   background reload, a push or socket update, an iPad split view — row 0 is now another restaurant,
   and that one gets the heart. If the list got shorter, the write is out of range and the app
   crashes. Find the restaurant by `id`, never by position.
2. **`var restaurant: Restaurant!`** — push the detail without setting it and it crashes. Pass it in
   `init`.
3. **One missing field blanks the whole list.** `isFavourite` is a non-optional `Bool` in a
   `Decodable` type. If the API doesn't send it — and why would the server know my local hearts? —
   decoding the array throws `keyNotFound` and the user sees nothing. Take it out of the model.
4. **The detail screen edits a copy.** `Restaurant` is a struct, so the detail gets its own copy.
   Toggling there changes nothing the list can see. The callback papers over it, but only on "back".
5. **Changes flow back only one way, and only sometimes.** `onFavouriteChanged` fires in
   `viewWillDisappear` when popping. Push another screen from the detail and the list stays stale.
   Open the same detail from search or a deep link and there's no callback at all.
6. **A refresh wipes favourites.** `reload(with:)` replaces the array with the server's copy, which
   knows nothing about local taps. That's QA's "doesn't stick".
7. **Nothing is persisted.** Relaunch and every favourite is gone.
8. **The detail opens with the wrong heart.** `updateButton()` only runs after a tap, so a favourite
   shows an empty heart until you tap it — which then un-favourites it.
9. **The detail's heart can't be tapped.** `favouriteButton` is never added to the view and never
   gets a target. Maybe that's elided; I'd ask, because as written it does nothing.
10. **`sender.tag` as a row index.** The same stale-position bug as 1, for the list's own button, and
    it breaks the moment there's a second section. Ask the table which row the button is in.
11. **N sources of truth.** Every copy of a `Restaurant` holds its own `isFavourite`, and server data
    is mixed with user state. The fix isn't more syncing code; it's one owner, keyed by `id`.
12. **No accessibility label on the heart.** VoiceOver reads "heart, button" and never says whether
    it's on.
13. **Ties follow the server's order.** Swift's `sort` is stable, so equal ratings keep the order they
    arrived in — and after a refresh that order can change, so rows swap. Add a tie-breaker (name,
    then `id`) if the order should hold still.
14. **`rating` is `var` for no reason.** Server data the app never edits should be `let`.
15. **Not a bug: `self` in the `didSelectRowAt` closure.** The detail holds the closure, the
    navigation stack holds the detail, and the list holds neither — so there's no cycle, and it
    goes away on pop. Saying "this is fine, and here's why" scores too.
:::

::: The idea behind it
Swift has two kinds of types. A *value type* (a `struct` or `enum`) is copied when you assign or
pass it: you get your own photocopy, and writing on it doesn't change the original. A *reference
type* (a `class`) is shared: assigning it hands over another pointer to the *same* object, so a
change made through one pointer is seen through all of them.

Value types are great for data that doesn't change underneath you — a restaurant's name and rating.
Nobody can edit your copy behind your back. But "is this a favourite?" is state that two screens must
*share*. Copy it into each screen and you've made two answers to one question, and now something
must keep them equal. That something is the buggy callback.

The fix is a *single source of truth*: one object owns the answer, and everyone else asks it when
they draw. It's a reference type, so both screens hold the same one. It's keyed by `id`, so the
order of any list doesn't matter. And it saves on every change, so a relaunch reads the same answer.

Think of a shared calendar versus everyone writing the meeting time on a sticky note. Move the
meeting and the sticky notes are all wrong. The calendar just shows the new time.
:::

::: The fix
```swift
struct Restaurant: Decodable {
    let id: String
    let name: String
    let rating: Double                                   // key 3, 11, 14: no isFavourite
}

/// The one place that knows what is a favourite. Both screens ask it.
@MainActor
final class FavouritesStore {                            // key 4–7, 11
    private let defaults: UserDefaults
    private let key = "favourites.restaurantIDs"
    private var ids: Set<String>

    init(defaults: UserDefaults) {
        self.defaults = defaults
        ids = Set(defaults.stringArray(forKey: key) ?? [])
    }

    func isFavourite(_ id: String) -> Bool { ids.contains(id) }

    func toggle(_ id: String) {
        if ids.remove(id) == nil { ids.insert(id) }
        defaults.set(ids.sorted(), forKey: key)          // key 7: saved on every tap
    }
}

final class RestaurantListViewController: UITableViewController {
    var restaurants: [Restaurant] = []
    private let favourites: FavouritesStore

    init(favourites: FavouritesStore) {
        self.favourites = favourites
        super.init(style: .plain)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    override func viewWillAppear(_ animated: Bool) {     // key 5: redraw hearts on the way back
        super.viewWillAppear(animated)
        tableView.reloadRows(at: tableView.indexPathsForVisibleRows ?? [], with: .none)
    }

    // sortByRating() and reload(with:) unchanged

    @objc func favouriteTapped(_ sender: UIButton) {     // key 10: the row under the button, now
        let point = sender.convert(CGPoint.zero, to: tableView)
        guard let indexPath = tableView.indexPathForRow(at: point) else { return }
        favourites.toggle(restaurants[indexPath.row].id)
        tableView.reloadRows(at: [indexPath], with: .none)
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        let detail = RestaurantDetailViewController(      // key 1, 4: no index, no callback
            restaurant: restaurants[indexPath.row], favourites: favourites)
        navigationController?.pushViewController(detail, animated: true)
    }
}

final class RestaurantDetailViewController: UIViewController {
    private let restaurant: Restaurant                   // key 2: no `!`
    private let favourites: FavouritesStore
    private let favouriteButton = UIButton(type: .system)

    init(restaurant: Restaurant, favourites: FavouritesStore) {
        self.restaurant = restaurant
        self.favourites = favourites
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    override func viewDidLoad() {
        super.viewDidLoad()
        favouriteButton.addTarget(self, action: #selector(favouriteTapped), for: .touchUpInside)
        view.addSubview(favouriteButton)                 // key 9 (layout left out)
        updateButton()                                   // key 8: the right heart on open
    }

    @objc func favouriteTapped() {
        favourites.toggle(restaurant.id)
        updateButton()
    }

    private func updateButton() {
        let isFavourite = favourites.isFavourite(restaurant.id)
        favouriteButton.setImage(UIImage(systemName: isFavourite ? "heart.fill" : "heart"), for: .normal)
        favouriteButton.accessibilityLabel = isFavourite ? "Remove from favourites" : "Add to favourites"
    }
}
```

**Said out loud, not coded:** make the store `@Observable` (or give it a small observer list) so
an iPad split view updates live · move both screens to SwiftUI with a `NavigationStack` · a
tie-breaker in `sortByRating()` · sync favourites with the server later.

- **Why a class keyed by `id`.** Both screens hold the same object, so there's nothing to copy back
  and no position to go stale. A refresh can replace every restaurant and no heart moves.
- **Why `UserDefaults` is injected.** The app passes `.standard`; the tests pass a private suite.
  That's the only seam, and the tests need nothing more.
- **Why `viewWillAppear` and not a callback.** However the user got to the detail and back — pop,
  search, deep link — the list redraws its visible hearts from the store when it reappears.
- **Why `@MainActor` on the store.** It's UI state, touched from taps, and being on main lets it
  hold `UserDefaults`, which isn't `Sendable`.
:::

::: Now write the tests
> "Good. Now write me a few tests for the store — the ones you'd want before merging."

**What I'd test, and why**

1. **Favourites survive a relaunch** — QA's "gone after a relaunch". A second store built on the
   same defaults is what a relaunch looks like.
2. **Toggle turns a favourite on, then off** — the edge case: the second tap must remove it, on disk
   too.
3. **A toggle is saved straight away** — the regression guard. The old code only "saved" on the back
   button; nothing may wait for a later event again.

I use a real `UserDefaults`, not a fake: it's fast and local. Each test gets its own suite name, so
it never touches the app's defaults, and deletes it at the end. The view controllers hold no logic
worth a unit test now; they ask the store.

```swift
import Foundation
import Testing

@MainActor
struct FavouritesStoreTests {
    /// Real UserDefaults, but a private suite: not the app's, and deleted afterwards.
    private func makeDefaults() throws -> (UserDefaults, String) {
        let suite = "FavouritesStoreTests.\(UUID().uuidString)"
        return (try #require(UserDefaults(suiteName: suite)), suite)
    }

    @Test func favouritesSurviveARelaunch() throws {
        let (defaults, suite) = try makeDefaults()
        defer { defaults.removePersistentDomain(forName: suite) }

        FavouritesStore(defaults: defaults).toggle("pizza")
        let relaunched = FavouritesStore(defaults: defaults)     // a new store = a relaunch

        #expect(relaunched.isFavourite("pizza"))
        #expect(!relaunched.isFavourite("sushi"))
    }

    @Test func toggleTurnsAFavouriteOnAndOff() throws {
        let (defaults, suite) = try makeDefaults()
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = FavouritesStore(defaults: defaults)

        store.toggle("pizza")
        #expect(store.isFavourite("pizza"))

        store.toggle("pizza")
        #expect(!store.isFavourite("pizza"))
        #expect(!FavouritesStore(defaults: defaults).isFavourite("pizza"))
    }

    @Test func toggleSavesStraightAway() throws {
        let (defaults, suite) = try makeDefaults()
        defer { defaults.removePersistentDomain(forName: suite) }

        let store = FavouritesStore(defaults: defaults)
        store.toggle("sushi")
        store.toggle("pizza")

        // No "back" or "background" event happened — it's already on disk.
        #expect(defaults.stringArray(forKey: "favourites.restaurantIDs") == ["pizza", "sushi"])
    }
}
```

Ran on the iOS Simulator (Swift 6 mode): 3 tests, all passed.
:::

::: What I'd ask next
- *"On iPad both screens are visible at once. Make the list update live."* — Make the store
  `@Observable` and read `isFavourite` in the cell's `updateProperties()`; on iOS 26 UIKit tracks
  that read and redraws the cell when it changes. On older UIKit, give the store a small observer list or post a typed
  notification, and have the list reload the changed row.
- *"Now move it to SwiftUI."* — The store becomes `@Observable`, both views read
  `isFavourite(id)` in `body`, and the heart redraws everywhere with no extra code. Inject it with
  `.environment(store)` at the root, or as an `init` parameter.
- *"Favourites must sync with the server."* — Keep the store as the truth the UI reads. Toggle
  optimistically, send the change, and roll back with a message if it fails. On launch, merge server
  and local sets, and decide the conflict rule (last write wins, with a timestamp per id).
- *"Is `UserDefaults` the right place?"* — For a few hundred ids, yes: small, local, not sensitive.
  Thousands, or records with more fields, move to a file or SwiftData.
- *"Why not make `Restaurant` a class so the copy problem goes away?"* — Then every screen can change
  server data behind every other screen's back. Keep data as values; put shared, changing state in
  one deliberate reference.
:::
