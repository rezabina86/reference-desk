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
straight forward with a few problems" · Verified: the snippet and the fix built in Swift 6 mode
(Swift 6.4) and ran on the iOS Simulator*

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
`PricingService` (capturing a non-`Sendable` completion in a `@Sendable` closure), and nothing at
all about the controller. It doesn't trap at runtime either: I ran it on the simulator in Swift 6
mode, and the callback ran on a background thread and set the label there. So Swift 6 doesn't save
you here — the warning points one file away from the crash.

::: A hint, if you're stuck
- For each QA bug, find the line that produces it. They are four different lines.
- Which thread does `completion` run on? How many of them can run at once?
- `viewWillAppear` runs more than once in a screen's life. When?
- Read the closure in `addTapped` line by line: what does the label say for the first item?
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

::: The key — what I expect a senior to find
1. **The crash: a data race on `items` (QA bug 4).** `price(for:)` calls back on a global
   concurrent queue, so with several SKUs several callbacks run at the same time, all appending to
   the same array. A Swift array is not safe to change from two threads at once; when two appends
   collide during a resize, memory is corrupted. Twenty runs of 1,000 concurrent appends, in a
   stand-alone program: 3 crashed and 3 more silently lost items. A three-item basket hits it far
   more rarely, which is why it reached QA. Fix: only touch `items` on the main thread.
2. **UI changed from a background thread.** `countLabel.text` is set in the same background
   callback. UIKit is main-thread only; off main the label may not redraw, redraw late, or crash
   inside UIKit. Main Thread Checker flags this line the first time it runs.
3. **The callback holds `self` strongly.** It isn't a cycle, so nothing leaks for good, but a closed
   cart stays alive until every price comes back and then updates a screen nobody sees. Fine for a
   fast local lookup; with a network call, capture `[weak self]`.
4. **Clear is wired to Add (QA bug 1).** `clearButton` targets `#selector(addTapped)`, so Clear
   prices and adds the selection. `clearTapped` is dead code. Wrong selector, compiles fine.
5. **Add is wired again every time the screen appears (QA bug 2).** `viewWillAppear` runs on first
   show *and* every time you come back from a pushed screen. Each `addAction` adds a new closure, so
   after one round trip a tap runs `addTapped` twice. Wire once, in `viewDidLoad`. (Adding the same
   target and selector twice keeps one entry; fresh `UIAction`s stack.)
6. **The count is one behind (QA bug 3).** The label is set *before* the append, so it shows the
   count before this item arrived. Update the label after the change.
7. **An add still in flight lands after Clear.** Tap Add, then Clear before the prices come back:
   the items reappear in a cart the user just emptied.
8. **One label update per item, in random order.** Even when fixed, the label flickers through
   1, 2, 3, and the items land in whatever order the callbacks finish, not the order the user chose.
9. **No guard against double taps.** Two quick taps price the basket twice. Disable Add while a
   request is in flight.
10. **"1 items".** The text isn't pluralised or localised. Use a String Catalog plural.
11. **Pricing has no failure path.** The completion only takes a `CartItem`. A failed lookup can't
    report anything, so the user taps Add and nothing happens. Pass a `Result`.
12. **`PricingService` is built inside the controller.** Nothing can be faked, so none of these bugs
    could have been caught by a test. Inject it behind a protocol.
13. **`selectedSKUs` is writable by anyone, and the wiring mixes styles.** Target-action for one
    button, `UIAction` for the other: pick one, so a reader can find every connection the same way.
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
Same screen, same callback API, same storyboard outlets. The four QA bugs are four small edits.

```swift
protocol PricingServiceType {                                          // key 12: the one seam
    func price(for sku: String, completion: @escaping @Sendable (CartItem) -> Void)
}

final class PricingService: PricingServiceType {
    func price(for sku: String, completion: @escaping @Sendable (CartItem) -> Void) {
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
    var pricing: PricingServiceType = PricingService()                 // key 12

    override func viewDidLoad() {
        super.viewDidLoad()
        addButton.addTarget(self, action: #selector(addTapped), for: .touchUpInside)     // key 5
        clearButton.addTarget(self, action: #selector(clearTapped), for: .touchUpInside) // key 4
    }

    // key 5: viewWillAppear deleted — nothing to wire there

    @objc private func addTapped() {
        for sku in selectedSKUs {
            pricing.price(for: sku) { item in
                DispatchQueue.main.async {                             // key 1, 2: main only
                    self.items.append(item)
                    self.countLabel.text = "\(self.items.count) items" // key 6: after the append
                }
            }
        }
    }

    @objc private func clearTapped() {
        items.removeAll()
        countLabel.text = "0 items"
    }
}
```

**Said out loud, not coded:** keep results in the user's order and update the label once (key 8);
disable Add while pricing (key 9); have Clear drop adds still in flight (key 7); a plural string
(key 10); a `Result` in the callback (key 11); then move to `async`/`await` on a `@MainActor`
controller and inject the service through `instantiateViewController(identifier:creator:)`.

Why each piece:

- **`DispatchQueue.main.async` around both lines.** Every append now happens on one thread, one
  after another, so the race is gone; the label is on main too.
- **`@Sendable` on the completion.** It tells the compiler the closure runs on another thread. It
  also clears the snippet's warning — and if someone deletes the main-queue hop, Swift 6 now warns
  on every line that touches `items` or `countLabel`.
- **A property with a default, not a new initialiser.** The storyboard still creates the controller
  the way it always did; a test just replaces `pricing`.
:::

::: Now write the tests
> "Good. Now write me tests for the race and the wiring — the things QA found."

**What I'd test, and why**

1. **Prices answered in the background all land.** 200 SKUs answered on background threads at once
   end as "200 items". That's the crash fix, and it goes first.
2. **The count reads N after adding N** — "3 items", not "2 items". The off-by-one.
3. **Clear empties the cart and prices nothing.** Catches Clear being wired to Add.
4. **Coming back to the screen doesn't double-add.** `viewWillAppear` twice, one tap, one price
   request.

I wouldn't count on test 1 to catch the race every time — a data race is a matter of luck, and
Thread Sanitizer finds it reliably. The test pins the behaviour; TSan and the main-queue hop do
the rest.

**The seam.** `pricing` is a property with a default, so the test swaps in a *fake* that records
each SKU and answers straight away (or on a background queue, for test 1). The test builds the
controller in code and connects the outlets by key, the way a storyboard would. The fix puts each
result on the main queue, so the test waits a bounded number of turns for the label instead of
sleeping.

```swift
import Testing
import UIKit

/// A fake price list: records every SKU it's asked for and answers straight away.
final class FakePricing: PricingServiceType, @unchecked Sendable {
    private(set) var asked: [String] = []
    var answersInBackground = false

    func price(for sku: String, completion: @escaping @Sendable (CartItem) -> Void) {
        asked.append(sku)
        let item = CartItem(sku: sku, price: 4.99)
        if answersInBackground {
            DispatchQueue.global().async { completion(item) }
        } else {
            completion(item)
        }
    }
}

/// Gives the main queue a turn, a fixed number of times, until the condition holds. No clocks.
@MainActor
func waitUntil(maxYields: Int = 1_000, _ condition: () async -> Bool) async {
    for _ in 0..<maxYields {
        if await condition() { return }
        await Task.yield()
    }
}

@MainActor
struct CartScreen {
    let controller = CartViewController()
    let add = UIButton()
    let clear = UIButton()
    let count = UILabel()
    let pricing = FakePricing()

    init(skus: [String]) {
        controller.setValue(add, forKey: "addButton")   // what the storyboard would connect
        controller.setValue(clear, forKey: "clearButton")
        controller.setValue(count, forKey: "countLabel")
        controller.pricing = pricing
        controller.selectedSKUs = skus
        controller.loadViewIfNeeded()                   // viewDidLoad wires the buttons
    }
}

@MainActor
struct CartViewControllerTests {

    @Test
    func pricesAnsweredInTheBackgroundAllLand() async {
        // Given a basket of 200 SKUs, priced on background threads at the same time
        let cart = CartScreen(skus: (0..<200).map { "sku\($0)" })
        cart.pricing.answersInBackground = true

        // When the user taps Add
        cart.add.sendActions(for: .touchUpInside)

        // Then every item lands, none lost
        await waitUntil { cart.count.text == "200 items" }
        #expect(cart.count.text == "200 items")
    }

    @Test
    func countReadsNAfterAddingN() async {
        let cart = CartScreen(skus: ["a", "b", "c"])

        cart.add.sendActions(for: .touchUpInside)

        await waitUntil { cart.count.text == "3 items" }
        #expect(cart.count.text == "3 items")          // not "2 items"
    }

    @Test
    func clearEmptiesTheCart() async {
        // Given two items in the cart
        let cart = CartScreen(skus: ["a", "b"])
        cart.add.sendActions(for: .touchUpInside)
        await waitUntil { cart.count.text == "2 items" }

        // When the user taps Clear
        cart.clear.sendActions(for: .touchUpInside)

        // Then the cart is empty, and Clear priced nothing
        #expect(cart.count.text == "0 items")
        #expect(cart.pricing.asked == ["a", "b"])
    }

    @Test
    func comingBackToTheScreenDoesNotDoubleAdd() async {
        // Given the screen appeared twice: first show, then back from the product page
        let cart = CartScreen(skus: ["a"])
        cart.controller.viewWillAppear(false)
        cart.controller.viewWillAppear(false)

        // When the user taps Add once
        cart.add.sendActions(for: .touchUpInside)
        await waitUntil { cart.count.text == "1 items" }

        // Then the SKU was priced once
        #expect(cart.pricing.asked == ["a"])
        #expect(cart.count.text == "1 items")
    }
}
```

The last two tests assert "1 items" and "0 items" on purpose: they pin today's text. When key 10
is fixed, they change with it.

Ran on the iOS Simulator (Swift 6 mode): 4 tests, all passed.
:::

::: What I'd ask next
- *"Why not move to `async`/`await` right away?"* — In the interview, the main-queue hop fixes all
  four bugs in a few lines. In the codebase I'd go further: an `async` price lookup on a
  `@MainActor` controller means the code after `await` is on main by construction, and the
  compiler checks it. The hop is something the next person can forget.
- *"The old `PricingService` can't change. How do you get `async` from it?"* — Wrap it with
  `withCheckedContinuation`: call the old method and resume the continuation in its completion,
  exactly once.
- *"Could you use a lock instead?"* — Yes, for a model that isn't UI state: a `Mutex` (from the
  Synchronization module) or an actor around the array. For state that drives a label, the main
  thread is simpler, because the UI has to read it there anyway.
- *"Why does Thread Sanitizer catch it when the app doesn't crash?"* — TSan watches every memory
  access and flags two unsynchronised accesses from different threads, whether or not they
  happened to collide this time. A crash needs the collision; TSan only needs the possibility.
- *"Would Swift 6 have caught all of this?"* — As written, no: the controller raises nothing, and
  the callback isn't checked at runtime either. Mark the completion `@Sendable` and Swift 6 mode
  flags every line in the callback that touches `items` or `countLabel` — as warnings, not errors,
  because UIKit's checks are relaxed for older code. The wiring bugs and the off-by-one, no: they
  are correct Swift that does the wrong thing.
:::
