---
title: 09 · Find the leak
summary: A profile screen that never deallocates — find all five reasons, explain weak versus unowned, and prove the fix.
minutes: 20
group: Find the bug
sources:
- LeetCode Discuss · Uber SSE iOS — "iOS memory leak question (identify and fix)" | https://leetcode.com/discuss/interview-experience/1632373/
- LeetCode Discuss · Swiggy iOS — pass data between ViewModel and ViewController using delegates | https://leetcode.com/discuss/post/4558238/swiggy-ios-developer-rejected
---

*Shape: find the bug · Reported: Uber — an "identify and fix the memory leak" question; Swiggy —
wiring a view model to its controller with a delegate · UIKit — the snippet and the fix typecheck
against the iOS SDK (iOS 18 target) in Swift 6 mode; both were also run in the iOS simulator, and
a Foundation-only stand-in was compiled and run with Swift 6.4*

> "Open the profile screen and close it. The `deinit` never prints. Do it ten times and there are
> ten profile screens in memory. Find out why — there's more than one reason."

```swift
@MainActor
protocol ProfileViewModelDelegate {
    func profileDidLoad(name: String)
}

@MainActor
final class ProfileViewModel {
    var delegate: ProfileViewModelDelegate?
    var onError: ((String) -> Void)?
    private(set) var avatar: AvatarViewModel!
    private(set) var name = ""

    init() {
        avatar = AvatarViewModel(parent: self)
    }

    func load() {
        name = "Ada Lovelace"
        delegate?.profileDidLoad(name: name)
    }

    func avatarFailed() {
        onError?("We couldn't load your photo.")
    }
}

@MainActor
final class AvatarViewModel {
    let parent: ProfileViewModel

    init(parent: ProfileViewModel) {
        self.parent = parent
    }

    func downloadFailed() {
        parent.avatarFailed()
    }
}

final class ProfileViewController: UIViewController, ProfileViewModelDelegate {
    private let viewModel = ProfileViewModel()
    private let nameLabel = UILabel()
    private var onRetry: (() -> Void)?

    lazy var greeting: () -> String = {
        "Hello, \(self.viewModel.name)"
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        viewModel.delegate = self
        viewModel.onError = { message in
            self.showError(message)
        }
        onRetry = {
            self.viewModel.load()
        }
        viewModel.load()
    }

    func profileDidLoad(name: String) {
        nameLabel.text = greeting()
    }

    private func showError(_ message: String) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Retry", style: .default) { _ in self.onRetry?() })
        present(alert, animated: true)
    }

    deinit {
        print("ProfileViewController deinit")
    }
}
```

It compiles in Swift 6 mode with no warnings (checked). Swift 6 checks for data races, not for
leaks — the compiler is no help here.

::: A hint, if you're stuck
- Draw arrows. Every stored property that holds an object or a closure is an arrow from its owner.
- A closure that mentions `self` holds an arrow to `self` too.
- Look for any path of arrows that leads back to where it started.
- Try writing `weak` in front of `delegate`. What does the compiler say?
:::

::: The key — what I expect a senior to find
1. **A strong delegate.** Controller → view model → `delegate` → controller. A delegate should be
   `weak`, but here `weak` won't even compile: *'weak' must not be applied to non-class-bound 'any
   ProfileViewModelDelegate'; consider adding a protocol conformance that has a class bound*
   (verified). Only class instances have reference counts, so the protocol must say "classes only"
   with `: AnyObject`. Note that `@MainActor` on the protocol doesn't do that — a struct can still
   conform.
2. **`onError` captures `self` strongly.** Controller → view model → `onError` closure →
   controller. Capture `[weak self]`.
3. **`onRetry` is stored on `self` and captures `self`.** A one-object loop: controller → closure →
   controller. Capture `[weak self]` — or better, don't store a closure for something a method
   already does.
4. **The `lazy var` closure captures `self`.** `greeting` is a stored property holding a closure
   that mentions `self`. The loop forms the first time `greeting` is read, which here is during
   `viewDidLoad`. Compare `lazy var title: String = { … self … }()`: that closure *runs* once and
   only its result is stored, so it keeps nothing. The trailing `()` is the whole difference.
5. **The child view model owns its parent.** `ProfileViewModel` → `avatar` → `parent` →
   `ProfileViewModel`. This one leaks the two view models *even after* the controller is fixed —
   I checked with a stand-in: with only this loop left, the screen was freed and the view model
   wasn't. Make `parent` `weak`, or better, give the child a callback so it doesn't know its parent.
6. **Not a leak: the alert's `self`.** The Retry handler captures `self` strongly, and the
   controller presents the alert, so there is a loop while the alert is up. UIKit drops the alert
   when it's dismissed and the loop breaks. Say it's temporary; `[weak self]` is still tidier.
7. **The `deinit` print is the right instinct, wrong tool.** It tells you *that* it leaks, not
   *why*. The Memory Graph tells you why (see the follow-ups).
:::

::: The idea behind it
Swift frees an object when nothing holds it any more. It keeps a count of *strong references* —
ordinary `let` and `var` properties pointing at the object — and when the count drops to zero, the
object goes and its `deinit` runs. This is *automatic reference counting* (ARC).

A *retain cycle* is two or more objects each holding the next, in a loop, so none of them ever
reaches zero. The screen is closed, nobody outside can reach these objects, but they still hold
each other up — like two people leaning back to back: each stays standing only because the other
does, and neither can step away first.

Closures count too. A closure that uses `self` stores a strong reference to `self`. So if `self`
stores that closure, that's a loop of one.

To break a loop, make one arrow *non-owning*:

- `weak` — "point at it, but don't keep it alive". It must be an optional `var`, and Swift sets it
  to `nil` when the object goes. Safe.
- `unowned` — "point at it, and I promise it outlives me". Not optional. If the promise is broken
  and you use it after the object is gone, the app crashes on purpose.

Pick `weak` unless you can prove the lifetime. Delegates, parents and callbacks back to a
controller are `weak`.
:::

::: The fix
```swift
@MainActor
protocol ProfileViewModelDelegate: AnyObject {
    func profileDidLoad(name: String)
}

@MainActor
final class ProfileViewModel {
    weak var delegate: ProfileViewModelDelegate?
    var onError: ((String) -> Void)?
    private(set) var avatar: AvatarViewModel!
    private(set) var name = ""

    init() {
        avatar = AvatarViewModel(parent: self)
    }

    func load() {
        name = "Ada Lovelace"
        delegate?.profileDidLoad(name: name)
    }

    func avatarFailed() {
        onError?("We couldn't load your photo.")
    }
}

@MainActor
final class AvatarViewModel {
    private weak var parent: ProfileViewModel?

    init(parent: ProfileViewModel) {
        self.parent = parent
    }

    func downloadFailed() {
        parent?.avatarFailed()
    }
}

final class ProfileViewController: UIViewController, ProfileViewModelDelegate {
    private let viewModel = ProfileViewModel()
    private let nameLabel = UILabel()

    override func viewDidLoad() {
        super.viewDidLoad()
        viewModel.delegate = self
        viewModel.onError = { [weak self] message in
            self?.showError(message)
        }
        viewModel.load()
    }

    func profileDidLoad(name: String) {
        nameLabel.text = greeting(for: name)
    }

    private func greeting(for name: String) -> String {
        "Hello, \(name)"
    }

    private func retry() {
        viewModel.load()
    }

    private func showError(_ message: String) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Retry", style: .default) { [weak self] _ in
            self?.retry()
        })
        present(alert, animated: true)
    }
}
```

The test I'd add, which typechecks with Swift Testing against the iOS SDK:

```swift
@MainActor
struct ProfileViewControllerTests {
    @Test func screenIsReleasedAfterItLoads() {
        weak var weakScreen: ProfileViewController?
        autoreleasepool {
            let screen = ProfileViewController()
            screen.loadViewIfNeeded()          // runs viewDidLoad, so every closure is wired
            weakScreen = screen
        }
        #expect(weakScreen == nil)
    }
}
```

I ran the same steps as a small program in the iOS simulator: the original controller printed
`screen released: false`, the fixed one `screen released: true`.

And here is the Foundation-only stand-in, plain classes playing the controller and the two view
models, with all five loops fixed:

```swift
protocol ViewModelDelegate: AnyObject { func didLoad(name: String) }

final class ViewModel {
    weak var delegate: ViewModelDelegate?
    var onError: ((String) -> Void)?
    private(set) var child: Child!
    private(set) var name = ""
    init() { child = Child(parent: self) }
    func load() { name = "Ada"; delegate?.didLoad(name: name) }
    deinit { print("ViewModel deinit") }
}

final class Child {
    weak var parent: ViewModel?
    init(parent: ViewModel) { self.parent = parent }
    deinit { print("Child deinit") }
}

final class Screen: ViewModelDelegate {
    let viewModel = ViewModel()
    var onRetry: (() -> Void)?
    lazy var greeting: () -> String = { [unowned self] in "Hello, \(self.viewModel.name)" }
    lazy var title: String = { "Profile of \(self.viewModel.name)" }()   // runs once, keeps nothing
    func viewDidLoad() {
        viewModel.delegate = self
        viewModel.onError = { [weak self] message in self?.show(message) }
        onRetry = { [weak self] in self?.viewModel.load() }
        viewModel.load()
    }
    func didLoad(name: String) { _ = greeting(); _ = title }
    func show(_ message: String) {}
    deinit { print("Screen deinit") }
}

weak var weakScreen: Screen?
weak var weakViewModel: ViewModel?
do {
    let screen = Screen()
    screen.viewDidLoad()
    weakScreen = screen
    weakViewModel = screen.viewModel
}
print("screen freed: \(weakScreen == nil), view model freed: \(weakViewModel == nil)")
```

```text
Screen deinit
ViewModel deinit
Child deinit
screen freed: true, view model freed: true
```

Compiled with `swiftc -swift-version 6`, no warnings. The same program with the original strong
references printed only `screen freed: false, view model freed: false` — no `deinit` at all. With
everything fixed except `Child.parent`, it printed `Screen deinit` and then `screen freed: true,
view model freed: false`: loop 5 is independent of the other four.

Why each piece:

- **`: AnyObject` on the protocol** — makes `weak var delegate` legal. `@MainActor` stays, because
  the controller conforms on the main actor.
- **`weak var delegate`** — the view model talks to the controller without owning it.
- **`[weak self]` in `onError`** — the view model owns the closure, so the closure must not own
  the controller.
- **`onRetry` and the lazy `greeting` became methods** — a method doesn't store anything, so
  there's no loop to break. The cleanest fix for a self-capturing stored closure is often to not
  store it.
- **`private weak var parent`** — the parent owns the child, never the other way round. `unowned`
  would also be correct here, since the parent creates and outlives the child, but `weak` costs
  nothing and can't crash if someone keeps an `AvatarViewModel` around.
- **`unowned self` in the stand-in's `greeting`** — shown on purpose: the closure is stored on
  `self`, so as long as nobody copies it out, it can't outlive `self`. That's the textbook case for
  `unowned` — and the "as long as" is why `greeting` should be `private`. Copy it into another
  object, call it after the screen is gone, and `unowned` crashes.
:::

::: What I'd ask next
- *"How do you find a leak like this in a real app?"* — Open and close the screen a few times, then
  press Debug Memory Graph in Xcode. Leaked objects get a purple warning badge; select one and the
  graph draws the loop, arrow by arrow. Instruments' Leaks template finds the same loops over a
  longer session.
- *"Why the `autoreleasepool` in the test?"* — Some UIKit objects are *autoreleased*: their last
  release is deferred to the end of the current pool. Without a pool the reference can still be
  alive when `#expect` runs, and the test fails for a screen that doesn't actually leak.
- *"When is `unowned` the right choice?"* — When the referenced object is guaranteed to outlive the
  reference: a closure stored on `self` that refers to `self`, or a child that's always destroyed
  before its parent. If you can't state the guarantee in one sentence, use `weak`.
- *"Does `[weak self]` in every closure fix leaks?"* — No. It's only needed when `self` stores the
  closure, directly or through something it owns. A closure passed to `UIView.animate` or a
  one-shot network call doesn't loop; it just keeps `self` alive a little longer.
- *"Delegate or closure for view model → controller?"* — A delegate for several related events
  (one `weak` reference, one place to look); a closure for one event. Either way, the arrow back
  to the controller must not own it. In new code an `@Observable` view model avoids the back
  arrow entirely.
:::
