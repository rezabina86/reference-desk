---
title: 18 · Core Data saved from the wrong thread
summary: A photo downloader that saves to Core Data from many threads at once — find the crashes, then answer how many managed object contexts it really needs.
minutes: 20
group: Find the bug
sources:
- LeetCode Discuss · PhonePe iOS — "downloading via multiple threads but need to save in coredata how many managed object contexts are required" | https://leetcode.com/discuss/interview-experience/1422835/
- Apple · NSManagedObjectContext — concurrency types, perform, merge policy | https://developer.apple.com/documentation/coredata/nsmanagedobjectcontext
---

*Shape: find the bug · Reported: PhonePe — "downloading via multiple threads but need to save in
Core Data, how many managed object contexts are required" · Core Data — the fix typechecks against
the iOS SDK (iOS 18 target) in Swift 6 mode with zero warnings; the snippet and the fix were also run on macOS
against a SQLite store built from a programmatic model, with and without
`-com.apple.CoreData.ConcurrencyDebug 1`*

> "Users import an album of photos. We download them in parallel and save each one to Core Data.
> It crashes in production, but never on my machine, and sometimes the album screen shows nothing
> until you relaunch. Find the bugs. And then tell me: how many managed object contexts does this
> need?"

```swift
import CoreData

final class PhotoDownloader {
    private let container: NSPersistentContainer
    var onSaved: ((NSManagedObject) -> Void)?

    init(container: NSPersistentContainer) {
        self.container = container
    }

    func download(_ urls: [URL], into album: NSManagedObject) {
        for url in urls {
            DispatchQueue.global().async {
                guard let data = try? Data(contentsOf: url) else { return }

                let context = NSManagedObjectContext(concurrencyType: .privateQueueConcurrencyType)
                context.persistentStoreCoordinator = self.container.persistentStoreCoordinator

                let photo = NSEntityDescription.insertNewObject(forEntityName: "Photo", into: context)
                photo.setValue(url.absoluteString, forKey: "remoteURL")
                photo.setValue(data, forKey: "imageData")
                photo.setValue(album, forKey: "album")

                try? context.save()
                DispatchQueue.main.async {
                    self.onSaved?(photo)
                }
            }
        }
    }

    func markAllSeen() {
        DispatchQueue.global().async {
            let context = self.container.viewContext
            let request = NSFetchRequest<NSManagedObject>(entityName: "Photo")
            let photos = try! context.fetch(request)
            photos.forEach { $0.setValue(true, forKey: "isSeen") }
            try? context.save()
        }
    }
}
```

::: A hint, if you're stuck
- `album` was fetched by the screen. Which context does it belong to? Which context is `photo` in?
- A context created with `.privateQueueConcurrencyType` owns a queue. Is any of this code running
  on it?
- `viewContext` is a main-queue context. What thread is `markAllSeen` on?
- Each download makes its own context and saves. Who tells the screen's context that something
  changed?
:::

::: The key — what I expect a senior to find
I ran it. Without any flags, the first download crashes on every run:

```text
*** Terminating app due to uncaught exception 'NSInvalidArgumentException', reason: 'Illegal
attempt to establish a relationship 'album' between objects in different contexts …
```

`markAllSeen` is quieter, which makes it worse. On its own, with four photos stored, it ran to the
end and reported `seen: 4` — it looked like it worked. With the launch argument
`-com.apple.CoreData.ConcurrencyDebug 1` it stopped at once (exit code 133, a trap) in
`_PFAssertSafeMultiThreadedAccess_impl`, on a `com.apple.root.default-qos` thread. That's the
production crash, caught on the first run instead of the thousandth.

In Swift 6 mode the snippet still compiles, with three warnings: `self` and `album` captured in
`@Sendable` closures. The compiler can see objects crossing threads. It can't see which queue a
context is used on — that's a runtime rule.

1. **An object from one context related to an object in another.** `album` lives in the screen's
   `viewContext`; `photo` lives in a brand-new context. Core Data refuses and throws. Pass the
   album's `objectID` and look it up inside the context doing the work.
2. **`viewContext` used off the main queue.** `viewContext` is a main-queue context. Fetching and
   saving it from a global queue is undefined behaviour: it usually works, and sometimes corrupts
   the context or crashes. This is "never on my machine".
3. **A private-queue context used without `perform`.** A private context owns a serial queue, and
   every touch — insert, `setValue`, save — must run on it via `perform` or `performAndWait`.
   Here nothing does.
4. **An `NSManagedObject` handed to another thread.** `photo` belongs to a background context and
   `onSaved` hands it to main. Managed objects are tied to their context's queue; only
   `NSManagedObjectID` is safe to pass around.
5. **The screen never sees the new photos.** The `viewContext` isn't told about other contexts'
   saves, because `automaticallyMergesChangesFromParent` is off. Verified with the fix minus that
   line: the store held 15 photos and `album.photos` in the `viewContext` held 0. That's "shows
   nothing until you relaunch."
6. **One context per download, and no merge policy.** Twenty downloads make twenty contexts, each
   saving on its own. Two downloads of the same URL produce two rows, or — with a uniqueness
   constraint — a merge conflict, because the default policy is to fail the save. "Check if it
   exists, then insert" can't work across contexts saving at the same time.
7. **Errors thrown away or turned into crashes.** `try?` on `save` hides every failure, including
   the merge conflict above; `try!` on `fetch` crashes.
8. **`Data(contentsOf:)` for a network URL, one global-queue block per photo.** It blocks a thread
   per download. Two hundred photos ask GCD for far more threads than there are cores. Use
   `URLSession`'s async API.
9. **Loading every photo to flip one flag.** `markAllSeen` fetches every row into memory. A batch
   update does it in the store.
10. **Images stored inline.** Large blobs in the SQLite file make every fetch heavier. Tick *Allows
    External Storage* on the attribute.
:::

::: The idea behind it
A *managed object context* is a scratchpad. You load objects into it, change them, and `save()`
writes the changes to the store on disk. Each context belongs to exactly one queue — a line of work
done one item at a time. The main context belongs to the main queue. A *private-queue* context
owns its own background queue.

The rule is strict: a context, and every object fetched from it, may only be touched on that
context's queue. `perform { }` is how you get onto it. Breaking the rule usually works, which is the
trap: it fails one time in thousands, in production, with a crash that points nowhere useful.

So what crosses between queues? The *object ID* — a stable address for a row, like a library
book's catalogue number. You don't carry the book between rooms. You carry the number, and each
room fetches its own copy.

How many contexts? Two. One main-queue context the UI reads from. One background context that does
all the writing. Downloads can run in parallel — they don't touch Core Data. Only their saves go
through the background context, one at a time. That queue is a feature: "is this URL already
saved?" has one true answer, because only one writer is asking.

The main context then needs to hear about each save. `automaticallyMergesChangesFromParent` does
that.
:::

::: The fix
```swift
import CoreData

protocol PhotoDownloading: Sendable {
    func data(from url: URL) async throws -> Data
}

/// Owns the ONE background context all imports write through. The UI reads `viewContext`.
final class PhotoImporter: Sendable {
    private let context: NSManagedObjectContext
    private let viewContext: NSManagedObjectContext
    private let downloader: any PhotoDownloading

    @MainActor
    init(container: NSPersistentContainer, downloader: any PhotoDownloading) {
        container.viewContext.automaticallyMergesChangesFromParent = true
        let context = container.newBackgroundContext()
        context.name = "PhotoImporter"
        context.mergePolicy = NSMergePolicy.mergeByPropertyObjectTrump   // another writer, same URL: no save error
        self.context = context
        self.viewContext = container.viewContext
        self.downloader = downloader
    }

    /// Downloads in parallel, saves one at a time on the background context.
    /// Returns object IDs — safe to hand to any thread or context.
    func importPhotos(_ urls: [URL], into albumID: NSManagedObjectID) async throws -> [NSManagedObjectID] {
        try await withThrowingTaskGroup(of: (URL, Data).self) { group in
            for url in urls {
                group.addTask { [downloader] in (url, try await downloader.data(from: url)) }
            }
            var saved: [NSManagedObjectID] = []
            for try await (url, data) in group {
                saved.append(try await save(data, from: url, albumID: albumID))
            }
            return saved
        }
    }

    func markAllSeen() async throws {
        let ids = try await context.perform { [context] in
            let update = NSBatchUpdateRequest(entityName: "Photo")
            update.propertiesToUpdate = ["isSeen": true]
            update.resultType = .updatedObjectIDsResultType
            let result = try context.execute(update) as? NSBatchUpdateResult
            return result?.result as? [NSManagedObjectID] ?? []
        }
        // A batch update skips every context, so tell the UI's context what changed.
        await viewContext.perform { [viewContext] in
            NSManagedObjectContext.mergeChanges(fromRemoteContextSave: [NSUpdatedObjectsKey: ids],
                                                into: [viewContext])
        }
    }

    private func save(_ data: Data, from url: URL, albumID: NSManagedObjectID) async throws -> NSManagedObjectID {
        try await context.perform { [context] in
            let album = try context.existingObject(with: albumID)        // re-fetch in THIS context
            let request = NSFetchRequest<NSManagedObject>(entityName: "Photo")
            request.predicate = NSPredicate(format: "remoteURL == %@", url.absoluteString)
            request.fetchLimit = 1
            let photo = try context.fetch(request).first                  // find or create:
                ?? NSManagedObject(entity: try Self.entity("Photo", in: context), insertInto: context)
            photo.setValue(url.absoluteString, forKey: "remoteURL")
            photo.setValue(data, forKey: "imageData")
            photo.setValue(album, forKey: "album")
            try context.save()
            return photo.objectID                                          // permanent after save
        }
    }

    private static func entity(_ name: String, in context: NSManagedObjectContext) throws -> NSEntityDescription {
        guard let entity = NSEntityDescription.entity(forEntityName: name, in: context) else {
            throw CocoaError(.coreData)
        }
        return entity
    }
}
```

Run on macOS with `-com.apple.CoreData.ConcurrencyDebug 1` on, a fake downloader with random
delays, and 20 URLs of which 5 appear twice (real output):

```text
CoreData: annotation: Core Data multi-threading assertions enabled.
saved: 20 | temporary IDs: 0
album.photos seen by viewContext: 15
rows in store: 15
isSeen before: false
isSeen after batch update: true
distinct IDs: 15 | all resolvable: true
```

No assertion fired. Duplicates became updates, the screen's context saw every photo without a
refetch, and every returned ID resolves in the `viewContext`.

Why each piece:

- **One `newBackgroundContext()`, kept** — the answer to "how many contexts": the `viewContext`
  for the UI plus this one for writes. All saves go through one serial queue, so find-or-create
  is race-free.
- **Every touch inside `context.perform`** — the async `perform` puts the work on the context's
  own queue and returns its result. No context or object escapes the closure; only IDs do.
- **`existingObject(with: albumID)`** — the album is fetched again inside the background context,
  so the relationship is between two objects in the same context.
- **Find or create by `remoteURL`** — importing the same photo twice updates it. My first version
  just inserted and relied on a uniqueness constraint; the store stayed clean, but the returned IDs
  for the duplicates pointed at rows that didn't exist. The fetch fixes that.
- **`mergeByPropertyObjectTrump`** — a safety net if anything else (a sync job) writes the same row:
  the in-memory change wins instead of the save failing.
- **`automaticallyMergesChangesFromParent`** — the UI's context hears about every save on the
  background one, so the album fills in live.
- **Downloads in a task group, outside Core Data** — the network runs in parallel; only the saves
  are serial.
- **`NSBatchUpdateRequest` plus `mergeChanges(fromRemoteContextSave:into:)`** — the update runs in
  SQLite without loading rows, then tells the `viewContext` which objects changed so it doesn't
  show stale flags.
:::

::: What I'd ask next
- *"Why not `performBackgroundTask` for each download?"* — Each call makes a new context, so you
  are back to many writers saving at once and racing on "does it exist?". Fine for independent
  one-off jobs; wrong for an import that must stay consistent.
- *"Isn't saving one photo at a time slow?"* — Each save is a disk write. For big imports, save
  every N photos, or use `NSBatchInsertRequest`, which writes straight to the store.
- *"What does `ConcurrencyDebug 1` actually do?"* — It makes Core Data check the current queue on
  every context and object access and trap on a violation. Turn it on in the debug scheme's
  launch arguments and leave it on; it costs nothing in release because you don't ship it.
- *"200 URLs — any problem with the task group?"* — 200 downloads at once. Cap it: start 6, and
  add one each time one finishes.
- *"Would SwiftData change this?"* — The rule stays. A `ModelContext` belongs to one actor;
  background writes go through a `@ModelActor`, and you pass `PersistentIdentifier`s, not models.
:::
