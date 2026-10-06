---
title: 6 · Encode and Decode Strings
summary: Turn a list of strings into one single string, and back again, so that the round trip always returns exactly the original list.
group: Arrays and hashing
minutes: 25
sources:
- LeetCode 271 · Encode and Decode Strings (premium) | https://leetcode.com/problems/encode-and-decode-strings/
- LintCode 659 · Encode and Decode Strings (free) | https://www.lintcode.com/problem/659/
- Swift standard library · String.UTF8View | https://developer.apple.com/documentation/swift/string/utf8view
---

*Medium · G*

Write two functions. The first takes a list of strings and packs them into a single string; the second takes that single string and unpacks it into the list again. The strings can contain **any** characters: letters, digits, spaces, `#`, commas, emoji, even nothing at all. Whatever list goes in, decoding the encoded form must give back the same strings, in the same order, the same number of them. The packed format is yours to design.

| List in | One possible encoding | List out |
|---|---|---|
| `["swift", "4#ever"]` | `"5#swift6#4#ever"` | `["swift", "4#ever"]` |
| `["", ""]` | `"0#0#"` | `["", ""]` — two empty strings, not one and not none |
| `[]` | `""` | `[]` |

Constraints that matter: up to 200 strings of up to 200 characters each, any characters at all. No separator can be "safe" by itself, since any character you pick may also appear inside a string. Both functions should run in time proportional to the total length. Because the encoding is free, the tests only check the round trip: `decode(encode(list)) == list`.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct EncodeAndDecodeStringsTests {

    @Test(arguments: [
        ["swift", "4#ever"],
        ["", ""],
        [],
    ])
    func decodingTheEncodedTextGivesBackTheSameList(strings: [String]) {
        #expect(decode(encode(strings)) == strings)
    }

    // MARK: - Privates
    private func encode(_ strings: [String]) -> String {
        ""
    }

    private func decode(_ encoded: String) -> [String] {
        []
    }
}
```

In a playground:

```swift
func encode(_ strings: [String]) -> String {
    "" // your solution
}

func decode(_ encoded: String) -> [String] {
    [] // your solution
}

let cases: [[String]] = [
    ["swift", "4#ever"],
    ["", ""],
    [],
]
for strings in cases {
    let got = decode(encode(strings))
    print(got == strings ? "PASS" : "FAIL", strings, "→", got)
}
```
:::

::: Pattern and cue
**Length-prefix framing.** The cue is *"any characters"* combined with *"get back exactly"*. Any separator you choose can appear inside a string, so instead of marking where each string *ends*, say up front how *long* it is. A reader that knows the length doesn't need to look at the content at all, so the content may hold anything. It is the same idea network protocols and file formats use to frame messages.
:::

::: Approach
To encode, write each string as its length, then a `#`, then the string itself, and join them all together. To decode, walk the packed string from the start: read digits until you reach a `#`, which gives you the length of the next string. Take exactly that many units after the `#` as the string, without looking at what they are, and jump past them to where the next length begins. Repeat until you reach the end.

A `#` or a digit *inside* a string can't confuse the decoder, because the decoder never searches for `#` inside a string: it only reads a `#` straight after a length, and it skips string contents by counting.

Time O(L) for both, where L is the total length of all strings: each unit is written once and read once. Space O(L) for the output.
:::

::: Swift solution
```swift
func encode(_ strings: [String]) -> String {
    var encoded = ""
    for string in strings {
        encoded += "\(string.utf8.count)#\(string)"   // length in bytes, then the bytes
    }
    return encoded
}

func decode(_ encoded: String) -> [String] {
    let bytes = Array(encoded.utf8)
    let hash = UInt8(ascii: "#")
    let zero = UInt8(ascii: "0")
    var strings: [String] = []
    var index = 0

    while index < bytes.count {
        var length = 0
        while bytes[index] != hash {
            length = length * 10 + Int(bytes[index] - zero)
            index += 1
        }
        index += 1                                     // step over the "#"
        let end = index + length
        strings.append(String(decoding: bytes[index..<end], as: UTF8.self))
        index = end
    }
    return strings
}
```

The length is counted in UTF-8 bytes and the decoder walks the same bytes, so the two sides agree on every unit, whatever the text contains. The trap below is why it can't be `string.count` and a walk over `Character`s.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (one empty string, a string that looks like an encoding (`"12#"`), strings of 10 and 200 characters so the length has several digits, emoji and accented letters, a string that starts with a combining accent, a single string of only `#`), and 3,000 random lists drawn from an alphabet of digits, `#`, letters, spaces, `é`, a combining accent and an emoji, each checked for an exact round trip.
:::

::: Walk it through
**Encode `["swift", "4#ever"]`** → `"5#"` + `"swift"` + `"6#"` + `"4#ever"` = `"5#swift6#4#ever"`.

**Decode `"5#swift6#4#ever"`**

| Position | Read | Length | Take | List so far |
|---|---|---|---|---|
| 0 | `5`, then `#` | 5 | positions 2–6: `swift` | `["swift"]` |
| 7 | `6`, then `#` | 6 | positions 9–14: `4#ever` | `["swift", "4#ever"]` |
| 15 | end | | | done |

The `#` inside `4#ever` is never examined: by then the decoder is counting six units, not looking for separators.

**`["", ""]`** encodes to `"0#0#"`. The decoder reads length 0, takes nothing, appends `""`, and does the same again: two empty strings. A separator-only scheme such as joining with `","` can't tell `[""]` from `[]`; the length prefix can.
:::

::: The Swift trap
**Characters can swallow your separator.** It feels natural to write the length as `string.count` and decode by walking `Array(encoded)`, a `[Character]`. That breaks on text whose first character is a combining mark. Encode `["e", "\u{301}"]` (the second string is just a combining acute accent) and you get `1#e1#` followed by the accent; Swift joins the `#` and the accent into **one** `Character`, `"#́"`, which is not equal to `"#"`. The decoder never finds the separator and runs off the end. Swift `Character`s are user-perceived characters that can merge across your boundaries, so a length in one unit has to be read back in exactly that unit. Bytes (`utf8`) never merge, which is why the solution counts and walks bytes.

Smaller one: `bytes[index] - zero` is `UInt8` arithmetic. With well-formed input it never goes below zero, but on a corrupted string a byte below `"0"` traps rather than giving a wrong number. Converting first, `Int(bytes[index]) - Int(zero)`, turns that crash into a value you can check.
:::

::: What they ask next
- **"Why not just escape the separator?"** → Also correct: write `#` as `##` and end each string with `#,`, as CSV does with quotes. Decoding then has to inspect every character; the length prefix skips the contents.
- **"Make the length a fixed 4 bytes instead of digits plus `#`."** → Then no separator is needed at all, and the decoder reads exactly 4 bytes for the length every time. That is how binary protocols frame messages; it caps a string at 4 GB.
- **"How would you do this in a real iOS app?"** → `JSONEncoder` on the `[String]`, or `PropertyListEncoder`. Writing your own format is the exercise, not the production answer.
:::
