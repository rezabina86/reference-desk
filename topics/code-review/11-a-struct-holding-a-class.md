---
title: 11 · A struct holding a class
summary: Copy a struct that holds a class, a class that holds a struct, an array of objects and a copy-on-write type — then count the instances.
minutes: 15
group: What does this print?
sources:
- LeetCode Discuss · Zomato iOS — "how many instance would be created when copying objects… structure containing class as property and vice versa" | https://leetcode.com/discuss/interview-experience/1772763/
- LeetCode Discuss · Practo iOS — "Explain the copy on write" | https://leetcode.com/discuss/post/2062561/
---

*Shape: what does this print · Reported: Zomato — how many instances after copying a struct that holds a class, and the reverse; Practo — explain copy-on-write · Compiled and run with Swift 6.4*

> "Four small blocks. Tell me what prints, line by line — and at the end, how many objects exist."

```swift
final class Engine {
    let name: String
    var rpm = 0
    init(_ name: String) {
        self.name = name
        print("init engine", name)
    }
}

struct Car {
    var engine: Engine
    var speed = 0
}

let car1 = Car(engine: Engine("V8"))
var car2 = car1
car2.speed = 100
car2.engine.rpm = 3000
print(car1.speed, car1.engine.rpm, car1.engine === car2.engine)   // ①

struct Address { var city: String }

final class Person {
    var address: Address
    init(_ address: Address) { self.address = address }
}

let p1 = Person(Address(city: "Berlin"))
let p2 = p1
var saved = p1.address
saved.city = "Paris"
p2.address.city = "Munich"
print(p1.address.city, saved.city)                                 // ②

var garage = [Engine("A"), Engine("B")]
var copy = garage
copy[0].rpm = 900
copy.append(Engine("C"))
print(garage.count, copy.count, garage[0].rpm)                     // ③

final class Storage {
    var items: [String]
    init(_ items: [String]) { self.items = items }
}

struct Notes {
    private var storage = Storage([])
    var items: [String] { storage.items }

    mutating func add(_ note: String) {
        if !isKnownUniquelyReferenced(&storage) {
            print("copying storage")
            storage = Storage(storage.items)
        }
        storage.items.append(note)
    }
}

var draft = Notes()
draft.add("a")
var shared = draft
shared.add("b")
shared.add("c")
print(draft.items, shared.items)                                   // ④
```

::: A hint, if you're stuck
- Copying a struct copies each of its fields. Ask what a field of class type actually *holds*.
- `let` on a struct freezes its fields. Does it freeze the object a field points at?
- Count the `init engine` lines. Each one is exactly one new object — nothing else creates one.
- In ④, ask how many variables point at the `Storage` object at the moment each `add` runs.
:::

::: Answers (verified output)
```text
init engine V8
0 3000 true
Munich Paris
init engine A
init engine B
init engine C
2 3 900
copying storage
["a"] ["a", "b", "c"]
```

- **① `0 3000 true`.** `var car2 = car1` copies the struct: `speed` is copied, so `car1.speed`
  stays `0`. But the `engine` field holds a *reference* — an address of an object — and copying
  an address gives you a second pointer to the same engine, not a second engine. So the rpm change
  shows through `car1`, `===` is `true`, and `init engine V8` printed once. Note `car1` is a
  `let`: that stops you reassigning `car1.engine`, not changing the engine's insides.
- **② `Munich Paris`.** The reverse case. `p2 = p1` copies a reference — one `Person`.
  `saved = p1.address` copies the struct *value* out of the object at that moment, so `saved` is
  independent: `Paris` stays local. `p2.address.city = "Munich"` edits the one person's address in
  place, so `p1` sees it.
- **③ `2 3 900`.** `copy = garage` gives a second array *value*. Appending to `copy` doesn't
  touch `garage` (2 vs 3). But the elements are references, so `copy[0]` and `garage[0]` are the
  same `Engine` — `900` shows through. Writing `copy[0].rpm` didn't even copy the array: changing a
  property of a class element only *reads* the array to find the object. The two arrays still
  shared one buffer until `append`, and even then the copy holds references — no new engines.
  Only three `init engine` lines, for A, B and C.
- **④ one `copying storage`, then `["a"] ["a", "b", "c"]`.** The first `add` runs while `draft`
  is the only owner of its `Storage`, so it appends in place. `shared = draft` makes two owners
  of one `Storage`. The next `add` sees it's not uniquely referenced, copies, and only then
  writes. The third `add` owns its new storage alone, so no second copy. `draft` never sees `b`
  or `c` — that's value semantics, built on a class, paid for only once.
- **How many objects?** Six class instances: four `Engine`s (V8, A, B, C), one `Person`, and two
  `Storage`s (the original and the one copy). Copying a struct, a class reference or an array
  never created one by itself.
:::

::: The idea behind it
Swift has two kinds of types. A *value type* (struct, enum, tuple, `Array`, `String`) is like a
photocopy: hand someone a copy and their scribbles don't reach yours. A *reference type* (class,
actor) is like a shared Google Doc: hand someone the link and you both edit one document.

A struct is a bundle of fields, and copying it copies each field. If a field is an `Int`, you get
a new number. If a field is a class, the field only holds the *link*, so you get a new link to
the same document. That's why "a struct holding a class" behaves half like a value and half like
a reference. The struct is copied; the object isn't.

*Copy-on-write* (CoW) is the trick that makes big values cheap. Instead of copying the whole
photocopy every time you hand it over, both people share one copy until somebody wants to
scribble — and only then does that person get their own. Swift checks "am I the only owner?"
with `isKnownUniquelyReferenced`, which reads the object's reference count (how many variables
point at it). `Array`, `Dictionary` and `String` do this internally. Your own struct only gets it
if you write it, as `Notes` does.
:::

::: How to make it unsurprising
- **If the object is meant to be shared, say so in the type.** A `Car` whose engine is shared
  between copies is a surprise. Either make `Engine` a struct, or make `Car` a class so nobody
  expects copies to be independent.
- **If you need a class for storage, hide it behind CoW.** Keep the class `private`, and check
  uniqueness in every mutating method, as `Notes` does. Callers then get honest value semantics.
- **Don't expose mutable class properties from a struct.** `car2.engine.rpm = 3000` compiling on
  a copy is the bug factory; a `let` engine with no `var` inside it can't surprise anyone.
:::

::: What I'd ask next
- *"Does `var copy = garage` copy the array's memory right away?"* — No. Arrays are
  copy-on-write: both variables share one buffer until one of them mutates *the array itself*. In ③
  that's the `append` — `copy[0].rpm = 900` doesn't count, because it changes the engine, not the
  array (checked by comparing the buffers' addresses before and after). The append copies the
  references, so still no new engines.
- *"Is `Car` `Sendable`?"* — No. A struct is only `Sendable` if every stored property is. `Engine`
  is a class with a `var` and no locking, so it isn't, and neither is `Car`. Copying `Car` across threads would share the engine — a data race.
- *"Why can't `isKnownUniquelyReferenced` take a `let`?"* — It takes its argument `inout`, so the
  check and the write that follows happen on the same variable you own. Taking it `inout` also
  means the check doesn't add a temporary reference of its own, which would make the answer
  always "no".
- *"Does `===` work on the structs?"* — No. `===` asks "same object?", which only means something
  for class instances. For structs you compare contents with `==` (if `Equatable`).
:::
