---
title: Finding memory problems
summary: Leaked, abandoned, useful — telling them apart, and the tool for each.
minutes: 8
sources:
- WWDC24 · Analyze heap memory | https://developer.apple.com/videos/play/wwdc2024/10173/
- WWDC18 · iOS Memory Deep Dive | https://developer.apple.com/videos/play/wwdc2018/416/
- Apple · Gathering information about memory use | https://developer.apple.com/documentation/xcode/gathering-information-about-memory-use
---

Everything so far tells you what *should* happen. This chapter is how you find out what did.

## Start by classifying, not by tooling

WWDC24 splits heap memory three ways, and picking the right bucket first saves most of the time an investigation takes.

**Useful** — reachable, and genuinely needed.

**Abandoned** — reachable, not needed. Caches with no bound, singletons accumulating, arrays of "recent" things, a coordinator that never drops a child. No bug in the counting sense; the program is doing exactly what it was told.

**Leaked** — not reachable at all, and therefore impossible to free. Retain cycles, chapters 4 to 6.

The symptom is identical: the memory graph in Xcode's debug navigator climbs and never comes back down. The causes are unrelated. **Abandoned memory is far more common in real apps than leaks**, and the reflex to hunt for a cycle is why an afternoon disappears into the wrong half of the problem.

It's also worth separating the *shape* of the growth, because it points at different causes:

- **Transient spikes** — a burst of allocation that comes back down but goes high enough to get the app killed, or to fragment the heap. Usually a batch operation: decoding many images, a large import, a loop creating temporaries.
- **Persistent growth** — a line that steps up with each cycle of some user action and never returns. Usually leaked or abandoned.

> **In the library.** Useful: the books in use. Abandoned: perfectly catalogued shelves nobody has opened since 2019. Leaked: books not in the catalogue that nobody can remove. Transient: the pile that appears every time a delivery is processed and clears afterwards — unless a delivery is big enough to block the corridors.

## The five-minute pass, in order

**1. `deinit` printing.** Put a `print` in the `deinit` of the type you suspect, push the screen, pop it, watch. Nothing printed means something still holds it. This costs thirty seconds and answers the question surprisingly often.

**2. The Memory Graph Debugger.** Run, reach the state, dismiss the screen, press the memory-graph button in the debug bar. Filter for your type. If instances are still there, select one and read the arrows pointing *at* it: that's every strong reference keeping it alive, including `closure context` nodes, which is how a captured `self` names itself.

Turn on **Malloc Stack Logging** first (Edit Scheme → Run → Diagnostics → Malloc Stack Logging, "Live Allocations Only"). Without it the graph shows you *who* holds the object; with it you also get the backtrace of where each allocation came from, which is the difference between "an array of view models holds it" and "*this line* put it there".

Purple badges mark what Xcode believes is leaked. Treat them as a hint: the graph can miss cycles that go through non-Swift memory, and can flag things that are merely abandoned.

**3. Instruments — Leaks.** Same idea, over time and without a debugger attached. Useful for "this leaks somewhere in a long session" rather than "this one screen leaks".

**4. Instruments — Allocations, with generations.** The tool for persistent growth. Reach a steady state, press **Mark Generation**, perform one complete cycle of the suspect action, return to the same state, mark again. Repeat three or four times. Each generation shows what was allocated since the last mark and is *still alive* — so anything that keeps appearing generation after generation is your growth, with its allocation backtrace attached. This is the single most effective memory technique in the toolbox, and it finds abandoned memory, which the Leaks instrument by definition cannot.

**5. Command line, when the app is on a device and you can't attach.** `leaks`, `heap`, `vmmap` and `malloc_history` do from a terminal what the graph does in Xcode.

## Two specific things to look for

**Autorelease pools, for transient spikes.** Objective-C APIs return objects that are released later, when the enclosing autorelease pool drains — which for the main thread means at the end of the current run-loop pass. A loop that calls into Cocoa a thousand times therefore accumulates a thousand objects before *any* of them is released.

```swift
for url in thousandsOfURLs {
    autoreleasepool {
        let image = UIImage(contentsOfFile: url.path)   // ObjC underneath
        process(image)
    }                                                   // drains here, every iteration
}
```

The fix is to drain per iteration, as above. The tell is a sawtooth in the allocations graph with a peak far above the steady state, in a loop touching UIKit, Core Graphics, Foundation bridging or `NSString`/`NSData`. Pure-Swift code doesn't autorelease, which is why this is rarer than it used to be and more confusing when it happens.

**Image memory, because it's almost never the file size.** A decoded image costs roughly width × height × 4 bytes in memory regardless of how well the JPEG compressed. A 12-megapixel photo is about 48 MB decoded, from a 3 MB file. Downsample at load time (`CGImageSourceCreateThumbnailAtIndex` with `kCGImageSourceThumbnailMaxPixelSize`, or `UIGraphicsImageRenderer` at the display size) rather than loading full-size and scaling in a view — the scaling happens after the 48 MB has already been allocated.

## What "too much memory" means on iOS

There is no fixed limit. The system watches total footprint, and when it's under pressure, it terminates — largest first, background first. Your app doesn't get an exception; it gets killed, and the user sees a relaunch. `applicationDidReceiveMemoryWarning` and `didReceiveMemoryWarning` are your one chance to shed caches before that happens, and a cache that ignores them is abandoned memory with extra steps. `NSCache` responds to pressure automatically, which is the main reason to prefer it over a `Dictionary` for anything large.

Footprint is what counts, not "allocations": it includes decoded images, Metal textures, layer backing stores and framework overhead, most of which never appears in your own allocation list.

> **In the library.** The city doesn't send a warning letter when a branch gets too full. It closes the largest branch that nobody is currently standing in.

## The habit worth building

Every time you build a screen that can be pushed and popped, push it and pop it three times with the memory graph open. Thirty seconds, and it catches nearly every cycle you will ever write — at the moment when you still remember which closure you meant to capture weakly.

The rest of it — generations, malloc stack logging, `vmmap` — is for the week when the graph is climbing and nobody knows why, which is a different and rarer day.
