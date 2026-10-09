---
title: 12 · Protocol extensions — who gets called?
summary: Same method, same object, three different answers — static vs dynamic dispatch through protocol extensions and subclasses.
minutes: 15
group: What does this print?
sources:
- LeetCode Discuss · Zomato iOS — "witness table - static/dynamic dispatch" | https://leetcode.com/discuss/interview-experience/1772763/
- LeetCode Discuss · TikTok iOS — "dynamic vs static dispatch" | https://leetcode.com/discuss/interview-experience/5550559/
---

*Shape: what does this print · Reported: Zomato — witness tables and static/dynamic dispatch;
TikTok — dynamic vs static dispatch · Verified: run with Swift 6.4*

> "Every line calls a method on the same kind of object. Tell me which implementation runs each
> time — and why."

```swift
protocol Greeter {
    func greet() -> String              // a requirement
}

extension Greeter {
    func greet() -> String { "default greet" }
    func wave() -> String { "default wave" }   // NOT a requirement
}

struct Friendly: Greeter {
    func greet() -> String { "friendly greet" }
    func wave() -> String { "friendly wave" }
}

let concrete = Friendly()
let existential: any Greeter = Friendly()
print(concrete.greet(), "|", existential.greet())   // ①
print(concrete.wave(), "|", existential.wave())     // ②

func introduce<G: Greeter>(_ g: G) -> String { g.wave() }
print(introduce(concrete))                          // ③

class Base: Greeter {}                              // uses the default greet()

class Child: Base {
    func greet() -> String { "child greet" }
}

let child = Child()
let asBase: Base = child
let asGreeter: any Greeter = child
print(child.greet(), "|", asBase.greet(), "|", asGreeter.greet())   // ④
```

::: A hint, if you're stuck
- Look at what the protocol itself declares, not what the extension adds.
- For each call, ask: does the compiler know the concrete type here, or only "something that
  conforms"?
- In ④, `Child.greet` compiles without the `override` keyword. What does that tell you?
:::

::: Answers (verified output)
```text
friendly greet | friendly greet
friendly wave | default wave
default wave
child greet | default greet | default greet
```

- **① both `friendly greet`.** `greet` is a *requirement*, so every conformance records which
  function implements it. Through `any Greeter` the call looks that up at runtime and finds
  `Friendly`'s version. Same answer either way — this is the case that behaves as people expect.
- **② `friendly wave | default wave`.** `wave` lives only in the extension. Through the concrete
  type, the compiler sees `Friendly.wave` and calls it. Through `any Greeter`, the compiler only
  knows "some Greeter", and the protocol has no `wave` slot to look up — so it calls the one
  function it can see, the extension's, chosen at compile time. Same object, different answer.
- **③ `default wave`.** Generics don't rescue it. Inside `introduce`, `G` is only known to be a
  `Greeter`, so `g.wave()` binds to the extension at compile time, exactly as in ②.
- **④ `child greet | default greet | default greet`.** The gotcha. When `Base` conformed, it
  had no `greet` of its own, so its conformance recorded the extension's default — and that
  record is shared by subclasses. `Child.greet` is a *new* method, not an override (the compiler
  didn't ask for `override` because `Base` has no `greet` to override). Through `any Greeter`
  the lookup finds `Base`'s record: default. Through `Base`, there's no class method to call, so
  it falls back to the extension: default. Only the static type `Child` finds `child greet`.
:::

::: The idea behind it
*Dispatch* is how a call finds the code to run. *Static dispatch* means the compiler picks the
function while building the app, from the type it can see. *Dynamic dispatch* means the choice
waits until the program runs and looks at the actual object.

Swift does dynamic dispatch with lookup tables. A class has a *vtable*: a list of its overridable
methods, which a subclass copies and edits when it overrides one. A protocol conformance has a
*witness table*: for each requirement of the protocol, "this is the function that satisfies it
for this type". It's like a phone directory per company — call "support" at any company and the
directory says which person picks up.

The rule that explains every line above: **only requirements get a directory entry.** A method
added in an extension but not declared in the protocol has no entry, so through the protocol
type there's nothing to look up and the compiler calls the extension directly. And a witness
table entry is filled in once, when the type conforms — a subclass adding a same-named method
later doesn't edit it.

`final` on a class or method says "nobody will override this", so the compiler can skip the
table and call the function directly. That's faster, and it removes the guessing.
:::

::: How to make it unsurprising
```swift
protocol Greeter {
    func greet() -> String
    func wave() -> String                // promoted to a requirement
}

extension Greeter {
    func greet() -> String { "default greet" }
    func wave() -> String { "default wave" }
}

struct Friendly: Greeter {
    func greet() -> String { "friendly greet" }
    func wave() -> String { "friendly wave" }
}

let existential: any Greeter = Friendly()
print(existential.wave())                // friendly wave

class Base: Greeter {
    func greet() -> String { "base greet" }   // the class owns the witness
}

class Child: Base {
    override func greet() -> String { "child greet" }
}

let child = Child()
let asBase: Base = child
let asGreeter: any Greeter = child
print(child.greet(), "|", asBase.greet(), "|", asGreeter.greet())
// child greet | child greet | child greet
```

Why each piece:
- **Declare anything a conformer may customise in the protocol body.** Then it gets a witness
  table entry and dispatches dynamically everywhere. Extension-only methods should be pure
  helpers built from requirements, never something a type "overrides".
- **A class that wants subclasses to customise a protocol method must implement it itself.**
  Then the witness points at a class method, which goes through the vtable, so `override` works
  through every static type. The required `override` keyword is the compiler confirming it.
- **Mark classes `final` when nobody should subclass them.** It turns a silent shadowing bug into
  a compile error.
:::

::: What I'm really scoring
One rule, applied every time: a protocol *requirement* is looked up at runtime; a method that only
lives in an extension is picked at compile time from the type the compiler can see. Most candidates
get ① and ②. ④ is the separator — the strong answer spots that `Child.greet` has no `override`
and says what that means. In a real review, that missing keyword is the line I'd want flagged.
:::

::: What I'd ask next
- *"Does `some Greeter` change ②?"* — No. `some` hides the concrete type from the caller, so the
  call still resolves against `Greeter`, and `wave` still binds to the extension.
- *"What are the dispatch kinds in Swift?"* — Static (direct call), vtable (class methods),
  witness table (protocol requirements), and Objective-C message sending (`@objc dynamic`), which
  is what KVO and method swizzling rely on.
- *"Why is static dispatch faster?"* — The call target is known, so the compiler can inline it
  and optimise across it. A table lookup is cheap, but it blocks inlining.
- *"Would a linter catch ②?"* — The compiler doesn't warn. In review, the smell is a conforming
  type implementing a method that only exists in a protocol extension — that's the line to ask about.
:::
