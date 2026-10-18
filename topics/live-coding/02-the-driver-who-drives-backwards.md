---
title: 02 · The driver who drives backwards
summary: A SwiftUI ride-tracking screen fed by an AsyncStream of driver positions, with an ETA request per position. It doesn't build under Swift 6, freezes when it opens, shows an ETA that jumps back up, never says the driver arrived, and keeps tracking after you leave. Fix it, then add an "almost here" banner and a Cancel ride button, and test both with a fake stream.
minutes: 60
group: Rounds
sources:
- Uber · iOS onsite (2025) — an iOS debugging round on a broken app: async, main thread, races | https://medium.com/@ios-interview/uber-ios-interview-experience-questions-sunnyvale-ca-e0900c806cbb
- Revolut · Android and iOS loop — sequential tasks; concurrency and tests expected | https://ophyai.com/blog/company-guides/revolut-android-ios-interview
- Apple · Task — unstructured tasks, cancellation, and why nobody cancels a task nobody owns | https://developer.apple.com/documentation/swift/task
- Apple · AsyncStream — the continuation, onTermination and makeStream(of:) | https://developer.apple.com/documentation/swift/asyncstream
- Apple · task(priority:_:) — SwiftUI cancels the task when the view disappears | https://developer.apple.com/documentation/swiftui/view/task(name:priority:file:line:_:)
- Apple · Mutex — a Sendable lock for the test fake's counters | https://developer.apple.com/documentation/synchronization/mutex
---

*Shape: A · Fix the broken app — 60 minutes, your Xcode, screen shared, no AI assistant · Reported: Uber's
onsite "iOS debugging" round (a broken app with async bugs, main-thread work and races), with the
fix-then-extend ending and concurrency-heavy tests that Revolut's loop is reported to expect · Verified:
Xcode 27.1, iOS 26 target, Swift 6 language mode with main-actor default isolation and Approachable
Concurrency. The starter fails with the two build errors below, one after the other. On the iPhone 17
simulator I reproduced every runtime bug in the key: the ETA going up while the distance went down, the
screen stuck on "Arriving in 0 sec", and the stream still running after Back, from the service's own log
lines quoted below. For the freeze, I added a scratch watchdog thread that logs when the main thread is
blocked. The fix and the feature build with no warnings. The five tests pass, and the stale-ETA test fails
when the fix is removed.*

**How the hour runs**

| Time | The interviewer says | You're scored on |
|---|---|---|
| 0:00–0:10 | "It doesn't build. Make it build." | Reading region-isolation errors, fixing the cause, not silencing it |
| 0:10–0:30 | "Now use it. Something's wrong. Find it." | Using the console, naming the race, cancellation, the main thread |
| 0:30–0:50 | "Product wants an 'almost here' banner and a Cancel button." | The questions you ask first, state that can't flicker |
| 0:50–1:00 | "Test it. The stream is the hard part." | A fake stream you drive by hand, testing order and cancellation |

> "This is our ride-tracking screen. The service is a local package, so pretend it's the network: it
> streams the driver's position every second, and each position asks the backend for an ETA. People
> say it's flaky. Get it building, then find out why. Talk as you go."

The project is in `LiveCodingLab/Round02-RideTracking`. It's written the way a 2026 project is:
`@Observable` with `@State`, `NavigationStack` with a value link, `AsyncStream`, `.task`, MapKit for
SwiftUI, `Duration` and `Measurement` format styles. The bugs are the ones that survive in modern code.

```swift
// RideService/Sources/RideService/RideService.swift — a package: no default isolation
public struct DriverUpdate: Hashable, Sendable {
    public let sequence: Int            // 1, 2, 3… in the order the server sent them
    public let position: Coordinate
    public let metersAway: Int
    // public init(…)
}
// Coordinate and Ride are public Sendable structs with public inits.

// MARK: - Service
public final class RideService {
    public init() {}

    private var sequence = 0
    private let logger = Logger(subsystem: "RideService", category: "tracking")

    /// Pushes the driver's position once a second until they reach the pickup.
    public func driverUpdates(rideID: String) -> AsyncStream<DriverUpdate> {
        AsyncStream { continuation in
            Task {
                for waypoint in Self.waypoints {
                    try? await Task.sleep(for: .seconds(1))
                    sequence += 1
                    logger.notice("ride \(rideID, privacy: .public) sent update \(self.sequence)")
                    continuation.yield(DriverUpdate(sequence: sequence, position: waypoint.position,
                                                    metersAway: waypoint.metersAway))
                }
                continuation.finish()
            }
        }
    }

    /// Asks the routing backend how long the driver needs from this position.
    public func eta(for update: DriverUpdate) async throws -> Duration {
        logger.notice("eta request for update \(update.sequence)")
        // A real mobile network: every third request is slow.
        let latency: Duration = update.sequence.isMultiple(of: 3) ? .milliseconds(2500) : .milliseconds(300)
        try await Task.sleep(for: latency)
        return .seconds(Self.waypoints[update.sequence - 1].etaSeconds)
    }

    /// The planned route from the driver to the pickup, as the backend sends it.
    public func routeData(rideID: String) async throws -> Data { ... }   // 400 ms, then JSON

    /// Cancels the ride on the server. The driver is told and stops coming.
    public func cancelRide(rideID: String) async throws { ... }          // 600 ms

    // 24 waypoints: the driver starts 2.3 km away (ETA 3 min 55 s) and misses a turn
    // after 13 updates, so distance and ETA really do go up once (1:45 → 2:05 → 2:15).
}

// MARK: - Route decoding
public enum RouteDecoder {
    /// Decodes and smooths the route for drawing. CPU-heavy: about 2 s on an older phone.
    public static func decode(_ data: Data) throws -> [Coordinate] {
        let points = try JSONDecoder().decode([Coordinate].self, from: data)
        Thread.sleep(forTimeInterval: 2)      // stands in for the smoothing work
        return points
    }
}
```

```swift
// RideTracking/RideTracking/RideTrackingViewModel.swift — the target's default isolation is MainActor
import Foundation
import Observation
import RideService

@Observable
final class RideTrackingViewModel {
    let ride: Ride
    var route: [Coordinate] = []
    var driverPosition: Coordinate?
    var metersAway: Int?
    var eta: Duration?

    private let service = RideService()

    init(ride: Ride) {
        self.ride = ride
    }

    func startTracking() async {
        for await update in service.driverUpdates(rideID: ride.id) {
            driverPosition = update.position
            metersAway = update.metersAway
            Task {
                eta = try? await service.eta(for: update)
            }
        }
    }

    // Decoding the route is heavy, so keep it off the main actor.
    nonisolated func loadRoute() async {
        do {
            let data = try await service.routeData(rideID: ride.id)
            route = try RouteDecoder.decode(data)
        } catch {
            print("Route failed: \(error)")
        }
    }
}
```

```swift
// RideTracking/RideTracking/RideTrackingView.swift — pushed from a one-row HomeView
struct RideTrackingView: View {
    @State private var viewModel: RideTrackingViewModel

    init(ride: Ride) {
        _viewModel = State(initialValue: RideTrackingViewModel(ride: ride))
    }

    var body: some View {
        VStack(spacing: 0) {
            Map(initialPosition: ...) {
                MapPolyline(coordinates: viewModel.route.map(\.location))
                    .stroke(.blue, lineWidth: 4)
                Marker("Pickup", systemImage: "figure.wave", coordinate: viewModel.ride.pickup.location)
                if let driver = viewModel.driverPosition {
                    Annotation(viewModel.ride.driverName, coordinate: driver.location) { /* car.fill */ }
                }
            }

            VStack(alignment: .leading, spacing: 6) {
                if let eta = viewModel.eta {
                    Text("Arriving in \(eta.formatted(.units(allowed: [.minutes, .seconds], width: .abbreviated)))")
                        .font(.title2.bold())
                } else {
                    Text("Finding your driver…")
                        .font(.title2.bold())
                }
                if let meters = viewModel.metersAway {
                    Text("\(Measurement(value: Double(meters), unit: UnitLength.meters).formatted(.measurement(width: .abbreviated, usage: .road))) away")
                        .foregroundStyle(.secondary)
                }
                Text("\(viewModel.ride.driverName) · \(viewModel.ride.car)")
                    .font(.subheadline)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
        }
        .navigationTitle("Your ride")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.loadRoute()
        }
        .onAppear {
            Task { await viewModel.startTracking() }
        }
    }
}
```

## Part 1 — make it build, then make it right

::: A hint, if you're stuck
Both build errors are Swift 6 telling you the truth, so don't silence them. For the first, ask who else can
touch `sequence` while the `Task` runs. For the second, ask what `nonisolated` on an `async` function
means under this target's settings. Once it runs, open the console and filter on `RideService`. Watch it
while you open the screen, wait, tap Back, and open it again. Keep one eye on the ETA and one on the distance.
:::

::: The key — what I expect a senior to find
In the order you'd hit them: build, run, leave, read.

**It doesn't build**

1. **`passing closure as a 'sending' parameter risks causing data races between code in the current
   isolation context and concurrent execution of the closure`**, on the `Task {` in the package, with the
   note *"closure captures 'self' which is accessible to code in the current isolation context"*, pointing
   at `sequence += 1`. `RideService` is a non-`Sendable` class, and every stream's producer task mutates
   the same `sequence`. That's a real bug, not compiler fussiness. Two streams would share one counter and
   index past the end of `waypoints` in `eta(for:)`. The wrong fixes are `@unchecked Sendable` or
   `nonisolated(unsafe)`. The right one: make the counter local to each stream, and the service a
   stateless `Sendable` struct.
2. **`main actor-isolated property 'route' can not be mutated from a nonisolated context`**, in
   `loadRoute()`. The comment says the author wanted the decode off the main actor. The quick fixes compile:
   delete `nonisolated`, or wrap the assignment in `await MainActor.run { }`. Neither moves the decode, and
   that's the next bug.

**It runs — and the screen hangs when it opens**

3. **For about two seconds after the screen opens, nothing moves and Back doesn't respond.** Look at the
   service's own logs from the first run. Update 1 was sent at `20:39:43.368`, but `eta request for update 1`
   was logged at `20:39:44.536`, more than a second later. The view model couldn't take the update because
   the main thread was busy. My scratch watchdog logged *"main thread blocked for 2031 ms"* at that moment.
   With the target's Approachable Concurrency setting, a `nonisolated async` function runs **on the caller's
   actor** (SE-0461, `nonisolated(nonsending)` by default). Called from the view's `.task`, the caller is the
   main actor. So `RouteDecoder.decode` and its two seconds of work run on the main thread, whatever the
   keyword suggests. Fix: mark the function that does the work `@concurrent`, give it only the `Data`, and
   assign the result back on the main actor.

**Use it — watch the ETA and the distance together**

4. **The ETA goes up while the driver gets closer.** In the screenshots, "2 min, 50 sec · 0.99 mi away"
   becomes "3 min, 5 sec · 0.87 mi away", and later "55 sec · 1,650 ft" becomes "1 min, 25 sec · 1,650 ft".
   Every position starts its own unstructured `Task`, and every third ETA request takes 2.5 s instead of
   0.3 s. The slow answer for update 6 lands after the fast answer for update 7, and the last write wins.
   This is ordering by **arrival**, not by **sequence**. Fix: drop any result older than the one on screen,
   using the `sequence` the server already sends. Run the requests in a task group so that cancelling
   tracking cancels the requests too.
5. **The ride never ends.** The car sits on the pickup pin, and the screen says "Arriving in 0 sec · 0 ft
   away" forever. The stream *finishes*, which is the signal that the driver arrived, but nothing models it.
   Three optionals can't say "arrived". Add a `Status` enum: `findingDriver`, `enRoute`, `arrived`.

**Leave the screen — and read the console**

6. **Tracking keeps running after Back.** I left at update 4, and the log kept going to the end:
   `ride R-2081 sent update 12` … `eta request for update 12`, up to update 24. I opened the screen again,
   and a **second** stream started next to the first. Both appear in the log, interleaved:
   `sent update 1`, `sent update 13`, `eta request for update 1`, `eta request for update 13`.
   `.onAppear { Task { … } }` starts a task nobody owns. SwiftUI can't cancel it, and it holds the view
   model alive until the driver arrives. Fix: `.task { await viewModel.track() }`. SwiftUI cancels it when
   the view disappears.
7. **Fix 6 alone isn't enough.** With `.task`, the `eta request` lines stop when you leave, but
   `sent update` keeps ticking to 24. I checked: I left after update 3, and the producer logged updates
   4 to 24. The consumer stopped, but the producer task inside `AsyncStream` doesn't know. It needs
   `continuation.onTermination = { _ in producer.cancel() }`. The `try? await Task.sleep` has to become a
   real `try` that exits on cancellation. With `try?`, a cancelled sleep returns at once, and the loop
   runs the rest of the route without waiting. I tried `onTermination` with `try?` kept: after Back, the
   log showed `sent update 7` to `sent update 24` within one millisecond.

**Read the code**

8. **The service is built inside the view model.** Nothing can be tested without the real 24-second drive.
   Put a `RideTracking: Sendable` protocol in the package, inject it in `init`, and mark the stored
   dependency `@ObservationIgnored`. You need this before Part 3, so do it now.
9. **Said, not coded:**
   - `try?` on the ETA hides failures. After a failed request, the old ETA stays on screen as if it were
     current. Show when it's stale ("updated 40 s ago") once requests can fail for real.
   - `print` in an app. Use `Logger`, and keep the ride ID `.private` in production logs.
   - VoiceOver users get no announcement when the driver arrives. Post an
     `AccessibilityNotification.Announcement`.
   - The view model's public `var`s can be set from anywhere. Make them `private(set)`.

What sinks this part: `@unchecked Sendable` on the service to make error 1 go away, which ships the
shared-counter bug. Deleting `nonisolated` and never noticing the freeze. "Fixing" 4 with a debounce or
by awaiting each ETA in the loop, so the ETA lags by seconds. Stopping at 6, and never seeing in the
console that the producer is still running.
:::

::: The idea behind it
Every bug here is about **who owns a piece of async work, and where it runs**. The producer task had no
owner (7). The tracking task had no owner (6). The ETA tasks had no owner, and so no order (4). The decode
ran on an actor nobody chose on purpose (3). The counter was owned by everyone (1). The fix is
**structured concurrency all the way down**: the view's `.task` owns tracking, tracking owns a task group,
the group owns the ETA requests, and the stream's `onTermination` ties the producer to its consumer.
Cancel the top, and everything below it stops.

What "modern" means in this round:

| Use | Instead of |
|---|---|
| `.task { await viewModel.track() }` | `.onAppear { Task { … } }` |
| `withDiscardingTaskGroup` for fan-out work | a fire-and-forget `Task` per event |
| `@concurrent` for work that must leave the caller's actor | `nonisolated async` (runs on the caller under SE-0461), `Task.detached` |
| `continuation.onTermination` to stop the producer | a producer loop that runs to the end |
| `try await Task.sleep` that exits on cancellation | `try? await Task.sleep` |
| a stateless `Sendable` struct behind a protocol | a class with shared mutable state |
| a `Status` enum | several optionals that can't say "arrived" |
:::

::: The fix
The package: no shared state, a seam, and a producer that stops when its consumer goes away.

```swift
// MARK: - Service
public protocol RideTracking: Sendable {
    func driverUpdates(rideID: String) -> AsyncStream<DriverUpdate>
    func eta(for update: DriverUpdate) async throws -> Duration
    func routeData(rideID: String) async throws -> Data
    func cancelRide(rideID: String) async throws
}

public struct RideService: RideTracking {
    public init() {}

    private static let logger = Logger(subsystem: "RideService", category: "tracking")

    /// Pushes the driver's position once a second until they reach the pickup.
    /// Stops as soon as the consumer goes away.
    public func driverUpdates(rideID: String) -> AsyncStream<DriverUpdate> {
        AsyncStream { continuation in
            let producer = Task {
                for (index, waypoint) in Self.waypoints.enumerated() {
                    do {
                        try await Task.sleep(for: .seconds(1))
                    } catch {
                        return                          // cancelled: stop producing
                    }
                    let sequence = index + 1            // local to this stream, not shared
                    Self.logger.notice("ride \(rideID, privacy: .public) sent update \(sequence)")
                    continuation.yield(DriverUpdate(sequence: sequence, position: waypoint.position,
                                                    metersAway: waypoint.metersAway))
                }
                continuation.finish()
            }
            continuation.onTermination = { _ in producer.cancel() }
        }
    }

    // eta(for:), routeData(rideID:) and cancelRide(rideID:): unchanged, except `Self.logger`.
}
```

The view model: one status, results ordered by sequence, the decode off the main actor, and the service
injected:

```swift
import Foundation
import Observation
import os
import RideService

@Observable
final class RideTrackingViewModel {   // main actor: the target's default isolation
    enum Status: Equatable {
        case findingDriver
        case enRoute
        case arrived
    }

    let ride: Ride
    private(set) var status: Status = .findingDriver
    private(set) var route: [Coordinate] = []
    private(set) var driverPosition: Coordinate?
    private(set) var metersAway: Int?
    private(set) var eta: Duration?

    init(ride: Ride, service: any RideTracking) {
        self.ride = ride
        self.service = service
    }

    /// Runs until the driver arrives, or until the caller's task is cancelled (the view's `.task`).
    func track() async {
        await withDiscardingTaskGroup { group in
            for await update in service.driverUpdates(rideID: ride.id) {
                status = .enRoute
                driverPosition = update.position
                metersAway = update.metersAway
                group.addTask { [service] in
                    guard let eta = try? await service.eta(for: update) else { return }
                    await self.apply(eta, from: update.sequence)
                }
            }
            // The stream ends in two ways: the driver arrived, or we were cancelled.
            if !Task.isCancelled {
                status = .arrived
            }
            group.cancelAll()                       // late ETAs are meaningless now
        }
    }

    func loadRoute() async {
        do {
            let data = try await service.routeData(rideID: ride.id)
            route = try await Self.decodeRoute(data)
        } catch is CancellationError {
            // left the screen
        } catch {
            Self.logger.error("Route failed: \(error.localizedDescription)")   // the map still works without it
        }
    }

    @ObservationIgnored private let service: any RideTracking
    @ObservationIgnored private var etaSequence = 0     // the newest update an ETA was applied for

    private static let logger = Logger(subsystem: "RideTracking", category: "tracking")

    /// Results arrive in any order. Apply one only if it is newer than what's on screen.
    private func apply(_ eta: Duration, from sequence: Int) {
        guard status == .enRoute, sequence > etaSequence else { return }
        etaSequence = sequence
        self.eta = eta
    }

    /// `@concurrent` runs this on the global executor. A plain `nonisolated async` function runs on
    /// the caller's actor under Approachable Concurrency — here, the main actor.
    @concurrent
    private nonisolated static func decodeRoute(_ data: Data) async throws -> [Coordinate] {
        try RouteDecoder.decode(data)
    }
}
```

The view: inject through `init`, own both tasks with `.task`, and switch the headline on the status:

```swift
init(ride: Ride, service: any RideTracking = RideService()) {
    _viewModel = State(initialValue: RideTrackingViewModel(ride: ride, service: service))
}

// body: `Text(headline)`, and the distance only `if viewModel.status == .enRoute`.
    .task {
        await viewModel.loadRoute()
    }
    .task {
        await viewModel.track()                 // cancelled when the screen goes away
    }

private var headline: String {
    switch viewModel.status {
    case .findingDriver:
        "Finding your driver…"
    case .enRoute:
        if let eta = viewModel.eta {
            "Arriving in \(eta.formatted(.units(allowed: [.minutes, .seconds], width: .abbreviated)))"
        } else {
            "Your driver is on the way"
        }
    case .arrived:
        "\(viewModel.ride.driverName) is here"
    }
}
```

With this, the ETA only went up once in my run: at the missed turn, when the distance went up too
(1 min 45 s at 0.68 mi, then 2 min 5 s at 0.73 mi). The ride ended on "Mehmet is here". After Back, the log
stopped at the update on screen. The two-second block on opening was gone.
:::

## Part 2 — add the feature

> "Good. Two things from product. When the driver is less than two minutes away, show a banner:
> 'almost here, head to the pickup'. And add a Cancel ride button that stops tracking."

::: A hint, if you're stuck
Look at the ETA table in the package before you write `eta < 120`. One stretch goes 1:45 → 2:05 → 2:15 →
1:58. What should the banner do there? And for Cancel, ask what "stops tracking" means to the driver.
:::

::: The key — what I expect a senior to find
**The questions to ask first** — each one changes the code:

- **Show it once, or every time the ETA dips under two minutes?** Once per ride. This is the trap: a
  computed `eta < 120` shows the banner at 1:45, hides it at 2:05 after the missed turn, and shows it again
  at 1:58. It flickers, and with a notification it would buzz twice. The banner is a latched fact ("we
  told them"), not a live value.
- **Hide it if the ETA goes back up?** No. It's a heads-up, not a countdown. It goes away when the driver
  arrives, because the headline says "Mehmet is here" by then.
- **Does Cancel have to tell the server?** Yes. `cancelRide` already exists. Stopping only the local stream
  "cancels" the ride on the phone while the driver keeps driving.
- **When do we stop tracking: on tap, or once the server confirms?** Once the server confirms. If the
  request fails, the ride is still on, so keep tracking and say it failed. Disable the button while the
  request is in flight, so a second tap doesn't send a second request.
- **Can you cancel after arrival?** No. The button goes away once the driver is here.

**What I'm looking at while you build:**

- Part 1 is what makes this feature correct. With out-of-order ETAs, a stale 2:15 would land after 1:58,
  and any banner rule would fire on bad data.
- The latch and the cancel flow live in the view model. The view shows a flag and a button.
- Cancel can stop the tracking task from inside the view model. That needs a handle to it, and `.task`
  still has to cancel it when the screen goes away.
- Every state on screen: on the way, cancelling (button disabled), cancelled, arrived, cancel failed.
:::

::: The fix
The whole view model after Part 2. `track()` now owns a task that both `.task` and `cancelRide()` can
cancel:

```swift
import Foundation
import Observation
import os
import RideService

@Observable
final class RideTrackingViewModel {   // main actor: the target's default isolation
    enum Status: Equatable {
        case findingDriver
        case enRoute
        case arrived
        case cancelling
        case cancelled
    }

    let ride: Ride
    private(set) var status: Status = .findingDriver
    private(set) var route: [Coordinate] = []
    private(set) var driverPosition: Coordinate?
    private(set) var metersAway: Int?
    private(set) var eta: Duration?
    private(set) var cancelError: String?

    /// Shown once per ride, the first time a current ETA drops under two minutes.
    /// A later bump (a missed turn) doesn't hide it: it's a heads-up, not a live value.
    var showsArrivingBanner: Bool { hasCrossedArrivalThreshold && status == .enRoute }

    var canCancel: Bool { status == .findingDriver || status == .enRoute }

    init(ride: Ride, service: any RideTracking) {
        self.ride = ride
        self.service = service
    }

    /// Runs until the driver arrives, the ride is cancelled, or the caller's task is cancelled.
    func track() async {
        let tracking = Task { await runTracking() }   // inherits the main actor
        self.tracking = tracking
        await withTaskCancellationHandler {
            await tracking.value
        } onCancel: {
            tracking.cancel()                         // the view's .task went away
        }
    }

    func cancelRide() async {
        guard canCancel else { return }               // one request at a time
        let previous = status
        status = .cancelling
        cancelError = nil
        do {
            try await service.cancelRide(rideID: ride.id)
            tracking?.cancel()                        // stop only once the server agrees
            status = .cancelled
        } catch {
            status = previous                         // the driver is still coming: keep tracking
            cancelError = "Couldn't cancel the ride. Try again."
        }
    }

    func loadRoute() async { ... unchanged ... }

    @ObservationIgnored private let service: any RideTracking
    @ObservationIgnored private var tracking: Task<Void, Never>?
    @ObservationIgnored private var etaSequence = 0     // the newest update an ETA was applied for
    private var hasCrossedArrivalThreshold = false

    private static let arrivalThreshold: Duration = .seconds(120)
    private static let logger = Logger(subsystem: "RideTracking", category: "tracking")

    private func runTracking() async {
        await withDiscardingTaskGroup { group in
            for await update in service.driverUpdates(rideID: ride.id) {
                if status == .findingDriver { status = .enRoute }
                driverPosition = update.position
                metersAway = update.metersAway
                group.addTask { [service] in
                    guard let eta = try? await service.eta(for: update) else { return }
                    await self.apply(eta, from: update.sequence)
                }
            }
            // The stream ends in two ways: the driver arrived, or we were cancelled.
            if !Task.isCancelled {
                status = .arrived
            }
            group.cancelAll()                       // late ETAs are meaningless now
        }
    }

    /// Results arrive in any order. Apply one only if it is newer than what's on screen.
    private func apply(_ eta: Duration, from sequence: Int) {
        guard status == .enRoute, sequence > etaSequence else { return }
        etaSequence = sequence
        self.eta = eta
        if eta < Self.arrivalThreshold {
            hasCrossedArrivalThreshold = true
        }
    }

    // decodeRoute(_:): unchanged, @concurrent.
}
```

`if status == .findingDriver` matters. While a cancel is in flight, a new position must not flip the status
from `.cancelling` back to `.enRoute`.

In the view, the button and the error go under the driver line, and the banner is an overlay:

```swift
if viewModel.canCancel || viewModel.status == .cancelling {
    Button("Cancel ride", role: .destructive) {
        Task { await viewModel.cancelRide() }
    }
    .buttonStyle(.bordered)
    .disabled(viewModel.status == .cancelling)
    .padding(.top, 8)
}
if let error = viewModel.cancelError {
    Text(error)
        .font(.footnote)
        .foregroundStyle(.red)
}
```

```swift
.overlay(alignment: .top) {
    if viewModel.showsArrivingBanner {
        Label("\(viewModel.ride.driverName) is almost here. Head to the pickup.", systemImage: "car.fill")
            .font(.headline)
            .padding()
            .frame(maxWidth: .infinity)
            .background(.green.gradient, in: .rect(cornerRadius: 16))
            .foregroundStyle(.white)
            .padding()
            .transition(.move(edge: .top).combined(with: .opacity))
    }
}
.animation(.default, value: viewModel.showsArrivingBanner)
```

The headline gains `case .cancelling: "Cancelling…"` and `case .cancelled: "Ride cancelled"`. On the
simulator, the banner appeared at "1 min, 45 sec" and stayed through "2 min, 5 sec". After a tap on Cancel,
the screen showed "Cancelling…" with the button disabled, then "Ride cancelled". The log ended at
`ride R-2081 cancelled on the server`, with no update after it.
:::

## Part 3 — test it

> "Test what matters. The stream is the hard part."

::: Now write the tests
A fake whose stream the test drives by hand with `AsyncStream.makeStream`, and whose ETAs are scripted per
update, including a delay. The counters live in `Mutex`, so the fake is `Sendable` without
`@unchecked`. The target's default isolation puts the fake on the main actor, and a `Sendable` protocol
requirement can't be met from there, so mark it `nonisolated`.

```swift
import Foundation
import Synchronization
import Testing
import RideService
@testable import RideTracking

/// A stream the test drives by hand, and ETAs scripted per update.
nonisolated final class FakeRideService: RideTracking {
    let updates: AsyncStream<DriverUpdate>
    let driver: AsyncStream<DriverUpdate>.Continuation
    let etas: [Int: (eta: Duration, delay: Duration)]
    let cancelFails: Bool
    let cancelCalls = Mutex(0)
    let streamTerminated = Mutex(false)

    init(etas: [Int: (eta: Duration, delay: Duration)] = [:], cancelFails: Bool = false) {
        (updates, driver) = AsyncStream.makeStream(of: DriverUpdate.self)
        self.etas = etas
        self.cancelFails = cancelFails
        driver.onTermination = { [weak self] _ in self?.streamTerminated.withLock { $0 = true } }
    }

    func driverUpdates(rideID: String) -> AsyncStream<DriverUpdate> { updates }

    func eta(for update: DriverUpdate) async throws -> Duration {
        let scripted = etas[update.sequence] ?? (.seconds(300), .zero)
        try await Task.sleep(for: scripted.delay)
        return scripted.eta
    }

    func routeData(rideID: String) async throws -> Data { Data("[]".utf8) }

    func cancelRide(rideID: String) async throws {
        cancelCalls.withLock { $0 += 1 }
        if cancelFails { throw URLError(.notConnectedToInternet) }
    }

    func send(_ sequence: Int) {
        driver.yield(DriverUpdate(sequence: sequence, position: Coordinate(latitude: 52.52, longitude: 13.40),
                                  metersAway: 1000))
    }
}

/// Polls until the view model reaches the expected state. Fails instead of hanging.
private func waitUntil(_ condition: () -> Bool) async throws {
    for _ in 0..<200 where !condition() {
        try await Task.sleep(for: .milliseconds(10))
    }
    try #require(condition())
}

struct RideTrackingViewModelTests {
    let ride = Ride(id: "R-1", driverName: "Mehmet", car: "Prius",
                    pickup: Coordinate(latitude: 52.51, longitude: 13.37))

    @Test func aSlowOlderETADoesNotOverwriteANewerOne() async throws {
        let service = FakeRideService(etas: [1: (.seconds(200), .milliseconds(300)),   // slow
                                             2: (.seconds(190), .zero)])               // fast
        let viewModel = RideTrackingViewModel(ride: ride, service: service)
        let tracking = Task { await viewModel.track() }
        service.send(1)
        service.send(2)
        try await waitUntil { viewModel.eta == .seconds(190) }
        try await Task.sleep(for: .milliseconds(500))           // the slow answer for update 1 lands now
        #expect(viewModel.eta == .seconds(190))
        tracking.cancel()
    }

    @Test func theStreamEndingMeansTheDriverArrived() async {
        let service = FakeRideService()
        let viewModel = RideTrackingViewModel(ride: ride, service: service)
        service.send(1)
        service.driver.finish()
        await viewModel.track()
        #expect(viewModel.status == .arrived)
    }

    @Test func theBannerShowsOnceAndStaysWhenTheETAGoesBackUp() async throws {
        let service = FakeRideService(etas: [1: (.seconds(130), .zero),
                                             2: (.seconds(110), .zero),
                                             3: (.seconds(125), .zero)])   // a missed turn
        let viewModel = RideTrackingViewModel(ride: ride, service: service)
        let tracking = Task { await viewModel.track() }
        service.send(1)
        try await waitUntil { viewModel.eta == .seconds(130) }
        #expect(!viewModel.showsArrivingBanner)
        service.send(2)
        try await waitUntil { viewModel.eta == .seconds(110) }
        #expect(viewModel.showsArrivingBanner)
        service.send(3)
        try await waitUntil { viewModel.eta == .seconds(125) }
        #expect(viewModel.showsArrivingBanner)
        tracking.cancel()
    }

    @Test func cancellingStopsTrackingOnceTheServerConfirms() async throws {
        let service = FakeRideService()
        let viewModel = RideTrackingViewModel(ride: ride, service: service)
        let tracking = Task { await viewModel.track() }
        service.send(1)
        try await waitUntil { viewModel.status == .enRoute }
        await viewModel.cancelRide()
        await tracking.value                                    // returns: tracking really stopped
        #expect(viewModel.status == .cancelled)
        #expect(service.cancelCalls.withLock { $0 } == 1)
        #expect(service.streamTerminated.withLock { $0 })
    }

    @Test func aFailedCancelKeepsTracking() async throws {
        let service = FakeRideService(cancelFails: true)
        let viewModel = RideTrackingViewModel(ride: ride, service: service)
        let tracking = Task { await viewModel.track() }
        service.send(1)
        try await waitUntil { viewModel.status == .enRoute }
        await viewModel.cancelRide()
        #expect(viewModel.status == .enRoute)
        #expect(viewModel.cancelError != nil)
        #expect(!service.streamTerminated.withLock { $0 })
        tracking.cancel()
    }
}
```

The `Mutex` can't be captured in the `onTermination` closure: it's `~Copyable`, and the compiler says
*"'self.streamTerminated' is borrowed and cannot be consumed"*. Capture `self` weakly instead.

I checked that the first test catches the bug: without the `sequence > etaSequence` guard, it fails with
`Expectation failed: viewModel.eta == .seconds(190)`. `streamTerminated` proves the stream's
`onTermination` ran, which is the same hook the real producer now uses to stop.

This test uses real time (300 ms against 500 ms), so a very slow CI machine could make it flaky. If the
interviewer pushes, make the fake's ETA wait on a continuation the test resumes. Then the order is chosen by
the test, not by the clock.
:::

::: What I'd ask next
- **"The app goes to the background mid-ride."** Watch `scenePhase` and stop the stream in the
  background. When the app comes back, start it again, and fetch the current ETA first so the screen isn't
  stale. A Live Activity is the real answer for the lock screen, fed by push updates, not by this stream.
- **"The socket drops."** `AsyncStream` can't fail. Move to `AsyncThrowingStream`, retry with backoff, and
  show "reconnecting" instead of a frozen car. Resume from the last `sequence` you saw, so you don't
  re-apply old positions.
- **"Positions now come ten times a second."** Don't start an ETA request per position. Throttle the
  requests (one every few seconds, plus one when the distance changes a lot), and use the stream's
  buffering policy, `.bufferingNewest(1)`, so the UI never works through a backlog.
- **"Why not make the view model an actor?"** Its state drives the UI, so it belongs on the main actor.
  The work that must leave the main actor is small and explicit (`@concurrent`), and the ordering problem is
  solved by data (`sequence`), not by an actor's queue. An actor doesn't order calls by when they were
  started anyway.
- **"Another screen needs the driver's position too."** Don't open a second stream. Have one owner
  (a `RideSession` in the environment) consume the stream and expose `@Observable` state, or broadcast it
  with `Observations` (iOS 26).
:::
