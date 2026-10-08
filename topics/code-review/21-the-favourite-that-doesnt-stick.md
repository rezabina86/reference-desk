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
mirrored version on the first screen… all synchronized" · UIKit snippet typechecks cleanly against
the iOS SDK (iOS 18 target) in both Swift 5 and Swift 6 mode (the bugs are logic, not compiler-visible). The fix:
SwiftUI views typecheck against the iOS SDK (iOS 18 target) in Swift 6 mode with zero warnings; the store and its
persistence were compiled and run with Swift 6.4 in a harness; on-screen behaviour checked by hand*

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
1. **The wrong restaurant gets the heart.** The callback captured `indexPath` when the row was
   tapped. If the list re-sorts or refreshes while the detail is open, row 0 is now a different
   restaurant, and that one is changed. If the list got shorter, it's an out-of-range crash. A
   two-line simulation of "copy, toggle, re-sort, write back by index" printed
   `["sushi=true", "pizza=false"]` — sushi got pizza's heart. Identify by `id`, never by position.
2. **The detail screen edits a copy.** `Restaurant` is a struct, so the detail gets its own copy.
   Toggling there changes nothing the list can see. The callback papers over it — but only on the
   back button.
3. **Changes flow back only one way, and only sometimes.** `onFavouriteChanged` fires in
   `viewWillDisappear` when popping. Push a menu screen from the detail and the list stays stale;
   open the same detail from search or a deep link and there's no callback at all, so the change is
   simply lost. On iPad in a split view both screens are visible and visibly disagree.
4. **A refresh wipes favourites.** `reload(with:)` replaces the array with the server's copy, and
   its `isFavourite` knows nothing about local taps. That's QA's "doesn't stick".
5. **Nothing is persisted.** Relaunch and every favourite is gone.
6. **Two — really, N — sources of truth.** Every copy of a `Restaurant` holds its own
   `isFavourite`. The fix isn't more syncing code; it's one owner.
7. **The detail opens with the wrong heart.** `updateButton()` only runs after a tap, so a
   favourited restaurant shows an empty heart until you tap it — which then un-favourites it.
8. **`sender.tag` as a row index.** Same stale-position bug as 1 for the list's own button, and it
   breaks the moment there's a second section.
9. **`var restaurant: Restaurant!`** — push the screen without setting it and it crashes. Pass it in
   `init`.
10. **Server data and user state in one model.** Name and rating come from the API; "my favourite"
    is the user's. Keep them apart, keyed by `id`.
11. **No accessibility label on the heart** — VoiceOver reads "heart, button" and never says whether
    it's on.
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

The fix is a *single source of truth*: one object owns the answer, everyone else asks it. It's a
reference type, so both screens hold the same one. It's *observable* — screens get told when it
changes, so they redraw without being called. And it's keyed by `id`, so the order of any list
doesn't matter.

Think of a shared calendar versus everyone writing the meeting time on a sticky note. Move the
meeting and the sticky notes are all wrong. The calendar just shows the new time.
:::

::: The version I'd ship
The store — the only place that knows what is a favourite:

```swift
import Foundation
import Observation

struct Restaurant: Identifiable, Hashable, Sendable, Decodable {
    let id: String
    let name: String
    let rating: Double
}

protocol FavoritesPersisting {      // used only from the main-actor store
    func load() -> Set<Restaurant.ID>
    func save(_ ids: Set<Restaurant.ID>)
}

struct UserDefaultsFavoritesPersistence: FavoritesPersisting {
    private let defaults: UserDefaults
    private let key = "favorites.restaurantIDs"

    init(defaults: UserDefaults) { self.defaults = defaults }

    func load() -> Set<Restaurant.ID> { Set(defaults.stringArray(forKey: key) ?? []) }
    func save(_ ids: Set<Restaurant.ID>) { defaults.set(ids.sorted(), forKey: key) }
}

/// The one place that knows what is a favourite. Both screens read and write it.
@MainActor
@Observable
final class FavoritesStore {
    private(set) var ids: Set<Restaurant.ID>
    @ObservationIgnored private let persistence: FavoritesPersisting

    init(persistence: FavoritesPersisting) {
        self.persistence = persistence
        self.ids = persistence.load()
    }

    func isFavorite(_ id: Restaurant.ID) -> Bool { ids.contains(id) }

    func toggle(_ id: Restaurant.ID) {
        if ids.remove(id) == nil { ids.insert(id) }
        persistence.save(ids)
    }
}
```

The screens — both get the same store:

```swift
import SwiftUI

struct RestaurantListView: View {
    let restaurants: [Restaurant]
    let favorites: FavoritesStore

    var body: some View {
        NavigationStack {
            List(restaurants) { restaurant in
                NavigationLink(value: restaurant) {
                    HStack {
                        Text(restaurant.name)
                        Spacer()
                        FavoriteButton(id: restaurant.id, favorites: favorites)
                    }
                }
            }
            .navigationTitle("Restaurants")
            .navigationDestination(for: Restaurant.self) { restaurant in
                RestaurantDetailView(restaurant: restaurant, favorites: favorites)
            }
        }
    }
}

struct RestaurantDetailView: View {
    let restaurant: Restaurant          // a copy is fine: nothing here changes
    let favorites: FavoritesStore       // the shared, changing part is a reference

    var body: some View {
        VStack(spacing: 16) {
            Text(restaurant.name).font(.largeTitle)
            FavoriteButton(id: restaurant.id, favorites: favorites)
                .font(.title)
        }
        .navigationTitle(restaurant.name)
    }
}

struct FavoriteButton: View {
    let id: Restaurant.ID
    let favorites: FavoritesStore

    var body: some View {
        let isFavorite = favorites.isFavorite(id)       // read in body → tracked
        Button {
            favorites.toggle(id)
        } label: {
            Image(systemName: isFavorite ? "heart.fill" : "heart")
        }
        .buttonStyle(.borderless)                        // tap the heart, not the row
        .accessibilityLabel(isFavorite ? "Remove from favourites" : "Add to favourites")
    }
}
```

What the store harness printed (an in-memory persistence fake, two functions standing in for the
list row and the detail, `withObservationTracking` standing in for SwiftUI):

```text
list row told to redraw
list:   pizza ♥
detail: pizza ♥
ids: ["pizza", "sushi"]
after relaunch: ["pizza", "sushi"]
toggle off: ["sushi"] saved: ["sushi"]
UserDefaults round trip: ["ramen"]
```

A toggle from the "detail" told the "list row" to redraw, and both read the same answer. A new store
built from the same persistence — a relaunch — came back with the same favourites, through a real
`UserDefaults` suite too.

Why each piece:

- **One `FavoritesStore`, keyed by `id`** — the single source of truth. Sorting, refreshing or opening
  the detail from a deep link can't desync it, because nothing holds a copy of the answer.
- **`@Observable`, not a delegate, closure or notification** — a *delegate* is one-to-one, and here
  any number of screens care. A closure is what broke: it captured a position. `NotificationCenter`
  works for many listeners but is stringly typed and every screen must remember to subscribe and
  reload. With `@Observable`, a view that *reads* `isFavorite(id)` in `body` is redrawn when `ids`
  changes — nothing to forget. (UIKit on iOS 26 also tracks `@Observable` reads made in
  `layoutSubviews()` or `updateProperties()`; on older UIKit I'd give the store a small typed
  observer list or a Combine publisher, for the same reason.)
- **`Restaurant` loses `isFavourite`** — server data stays a plain, immutable value. A refresh can
  replace every restaurant and no heart moves.
- **`@MainActor` on the store** — UI state, written from taps, read in `body`. Being on main also
  lets it hold `UserDefaults`, which isn't `Sendable`.
- **Persistence behind a protocol** — the store doesn't know about `UserDefaults`; the test injects
  an in-memory fake, and switching to a file or SwiftData later touches one type.
- **`.buttonStyle(.borderless)`** — inside a `List` row, a default-styled button makes the whole
  row its tap target; borderless keeps the heart tap separate from the navigation.
:::

::: Now write the tests
> "Good. Now write me a few tests for the store — the ones you'd want before merging."

What I'd test, and why:

1. **A refresh doesn't move a heart.** The list comes back in a new order, with new data and a new
   restaurant. The heart must stay on pizza and only pizza. That's QA's "wrong restaurant gets the
   heart", and keying by `id` is what fixes it.
2. **Toggle turns a favourite on, then off.** The basic contract.
3. **A toggle is saved straight away**, not on some later "back" or "background" event.
4. **Favourites survive a relaunch.** A new store built from the same persistence reads them back.
   That's the "gone after a relaunch" bug.
5. **A toggle tells readers to redraw.** This is how the list hears about a tap on the detail
   screen. `withObservationTracking` does in a test what SwiftUI does in `body`: it records what was
   read and calls back when it changes.
6. **The real `UserDefaults` persistence round-trips.** One test against the real thing.

I wouldn't unit-test the views: they hold no logic, they just read the store. Whether the heart
looks right is a job for a preview.

**The seam.** The store takes `FavoritesPersisting` in `init`, so the tests pass a *fake* — a tiny
in-memory stand-in that remembers what was "saved". No disk, nothing left behind, same result every
run. For the last test a real `UserDefaults` is fine: it's fast and local. I give it its own suite
name, so it never touches the app's real defaults, and delete it at the end.

```swift
import Foundation
import Observation
import Testing

// A fake: keeps the "saved" ids in memory instead of on disk.
final class InMemoryFavorites: FavoritesPersisting {
    var stored: Set<Restaurant.ID> = []
    func load() -> Set<Restaurant.ID> { stored }
    func save(_ ids: Set<Restaurant.ID>) { stored = ids }
}

@MainActor
struct FavoritesStoreTests {
    @Test func refreshDoesNotMoveTheHeart() {
        // Given pizza is a favourite
        let store = FavoritesStore(persistence: InMemoryFavorites())
        store.toggle("pizza")

        // When a refresh brings the list back in a new order, with new data
        let refreshed = [
            Restaurant(id: "sushi", name: "Sushi", rating: 4.8),
            Restaurant(id: "ramen", name: "Ramen", rating: 4.5),
            Restaurant(id: "pizza", name: "Pizza", rating: 4.1),
        ]

        // Then the heart is still on pizza, and only on pizza
        #expect(refreshed.filter { store.isFavorite($0.id) }.map(\.name) == ["Pizza"])
    }

    @Test func toggleTurnsAFavouriteOnAndOff() {
        let store = FavoritesStore(persistence: InMemoryFavorites())

        store.toggle("pizza")
        #expect(store.isFavorite("pizza"))

        store.toggle("pizza")
        #expect(!store.isFavorite("pizza"))
    }

    @Test func toggleSavesStraightAway() {
        let persistence = InMemoryFavorites()
        let store = FavoritesStore(persistence: persistence)

        store.toggle("pizza")
        store.toggle("sushi")

        #expect(persistence.stored == ["pizza", "sushi"])
    }

    @Test func favouritesSurviveARelaunch() {
        // Given favourites saved by one store
        let persistence = InMemoryFavorites()
        FavoritesStore(persistence: persistence).toggle("pizza")

        // When the app relaunches and builds a new store
        let relaunched = FavoritesStore(persistence: persistence)

        // Then it reads them back
        #expect(relaunched.ids == ["pizza"])
    }

    @Test func toggleTellsReadersToRedraw() async {
        // Given a "list row" that has read pizza's heart
        let store = FavoritesStore(persistence: InMemoryFavorites())

        // When the "detail screen" toggles it, the row is told to redraw
        await confirmation { redraw in
            withObservationTracking {
                _ = store.isFavorite("pizza")
            } onChange: {
                redraw()
            }
            store.toggle("pizza")
        }
    }

    @Test func userDefaultsPersistenceRoundTrips() throws {
        // A private suite: real UserDefaults, but not the app's own, and deleted afterwards.
        let suite = "FavoritesStoreTests.\(UUID().uuidString)"
        let defaults = try #require(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }

        FavoritesStore(persistence: UserDefaultsFavoritesPersistence(defaults: defaults)).toggle("ramen")
        let relaunched = FavoritesStore(persistence: UserDefaultsFavoritesPersistence(defaults: defaults))

        #expect(relaunched.ids == ["ramen"])
    }
}
```

Ran with Swift 6.4: 6 tests, all passed.
:::

::: What I'd ask next
- *"How would the views get the store without passing it everywhere?"* — `.environment(store)` at
  the root and `@Environment(FavoritesStore.self) private var favorites` where needed. Fine for an
  app-wide store; explicit init parameters are clearer in a review and easier to preview.
- *"Favourites must sync with the server."* — Keep the store as the truth the UI reads. Toggle
  optimistically, send the change, and roll back with a message if it fails. On launch, merge server
  and local sets; decide the conflict rule (last write wins, with a timestamp per id).
- *"Is `UserDefaults` the right place?"* — For a few hundred ids, yes: it's small, local, and not
  sensitive. Thousands, or data with more fields, move to a file or SwiftData.
- *"Why not make `Restaurant` a class so the copy problem goes away?"* — Then every screen can mutate
  server data behind every other screen's back, and SwiftUI's diffing gets harder. Keep data as
  values; put shared mutable state in one deliberate reference.
- *"How would you test it?"* — The store with an in-memory persistence fake, as above: toggle, assert
  `ids`, build a second store from the same fake, assert it reloaded. The views hold no logic.
:::
