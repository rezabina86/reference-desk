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
wiring a view model to its controller with a delegate · Verified: snippet and fix compiled in Swift
6 mode against the iOS SDK, and the leak tests ran on the iOS Simulator, Swift 6.4*

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

It compiles in Swift 6 mode with no warnings (checked against the iOS SDK). Swift 6 checks for data races, not for
leaks — the compiler is no help here.

::: A hint, if you're stuck
- Draw arrows. Every stored property that holds an object or a closure is an arrow from its owner.
- A closure that mentions `self` holds an arrow to `self` too.
- Look for any path of arrows that leads back to where it started.
- Try writing `weak` in front of `delegate`. What does the compiler say?
:::

::: The key — what I expect a senior to find
The five leaks first — that's the reported bug — then what else I'd raise.

1. **A strong delegate.** Controller → view model → `delegate` → controller. A delegate should be
   `weak`, but here `weak` won't compile: *'weak' must not be applied to non-class-bound 'any
   ProfileViewModelDelegate'; consider adding a protocol conformance that has a class bound*
   (verified). Add `: AnyObject` to the protocol. `@MainActor` alone doesn't make it class-only.
2. **`onError` captures `self` strongly.** Controller → view model → `onError` closure →
   controller. Capture `[weak self]`.
3. **`onRetry` is stored on `self` and captures `self`.** A loop of one: controller → closure →
   controller. Better than `[weak self]`: don't store a closure for something a method already does.
4. **The `lazy var` closure captures `self`.** `greeting` stores a closure that mentions `self`; the
   loop forms the first time it's read, during `viewDidLoad`. Compare `lazy var title: String =
   { … self … }()`: that closure *runs* once and only its result is stored. The `()` is the whole
   difference.
5. **The child view model owns its parent.** `ProfileViewModel` → `avatar` → `parent` →
   `ProfileViewModel`. This leaks both view models even after the controller is fixed — I checked:
   with only this loop left, the screen was freed and its view model wasn't. Make `parent` `weak`.
6. **Not a leak: the alert's `self`.** The Retry handler captures `self` while the controller
   presents the alert. UIKit drops the alert on dismiss, so the loop is temporary. `[weak self]` is
   still tidier.
7. **`nameLabel` is never added to the view.** If this is the whole screen, the name never appears
   at all.
8. **`profileDidLoad(name:)` ignores its argument.** It reads `viewModel.name` through the
   `greeting` closure instead. Two sources for one value; use the `name` you were given.
9. **The view model is built inside the controller.** `private let viewModel = ProfileViewModel()`
   means no test can hand in a fake. Inject it.
10. **`avatar: AvatarViewModel!` exists only to pass `self` in `init`.** The force-unwrapped
    optional is a sign the child shouldn't know its parent. Give the child an `onFailure` callback.
11. **`delegate`, `onError` and `greeting` are publicly writable.** Any caller can swap them out.
    Make what isn't API `private`.
12. **Two callback styles on one view model.** A delegate for loading, a closure for errors. Pick
    one, so there is one place to look.
13. **User-facing copy in the view model, not localised.** "We couldn't load your photo." belongs
    in a string catalog, reached through `String(localized:)`.
14. **The `deinit` print is the right instinct, wrong tool.** It tells you *that* it leaks, not
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
Same types, same shape. Only the lines marked with a key number change.

```swift
@MainActor
protocol ProfileViewModelDelegate: AnyObject {                  // key 1
    func profileDidLoad(name: String)
}

@MainActor
final class ProfileViewModel {
    weak var delegate: ProfileViewModelDelegate?                // key 1
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
    private weak var parent: ProfileViewModel?                  // key 5

    init(parent: ProfileViewModel) {
        self.parent = parent
    }

    func downloadFailed() {
        parent?.avatarFailed()                                  // key 5
    }
}

final class ProfileViewController: UIViewController, ProfileViewModelDelegate {
    private let viewModel = ProfileViewModel()
    private let nameLabel = UILabel()
    // keys 3, 4: the stored onRetry and the lazy greeting closure are gone
    override func viewDidLoad() {
        super.viewDidLoad()
        viewModel.delegate = self
        viewModel.onError = { [weak self] message in            // key 2
            self?.showError(message)
        }
        viewModel.load()
    }

    func profileDidLoad(name: String) {
        nameLabel.text = "Hello, \(name)"                       // key 4
    }

    private func showError(_ message: String) {
        let alert = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "Retry", style: .default) { [weak self] _ in
            self?.viewModel.load()                              // keys 3, 6
        })
        present(alert, animated: true)
    }

    deinit {
        print("ProfileViewController deinit")
    }
}
```

**Said out loud, not coded:** give `AvatarViewModel` a callback so it doesn't know its parent;
inject the view model; one callback style (or an `@Observable` view model); localised copy; add
`nameLabel` to the layout.

Why each piece:

- **`: AnyObject` on the protocol** — makes `weak var delegate` legal. `@MainActor` stays, because
  the controller conforms on the main actor.
- **`onRetry` and `greeting` are gone, not patched** — a method or an inline string stores
  nothing, so there's no loop to break.
- **`weak` for `parent`, not `unowned`** — the parent creates and outlives the child, so `unowned`
  would work, but `weak` costs nothing and can't crash if someone keeps the child around.
- **`[weak self]` in the alert** — not needed for the leak (key 6), but it keeps the rule simple.
:::

::: Now write the tests
> "Good. How do I know it doesn't come back next sprint? Write me the tests."

**What I'd test, and why**

1. **The screen is freed after it loads.** `loadViewIfNeeded()` runs `viewDidLoad`, so every
   closure is wired; then a *weak reference* — one that doesn't keep the object alive — must be
   `nil`. Any of loops 1–4 makes it fail.
2. **The view model is freed with the screen.** This catches loop 5 (child → parent), which leaks
   the view models even when the screen itself is freed.
3. **The child doesn't keep its parent alive** — even while something else still holds the child,
   and calling it afterwards is safe.

Not unit-tested: the alert's Retry closure. Presenting an alert needs a real window on screen, so
its `[weak self]` is checked in review and with the Memory Graph.

**The seam.** Leak tests need no fakes — just a weak reference and an `autoreleasepool`, which makes
UIKit's deferred releases happen before the check. The view model is private, so the test reads it
with `Mirror`, Swift's built-in way to look at an object's stored properties, rather than widening
the screen's API for a test.

```swift
import Testing
import UIKit

extension ProfileViewController {
    // The view model is private. Mirror reads it without widening the screen's API.
    var viewModelForTest: ProfileViewModel? {
        Mirror(reflecting: self).descendant("viewModel") as? ProfileViewModel
    }
}

@MainActor
struct ProfileLeakTests {
    @Test func screenIsReleasedAfterItLoads() {
        weak var weakScreen: ProfileViewController?
        autoreleasepool {
            let screen = ProfileViewController()
            screen.loadViewIfNeeded()          // runs viewDidLoad, so every closure is wired
            weakScreen = screen
        }
        #expect(weakScreen == nil)
    }

    @Test func viewModelIsReleasedWithTheScreen() {
        weak var weakViewModel: ProfileViewModel?
        autoreleasepool {
            let screen = ProfileViewController()
            screen.loadViewIfNeeded()
            weakViewModel = screen.viewModelForTest
        }
        #expect(weakViewModel == nil)
    }

    @Test func childDoesNotKeepItsParentAlive() {
        // Given someone still holds the child, say an image download
        var child: AvatarViewModel?
        weak var weakParent: ProfileViewModel?
        autoreleasepool {
            let parent = ProfileViewModel()
            weakParent = parent
            child = parent.avatar
        }

        // Then the parent is freed anyway, and calling the child is still safe
        #expect(weakParent == nil)
        child?.downloadFailed()
    }
}
```

Ran on the iOS Simulator (Swift 6 mode): 3 tests, all passed.
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
  reference. The textbook case is a closure stored on `self` that refers to `self`:
  `lazy var greeting = { [unowned self] in "Hello, \(viewModel.name)" }` can't outlive the screen — as long
  as nobody copies it out. Copy it into another object, call it after the screen is gone, and
  `unowned` crashes. If you can't state the guarantee in one sentence, use `weak`.
- *"Does `[weak self]` in every closure fix leaks?"* — No. It's only needed when `self` stores the
  closure, directly or through something it owns. A closure passed to `UIView.animate` or a
  one-shot network call doesn't loop; it just keeps `self` alive a little longer.
- *"Delegate or closure for view model → controller?"* — A delegate for several related events
  (one `weak` reference, one place to look); a closure for one event. Either way, the arrow back
  to the controller must not own it. In new code an `@Observable` view model avoids the back
  arrow entirely.
:::
