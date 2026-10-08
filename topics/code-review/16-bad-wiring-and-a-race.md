---
title: 16 · Bad wiring and a race condition
summary: A cart screen where Clear adds items, Add adds twice, the count lags by one and big baskets crash — find each cause and say how you'd debug it.
minutes: 20
group: Find the bug
sources:
- Glassdoor · DoorDash iOS — "debugging a sample application with bad interface wiring and a race condition" | https://www.glassdoor.com/Interview/DoorDash-Interview-RVW57524208.htm
- Blind · DoorDash iOS debugging round — "a piece of code doing something pretty straight forward with a few problems" | https://www.teamblind.com/post/doordash-on-site-ios-debugging-behaviour-round-p58mcuuw
---

*Shape: find the bug · Reported: DoorDash — debugging a sample app with "bad interface wiring and
a race condition" (from a Glassdoor search snippet), and "a piece of code doing something pretty
straight forward with a few problems" · UIKit — the snippet and the fix typecheck against the iOS
SDK (iOS 18 target); the fix has zero warnings in Swift 6 mode; the race and the fixed pricing
logic were compiled and run as Foundation-only programs with Swift 6.4, the rest checked by hand*

> "Here's a small sample app — a cart. QA filed four bugs: Clear doesn't clear, it adds things.
> After you come back from the product page, one tap on Add adds everything twice. The item count
> is always one behind. And with a big basket it sometimes crashes on Add. Find and fix them, and
> talk me through how you'd debug it if you couldn't spot it by reading."

```swift
struct CartItem {
    let sku: String
    let price: Decimal
}

final class PricingService {
    func price(for sku: String, completion: @escaping (CartItem) -> Void) {
        DispatchQueue.global().async {
            // Looks the price up in a local database, then calls back.
            completion(CartItem(sku: sku, price: 4.99))
        }
    }
}

final class CartViewController: UIViewController {
    @IBOutlet private var addButton: UIButton!
    @IBOutlet private var clearButton: UIButton!
    @IBOutlet private var countLabel: UILabel!

    var selectedSKUs: [String] = []
    private var items: [CartItem] = []
    private let pricing = PricingService()

    override func viewDidLoad() {
        super.viewDidLoad()
        clearButton.addTarget(self, action: #selector(addTapped), for: .touchUpInside)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        addButton.addAction(UIAction { [weak self] _ in
            self?.addTapped()
        }, for: .touchUpInside)
    }

    @objc private func addTapped() {
        for sku in selectedSKUs {
            pricing.price(for: sku) { item in
                self.countLabel.text = "\(self.items.count) items"
                self.items.append(item)
            }
        }
    }

    @objc private func clearTapped() {
        items.removeAll()
        countLabel.text = "0 items"
    }
}
```

In Swift 5 mode this compiles silently. In Swift 6 mode it compiles with one warning, inside
`PricingService` (capturing a non-`Sendable` completion in a `@Sendable` closure) — and nothing at
all about the controller (both checked). The warning points one file away from the crash.

::: A hint, if you're stuck
- For each QA bug, find the line that produces it. They are four different lines.
- Which thread does `completion` run on? How many of them can run at once?
- `viewWillAppear` runs more than once in a screen's life. When?
- Read the closure in `addTapped` line by line: what does the label say for the first item?
:::

::: The key — what I expect a senior to find
1. **The crash: a data race on `items`.** `price(for:)` calls back on a global concurrent queue, so
   with several SKUs several callbacks run at the same time, all appending to the same array. A
   Swift array is not safe to change from two threads at once; when two appends collide during a
   resize, memory is corrupted. I ran the same pattern 20 times — 1,000 appends with
   `DispatchQueue.concurrentPerform` on an 8-core Mac: 19 runs crashed (segfaults, a trap, a bus
   error) and the one that finished had 989 items, not 1,000. On a phone with a three-item basket
   it's rarer, which is why it reached QA. Fix: only ever touch `items` on the main actor.
2. **UI changed from a background thread.** `countLabel.text` is set inside the same background
   callback. UIKit is main-thread only; off main the label may not redraw, may redraw late, or may
   crash inside UIKit. Main Thread Checker flags this line the first time it runs.
3. **Clear is wired to Add (QA bug 1).** `clearButton` targets `#selector(addTapped)`, so Clear
   prices and adds the selection. `clearTapped` is dead code. Wrong selector, compiles fine.
4. **Add is wired again every time the screen appears (QA bug 2).** `viewWillAppear` runs on first
   show *and* every time you come back from a pushed screen. Each time, `addAction` adds a new
   closure, and closures don't replace each other, so after one round trip a tap runs `addTapped`
   twice. Wire once, in `viewDidLoad`. (I checked: adding the *same* target and selector twice
   keeps one entry, so the old `addTarget` style would have hidden this. Fresh `UIAction`s stack.)
5. **The count is one behind (QA bug 3).** The label is set *before* the append, so it shows the
   count before this item arrived. Update the label after the change — a `didSet` on `items` makes
   it impossible to get the order wrong.
6. **One label update per item, in random order.** Even when fixed, the label flickers through
   1, 2, 3 and the items land in whatever order the callbacks finish. Price everything, then
   append once, in the order the user chose.
7. **No guard against double taps.** Two quick taps price the basket twice. Disable Add while a
   request is in flight.
8. **`PricingService` is built inside the controller.** Nothing can be faked, so none of these
   bugs could have been caught by a test. Inject it behind a protocol.
:::

::: How I'd debug it
I'd say this before touching code, because the round scores *how* you debug as much as the fix:

- **Reproduce each bug, one at a time.** "Add twice after coming back" means push and pop first.
  A bug I can't reproduce is a bug I'm guessing about.
- **Breakpoint in `addTapped`, then tap once.** If it's hit twice, the backtrace shows who called
  it. On the button, `po addButton.allTargets` and `enumerateEventHandlers` show what's wired.
- **Main Thread Checker** (on by default for Debug runs, in the scheme's Diagnostics tab) prints a
  purple runtime issue the moment `countLabel.text` is set off main. Tick *Pause on issues* to stop
  right there.
- **Thread Sanitizer** (same tab, simulator only, and not together with Address Sanitizer) reports
  the race on `items` with both stack traces — the two appends that collided — even on runs that
  don't crash. That's the point: a race shows up in TSan far more reliably than as a crash.
- **For the off-by-one, a breakpoint with a log action** on the label line that prints
  `items.count` makes the "before the append" order obvious.
:::

::: The idea behind it
A *thread* is a line of work the processor runs. A *race condition* is when two threads touch the
same data at the same time and the result depends on who gets there first. A *data race* is the
dangerous kind: at least one of them is writing, with nothing coordinating them.

Appending to an array looks like one step but is several: read the count, maybe grow the storage
by copying everything to a bigger block, write the new item, bump the count. If two threads
interleave those steps, both can write to the same slot (an item is lost) or one can write into
storage the other has just thrown away (a crash). It's two people writing on the same line of the
same notepad at once.

The cure is to make sure only one thread ever touches the array — here, the main thread, which is
also the only thread allowed to touch UIKit. Swift's `@MainActor` says that in the type system:
code marked with it always runs on main, and the compiler checks the calls.

*Wiring* bugs are simpler: the connection between a button and the code it runs is made at
runtime, so a wrong selector or a connection made twice compiles fine. Read every `addTarget`
and `addAction`, and ask how many times each runs.
:::

::: The fix
```swift
struct CartItem: Sendable, Equatable {
    let sku: String
    let price: Decimal
}

protocol Pricing: Sendable {
    func price(for sku: String) async -> CartItem
}

extension Pricing {
    /// Prices every SKU at the same time, then hands back the results in the order asked for.
    func prices(for skus: [String]) async -> [CartItem] {
        await withTaskGroup(of: (Int, CartItem).self) { group in
            for (index, sku) in skus.enumerated() {
                group.addTask { (index, await price(for: sku)) }
            }
            var priced = [CartItem?](repeating: nil, count: skus.count)
            for await (index, item) in group {   // results arrive one at a time, here
                priced[index] = item
            }
            return priced.compactMap { $0 }
        }
    }
}

final class CartViewController: UIViewController {
    @IBOutlet private var addButton: UIButton!
    @IBOutlet private var clearButton: UIButton!
    @IBOutlet private var countLabel: UILabel!

    var selectedSKUs: [String] = []
    private var items: [CartItem] = [] {
        didSet { countLabel.text = "\(items.count) items" }   // runs after the change
    }
    private let pricing: Pricing
    private var addTask: Task<Void, Never>?

    init?(coder: NSCoder, pricing: Pricing) {
        self.pricing = pricing
        super.init(coder: coder)
    }

    required init?(coder: NSCoder) { fatalError("Use init(coder:pricing:)") }

    override func viewDidLoad() {
        super.viewDidLoad()
        addButton.addTarget(self, action: #selector(addTapped), for: .touchUpInside)
        clearButton.addTarget(self, action: #selector(clearTapped), for: .touchUpInside)
    }

    @objc private func addTapped() {
        guard addTask == nil else { return }
        addButton.isEnabled = false
        let skus = selectedSKUs
        addTask = Task {
            defer {
                addTask = nil
                addButton.isEnabled = true
            }
            let priced = await pricing.prices(for: skus)
            guard !Task.isCancelled else { return }
            items.append(contentsOf: priced)   // on the main actor: one writer, one label update
        }
    }

    @objc private func clearTapped() {
        addTask?.cancel()   // an add still in flight must not land after Clear
        items.removeAll()
    }
}
```

The broken pattern, as a Foundation-only program (compiled with `-swift-version 5`; Swift 6 mode
gives a warning here, not an error, because Dispatch's API predates strict checking):

```swift
final class Cart {
    var items: [Int] = []
}

func addAll() {
    let cart = Cart()
    DispatchQueue.concurrentPerform(iterations: 1_000) { i in
        cart.items.append(i)          // many threads append at once
    }
    print("expected 1000, got \(cart.items.count)")
}
addAll()
```

```text
20 runs: 15 × exit 139 (segfault), 3 × exit 133 (trap), 1 × exit 138 (bus error),
         1 × "expected 1000, got 989"
```

The fixed pricing logic, driven by a fake that answers each SKU after a random 0–500 µs so
replies come back out of order (compiled with `-swift-version 6`, no warnings):

```swift
struct FakePricing: Pricing {
    func price(for sku: String) async -> CartItem {
        try? await Task.sleep(for: .microseconds(Int.random(in: 0...500)))   // replies in random order
        return CartItem(sku: sku, price: 4.99)
    }
}

@MainActor final class Cart {
    private(set) var items: [CartItem] = []
    func add(_ skus: [String], using pricing: Pricing) async {
        items.append(contentsOf: await pricing.prices(for: skus))
    }
}
```

Twenty runs of 1,000 SKUs: all 20 ended with 1,000 items, in the order asked for.

Why each piece:

- **`async` pricing instead of a callback** — the controller is `@MainActor` (every
  `UIViewController` is), so code after `await` in its `Task` runs on main. The append and the
  label update can't happen on a background thread.
- **The task group** — still prices in parallel, but results are collected by a single `for await`
  loop, one at a time. Parallel work, one writer.
- **Results placed by index** — the cart shows items in the order the user picked them, not the
  order the database answered.
- **`didSet` on `items`** — the label is derived from the array *after* every change, so it can't
  be one behind, and Clear updates it for free.
- **Both buttons wired once, in `viewDidLoad`, to the right selectors.**
- **`addTask` and `isEnabled`** — one add at a time; Clear cancels a pending add so a slow reply
  can't refill a cart the user just emptied.
- **`init?(coder:pricing:)`** — the service is injected (with a storyboard, through
  `instantiateViewController(identifier:creator:)`), so a test can use `FakePricing`.
:::

::: What I'd ask next
- *"The old `PricingService` can't change. How do you get `async` from it?"* — Wrap it with
  `withCheckedContinuation`: call the old method and resume the continuation in its completion,
  exactly once.
- *"Why not just wrap the append in `DispatchQueue.main.async`?"* — It would fix the race and the
  thread, and it's a fine minimal fix in an interview. But the compiler can't check it, and the
  next person to add a callback can forget it. `@MainActor` makes forgetting a compile error.
- *"Could you use a lock instead?"* — Yes, for a model that isn't UI state: a `Mutex` (from the
  Synchronization module) or an actor around the array. For state that drives a label, the main
  actor is simpler, because the UI has to read it there anyway.
- *"Why does Thread Sanitizer catch it when the app doesn't crash?"* — TSan watches every memory
  access and flags two unsynchronised accesses from different threads, whether or not they
  happened to collide this time. A crash needs the collision; TSan only needs the possibility.
- *"Would Swift 6 have caught all of this?"* — The race, partly. As written, no: the controller
  raises nothing. Mark the completion `@Sendable` and Swift 6 mode flags every line in the callback
  that touches `items` or `countLabel` — but as warnings, not errors, when I checked against the iOS
  SDK. Warnings get ignored; moving to `async` makes the problem disappear instead. The wiring bugs
  and the off-by-one, no — they are correct Swift that does the wrong thing.
:::
