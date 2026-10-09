---
title: 25 · The PR that is mostly fine
summary: A clean, small SwiftUI settings row with one real problem and one judgement call. The test is restraint — find the one thing, say what's fine and why, and approve with comments.
minutes: 15
group: Review this PR
sources:
- Google Engineering Practices · The standard of code review — approve once it improves the code, even if it isn't perfect | https://google.github.io/eng-practices/review/reviewer/standard.html
- Google Engineering Practices · How to write review comments — label Nit and Optional | https://google.github.io/eng-practices/review/reviewer/comments.html
- Google Engineering Practices · Speed of reviews — "LGTM with comments" | https://google.github.io/eng-practices/review/reviewer/speed.html
- Apple · Text.init(_:) for a String — "displays a stored string without localization" | https://developer.apple.com/documentation/swiftui/text/init(_:)-9d1g4
- Apple · Localizing and varying text with a String Catalog — plural variations | https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog
---

*Shape: review this PR · Reported: a common senior-round topic; no specific company report found ·
Verified: the row and the fix typecheck against the iOS SDK in Swift 6 mode with no warnings; the
model's tests ran with Swift 6.4*

> "Last one, a quick one. A teammate added an iCloud sync row to Settings. Review it like you
> would on a normal Tuesday."

```swift
import SwiftUI

@MainActor
@Observable
final class SyncSettingsModel {
    var isSyncEnabled: Bool {
        didSet { defaults.set(isSyncEnabled, forKey: Keys.syncEnabled) }
    }
    let deviceCount: Int

    @ObservationIgnored private let defaults: UserDefaults

    init(defaults: UserDefaults, deviceCount: Int) {
        self.defaults = defaults
        self.deviceCount = deviceCount
        self.isSyncEnabled = defaults.bool(forKey: Keys.syncEnabled)
    }

    private enum Keys {
        static let syncEnabled = "settings.syncEnabled"
    }
}

struct SyncSettingsRow: View {
    @Bindable var model: SyncSettingsModel

    var body: some View {
        Toggle(isOn: $model.isSyncEnabled) {
            VStack(alignment: .leading, spacing: 2) {
                Text("iCloud sync")
                Text("\(model.deviceCount) " + String(localized: "devices signed in"))
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .accessibilityHint("Keeps your notes the same on all your devices")
    }
}

#Preview {
    Form {
        SyncSettingsRow(model: SyncSettingsModel(defaults: .standard, deviceCount: 2))
    }
}
```

::: A hint, if you're stuck
- Most of this is good. Before you write a comment, ask: *would this change what a user sees, or
  what the next developer can safely do?* If not, don't write it.
- Read each `Text` and ask what a translator receives.
- What does the row say with exactly one device?
:::

::: The key — what I expect a senior to find
The whole point of this one is restraint. I score a candidate down for every invented problem:
inventing nits is worse than missing a style point, because on a real team it costs the author an
afternoon and teaches them to stop asking you for reviews.

**The one blocking comment**

1. **The device count is built by gluing strings together.** `"\(count) " + String(localized:
   "devices signed in")` makes a plain `String`, and `Text` shows a plain `String` *without
   localization* — Apple's wording for that initializer. So the translator only ever sees the
   fragment "devices signed in", with no number and no way to reorder it. Three visible bugs
   follow: English says "1 devices signed in"; languages that put the number elsewhere can't; and
   languages with several plural forms (Polish, Arabic, Russian) can't get them right. The fix is
   one line — `Text("\(model.deviceCount) devices signed in")`, which becomes the localized key
   `%lld devices signed in` — plus a plural variation for it in the String Catalog.

**The one optional comment (a judgement call)**

2. **`@AppStorage` would do this without a model.** `@AppStorage("settings.syncEnabled") var
   isSyncEnabled = false` in the view saves the toggle in one line, and the class goes away. But
   the model keeps the key in one place, takes injected `UserDefaults` so it's testable, and will
   be the place to start the real sync when the toggle flips. Either is fine. I'd write it as
   "Optional: …" and let the author decide — I'd keep the model.

**Fine, and I'd say so** (one line in the review, so the author knows I read it):

- `@MainActor @Observable` — right for UI state; `@ObservationIgnored` on `defaults` keeps a
  dependency out of change tracking.
- `UserDefaults` is injected, not `.standard` inside the class — testable, and the preview can use
  the real one.
- `didSet` doesn't fire during `init`, so opening the screen writes nothing. I tested it.
- A private `Keys` enum — no stringly-typed key scattered around.
- `@Bindable` — the right wrapper to get a `$binding` from an `@Observable` passed in.
- The `Toggle`'s label is its VoiceOver label, so the row reads the title and the count with no
  extra work; the hint adds the "why". No icon-only control needs a label here.
- `deviceCount` is a `let` — a snapshot taken when Settings opens. For a settings row that's fine.

**What I would *not* write** — each of these scores negative: "make `Keys` an enum with raw
values", "add MARK comments", "rename `model` to `viewModel`", "`spacing: 2` is a magic number",
"don't use `.standard` in the preview", "make the model a struct" (it can't be: it's shared,
observable state).

**Verdict: approve with comments.** One must-fix, small and obvious, and one optional. I trust the
author to fix the string without another round, so I approve now and say "please fix the plural
before merging". That's Google's "LGTM with comments": approve when the remaining comments are
small and you trust the author to address them.
:::

::: The idea behind it
A review has a *severity budget*. Every comment costs the author time and attention, so each one
should earn it. Google's own guidelines say approve once the change makes the code better, even if
it isn't what you'd have written. Perfect isn't the bar; *better, and safe* is.

So sort what you see into three piles. **Blocking:** it would hurt a user or the next developer
— a bug, a crash, a leak, text a translator can't fix. **Optional:** a real alternative, where
reasonable people differ; label it "Optional:" or "Consider:" so the author knows they can say no.
**Nothing:** taste. Don't write it. If it really matters to the team, it belongs in a linter or a
style guide, not in one person's PR.

Why is the string the blocker? Because localization is a *data* problem disguised as a code
problem. When you glue a number onto a translated fragment, the sentence's shape is frozen in code,
in English word order. A translator can only fix what they can see, and they can't see your `+`.
Give them the whole sentence with a placeholder — `%lld devices signed in` — and they can move the
number, and the String Catalog can choose "device" or "devices" (or six forms, in Arabic) by count.

Think of a restaurant inspector. A good one notes the raw chicken next to the salad and leaves; a
bad one also tells you the menu font is ugly. The kitchen remembers only the second inspector.
:::

::: The fix
```swift
Text("\(model.deviceCount) devices signed in")      // was: "\(…) " + String(localized: "devices signed in")
```

In `Localizable.xcstrings`, the key `%lld devices signed in` gets a plural variation (in Xcode:
right-click the string → Vary by Plural):

```json
"%lld devices signed in" : {
  "localizations" : {
    "en" : {
      "variations" : {
        "plural" : {
          "one" : { "stringUnit" : { "state" : "translated", "value" : "%lld device signed in" } },
          "other" : { "stringUnit" : { "state" : "translated", "value" : "%lld devices signed in" } }
        }
      }
    }
  }
}
```

**Said out loud, not coded:** nothing else. The optional `@AppStorage` comment is the author's
call, and I'd keep the model.

Why this works: `Text("…\(count)…")` with a string *literal* builds a `LocalizedStringKey`, so the
interpolation becomes a `%lld` placeholder inside one translatable sentence. A `String` variable —
which is what the `+` produced — goes to the other `Text` initializer, the one that shows text as is.
:::

::: Now write the tests
> "Fine. Any tests for this?"

**What I'd test, and why**

1. **Turning sync on is saved and read back** — the model's one job: a new model built on the same
   defaults sees the saved value.
2. **Opening the screen writes nothing** — `didSet` must not fire from `init`. If someone later
   moves the read into a setter, this catches a write on every screen open.

**What I wouldn't unit-test: the string.** A `Text`'s localized output isn't something a unit test
can read cleanly, and the fix is a literal. Instead, check it where it shows: a preview with
`deviceCount: 1` (it must say "1 device"), the same preview with
`.environment(\.locale, Locale(identifier: "de"))`, and a run with the scheme's App Language set to
a pseudo-language (Double-Length or Right-to-Left) to catch any other glued strings. The String
Catalog itself lists the key, so a missing plural is visible in Xcode.

**The seam.** The model already takes `UserDefaults` in `init`, so each test uses its own suite —
real storage, never the app's own — and deletes it afterwards.

```swift
import Foundation
import Testing

@MainActor
struct SyncSettingsModelTests {
    /// A private UserDefaults suite per test: real storage, never the app's own, deleted afterwards.
    func withDefaults(_ body: (UserDefaults) throws -> Void) throws {
        let suite = "SyncSettingsModelTests.\(UUID().uuidString)"
        let defaults = try #require(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        try body(defaults)
    }

    @Test func turningSyncOnIsSavedAndReadBack() throws {
        try withDefaults { defaults in
            SyncSettingsModel(defaults: defaults, deviceCount: 2).isSyncEnabled = true

            let reopened = SyncSettingsModel(defaults: defaults, deviceCount: 2)

            #expect(reopened.isSyncEnabled)
        }
    }

    @Test func openingTheScreenWritesNothing() throws {
        try withDefaults { defaults in
            _ = SyncSettingsModel(defaults: defaults, deviceCount: 2)

            #expect(defaults.object(forKey: "settings.syncEnabled") == nil)
        }
    }
}
```

Ran with Swift 6.4: 2 tests, all passed.
:::

::: What I'd ask next
- *"How do you decide what's blocking?"* — Would it hurt a user (a bug, a crash, a wrong or
  untranslatable string, an accessibility gap) or the next developer (a trap, a leak, a race)? Then
  it blocks. Anything else is optional or unsaid.
- *"The author pushes back on your blocking comment. What now?"* — Explain the user impact once,
  with the example ("1 devices", and German word order). If they still disagree, talk — a call
  beats a 20-comment thread — and if it's genuinely a judgement call, let them have it.
- *"Is there a shortcut for English plurals?"* — Automatic grammar agreement:
  `Text("^[\(count) device](inflect: true) signed in")` inflects "device" by count in supported
  languages. The String Catalog plural works in every language, so I'd still use it.
- *"Would you approve a PR you'd have written differently?"* — Yes, if it's correct, clear and
  consistent with the codebase. "Different" isn't "worse".
- *"What if there were twenty of these nits?"* — Then it's a team problem, not a PR problem: agree
  on a style guide and a linter (SwiftLint, swift-format), and stop spending reviews on it.
:::
