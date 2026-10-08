---
title: 14 · Optional of an optional
summary: Int?? from a dictionary of optionals, ?? and if let peeling one layer, map vs flatMap, try? flattening, optional chaining, and an isNil you write yourself.
minutes: 15
group: What does this print?
sources:
- LeetCode Discuss · Swiggy iOS — "Define the type of Optionals along with their cases"; implement "isNil()" | https://leetcode.com/discuss/post/4558238/swiggy-ios-developer-rejected
- SE-0230 · Flatten nested optionals resulting from try? | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0230-flatten-optional-try.md
---

*Shape: what does this print · Reported: Swiggy — define Optional's type and its cases, then implement `isNil()` · Compiled and run with Swift 6.4*

> "A dictionary where some people have no nickname. Tell me what each line prints — types
> included."

```swift
let nicknames: [String: String?] = ["ana": "Annie", "ben": nil]

let ana = nicknames["ana"]
let ben = nicknames["ben"]
let cleo = nicknames["cleo"]
print(ana as Any, ben as Any, cleo as Any)                 // ①
print(type(of: ben), ben == nil, cleo == nil)              // ②

print((ben ?? "no key") as Any, (cleo ?? "no key") as Any) // ③
print((ben ?? nil) ?? "no nickname")                       // ④

if let value = ben {
    print("found key, value is", value as Any)             // ⑤
} else {
    print("no such key")
}

let digits: String? = "42"
let mapped = digits.map { Int($0) }
let flat = digits.flatMap { Int($0) }
print(type(of: mapped), type(of: flat))                    // ⑥

enum ParseError: Error { case bad }
func parse(_ text: String) throws -> Int? {
    guard !text.isEmpty else { throw ParseError.bad }
    return Int(text)
}
let attempt = try? parse("x")
print(type(of: attempt), attempt as Any)                   // ⑦

struct Profile { var nickname: String? }
struct User { var profile: Profile? }
let user: User? = User(profile: Profile(nickname: nil))
print(type(of: user?.profile?.nickname))                   // ⑧

extension Optional {
    var isNil: Bool {
        if case .none = self { return true }
        return false
    }
}
print(ben.isNil, cleo.isNil, ben?.isNil as Any)            // ⑨
```

::: A hint, if you're stuck
- A dictionary subscript returns `Value?`. Here `Value` is already `String?`.
- There are two ways to be "nothing" here: no key, or a key whose value is `nil`. Which lines can
  tell them apart?
- `??`, `if let` and `?.` each remove exactly one layer.
- `Optional` is an ordinary enum. What are its two cases?
:::

::: Answers (verified output)
```text
Optional(Optional("Annie")) Optional(nil) nil
Optional<Optional<String>> false true
nil Optional("no key")
no nickname
found key, value is nil
Optional<Optional<Int>> Optional<Int>
Optional<Int> nil
Optional<String>
false true Optional(true)
```

- **① three different shapes.** The subscript wraps the stored value in one more optional, so
  the type is `String??`. `ana` is `.some(.some("Annie"))`. `ben` is `.some(.none)` — "the key
  exists, and its value is nil" — printed `Optional(nil)`. `cleo` is `.none` — no key at all.
- **② `ben == nil` is `false`.** Only the outer layer is compared with `nil`, and `ben`'s outer
  layer is `.some`. This is the line that catches people.
- **③ `nil Optional("no key")`.** `??` peels one layer. For `ben` it peels to the inner value,
  which is `nil`. For `cleo` it uses the default — but the result type is `String?` (that's the
  overload that fits a `String??` on the left), so the default comes back wrapped.
- **④ `no nickname`.** Two `??`s peel two layers. Quick, but it erases the difference between
  "no key" and "no nickname".
- **⑤ `found key, value is nil`.** `if let` also peels one layer. It succeeds for `ben` because
  the key exists, and binds `value` as a `String?` that is `nil`. Code that reads "found it" here
  and carries on is the real-world bug.
- **⑥ `map` wraps, `flatMap` flattens.** `Int($0)` already returns `Int?`. `map` wraps that
  again: `Int??`. `flatMap` expects the closure to return an optional and doesn't add a layer: `Int?`.
- **⑦ `Optional<Int> nil` — `try?` flattens.** Since Swift 5 (SE-0230), `try?` on something
  that returns `Int?` gives `Int?`, not `Int??`. We also compiled the same file with
  `-swift-version 4`, where this line prints `Optional<Optional<Int>> Optional(nil)`. The cost
  of flattening: `nil` here can mean "it threw" or "it returned nil", and you can't tell which.
- **⑧ `Optional<String>`.** Optional chaining never stacks. However many `?.` you chain, the
  result has exactly one optional layer around the last property's type.
- **⑨ `false true Optional(true)`.** `ben.isNil` checks the outer layer: `.some`, so `false`.
  `cleo.isNil` is `true`. `ben?.isNil` first peels one layer, then calls `isNil` on the inner
  `String?`, which is `nil` — `true`, wrapped by the chain into `Optional(true)`.
:::

::: The idea behind it
`Optional` isn't magic. It's a plain generic enum in the standard library:

```swift
enum Optional<Wrapped> {
    case none
    case some(Wrapped)
}
```

`String?` is shorthand for `Optional<String>`, and `nil` is shorthand for `.none`. Because
`Wrapped` can be any type, it can be another optional: `String??` is
`Optional<Optional<String>>`, a box that may contain a box that may contain a string.

Think of a parcel. An empty outer box means "no parcel came" — no key. An outer box with an
empty inner box means "a parcel came, and it was empty on purpose" — the key exists, set to
`nil`. Both are "no string", but they mean different things.

Every unwrapping tool — `if let`, `guard let`, `??`, `?.`, `!` — opens exactly one box. To get
the string out of `String??` you need two. That's the whole chapter: count the boxes, then count
the openings.

Swiggy's `isNil` is just a pattern match on the enum's case, as in ⑨. `self == nil` also works,
because Swift lets any optional be compared with the `nil` literal.
:::

::: How to make it unsurprising
- **Avoid `[Key: Value?]`.** Use `[String: String]` and let "no key" mean "no nickname". If you
  really need three states (unknown, none, some), write an enum with three named cases — nobody
  has to count boxes.
- **Never assign `nil` through the subscript of such a dictionary.** `nicknames["ben"] = nil`
  *removes* the key. To store a `nil` value you need `.some(nil)` or `updateValue(nil, forKey:)`.
- **Prefer `flatMap` when the transform can fail**, and treat a `try?` on a function that already
  returns an optional as a review comment — `do`/`catch` keeps the two failures apart.
:::

::: What I'd ask next
- *"`nicknames["ben"] = nil` — what happens?"* — The key is removed: the count goes from 2 to 1.
  We ran it. `.some(nil)` or `updateValue(nil, forKey:)` stores a `nil` value instead.
- *"How do you unwrap `ben` fully in one statement?"* — `if case let name?? = ben`, or
  `if let inner = ben, let name = inner`. Or `ben ?? nil` to flatten to `String?` first.
- *"What does `!` do on `String??` when the key is missing?"* — Crashes. When the key exists with
  `nil`, a single `!` succeeds and gives you a `String?` that is still `nil`.
- *"What is `compactMap` on an array of `String?`?"* — It drops the `nil`s and returns `[String]`.
  On an array of `String??` it peels just one layer, so a `.some(nil)` survives as a `nil` element.
:::
