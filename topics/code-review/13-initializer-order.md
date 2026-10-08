---
title: 13 · Initializer order
summary: Convenience to designated, two-phase init, the didSet that doesn't fire, an overridden method called from super.init, required and failable inits.
minutes: 15
group: What does this print?
sources:
- LeetCode Discuss · PhonePe iOS — "flow of initialization convinience to designated" | https://leetcode.com/discuss/interview-experience/1422835/
- The Swift Programming Language · Initialization | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/initialization/
---

*Shape: what does this print · Reported: PhonePe — walk through the flow of initialisation from convenience to designated · Compiled and run with Swift 6.4*

> "Walk me through the order. Every `print` — which one comes first, and does every `didSet`
> fire?"

```swift
func trace(_ label: String) -> Int {
    print("default value:", label)
    return 0
}

class Vehicle {
    var odometer = trace("odometer")
    var wheels: Int {
        didSet { print("didSet wheels =", wheels) }
    }

    init(wheels: Int) {
        print("Vehicle.init starts")
        self.wheels = wheels
        self.wheels += 1
        describe()
        print("Vehicle.init ends")
    }

    convenience init() {
        print("Vehicle.convenience starts")
        self.init(wheels: 4)
        self.wheels = 10
        print("Vehicle.convenience ends")
    }

    func describe() { print("Vehicle.describe") }
}

print("① ---")
_ = Vehicle()

class Bike: Vehicle {
    let brand: String

    init(brand: String) {
        self.brand = brand
        print("Bike phase 1 done")
        super.init(wheels: 2)
        print("Bike phase 2 starts")
        wheels = 3
    }

    override func describe() { print("Bike.describe brand =", brand) }
}

print("② ---")
_ = Bike(brand: "Brompton")

class Shape {
    let sides: Int
    required init(sides: Int) { self.sides = sides }

    init?(name: String) {
        guard name == "triangle" else { return nil }
        self.sides = 3
    }
}

final class Square: Shape {
    required init(sides: Int) {
        print("Square.init sides =", sides)
        super.init(sides: sides)
    }
}

func make<S: Shape>(_ type: S.Type) -> S { type.init(sides: 4) }

print("③ ---")
let square = make(Square.self)
print(type(of: square), square.sides)

print("④ ---")
print(Shape(name: "triangle")?.sides as Any, Shape(name: "circle")?.sides as Any)
```

And one more: does this compile?

```swift
class Bike: Vehicle {
    let brand: String

    init(brand: String) {
        describe()                                    // ⑤
        self.brand = brand
        super.init(wheels: 2)
    }
}
```

::: A hint, if you're stuck
- A convenience init can't set anything up itself — it must hand off to a designated init of the
  same class. When do the default values like `odometer` get assigned?
- Observers don't fire for some assignments made inside initializers. Which ones?
- In ②, `describe()` is called from inside `super.init`. Which `describe` runs, and has `brand`
  been set yet?
:::

::: Answers (verified output)
```text
① ---
Vehicle.convenience starts
default value: odometer
Vehicle.init starts
Vehicle.describe
Vehicle.init ends
Vehicle.convenience ends
② ---
Bike phase 1 done
default value: odometer
Vehicle.init starts
Bike.describe brand = Brompton
Vehicle.init ends
Bike phase 2 starts
didSet wheels = 3
③ ---
Square.init sides = 4
Square 4
④ ---
Optional(3) nil
```

And ⑤ doesn't compile:

```text
p13err.swift:11:9: error: 'self' used in method call 'describe' before 'super.init' call
```

- **① convenience first, then across to designated.** The convenience body runs until
  `self.init(wheels:)`. Only then does the designated init run — and it starts by assigning the
  default values (`default value: odometer`) before its own body. No `didSet` line at all:
  neither `self.wheels = wheels` nor `+= 1` in `Vehicle`'s own designated init fires it, and —
  we checked — neither does `self.wheels = 10` in `Vehicle`'s own convenience init, even though
  it runs after the object is fully built.
- **② subclass first, then up, then back down.** `Bike` sets `brand` (its phase 1), then calls
  `super.init`, which sets `Vehicle`'s properties. Inside it, `describe()` dispatches to `Bike`'s
  override — the object is a `Bike` the whole time — and `brand` is already `Brompton`, because
  Swift forces a subclass to set its own properties *before* calling `super.init`. After
  `super.init` returns, phase 2: `wheels = 3` in the *subclass* init does fire the superclass's
  `didSet`.
- **③ `required` makes an init part of the contract for every subclass.** `make` calls
  `type.init(sides:)` on a metatype it only knows is some `Shape`. That's only legal because the
  init is `required`, so every subclass must provide it — and `Square` must repeat `required`.
- **④ a failable init returns an optional.** `init?` can give up with `return nil`. The
  triangle builds, the circle doesn't.
- **⑤ won't compile.** `describe()` uses `self`, and `self` isn't fully built until phase 1 is
  done all the way up the chain. Swift refuses to let you touch it early.
:::

::: The idea behind it
Building a class instance is *two-phase initialisation*. Think of building a house floor by
floor. **Phase 1** goes up: each class, starting with the most specific, fills in the stored
properties it declared, then hands over to its parent with `super.init`. When the top class has
filled in its own properties, every property of the object has a value. **Phase 2** comes back
down: each initializer, now able to use `self` freely, can call methods and change properties.

A *designated* initializer is a main one: it fills in its own class's properties and calls up to
the parent. A *convenience* initializer is a shortcut: it must call another initializer of the
*same* class first, and only then tweak things. Delegation goes "across" for convenience inits
and "up" for designated ones.

Property observers (`willSet`/`didSet`) exist to react to *changes*. While a class is setting its
own properties during its initializers there is nothing to react to yet, so they don't fire. A
subclass setting a parent's property after `super.init` is a change the parent should hear
about — so they fire.

Swift's phase-1 rule is why ② is safe. In Objective-C, a parent's init that calls an overridden
method can reach a subclass whose properties are still `nil` or zero. Swift makes that impossible.
:::

::: How to make it unsurprising
- **Don't call overridable methods from an initializer.** ② works in Swift, but the reader has to
  know phase 1 to trust it. Make `describe` `final`, or call it after construction.
- **Don't put work you rely on in a `didSet` for a value set in `init`.** It won't run. If the
  side effect matters on first set, call it explicitly from the init too.
- **Prefer one designated init plus convenience inits.** Every path then funnels through one
  place that sets every property, which keeps the order easy to follow.
:::

::: What I'd ask next
- *"When does a subclass inherit its parent's designated inits?"* — When it defines no designated
  init of its own (and its new properties all have default values). If it implements all of the
  parent's designated inits, it also inherits the parent's convenience inits.
- *"Why must `Square` write `required` again?"* — So every subclass of `Square` is also forced to
  have it; the requirement keeps passing down the chain. A `final` class can't have subclasses,
  but the keyword is still required.
- *"Structs don't have any of this — why?"* — No inheritance, so no phase across classes. A
  struct gets a memberwise init for free, and its observers likewise don't fire for assignments
  in its own init.
- *"`init?` vs `init() throws`?"* — Use `throws` when the caller needs to know *why* it failed;
  `init?` when "it didn't work" is the whole story, like `Int("abc")`.
:::
