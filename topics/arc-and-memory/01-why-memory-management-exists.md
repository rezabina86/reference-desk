---
title: Why memory management exists
summary: What memory is, the two places a program puts things, and why one of them needs somebody to decide when things die.
minutes: 7
sources:
- Apple · Automatic Reference Counting (TSPL) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/automaticreferencecounting/
- WWDC21 · ARC in Swift&#58; Basics and beyond | https://developer.apple.com/videos/play/wwdc2021/10216/
---

Nothing in this chapter is Swift. It is the ground the rest of the topic stands on, and skipping it is why "just use `weak self`" gets passed around as folklore instead of understood as a decision.

## What memory is

A running app is given a large block of numbered slots to keep things in. Every photo, every string of text, every screen is somewhere in those slots. The number of a slot is an **address**, and a value that holds an address — a note saying *the thing you want is over there* — is a **reference**.

Two facts shape everything else.

**The block is finite.** An iPhone has a few gigabytes of it, shared between your app, the system and everything else running. iOS does not swap to disk the way a Mac does, so when the system runs short it doesn't get slower — it picks apps and terminates them. An app that keeps taking more memory and never gives any back eventually gets killed while the user is in the middle of something.

**Slots must be reused.** The app asks for space when it needs it and gives it back when it doesn't, thousands of times a second. The entire subject is one question asked over and over: *is anybody still using this, or can the space go back?*

> **In the library.** The building is your app's memory. It has a fixed number of shelves, and it is not the only library in town — the city can and does close a branch that keeps requesting more space.
>
> **A book on a shelf is an object.** That is the mapping for the whole topic: wherever you see *book*, it means one object living in memory, and nothing else ever does. A book takes up shelf space whether or not anybody is reading it.

## The two places things live

A program keeps things in two quite different places, and the difference is the reason only one half of this topic is hard.

**The stack** is scratch space belonging to one thread. Every time a function is called it gets a fresh slice for its local variables; when the function returns, the slice is discarded whole. It's fast — reserving space costs one arithmetic instruction — and it needs no thinking, because the lifetime is decided by the shape of the code. A local `Int`, a `CGPoint`, a `Bool` typically live here.

**The heap** is the shared area for things that must outlive the function that created them, or whose size isn't known in advance. Anything you can still reach after the creating function has returned lives here. Allocating from the heap is much more expensive: the runtime has to find a free region, mark it taken, and eventually hand it back.

That last word is the problem. The stack frees itself by construction. The heap does not.

> **In the library.** The stack is the desk you carry over to a chair: your own workspace, yours alone, cleared the moment you stand up. Nobody has to decide when to clear it — standing up *is* the clearing.
>
> The shelves are the heap. Anything placed there outlives your visit, can be found by other readers, and stays until somebody makes a decision about it.

In Swift, the rough split is that **structs and enums are usually stack-allocated values**, and **class instances, closures and actors always live on the heap**. "Usually" is doing real work in that sentence — a struct that is captured by a closure, or stored inside a class, lives wherever its owner lives. Chapter 7 is about what follows from that.

## Why the heap needs a decision

Say a screen loads a photo. The photo is on the heap. The screen closes. Is the photo still needed?

Nobody can answer that from inside the photo. The answer depends on whether anything else is still pointing at it — a cache, a share sheet, an upload in progress. So *something* has to keep track, and there are exactly three ways to get this wrong.

**Free it too late, or never.** The space is never reused. Do that repeatedly and the app's footprint climbs until the system terminates it. This is a **leak**.

**Free it too early.** Some other part of the app still holds the address and goes there expecting a photo. What it finds is whatever has since been written into those slots — garbage, or a different object entirely. That is a **use-after-free**, and it is the worst failure mode in the subject: it does not crash where the mistake was, it crashes somewhere unrelated, later, sometimes only on a customer's phone.

**Free it twice.** The space gets handed out to someone else after the first free, and the second free rips it away from its new owner. Same class of chaos.

> **In the library.** Pulp a book while three people are still reading it, and each of them is suddenly staring at a page of something else. They won't report *"the book was pulped"* — they will report that page 40 of the cookbook contains a tax form, which is not a problem anybody can locate.

## Two things that both get called "a memory problem"

Worth separating early, because the fixes are unrelated and the mix-up is common even among experienced engineers.

**A leak** is memory that is still *allocated* but no longer *reachable* — nothing in the running program has any way to get to it. A retain cycle is the usual cause in Swift, and that is chapters 4 to 6.

**Abandoned memory** is memory that is perfectly reachable and simply shouldn't still be there: an image cache with no limit, a log array that only ever grows, view controllers kept in an array "in case we need them". Nothing is broken, there's no cycle, nobody wrote a bug. The app just holds things it will never look at again.

Both show up as the same climbing line in Xcode's memory report. They have almost nothing else in common, and chapter 9 is about telling them apart, which is most of the work in a real investigation.

> **In the library.** A leak is a book nobody can find in the catalogue and nobody can remove, sitting on a shelf forever. Abandoned memory is a shelf of perfectly catalogued books that nobody has opened since 2019. The building is equally full either way.

## What the rest of this topic is

The question *"is anybody still using this?"* has been answered in three different ways in mainstream languages: **make the programmer say so** (C, and Objective-C before 2011), **let a runtime go and check periodically** (Java, C#, Go), or **count the owners as the program runs** (Objective-C since 2011, and Swift). Chapter 2 is why Swift picked the third, and what that choice costs — because it does cost something, and the price is paid in exactly one place: cycles.
