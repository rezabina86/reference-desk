---
title: Arrays and hashing — the idea
summary: Trade memory for speed by remembering what you've already seen, so each question about the past costs one lookup instead of another pass.
group: Arrays and hashing
minutes: 8
sources:
- Swift standard library · Dictionary | https://developer.apple.com/documentation/swift/dictionary
- Swift standard library · Set | https://developer.apple.com/documentation/swift/set
- Swift standard library · Hashable | https://developer.apple.com/documentation/swift/hashable
---

Most first attempts at an array problem compare every element with every other one: two nested loops, O(n²). This topic is about the single most useful way out. As you walk the array once, write down what you have seen in a structure that answers "is this here?" in constant time. Then the inner loop disappears.

## When to reach for it

- *"appears more than once"*, *"duplicate"*, *"distinct"* — a set
- *"find a pair"*, *"two numbers that add up to"*, *"its partner"* — a dictionary from value to position
- *"how often"*, *"most frequent"*, *"the same number of times"* — a dictionary from value to count
- *"group together"*, *"the ones that share"* — a dictionary from a key to a list
- *"unsorted"* together with *"in O(n)"* — sorting is ruled out, so constant-time lookups have to replace it

## The idea in plain words

Picture a cloakroom attendant. Without a ticket system, finding your coat means walking along every hook and checking each one. With tickets, the number on your ticket says exactly which hook to go to: one step, however many coats there are. A hash set or a dictionary is that ticket system. It turns a value into a position directly, so "have I seen 42?" doesn't need a search.

The price is memory: you keep a note for every element you've walked past. Almost every problem here is the same trade, O(n) extra space bought to turn O(n²) time into O(n). The skill is choosing **what to write down**: the value itself, where it was, how many times it appeared, or a key that makes different-looking items equal.

## The template in Swift

```swift
/// "Have I seen this before?" — a set. Returns the first value that repeats.
func firstRepeat<Element: Hashable>(_ items: [Element]) -> Element? {
    var seen = Set<Element>()
    for item in items {
        if !seen.insert(item).inserted { return item }   // insert reports whether it was new
    }
    return nil
}

/// "How many of each?" — a dictionary of counts.
func counts<Element: Hashable>(_ items: [Element]) -> [Element: Int] {
    var counts: [Element: Int] = [:]
    for item in items {
        counts[item, default: 0] += 1
    }
    return counts
}

/// "Which ones belong together?" — a dictionary from a shared key to a list.
func grouped<Element, Key: Hashable>(_ items: [Element], by key: (Element) -> Key) -> [Key: [Element]] {
    var groups: [Key: [Element]] = [:]
    for item in items {
        groups[key(item), default: []].append(item)
    }
    return groups
}

/// "Have I seen what this one needs, and where?" — a dictionary from value to position.
/// Look first, then record, so an element never pairs with itself.
func firstPair(in numbers: [Int], where partner: (Int) -> Int) -> (Int, Int)? {
    var indexByValue: [Int: Int] = [:]
    for (index, number) in numbers.enumerated() {
        if let earlier = indexByValue[partner(number)] { return (earlier, index) }
        indexByValue[number] = index
    }
    return nil
}
```

## Variations

1. **Membership.** A set of everything seen, asked "is this here?" — a repeat check, or "is the next value present?" when walking runs of values.
2. **Complement lookup.** For each element, compute what its partner would have to be, and ask a dictionary whether that partner has appeared and where. The order "look, then record" is load-bearing.
3. **Counting.** A dictionary from value to count, then a question about the counts: are they all equal between two inputs, or which are the largest? When counts are bounded by n, they can be used as array positions (bucketing) and no sort is needed.
4. **Canonical key.** Different-looking items that should count as the same are mapped to one key — sorted letters, a tally — and grouped under it. The whole problem becomes choosing that key.

One problem here is an outlier on purpose: packing a list of strings into one string and back. It is in this group because it is the array-and-string bookkeeping every other problem assumes you can do without thinking.

## Complexity

Time O(n): one pass, with O(1) **average** work per set or dictionary operation. Hashing can degrade to O(n) per operation on a pathological input, which is worth one sentence in an interview and no more; Swift seeds its hashes randomly per process, which makes deliberate collisions hard. Space O(n) for the stored notes, or O(k) when only k distinct keys can exist (26 letters, for example).

## Swift traps

- **A tuple is not `Hashable`.** `Set<(Int, Int)>` doesn't compile. Use a small `struct` that conforms to `Hashable`, or an `[Int]` as the key.
- **Reading a dictionary gives an optional.** `counts[key]` is `Int?`. Use `counts[key, default: 0]`: when read it returns 0 without inserting, when written (`+= 1`) it inserts and updates in one step. Avoid `!` on lookups.
- **Dictionary and set order changes on every run.** Swift randomises hashing per process, so `dict.values` or iterating a `Set` comes out in a different order each time. Never compare unordered results directly in a test: sort them first.
- **`String` is not an array.** There is no `text[i]`. `Array(text)` gives `[Character]` with integer indices at O(n) cost; `text.utf8` gives bytes. They count different things, and the difference matters for anything beyond ASCII.
- **`Double.nan` is never equal to itself,** so a set can hold several NaNs and never report them as duplicates.
- **No `Heap` in the standard library.** When counting turns into "the k largest", say the heap answer, then write a sort or a bucket array.

## The problems in this topic

- [1 · Contains Duplicate](#/dsa/contains-duplicate) — Easy
- [2 · Valid Anagram](#/dsa/valid-anagram) — Easy
- [3 · Two Sum](#/dsa/two-sum) — Easy
- [4 · Group Anagrams](#/dsa/group-anagrams) — Medium
- [5 · Top K Frequent Elements](#/dsa/top-k-frequent-elements) — Medium
- [6 · Encode and Decode Strings](#/dsa/encode-and-decode-strings) — Medium
- [7 · Longest Consecutive Sequence](#/dsa/longest-consecutive-sequence) — Medium
