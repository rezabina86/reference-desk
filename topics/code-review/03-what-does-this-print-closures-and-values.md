---
title: 03 · What does this print? — closures and values
summary: Value vs reference semantics, capture lists, loop captures and defer — five lines of output to predict.
minutes: 15
group: What does this print?
sources:
- Glassdoor · Revolut Senior iOS — escaping vs non-escaping closures | https://www.glassdoor.com/Interview/Revolut-Senior-IOS-Developer-Interview-Questions-EI_IE1176471.0,7_KO8,28.htm
- Glassdoor · Delivery Hero Senior iOS — retain-cycle scenarios | https://www.glassdoor.com/Interview/Delivery-Hero-Senior-IOS-Developer-Interview-Questions-EI_IE504556.0,13_KO14,34.htm
- The Swift Programming Language · Closures — capturing values | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/closures/
---

*Shape: what does this print · Reported: closure capture and escaping questions at Revolut and
Delivery Hero · Compiled and run with Swift 6.2*

> "Line by line — what prints?"

```swift
struct Counter { var value = 0 }
var a = Counter()
var b = a
b.value += 1
print(a.value, b.value)                          // ①

var x = 1
let byReference = { print("ref", x) }
let byValue = { [x] in print("value", x) }
x = 2
byReference()                                    // ②
byValue()                                        // ③

final class Box { var value = 0 }
let box = Box()
let snapshot = { [box] in print("box", box.value) }
box.value = 5
snapshot()                                       // ④

var handlers: [() -> Void] = []
for i in 0..<3 { handlers.append { print("loop", i) } }
handlers.forEach { $0() }                        // ⑤

func f() -> Int {
    var n = 1
    defer { n += 10; print("defer", n) }
    n += 1
    return n
}
print("returned", f())                           // ⑥
```

::: A hint, if you're stuck
- Is `Counter` a value type or a reference type? What does `b = a` copy?
- A closure without a capture list sees the variable. With `[x]` it takes a copy — but a copy of what, for a class?
- When exactly does `defer` run, compared with `return`?
:::

::: Answers (verified output)
```text
0 1
ref 2
value 1
box 5
loop 0
loop 1
loop 2
defer 12
returned 2
```

- **①** Structs are values: `b = a` copies. Changing `b` leaves `a` alone.
- **②** A closure captures the *variable*, not its value at the time. It sees `x = 2`.
- **③** A capture list copies the value when the closure is *created*: `1`.
- **④** The trap. `[box]` copies the *reference*. It's still the same object, so it sees `5`.
  Capture lists snapshot values, not objects.
- **⑤** Each loop iteration has its own `i`, so `0 1 2`. (In some other languages this prints
  `3 3 3`; saying so shows you know why Swift doesn't.)
- **⑥** `return n` evaluates `2` first, then `defer` runs and changes `n` to `12` — too late to
  affect the returned value. Prints `defer 12` before `returned 2`, because `f()` must finish
  before the outer `print` can.
:::

::: The idea behind it
Swift has two kinds of types. A *value type* (a struct or an enum) behaves like a photocopy:
assign it and you get an independent copy. A *reference type* (a class) behaves like a house
address: copy it and you have two slips of paper pointing at the same house. Paint the house through
one slip and the other slip sees the new colour.

Closures *capture* the outside variables they use. By default they capture the variable itself, so
they see any later change to it. A *capture list* like `[x]` takes a copy at the moment the closure
is created. But copying a class reference copies the address, not the house — so the closure still
sees changes made to the object. That is exactly why `[weak self]` works: it changes *how* the
closure holds the address (without keeping the house standing), not what's inside.

`defer` runs when the function is on its way out — after the return value has already been worked
out. Changing a variable in `defer` can't change what was returned.
:::

::: What I'm really scoring
④ separates people who memorised "capture lists copy" from people who understand that a class
reference is itself the value being copied. That same understanding is what makes `[weak self]`
make sense — you're choosing how the closure holds the reference, not copying the object.
:::

::: What I'd ask next
- *"What makes a closure escaping, and why does Swift make you say so?"* — It can be called after
  the function returns (stored, or passed to async work). Escaping closures can create retain
  cycles and need explicit `self`; non-escaping ones can't outlive the call, so the compiler can
  optimise them and lets you omit `self`. Since Swift 5.3 (SE-0269) you can also omit it in an
  escaping closure that captures `[self]` explicitly, or when `self` is a struct or enum.
- *"When is `[weak self]` unnecessary?"* — When the closure isn't stored by anything `self` owns:
  `UIView.animate`, `map`, a one-shot request you're happy to let finish.
- *"`weak` vs `unowned`?"* — `unowned` crashes if the object is gone; use it only when the
  closure provably can't outlive the object.
- *"Change `Counter` to a class — what does ① print?"* — `1 1`: both names point at one object.
:::
