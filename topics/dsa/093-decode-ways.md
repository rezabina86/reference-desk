---
title: 78 · Decode Ways
summary: Count how many ways a string of digits can be read back as letters when A is 1, B is 2, and so on up to Z as 26.
group: 1-D dynamic programming
minutes: 25
sources:
- LeetCode 91 · Decode Ways | https://leetcode.com/problems/decode-ways/
- Swift standard library · Character.wholeNumberValue | https://developer.apple.com/documentation/swift/character/wholenumbervalue
---

*Medium · G*

A message of capital letters was turned into digits with A = 1, B = 2, …, Z = 26, and the numbers were written next to each other with no separators. You get the digit string. Count how many different letter messages could have produced it. A piece may be one digit (1–9) or two digits (10–26); a piece can never start with 0, so `"06"` is not a way to write F.

| Digits | Answer |
|---|---|
| `"2611"` | `4` — 2·6·1·1, 26·1·1, 2·6·11, 26·11 |
| `"10"` | `1` — only J; a lone 0 is no letter |
| `"06"` | `0` — the string starts with a 0, which nothing can begin with |

Constraints that matter: up to 100 digits. The count can be huge, but the statement promises it fits in a 32-bit integer. Listing every reading is exponential; the target is O(n) time and O(1) space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct DecodeWaysTests {

    @Test(arguments: [
        ("2611", 4),
        ("10", 1),
        ("06", 0),
    ])
    func countsTheLetterMessagesThatGiveTheseDigits(digits: String, expected: Int) {
        #expect(numDecodings(digits) == expected)
    }

    // MARK: - Privates
    private func numDecodings(_ text: String) -> Int {
        0
    }
}
```

In a playground:

```swift
func numDecodings(_ text: String) -> Int {
    0 // your solution
}

let cases: [(String, Int)] = [
    ("2611", 4),
    ("10", 1),
    ("06", 0),
]
for (digits, expected) in cases {
    let got = numDecodings(digits)
    print(got == expected ? "PASS" : "FAIL", digits, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming, counting — Climbing Stairs with rules.** The cue is *"how many ways"* to read a sequence where each piece is one or two items long. The last piece of any reading is either the last digit alone or the last two digits together, and those two groups don't overlap. So the count for a prefix is the sum of two smaller counts — exactly Climbing Stairs — except that each move is allowed only when the digits form a valid letter.
:::

::: Approach
Subproblem: the number of ways to read the first i digits. Recurrence: ways for i = (ways for i − 1, if digit i is not 0) + (ways for i − 2, if the two digits ending at i make a number from 10 to 26).

The empty prefix has one reading (nothing), and the first digit has one reading unless it is 0. Then move along the digits. At each one, start from zero: if this digit is 1–9 it can be its own letter, so add the count from one step back; if it and the digit before it form 10–26, they can be one letter, so add the count from two steps back. Only the last two counts are ever needed, so keep two numbers. A 0 that can't pair with the digit before it (as in `"30"`) makes the count 0, and it stays 0 to the end — correct, because nothing after it can repair the message.

Time O(n): constant work per digit. Space O(1) beyond the digit array.
:::

::: Swift solution
```swift
func numDecodings(_ text: String) -> Int {
    let digits = text.compactMap(\.wholeNumberValue)
    guard let first = digits.first else { return 0 }
    var twoBack = 1                            // ways to read the empty prefix
    var oneBack = first == 0 ? 0 : 1           // ways to read the first digit
    for index in digits.indices.dropFirst() {
        var ways = 0
        if digits[index] != 0 { ways += oneBack }                  // one-digit letter
        let pair = digits[index - 1] * 10 + digits[index]
        if digits[index - 1] != 0 && pair <= 26 { ways += twoBack } // two-digit letter, 10–26
        (twoBack, oneBack) = (oneBack, ways)
    }
    return oneBack
}
```

The two-digit check is two conditions: the first digit isn't 0 (that's what rules out `"06"`) and the value is at most 26. Building the pair with arithmetic instead of parsing a substring is both faster and avoids the trap below.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (`"1"`, `"0"`, `"100"`, `"27"`, `"226"`, `"1201234"`), and 3,000 random digit strings rich in 0s, 1s and 2s checked against a brute-force recursion.
:::

::: Walk it through
**`"2611"`**

| Digit | One-digit letter? | Pair | Two-digit letter? | Ways | twoBack, oneBack after |
|---|---|---|---|---|---|
| 2 | — | — | — | 1 (start) | 1, 1 |
| 6 | yes, +1 | 26 | yes, +1 | 2 | 1, 2 |
| 1 | yes, +2 | 61 | no | 2 | 2, 2 |
| 1 | yes, +2 | 11 | yes, +2 | 4 | 2, 4 |

Answer 4.

**`"10"`** — the 1 gives one way. The 0 can't stand alone (+0), but 10 is a letter, so it takes the count from two back, 1. Answer 1.

**`"06"`** — the first digit is 0, so one-back starts at 0. The 6 alone adds that 0; the pair starts with 0, so it adds nothing. Answer 0.
:::

::: The Swift trap
**`Int("06")` is 6, so a parsed pair passes a "1 to 26" check.** A natural first draft cuts the two characters out and parses them: `if let pair = Int(String(letters[index - 1...index])), (1...26).contains(pair)`. Swift's integer parser accepts leading zeros, so `"06"` parses to 6, lands in range, and is counted as a letter — the draft returns 1 for `"06"` instead of 0. (It also accepts a leading `+`: `Int("+6")` is 6.) Either write the range as `10...26`, or build the number from digits and check that the first digit isn't 0, as the solution does. The parse version also allocates a `String` for every position.

The surrounding trap is the usual one: `text[index]` doesn't compile on a `String`. Converting once — here to `[Int]` with `compactMap(\.wholeNumberValue)` — gives integer indexing and digit values in one step.
:::

::: What they ask next
- **"The message may also contain `*`, which stands for any digit 1–9 (Decode Ways II)."** → Same two counts, but each condition becomes a count of matching cases (`*` alone is 9 ways, `1*` is 9, `2*` is 6, `**` is 15), and the statement asks for the answer modulo 1,000,000,007.
- **"Return the decodings, not the count."** → Backtracking over the same two choices; the output itself can be exponential, so no DP can make it fast.
- **"Why does the count stay 0 after a bad 0?"** → The first prefix with no reading always ends in a 0 that couldn't pair with the digit before it. The next digit can't pair with that 0 either (no piece starts with 0), and on its own it only adds the 0 count — so from there both counts stay 0.
:::
