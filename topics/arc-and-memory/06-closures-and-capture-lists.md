---
title: Closures and capture lists
summary: Why a closure is an object, what a capture list actually captures, and when [weak self] is wrong.
minutes: 8
sources:
- Apple · Closures (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/closures/
- Apple · Automatic Reference Counting (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
- SE-0345 · if let shorthand for shadowing an existing optional variable | https://github.com/swiftlang/swift-evolution/blob/main/proposals/0345-if-let-shorthand.md
---

Chapter 5 listed the closure cycle as the most common one in modern Swift. This chapter is why it happens, which is a matter of what a closure *is*.

## A closure is an object

A closure is code plus the things it needs to run that code — the values it captured from where it was written. Those values have to live somewhere for as long as the closure might be called, so a closure that outlives its creating scope is a heap allocation: a **context** object holding the captures, reference counted exactly like a class instance.

Which means every capture is a strong reference, held by an object that you are probably storing somewhere.

```swift
final class Screen {
    var onTap: (() -> Void)?

    func setUp() {
        onTap = { self.reload() }      // context retains self; self retains context
    }
}
```

That's the cycle, and it's structural rather than accidental. Nothing about the code is careless; two entirely normal decisions — store a callback, mention `self` inside it — happen to form a loop.

> **In the library.** A closure is a note pinned to a book: *"when this is returned, do the following — and the following mentions book 412."* The note counts as a reader of 412. Pin the note inside 412 itself and you have a book whose own note keeps it borrowed forever.

## Escaping is the whole distinction

A **non-escaping** closure is guaranteed not to outlive the call it was passed to. `map`, `filter`, `sorted`, most callbacks that run before the function returns. It can live on the stack, it doesn't need to retain its captures in the same way, and **it cannot create a cycle** — it's gone before anything could observe one.

```swift
let names = users.map { $0.name }          // no self., no cycle, nothing to think about
```

An **`@escaping`** closure may be stored and called later: completion handlers, `Task` bodies, subscriptions, anything handed to a timer. It has to keep its captures alive, and Swift makes you write `self.` explicitly inside it. That requirement is the language pointing at the exact thing this chapter is about — if you're typing `self.` inside a closure, you're creating a strong reference to `self` that will live as long as the closure does.

The first question, then, is never "should I use `weak self`?" It's **does this closure escape, and who stores it?**

## What a capture list actually does

A capture list is the `[ ... ]` before the parameters. It captures the listed values **at the moment the closure is created**, rather than referring to the variable afterwards.

```swift
var count = 0
let printLater = { print(count) }          // refers to the variable
let printNow   = { [count] in print(count) }  // captured the value 0, right now

count = 42
printLater()   // 42
printNow()     // 0
```

Two separate mechanisms, and people usually meet only the memory half. Without a capture list a mutable local variable is captured **by reference** — it's promoted to a heap box that both the closure and the enclosing scope share, which is also the reason `@Sendable` closures refuse mutable captures (that's the concurrency topic's ground). With a capture list you get a copy, made once, at closure creation.

For references, the list is also where you choose the strength: `[weak self]`, `[unowned self]`, `[weak delegate, unowned store]`.

## The weak-self dance, and why it has three forms

```swift
loader.load { [weak self] result in
    guard let self else { return }        // SE-0345 shorthand, Swift 5.7+
    self.apply(result)
}
```

`[weak self]` makes `self` an optional that reads `nil` once the object is gone. The `guard` turns it back into a strong reference for the duration of this call, which is what you want: it means `self` can't die half way through the body.

There are three shapes, and they say different things.

**`guard let self else { return }`** — the object may be gone, and if it is, doing nothing is correct. Fine for "update the UI with this result".

**`self?.method()` with no guard** — same, but each mention is a separate weak read, so `self` may exist on line one and be `nil` on line three. Acceptable for a single call; a trap in a multi-step body.

**No capture list at all** — the closure keeps the object alive on purpose. This is right more often than the internet suggests. A network request whose completion writes to a database *should* keep the writer alive until it finishes; making that `weak` turns a rare race into a silently dropped save.

That's the judgement to make, and it's the same one as chapter 4: if the object dying mid-flight would make the work meaningless, use `weak` and return early. If the work must finish regardless, hold it strongly and make sure the closure doesn't get stored on the object itself.

`[unowned self]` in an escaping closure deserves suspicion. It says *this closure can never outlive self*, which for anything asynchronous means you are promising that a network response cannot arrive after the screen is dismissed. That promise is usually false, and the payoff for being right is one optional unwrap.

## Tasks capture too

`Task { }` takes a closure, so everything above applies — with one extra wrinkle worth saying out loud.

```swift
final class Screen {
    private var task: Task<Void, Never>?

    func start() {
        task = Task {                       // this closure captures self strongly
            let items = await load()
            self.show(items)
        }
    }
    deinit { task?.cancel() }
}
```

A running task holds its closure, and therefore its captures, until it completes or is cancelled. So a `Task` that mentions `self` keeps `self` alive for the duration of the work — which is often exactly what you want, and is not a leak: it ends.

It becomes a leak when you also store the task on `self`, as above, because now `self → task → closure → self` is a cycle for as long as the task runs. Two rules keep it honest: store the handle only if you intend to cancel it, and cancel from a real teardown point (`onDisappear`, a `stop()` method) rather than from `deinit`, which the cycle is preventing from ever running.

An infinite task — `for await event in stream { … }` — never completes on its own, so "it ends" stops being true and the capture becomes permanent. Those need `[weak self]` and a cancel, or the whole thing needs to be owned by something with a shorter life.

> **In the library.** A running task is a reader who has taken the book home. Nothing is wrong: they'll bring it back. It only becomes a problem when the book is what's holding their address, and the trip has no end date.

## The short version

Ask the questions in this order, and most of the difficulty disappears:

1. **Does this closure escape?** No — stop, there is nothing to do.
2. **Who stores it?** If the thing storing it is the thing it captures, that's a cycle; break it in the capture list or move the storage.
3. **If the captured object died mid-flight, should the work still finish?** Yes — capture strongly. No — `[weak self]` with a `guard`.
4. **Can I state a reason the closure cannot outlive the object?** Only then is `unowned` the honest spelling.
