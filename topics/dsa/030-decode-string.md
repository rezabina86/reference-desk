---
title: 25 · Decode String
summary: Expand a compressed string in which a number followed by text in square brackets means that text repeated, with repeats allowed inside repeats.
group: Stack
minutes: 25
sources:
- LeetCode 394 · Decode String | https://leetcode.com/problems/decode-string/
- Swift standard library · Character.wholeNumberValue | https://developer.apple.com/documentation/swift/character/wholenumbervalue
---

*Medium*

You get an encoded string. The rule is `k[text]`: the text inside the brackets, written k times in a row. Encodings can sit side by side and inside each other, and plain letters can appear anywhere outside brackets. Return the fully expanded string. The input is always well formed: every number is a positive integer followed by `[`, brackets always match, and letters are lowercase.

| Encoded | Decoded |
|---|---|
| `"3[ab]2[c]"` | `"abababcc"` |
| `"2[x3[y]]"` | `"xyyyxyyy"` — the inner repeat is expanded inside the outer one |
| `"10[a]"` | `"aaaaaaaaaa"` — a two-digit count; the edge case |

Constraints that matter: the encoded string is at most 30 characters, counts go up to 300, and the decoded output stays under 100,000 characters. The work is dominated by writing the output, so the target is time close to the output's length.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct DecodeStringTests {

    @Test(arguments: [
        ("3[ab]2[c]", "abababcc"),
        ("2[x3[y]]", "xyyyxyyy"),
        ("10[a]", "aaaaaaaaaa"),
    ])
    func expandsEveryRepeatIncludingNestedOnes(encoded: String, expected: String) {
        #expect(decodeString(encoded) == expected)
    }

    // MARK: - Privates
    private func decodeString(_ encoded: String) -> String {
        ""
    }
}
```

In a playground:

```swift
func decodeString(_ encoded: String) -> String {
    "" // your solution
}

let cases: [(String, String)] = [
    ("3[ab]2[c]", "abababcc"),
    ("2[x3[y]]", "xyyyxyyy"),
    ("10[a]", "aaaaaaaaaa"),
]
for (encoded, expected) in cases {
    let got = decodeString(encoded)
    print(got == expected ? "PASS" : "FAIL", encoded, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Stack of saved context.** The cue is *nesting*: brackets inside brackets, where an inner part must be finished before the outer part can use it. Each `[` interrupts what you were building; each `]` finishes the most recent interruption and hands the result back to the one before.
:::

::: Approach
Read left to right, building the current piece of text and the current number. Digits extend the number. A letter is added to the current text. An opening bracket means "start something new": save the text built so far and the number in front of the bracket on a pile, then start an empty text and reset the number. A closing bracket means "this inner part is done": take the last saved text and count off the pile, and the current text becomes that saved text followed by the inner text repeated count times. At the end, the current text is the answer.

Time: building the output dominates. Each `]` copies the text built so far at its level once, so the worst case is the output length times the number of brackets — with an input of at most 30 characters that is a small constant factor. Space O(output length) for the strings, plus the pile, which is as deep as the nesting.
:::

::: Swift solution
```swift
func decodeString(_ encoded: String) -> String {
    var saved: [(prefix: String, count: Int)] = []
    var current = ""
    var count = 0

    for character in encoded {
        if let digit = character.wholeNumberValue {
            count = count * 10 + digit                    // "12[" is twelve, not one then two
        } else if character == "[" {
            saved.append((current, count))
            current = ""
            count = 0
        } else if character == "]" {
            let (prefix, times) = saved.removeLast()
            current = prefix + String(repeating: current, count: times)
        } else {
            current.append(character)
        }
    }
    return current
}
```

The `]` branch is the whole idea: the text from before the bracket is restored and the finished inner text, repeated, is glued onto it. `String(repeating:count:)` takes a whole `String`, not only a `Character`, so no loop is needed.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (empty string, plain text with no brackets, letters around a repeat, a count of 1, three levels of nesting, `12[ab]`), and 3,000 random encodings with counts up to 12 and nesting up to three levels, checked against the expansion built alongside the encoding.
:::

::: Walk it through
**`"2[x3[y]]"`**

| Character | Action | Saved (prefix, count) | Current | Count |
|---|---|---|---|---|
| `2` | digit | — | `""` | 2 |
| `[` | save, reset | `("", 2)` | `""` | 0 |
| `x` | letter | `("", 2)` | `"x"` | 0 |
| `3` | digit | `("", 2)` | `"x"` | 3 |
| `[` | save, reset | `("", 2) ("x", 3)` | `""` | 0 |
| `y` | letter | `("", 2) ("x", 3)` | `"y"` | 0 |
| `]` | pop ("x", 3): `"x" + "yyy"` | `("", 2)` | `"xyyy"` | 0 |
| `]` | pop ("", 2): `"" + "xyyy" × 2` | — | `"xyyyxyyy"` | 0 |

Answer `"xyyyxyyy"`.

**`"10[a]"`** — `1` makes count 1, `0` makes it 1 × 10 + 0 = 10. The `[` saves `("", 10)`, `a` builds `"a"`, and `]` gives `"a"` repeated ten times. Reading one digit at a time without the `* 10` would save a count of 0.
:::

::: The Swift trap
**`Character.isNumber` is too generous, and digits arrive one at a time.** The tempting test is `if character.isNumber`, then `Int(String(character))!`. But `isNumber` is true for `"½"`, and `Int("½")` is `nil`, so that force unwrap is a crash waiting for unusual input. `character.wholeNumberValue` returns the value or `nil` in one step, with no `String` conversion — though it is generous too (`"٣"` gives 3, `"Ⅻ"` gives 12), so if the input isn't promised to be ASCII, add `character.isASCII`. Whichever you use, the count has to be accumulated (`count * 10 + digit`); resetting it at each digit passes every single-digit example and fails `"10[a]"`.
:::

::: What they ask next
- **"Write it recursively."** → A function that reads from a shared index until it hits `]` or the end, returning the text built; on `k[` it calls itself for the inner part and repeats the result. The call stack replaces the explicit pile.
- **"The decoded output could be huge. Return only its length."** → Keep counts instead of strings: a stack of lengths, multiplying by k on `]`. If they ask for the character at position n, walk backwards through that length with a modulo.
- **"What if the input might be malformed?"** → Use `popLast()` on `]` and return `nil` if nothing was saved, and fail if the pile isn't empty at the end — the Valid Parentheses check, folded in.
:::
