---
title: 26 · The search that shows old results
summary: A Combine search pipeline that shows results for what you typed a second ago, stops working after one network error, and never deallocates — find all of it.
minutes: 20
group: Find the bug
sources:
- Apple · switchToLatest() — republishes elements sent by the most recently received publisher | https://developer.apple.com/documentation/combine/publisher/switchtolatest()-453ht
- Apple · debounce(for:scheduler:options:) | https://developer.apple.com/documentation/combine/publisher/debounce(for:scheduler:options:)
- Apple · removeDuplicates() | https://developer.apple.com/documentation/combine/publisher/removeduplicates()
- Apple · receive(on:options:) — the scheduler that delivers elements downstream | https://developer.apple.com/documentation/combine/publisher/receive(on:options:)
- Apple · assign(to:on:) versus assign(to:) — who owns the subscription | https://developer.apple.com/documentation/combine/publisher/assign(to:)
- Apple · AnyCancellable — cancels its subscription when deallocated | https://developer.apple.com/documentation/combine/anycancellable
- Apple · Receiving and handling events with Combine — a debounced text field | https://developer.apple.com/documentation/combine/receiving-and-handling-events-with-combine
---

*Shape: find the bug · Reported: a common senior-round topic; no specific company report found ·
Verified: the snippet compiles cleanly in Swift 6 mode; the stale result, the dead pipeline and the
leak were reproduced with a fake search, and the fix's tests ran with Swift 6.4*

> "Movie search. QA has three tickets. Type 'star' quickly and you sometimes get the results for
> 'st'. After the Wi-Fi drops once, search does nothing until you restart the app. And the
> Memory Graph shows every search screen ever opened. Here's the view model. Find out why — and
> anything else you'd change."

```swift
import Combine
import Foundation

struct Movie: Decodable, Equatable {
    let id: Int
    let title: String
}

final class MovieSearchService: Sendable {
    static let shared = MovieSearchService()

    func search(_ query: String) -> AnyPublisher<[Movie], Error> {
        let url = URL(string: "https://api.example.com/search?q=\(query)")!
        return URLSession.shared.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: [Movie].self, decoder: JSONDecoder())
            .eraseToAnyPublisher()
    }
}

final class SearchViewModel: ObservableObject {
    @Published var query = ""
    @Published private(set) var results: [Movie] = []
    @Published private(set) var recentQueries: [String] = []
    private var cancellables = Set<AnyCancellable>()

    init() {
        $query
            .flatMap { query in
                MovieSearchService.shared.search(query)
            }
            .replaceError(with: [])
            .assign(to: \.results, on: self)
            .store(in: &cancellables)

        _ = $query
            .filter { $0.count > 2 }
            .sink { query in
                self.recentQueries.append(query)
            }
    }
}
```

It compiles in Swift 6 mode with no warnings (checked). The compiler checks data races between
actors; it doesn't look inside Combine closures, so none of these bugs show up.

::: A hint, if you're stuck
- Type "s", "st", "sta", "star". How many searches start? Which one wins if "st" is the slowest?
- `replaceError(with:)` replaces the error — and then what does the publisher do?
- Who holds `self` in `assign(to:on:)`, and who holds that?
- What happens to the value a `sink` returns when nobody keeps it?
:::

::: How I'd debug it
- **Stale results.** Put `.print("search")` after `flatMap` and turn on the Network Link Conditioner
  ("Very bad network"). The log shows two searches in flight and both delivering — the slow one last.
- **Dead after an error.** The same `.print` shows `receive finished` right after the first
  failure. A finished subscription never wakes up again.
- **The leak.** Open and close the screen, then Debug Memory Graph. Select a `SearchViewModel`:
  the graph runs from `cancellables` to an `Assign` subscriber and back to the view model.
- **The missing history.** A breakpoint in the `recentQueries` closure is never hit.
:::

::: The key — what I expect a senior to find
1. **Results for an old query (the reported bug).** `flatMap` starts a new search for every query
   and keeps *all* of them running, forwarding whatever comes back. If "st" answers after "star",
   the screen shows "st". Use `map` to turn each query into a search, then `switchToLatest()`,
   which cancels the previous search when a new one starts.
2. **One error ends search for good.** `replaceError(with: [])` sits on the outer pipeline. On the
   first failure it sends `[]` and then *finishes*. A finished pipeline never runs again, so typing
   does nothing until the screen is rebuilt. I checked: after one failure, no new search was
   started. Catch the error *inside* each search, so it ends that search, not the pipeline.
3. **`@Published` written off the main thread.** `dataTaskPublisher` delivers on URLSession's
   queue, so `results` changes on a background thread. SwiftUI warns "Publishing changes from
   background threads is not allowed", and it's a data race. Add `.receive(on: DispatchQueue.main)`
   after the search.
4. **`assign(to:on: self)` leaks the view model.** It holds `self` strongly, and the subscription
   is stored in `self.cancellables`: a loop. I checked: the view model's `deinit` never ran, even
   after the pipeline had finished. Use `assign(to: &$results)`, which ties the subscription to
   the property, or `sink` with `[weak self]`.
5. **The history subscription dies at once.** `sink` returns an `AnyCancellable`, and an
   `AnyCancellable` cancels its subscription when it's freed. `_ =` frees it on that line, so
   `recentQueries` never changes. Store it — with `[weak self]`, or storing it creates a second loop.
6. **A failure looks like "no results".** `replaceError(with: [])` turns "the network is down" into
   an empty list. The user thinks the movie doesn't exist. Keep an error state.
7. **A request for every keystroke.** No `debounce`, so "star" is four requests. Wait for a pause
   in typing (`debounce(for: .milliseconds(300), scheduler: DispatchQueue.main)`).
8. **No `removeDuplicates()`.** Type "star", add an "s", delete it: the same query is searched
   again.
9. **It searches for nothing.** `$query` sends its current value, `""`, as soon as you subscribe,
   so the screen searches for the empty string on open. Skip queries that are too short.
10. **The query isn't escaped.** `"rock & roll"` pasted into the URL ends the `q` parameter at
    `&`. Build the URL with `URLComponents` and a `URLQueryItem`.
11. **A singleton inside the view model.** `MovieSearchService.shared` can't be replaced, so none
    of this can be tested without the network. Inject it.
12. **The history records keystrokes.** "sta", "star", "stars" are three entries, and the array
    never stops growing. Record a query when the user commits it, and cap the list.
:::

::: The idea behind it
Combine is a pipe. A *publisher* sends values over time; *operators* sit in the pipe and change
them; a *subscriber* at the end does something with each one. Three things about the pipe explain
every bug here.

**Turning one value into a stream.** A search box sends text; each text needs its own network
request, which is a publisher of its own. So you have a publisher of publishers. `flatMap`
subscribes to *every* inner publisher and merges their outputs, so all searches race and the
slowest one wins. `map` + `switchToLatest()` keeps only the newest inner publisher and cancels the
rest. For a search box you always want the newest.

**Errors end the pipe.** A publisher can send many values, but only one *completion*: `finished`
or `failure`. After that it's done, forever. So an error that reaches the outer pipe kills the
whole search screen. Errors you can recover from must be handled inside the inner publisher, where
ending is fine, because the next query makes a new one.

**A subscription lives as long as its `AnyCancellable`.** Keep the cancellable and the pipe stays
open; drop it and the pipe closes. That's why `_ =` does nothing, and why storing a pipe that holds
`self` in `self` is a retain cycle: the view model keeps the pipe, the pipe keeps the view model.

Think of a radio with one dial. `flatMap` plays every station you tuned past, all at once.
`switchToLatest` plays only the one you stopped on.
:::

::: The fix
```swift
protocol MovieSearching {                                           // the seam
    func search(_ query: String) -> AnyPublisher<[Movie], Error>
}

extension MovieSearchService: MovieSearching {}
// In search(_:): URLComponents + URLQueryItem(name: "q", value: query)   // key 10

final class SearchViewModel: ObservableObject {
    @Published var query = ""
    @Published private(set) var results: [Movie] = []
    @Published private(set) var errorMessage: String?                // key 6
    @Published private(set) var recentQueries: [String] = []
    private var cancellables = Set<AnyCancellable>()

    init(service: MovieSearching = MovieSearchService.shared,         // key 11
         debounce: DispatchQueue.SchedulerTimeType.Stride = .milliseconds(300)) {
        $query
            .debounce(for: debounce, scheduler: DispatchQueue.main)     // key 7
            .removeDuplicates()                                         // key 8
            .map { query -> AnyPublisher<[Movie]?, Never> in
                guard query.count > 1 else {                            // key 9
                    return Just([]).eraseToAnyPublisher()
                }
                return service.search(query)
                    .map(Optional.some)
                    .replaceError(with: nil)                            // key 2: ends this search only
                    .eraseToAnyPublisher()
            }
            .switchToLatest()                                           // key 1
            .receive(on: DispatchQueue.main)                            // key 3
            .sink { [weak self] movies in                               // key 4
                self?.results = movies ?? []
                self?.errorMessage = movies == nil ? "Search failed. Try again." : nil
            }
            .store(in: &cancellables)

        $query
            .filter { $0.count > 2 }
            .sink { [weak self] query in
                self?.recentQueries.append(query)
            }
            .store(in: &cancellables)                                   // key 5
    }
}
```

**Said out loud, not coded:** record history on submit and cap it (key 12); localize the error
string; cache results per query; on iOS 17+, an `@Observable` model with `.task(id: query)` and
`Task.sleep` for the debounce, which cancels the old search for free; a typed error to tell
"offline" from "server down".

Why each piece:

- **The error is caught *before* `switchToLatest`.** Inside, it ends one search; outside, it ended
  the screen. Order is the whole fix for key 2.
- **`nil` means "this search failed".** The smallest way to carry a failure past
  `switchToLatest` without a new type. A `Result` works too.
- **`receive(on:)` after `switchToLatest`, not before.** The network replies on its own queue
  whatever thread you subscribed on; the hop has to come after the reply.
- **`debounce` is an init parameter.** The tests pass `.zero`, so they never wait on a clock.
:::

::: Now write the tests
> "Good. Now prove it. Start with the stale result QA reported."

**What I'd test, and why**

1. **A late reply for an old query is ignored** — the reported bug. "st" is still in flight when
   the user types "star"; "star" answers, then "st" answers late. The screen must still show "star".
2. **Search still works after a failure** — the error ends one search, the next query searches again,
   and the error message clears.
3. **Fast typing sends one request** — `debounce` and `removeDuplicates`, together. Typing the same
   text again sends nothing.
4. **The view model is released** — the retain cycle from `assign(to:on:)`.

I wouldn't test `URLSession` or the decoder here; they belong to the service's own tests.

**The seam.** The view model takes a `MovieSearching`. The fake gives every query its own
`PassthroughSubject` — a publisher the test sends values through by hand — so the test decides
which reply arrives, and in what order. With `debounce: .zero` everything runs on the main queue,
and `waitUntil(maxYields:_:)` gives the main queue turns until the condition holds: a bounded
count of yields, never a clock.

```swift
import Combine
import Foundation
import Testing

/// A fake search: each query gets its own subject, so the test decides
/// which reply arrives, and in what order. No network, no clock.
final class FakeMovieSearch: MovieSearching {
    private(set) var queries: [String] = []
    private var replies: [String: PassthroughSubject<[Movie], Error>] = [:]

    func search(_ query: String) -> AnyPublisher<[Movie], Error> {
        queries.append(query)
        let subject = PassthroughSubject<[Movie], Error>()
        replies[query] = subject
        return subject.eraseToAnyPublisher()
    }

    func reply(to query: String, with movies: [Movie]) { replies[query]?.send(movies) }
    func fail(_ query: String) { replies[query]?.send(completion: .failure(URLError(.timedOut))) }
}

/// Gives the main queue turns until `condition` holds. Bounded by a count, not a clock.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () -> Bool) async -> Bool {
    for _ in 0..<maxYields {
        if condition() { return true }
        await Task.yield()
    }
    return condition()
}

@MainActor
struct SearchViewModelTests {
    let star = [Movie(id: 1, title: "Star Wars")]
    let st = [Movie(id: 2, title: "Stalker")]

    @Test func lateReplyForAnOldQueryIsIgnored() async {
        // Given a search for "st" still in flight when the user types "star"
        let search = FakeMovieSearch()
        let viewModel = SearchViewModel(service: search, debounce: .zero)
        viewModel.query = "st"
        #expect(await waitUntil { search.queries == ["st"] })
        viewModel.query = "star"
        #expect(await waitUntil { search.queries == ["st", "star"] })

        // When "star" answers first, and "st" answers late
        search.reply(to: "star", with: star)
        #expect(await waitUntil { viewModel.results == star })
        search.reply(to: "st", with: st)
        _ = await waitUntil(maxYields: 100) { false }       // let a late reply land, if it can

        // Then the screen still shows "star"
        #expect(viewModel.results == star)
    }

    @Test func searchStillWorksAfterAFailure() async {
        let search = FakeMovieSearch()
        let viewModel = SearchViewModel(service: search, debounce: .zero)
        viewModel.query = "st"
        #expect(await waitUntil { search.queries == ["st"] })

        search.fail("st")
        #expect(await waitUntil { viewModel.errorMessage != nil })

        viewModel.query = "star"
        #expect(await waitUntil { search.queries == ["st", "star"] })
        search.reply(to: "star", with: star)
        #expect(await waitUntil { viewModel.results == star })
        #expect(viewModel.errorMessage == nil)
    }

    @Test func fastTypingSendsOneRequest() async {
        let search = FakeMovieSearch()
        let viewModel = SearchViewModel(service: search, debounce: .zero)

        for text in ["s", "st", "sta", "star"] { viewModel.query = text }
        #expect(await waitUntil { search.queries == ["star"] })
        viewModel.query = "star"                            // the same text again
        _ = await waitUntil(maxYields: 100) { false }

        #expect(search.queries == ["star"])
    }

    @Test func viewModelIsReleased() async {
        let search = FakeMovieSearch()
        weak var weakViewModel: SearchViewModel?
        do {
            let viewModel = SearchViewModel(service: search, debounce: .zero)
            viewModel.query = "star"
            weakViewModel = viewModel
            #expect(await waitUntil { search.queries == ["star"] })
        }
        #expect(weakViewModel == nil)
    }
}
```

Ran with Swift 6.4: 4 tests, all passed.
:::

::: What I'd ask next
- *"Why does `debounce: .zero` still coalesce the four keystrokes in the test?"* — Each new value
  cancels the pending one and schedules itself on the main queue. The four assignments happen in one
  go, before the main queue gets a turn, so only "star" survives.
- *"`debounce` or `throttle`?"* — `debounce` waits for a pause, which suits a search box.
  `throttle` sends at most one value per interval *while* typing continues — better for something
  like a live scroll position.
- *"`receive(on:)` or `subscribe(on:)`?"* — `subscribe(on:)` moves the *start* of the work.
  `receive(on:)` moves where values are *delivered*, which is what the UI needs.
- *"How would you write this without Combine?"* — In SwiftUI, `.task(id: query)` starts a task per
  query and cancels the old one when `query` changes. `try await Task.sleep(for: .milliseconds(300))`
  at the top is the debounce; the cancelled task throws out of the sleep, so no request is sent.
- *"Does `assign(to: &$results)` leak?"* — No. It stores no `AnyCancellable`: the subscription
  belongs to the `@Published` property and ends when the object is freed, which Apple's docs state.
:::
