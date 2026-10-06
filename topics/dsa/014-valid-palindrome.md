---
title: 11 · Valid Palindrome
summary: Decide whether a sentence reads the same forwards and backwards once you ignore case, spaces and punctuation.
group: Two pointers
minutes: 25
sources:
- LeetCode 125 · Valid Palindrome | https://leetcode.com/problems/valid-palindrome/
- Swift standard library · String.Index | https://developer.apple.com/documentation/swift/string/index
- Swift standard library · Character.isLetter | https://developer.apple.com/documentation/swift/character/isletter
---

*Easy · G — the warm-up; the point is to finish it clean in under ten minutes*

You get a string. Keep only its letters and digits, treat uppercase and lowercase as the same, and decide whether what's left reads the same forwards and backwards. A string with nothing left after that clean-up counts as reading the same both ways.

| Text | Answer | Why |
|---|---|---|
| `"Taco cat"` | `true` | cleaned: `tacocat` |
| `"Coffee"` | `false` | cleaned: `coffee`, backwards `eeffoc` |
| `", ;"` | `true` | nothing left — the empty string is a palindrome |

Constraints that matter: up to 200,000 characters, all printable ASCII. Letters and digits both count; everything else is skipped. The simple answer builds a cleaned copy and compares it with its reverse — correct, but it uses O(n) extra memory, and the follow-up will be to do without it.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ValidPalindromeTests {

    @Test(arguments: [
        ("Taco cat", true),
        ("Coffee", false),
        (", ;", true),
    ])
    func readsTheSameBothWaysIgnoringCaseAndPunctuation(text: String, expected: Bool) {
        #expect(isPalindrome(text) == expected)
    }

    // MARK: - Privates
    private func isPalindrome(_ text: String) -> Bool {
        false
    }
}
```

In a playground:

```swift
func isPalindrome(_ text: String) -> Bool {
    false // your solution
}

let cases: [(String, Bool)] = [
    ("Taco cat", true),
    ("Coffee", false),
    (", ;", true),
]
for (text, expected) in cases {
    let got = isPalindrome(text)
    print(got == expected ? "PASS" : "FAIL", text, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Two pointers, moving inward from both ends.** The cue is *"reads the same forwards and backwards"* — you are comparing the first with the last, the second with the second-to-last, and so on. Two positions walking toward each other do that in one pass, and skipping punctuation is just "move this pointer on without comparing".
:::

::: Approach
Put one finger on the first character and one on the last. If the left finger is on something that isn't a letter or digit, move it right; if the right finger is, move it left. When both are on letters or digits, compare them ignoring case: if they differ, the answer is no; if they match, move both inward. When the fingers meet or cross, every pair matched, so the answer is yes.

Time O(n): each finger only moves inward, so together they visit each character once. Space O(n) in the version below, because it copies the string into an array for indexing; the String.Index version in the trap is O(1).
:::

::: Swift solution
```swift
func isPalindrome(_ text: String) -> Bool {
    let characters = Array(text)
    var left = 0
    var right = characters.count - 1

    while left < right {
        guard isAlphanumeric(characters[left]) else { left += 1; continue }
        guard isAlphanumeric(characters[right]) else { right -= 1; continue }
        if characters[left].lowercased() != characters[right].lowercased() {
            return false
        }
        left += 1
        right -= 1
    }
    return true
}

func isAlphanumeric(_ character: Character) -> Bool {
    character.isASCII && (character.isLetter || character.isNumber)
}
```

For an empty string `right` starts at −1, the loop never runs, and the answer is `true` — no special case, but say that you checked.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above plus ten more — the empty string, one character, letters mixed with digits (`"ab2A"`, `"1a1"`, `"0P"`), a full sentence with punctuation, a trailing full stop, a plain mismatch, and two strings with accented letters that the ASCII rule skips — and 3,000 random strings checked against the clean-copy-and-reverse answer.
:::

::: Walk it through
**`"Taco cat"`** — eight characters, positions 0 to 7.

| Left | Right | Action |
|---|---|---|
| 0 `T` | 7 `t` | same ignoring case → move both |
| 1 `a` | 6 `a` | same → move both |
| 2 `c` | 5 `c` | same → move both |
| 3 `o` | 4 `␣` | right is a space → right moves to 3 |
| 3 | 3 | fingers meet → `true` |

**`", ;"`** — left skips `,` then the space and reaches position 2; right is already at 2. `2 < 2` is false, the loop ends, `true`.
:::

::: The Swift trap
**You can't write `text[left]` with an `Int`.** A Swift `String` is a collection of `Character`s, each possibly several bytes, so it has no integer indexing. There are two honest ways out, and you should name the cost of each. `Array(text)` gives you integer indexing at the price of an O(n) copy — what the solution above does. Or walk two `String.Index` values with `text.index(after:)` and `text.index(before:)`, which is O(1) extra space and exactly what "can you do it without the copy?" is asking for. Either is fine; writing `text[text.index(text.startIndex, offsetBy: i)]` inside the loop is not — each of those is O(i), and the whole thing quietly becomes O(n²).

Smaller one: `Character.isLetter` and `isNumber` are Unicode-wide — `"é"` is a letter, `"½"` is a number. The problem means ASCII, hence the `isASCII` check. And `Character.lowercased()` returns a `String`, not a `Character`; comparing two strings is fine, but don't try to store it back into a `[Character]`.
:::

::: What they ask next
- **"Do it in O(1) extra space."** → Two `String.Index` values, `index(after:)` and `index(before:)`, loop while `left < right`. Same logic.
- **"May you delete at most one character to make it a palindrome?"** → On the first mismatch, try skipping the left character or the right one, and check the rest of each with the same two-pointer loop. Still O(n).
- **"Unicode text, where `é` should equal `e`?"** → Normalise first: `text.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: nil)` from Foundation, then drop the `isASCII` check.
:::
