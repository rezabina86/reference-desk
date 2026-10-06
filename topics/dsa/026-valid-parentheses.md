---
title: 21 · Valid Parentheses
summary: Decide whether a string made only of round, square and curly brackets closes every bracket correctly.
group: Stack
minutes: 25
sources:
- LeetCode 20 · Valid Parentheses | https://leetcode.com/problems/valid-parentheses/
- Swift standard library · Array.popLast() | https://developer.apple.com/documentation/swift/array/poplast()
---

*Easy · G · Z — Zalando is documented asking bracket balancing*

You get a string that contains only the six characters `(`, `)`, `[`, `]`, `{` and `}`. Return `true` if every opening bracket is closed by a bracket of the same kind, and the brackets close in the right order: whatever opened last must close first. Return `false` otherwise, including when something is left open at the end or a closer appears with nothing open.

| Text | Answer |
|---|---|
| `"{[]()}"` | `true` — the pairs nest and sit side by side cleanly |
| `"([)]"` | `false` — the right counts, but `)` arrives while `[` is still open |
| `"(("` | `false` — nothing is wrong until the end, where two brackets are still open |

Constraints that matter: up to 10,000 characters, only the six brackets. Counting each kind isn't enough (the second example has perfect counts); the target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct ValidParenthesesTests {

    @Test(arguments: [
        ("{[]()}", true),
        ("([)]", false),
        ("((", false),
    ])
    func returnsWhetherEveryBracketClosesInTheRightOrder(text: String, expected: Bool) {
        #expect(isValid(text) == expected)
    }

    // MARK: - Privates
    private func isValid(_ text: String) -> Bool {
        false
    }
}
```

In a playground:

```swift
func isValid(_ text: String) -> Bool {
    false // your solution
}

let cases: [(String, Bool)] = [
    ("{[]()}", true),
    ("([)]", false),
    ("((", false),
]
for (text, expected) in cases {
    let got = isValid(text)
    print(got == expected ? "PASS" : "FAIL", text, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Stack, match and cancel.** The cue is *"closed in the right order"*: a closer always belongs to the most recent bracket that is still open. "Most recent still open" is exactly what the top of a stack holds.
:::

::: Approach
Read the brackets from left to right and keep a pile of the ones that are open. An opening bracket goes on top of the pile. A closing bracket must match the bracket on top: if it does, take that one off, because the pair is done; if it doesn't, or the pile is empty, the string is invalid right there. When the string ends, it's valid only if the pile is empty, because anything still on it was never closed.

Time O(n): each character is pushed or popped once. Space O(n): a string of only openers puts all of them on the pile.
:::

::: Swift solution
```swift
func isValid(_ text: String) -> Bool {
    let opener: [Character: Character] = [")": "(", "]": "[", "}": "{"]
    var stack: [Character] = []

    for character in text {
        if let expected = opener[character] {
            guard stack.popLast() == expected else { return false }   // nil on an empty stack
        } else {
            stack.append(character)
        }
    }
    return stack.isEmpty
}
```

The map goes from each closer to the opener it needs, so one lookup both says "this is a closer" and names its partner. `stack.popLast() == expected` compares an optional with a value: an empty stack gives `nil`, which is never equal, so a stray closer returns `false` without a separate check.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, seven more (empty string, a lone `]`, `"()"`, `"(]"`, `"({[]})[]"`, `"))(("`, `"([]"`), and 5,000 random bracket strings checked against a brute force that keeps deleting `()`, `[]` and `{}` until nothing changes.
:::

::: Walk it through
**`"{[]()}"`**

| Character | Kind | Top before | Action | Stack after |
|---|---|---|---|---|
| `{` | opener | — | push | `{` |
| `[` | opener | `{` | push | `{[` |
| `]` | closer, needs `[` | `[` | pop, match | `{` |
| `(` | opener | `{` | push | `{(` |
| `)` | closer, needs `(` | `(` | pop, match | `{` |
| `}` | closer, needs `{` | `{` | pop, match | empty |

The string ends with an empty stack: `true`.

**`"([)]"`** — `(` and `[` are pushed. Then `)` needs `(`, but the top is `[`: return `false` immediately. The final `]` is never read.

**`"]"`** (the edge the trap is about) — the first character is a closer and the stack is empty. `popLast()` returns `nil`, `nil == "["` is false, so the answer is `false` — no crash.
:::

::: The Swift trap
**`removeLast()` crashes on the input that starts with a closer.** The natural first draft is `if stack.removeLast() != expected { return false }`. It passes every balanced example and then traps at runtime on `"]"` or `"())"`, because `removeLast()` on an empty array is a fatal error, not a `nil`. Either guard with `stack.isEmpty` first, or use `popLast()`, which returns an optional and makes the empty case fall out of the same comparison. The same trap waits at the other end: forgetting the final `stack.isEmpty` makes `"(("` return `true`.
:::

::: What they ask next
- **"The string also contains letters and other characters."** → Skip anything that's neither an opener nor a closer; the stack logic doesn't change.
- **"Only round brackets. Can you do it in O(1) space?"** → Keep a counter: +1 for `(`, −1 for `)`, fail if it ever goes negative, and require 0 at the end. With several kinds a counter can't see order, which is why the stack is needed.
- **"Return the minimum number of brackets to add to make it valid."** → Same pass with counters for round brackets: unmatched closers seen plus openers left at the end.
:::
