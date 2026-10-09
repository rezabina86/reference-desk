---
title: 18 · Core Data saved from the wrong thread
summary: A photo downloader that saves to Core Data from many threads at once — find the crashes, then answer how many managed object contexts it really needs.
minutes: 20
group: Find the bug
sources:
- LeetCode Discuss · PhonePe iOS — "downloading via multiple threads but need to save in coredata how many managed object contexts are required" | https://leetcode.com/discuss/interview-experience/1422835/
- Apple · NSManagedObjectContext — concurrency types, perform, merge policy | https://developer.apple.com/documentation/coredata/nsmanagedobjectcontext
- Apple · automaticallyMergesChangesFromParent | https://developer.apple.com/documentation/coredata/nsmanagedobjectcontext/automaticallymergeschangesfromparent
---

*Shape: find the bug · Reported: PhonePe — "downloading via multiple threads but need to save in
Core Data, how many managed object contexts are required" · Verified: snippet and fix typecheck in
Swift 6 mode, Swift 6.4; the snippet's crashes were reproduced on macOS*

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

In Swift 6 mode this compiles with three warnings: `self` and `album` captured in `@Sendable`
closures. The compiler sees objects crossing threads. It can't see which queue a context is used
on — that's a runtime rule.

::: A hint, if you're stuck
- `album` was fetched by the screen. Which context does it belong to? Which context is `photo` in?
- A context created with `.privateQueueConcurrencyType` owns a queue. Is any of this code running
  on it?
- `viewContext` is a main-queue context. What thread is `markAllSeen` on?
- Each download makes its own context and saves. Who tells the screen's context that something
  changed?
:::

::: How I'd debug it
Turn on Core Data's own checker: add `-com.apple.CoreData.ConcurrencyDebug 1` to the scheme's
launch arguments. It makes every context check it is on its own queue, and trap if not.

I ran the snippet against a small store. Without the flag, the first download crashes on every run:
"Illegal attempt to establish a relationship 'album' between objects in different contexts".
`markAllSeen` is quieter, which makes it worse: with four photos stored it ran to the end and all
four were marked seen — it looked like it worked. With the flag it trapped at once (exit code 133).
That's the production crash, caught on the first run instead of the thousandth.
:::

::: The key — what I expect a senior to find
**Answer:** two contexts. One main-queue `viewContext` the UI reads, and one background context
that does all the writing, one save at a time. The downloads can run in parallel; they don't need
a context at all.

1. **An object from one context related to an object in another.** `album` lives in the screen's
   `viewContext`; `photo` lives in a brand-new context. Core Data throws, every time. Pass the
   album's `objectID` and look it up inside the context doing the work.
2. **`try!` on the fetch.** Any fetch error — a migration problem, a full disk — crashes the app.
   Use `try` and let the caller hear about it.
3. **`viewContext` used off the main queue.** `markAllSeen` fetches and saves the main-queue
   context from a global queue. It usually works, and sometimes corrupts the context or crashes.
   This is "never on my machine". Do the work in `perform` on a background context.
4. **A private-queue context used without `perform`.** A private context owns a serial queue, and
   every touch — insert, `setValue`, save — must run on it through `perform`. Here nothing does.
5. **An `NSManagedObject` handed to another thread.** `onSaved` gives the main thread a `photo`
   that belongs to a background context. Only `NSManagedObjectID` is safe to pass around.
6. **`onSaved` is a data race.** The caller sets it on one thread; it's read inside
   `DispatchQueue.main.async`. Keep the class on the main actor so both happen on main.
7. **The screen never sees the new photos.** The `viewContext` isn't told about other contexts'
   saves: `automaticallyMergesChangesFromParent` is off. That's "shows nothing until you
   relaunch."
8. **One context per download, so duplicates.** Twenty downloads make twenty contexts, each
   saving on its own. The same URL twice gives two rows, and "check if it exists, then insert"
   can't work across contexts saving at the same time. One writer context can.
9. **Errors thrown away.** `try?` on `save` hides every failure, and a failed download returns
   silently: the user is never told a photo is missing, and nothing retries.
10. **No HTTP status check.** `Data(contentsOf:)` doesn't care about status codes, so a 404 error
    page is saved as `imageData`. Check for a 200.
11. **No cancellation or progress.** Two hundred global-queue blocks can't be stopped when the user
    leaves, and the screen can't show "12 of 200".
12. **Nothing can be tested.** The network is `Data(contentsOf:)`, called directly. Inject the
    download behind one protocol.
13. **`Data(contentsOf:)` for a network URL, one global-queue block per photo.** It blocks a thread
    per download. Two hundred photos ask GCD for far more threads than there are cores. Use
    `URLSession`'s async API.
14. **Loading every photo to flip one flag.** `markAllSeen` fetches every row into memory. A batch
    update does it in the store.
15. **Images stored inline.** Large blobs in the SQLite file make every fetch heavier. Tick *Allows
    External Storage* on the attribute.
16. **Stringly typed attributes.** `setValue(_:forKey:)` with `"remoteURL"` and `"isSeen"` compiles
    with any typo and crashes at run time. Use generated `NSManagedObject` subclasses.
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

protocol PhotoDownloading: Sendable {                                   // key 12: the one seam
    func imageData(from url: URL) async throws -> Data
}

extension URLSession: PhotoDownloading {
    func imageData(from url: URL) async throws -> Data {
        let (data, response) = try await data(from: url)                // key 13: no thread per photo
        guard (response as? HTTPURLResponse)?.statusCode == 200 else {   // key 10
            throw URLError(.badServerResponse)
        }
        return data
    }
}

@MainActor                                                              // key 6: onSaved only on main
final class PhotoDownloader {
    private let context: NSManagedObjectContext                         // key 8: ONE writer context
    private let downloader: any PhotoDownloading
    var onSaved: ((NSManagedObjectID) -> Void)?                         // key 5: IDs, not objects

    init(container: NSPersistentContainer, downloader: any PhotoDownloading = URLSession.shared) {
        container.viewContext.automaticallyMergesChangesFromParent = true // key 7
        context = container.newBackgroundContext()
        context.mergePolicy = NSMergePolicy.mergeByPropertyObjectTrump
        self.downloader = downloader
    }

    /// Downloads in parallel, saves one at a time. Returns the URLs that failed.
    @discardableResult
    func download(_ urls: [URL], into album: NSManagedObject) async throws -> [URL] {
        let albumID = album.objectID                                    // key 1: read on main, where album lives
        var failed: [URL] = []
        try await withThrowingTaskGroup(of: (URL, Data?).self) { group in
            for url in urls {
                group.addTask { [downloader] in (url, try? await downloader.imageData(from: url)) }
            }
            for try await (url, data) in group {
                guard let data else { failed.append(url); continue }   // key 9: skipped, but reported
                let id = try await save(data, from: url, albumID: albumID)  // never inside onSaved?(…)
                onSaved?(id)
            }
        }
        return failed
    }

    func markAllSeen() async throws {
        try await context.perform { [context] in                        // key 3: background, on its queue
            let photos = try context.fetch(NSFetchRequest<NSManagedObject>(entityName: "Photo"))  // key 2
            photos.forEach { $0.setValue(true, forKey: "isSeen") }
            try context.save()
        }
    }

    private func save(_ data: Data, from url: URL, albumID: NSManagedObjectID) async throws -> NSManagedObjectID {
        try await context.perform { [context] in                        // key 4: every touch inside perform
            let album = try context.existingObject(with: albumID)       // key 1: the album, in THIS context
            let request = NSFetchRequest<NSManagedObject>(entityName: "Photo")
            request.predicate = NSPredicate(format: "remoteURL == %@", url.absoluteString)
            let photo = try context.fetch(request).first                // key 8: find or create
                ?? NSEntityDescription.insertNewObject(forEntityName: "Photo", into: context)
            photo.setValue(url.absoluteString, forKey: "remoteURL")
            photo.setValue(data, forKey: "imageData")
            photo.setValue(album, forKey: "album")
            do { try context.save() } catch { context.rollback(); throw error }  // key 9: no try?
            return photo.objectID
        }
    }
}
```

**Said out loud, not coded:** an `NSBatchUpdateRequest` for `markAllSeen` (key 14, then merge
its object IDs into the `viewContext`) · a cap of about six downloads at once · progress and
cancellation (key 11) · retry for failed URLs · *Allows External Storage* (key 15) · generated
`NSManagedObject` subclasses (key 16).

Why each piece:

- **The class is `@MainActor`, but the work isn't on main.** The downloads run in child tasks, and
  every Core Data touch runs inside `context.perform` on the background queue. Main only
  orchestrates: it reads `album.objectID` and calls `onSaved`.
- **`existingObject(with:)` inside `perform`** — the album is fetched again in the background
  context, so the relationship joins two objects in the same context. The album must already be
  saved: an unsaved object has a temporary ID another context can't open.
- **A failed download is skipped, like before, but reported.** The old code skipped silently; now
  the caller gets the failed URLs back. A failed *save* throws, because that's a real bug, and
  rolls back first — otherwise the bad insert stays in the context and every later save fails too.
- **`save` runs on its own line, before `onSaved?(id)`.** My first draft wrote
  `onSaved?(try await save(…))`. When `onSaved` is `nil`, optional chaining skips the whole call,
  arguments included — so nothing was saved. A test with no `onSaved` caught it.
:::

::: Now write the tests
> "Good. Now write me a few tests for the downloader — the ones that would have caught this before
> production."

**What I'd test, and why**

1. **The screen sees downloaded photos without a refetch.** The first bug: the album the screen
   already holds must fill in, and every ID passed to `onSaved` must open on the main context.
   It also proves the cross-context relationship no longer throws.
2. **A failed download is skipped and reported** — the edge case. The rest still save.
3. **The same URL twice gives one row** — what one writer context buys you.
4. **`markAllSeen` reaches the screen** — the regression check for the off-main `viewContext`.

The crash itself — a context used on the wrong queue — isn't something a `#expect` can see.
Core Data catches that: I add `-com.apple.CoreData.ConcurrencyDebug 1` to the test scheme's
launch arguments, so any wrong-queue access traps during the run.

**The seam.** `PhotoDownloading` is injected, so the tests use a *fake* downloader — a stand-in
that answers at once with no network, and can fail for one URL. The container is passed in too, so
each test builds its own fresh in-memory store.

```swift
import CoreData
import Testing

// A fake downloader: no network, answers at once, and can fail for one URL.
struct FakeDownloader: PhotoDownloading {
    var failing: URL? = nil
    func imageData(from url: URL) async throws -> Data {
        if url == failing { throw URLError(.badServerResponse) }
        return Data(url.absoluteString.utf8)
    }
}

// The model, built in code so the tests need no .xcdatamodeld file. It is long only because
// Core Data's model API is verbose: two entities, Album <->> Photo.
@MainActor let model: NSManagedObjectModel = {
    let album = NSEntityDescription(), photo = NSEntityDescription()
    album.name = "Album"
    photo.name = "Photo"

    func attribute(_ name: String, _ type: NSAttributeDescription.AttributeType) -> NSAttributeDescription {
        let attribute = NSAttributeDescription()
        attribute.name = name
        attribute.type = type
        return attribute
    }
    let isSeen = attribute("isSeen", .boolean)
    isSeen.defaultValue = false

    let photos = NSRelationshipDescription(), toAlbum = NSRelationshipDescription()
    photos.name = "photos"
    photos.destinationEntity = photo
    photos.maxCount = 0                       // to-many
    toAlbum.name = "album"
    toAlbum.destinationEntity = album
    toAlbum.maxCount = 1
    photos.inverseRelationship = toAlbum
    toAlbum.inverseRelationship = photos

    album.properties = [attribute("name", .string), photos]
    photo.properties = [attribute("remoteURL", .string), attribute("imageData", .binaryData), isSeen, toAlbum]
    let model = NSManagedObjectModel()
    model.entities = [album, photo]
    return model
}()

// An in-memory store, fresh per test.
@MainActor
func makeContainer() throws -> NSPersistentContainer {
    let container = NSPersistentContainer(name: "Photos", managedObjectModel: model)
    let store = NSPersistentStoreDescription()
    store.type = NSInMemoryStoreType
    container.persistentStoreDescriptions = [store]
    var loadError: (any Error)?
    container.loadPersistentStores { _, error in loadError = error }   // synchronous by default
    if let loadError { throw loadError }
    return container
}

@MainActor
func makeAlbum(in context: NSManagedObjectContext) throws -> NSManagedObject {
    let album = NSEntityDescription.insertNewObject(forEntityName: "Album", into: context)
    album.setValue("Holiday", forKey: "name")
    try context.save()                         // a saved object has a permanent ID
    return album
}

@MainActor
func photos(of album: NSManagedObject) -> Set<NSManagedObject> {
    album.value(forKey: "photos") as? Set<NSManagedObject> ?? []
}

let urls = (0..<10).map { URL(string: "https://example.com/\($0).jpg")! }

@Suite(.timeLimit(.minutes(1)))
@MainActor
struct PhotoDownloaderTests {
    @Test func screenSeesDownloadedPhotosWithoutRefetching() async throws {
        // Given an album the screen already holds
        let container = try makeContainer()
        let album = try makeAlbum(in: container.viewContext)
        let downloader = PhotoDownloader(container: container, downloader: FakeDownloader())
        var saved: [NSManagedObjectID] = []
        downloader.onSaved = { saved.append($0) }

        // When ten photos download and save on the background context
        try await downloader.download(urls, into: album)
        await container.viewContext.perform {}    // let merges already queued on main run first

        // Then the screen's own album object has them, and every reported ID opens on main
        #expect(photos(of: album).count == 10)
        #expect(saved.count == 10)
        for id in saved {
            #expect(throws: Never.self) { try container.viewContext.existingObject(with: id) }
        }
    }

    @Test func failedDownloadIsSkippedAndReported() async throws {
        let container = try makeContainer()
        let album = try makeAlbum(in: container.viewContext)
        let broken = urls[3]
        let downloader = PhotoDownloader(container: container, downloader: FakeDownloader(failing: broken))

        let failed = try await downloader.download(urls, into: album)
        await container.viewContext.perform {}

        #expect(failed == [broken])
        #expect(photos(of: album).count == 9)
    }

    @Test func downloadingTheSameURLTwiceGivesOneRow() async throws {
        let container = try makeContainer()
        let album = try makeAlbum(in: container.viewContext)
        let downloader = PhotoDownloader(container: container, downloader: FakeDownloader())

        try await downloader.download(urls + urls.prefix(3), into: album)

        #expect(try container.viewContext.count(for: NSFetchRequest(entityName: "Photo")) == 10)
    }

    @Test func markAllSeenReachesTheScreen() async throws {
        // Given photos the screen has already read as unseen
        let container = try makeContainer()
        let album = try makeAlbum(in: container.viewContext)
        let downloader = PhotoDownloader(container: container, downloader: FakeDownloader())
        try await downloader.download(urls, into: album)
        await container.viewContext.perform {}
        #expect(photos(of: album).allSatisfy { $0.value(forKey: "isSeen") as? Bool == false })

        // When they are marked seen in the background
        try await downloader.markAllSeen()
        await container.viewContext.perform {}

        // Then the same in-memory objects say "seen"
        #expect(photos(of: album).count == 10)
        #expect(photos(of: album).allSatisfy { $0.value(forKey: "isSeen") as? Bool == true })
    }
}
```

Ran on the iOS Simulator (Swift 6 mode) with `-com.apple.CoreData.ConcurrencyDebug 1`: 4 tests, all passed.
:::

::: What I'd ask next
- *"Why not `performBackgroundTask` for each download?"* — Each call makes a new context, so you
  are back to many writers saving at once and racing on "does it exist?". Fine for independent
  one-off jobs; wrong for an import that must stay consistent.
- *"Isn't saving one photo at a time slow?"* — Each save is a disk write. For big imports, save
  every N photos, or use `NSBatchInsertRequest`, which writes straight to the store.
- *"Why not a batch update for `markAllSeen`?"* — I would, for thousands of rows. It runs in
  SQLite without loading anything, but it skips every context, so I'd merge the changed object IDs
  into the `viewContext` with `mergeChanges(fromRemoteContextSave:into:)`.
- *"200 URLs — any problem with the task group?"* — 200 downloads at once. Cap it: start 6, and
  add one each time one finishes.
- *"Would SwiftData change this?"* — The rule stays. A `ModelContext` belongs to one actor;
  background writes go through a `@ModelActor`, and you pass `PersistentIdentifier`s, not models.
:::
