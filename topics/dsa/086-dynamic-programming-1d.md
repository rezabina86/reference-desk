---
title: 1-D dynamic programming — the idea
summary: Answer a big question by answering a row of smaller copies of it, each one once, and building on the ones already answered.
group: 1-D dynamic programming
minutes: 10
sources:
- Swift standard library · Array.init(repeating:count:) | https://developer.apple.com/documentation/swift/array/init(repeating:count:)
- Swift standard library · Int.addingReportingOverflow(_:) | https://developer.apple.com/documentation/swift/int/addingreportingoverflow(_:)
---

Some problems ask a question about a whole input — "how many ways to the top of 30 stairs?" — whose answer is built from the same question about a smaller input — "how many ways to stair 29, and to stair 28?". Asked naively, those smaller questions repeat: stair 27 is needed by both 29 and 28, and so on down, so the work doubles at every level. Dynamic programming (DP) answers each smaller question **once**, writes the answer down, and reads it back the next time it is needed. That single change turns exponential work into a straight line.

## When to reach for it

- The statement asks **"how many ways"**, **"the minimum cost"**, **"the maximum total"**, or **"is it possible"** — one number or a yes/no, not the list of every solution.
- You make a **choice at each position** (take this house or skip it, use this coin or not, cut here or not) and the choices **overlap**: two different histories arrive at the same position.
- A greedy rule ("always take the biggest coin") looks tempting but you can build a counter-example in a minute.
- The input is **one sequence** — an array, a string, a number n — and the natural question is "what is the best answer for the first i items?" or "for the items from i onward?".
- The brute force is recursion with **two or more calls per step** on overlapping arguments.

## The idea in plain words

Think of filling in a row of boxes on paper, one box per position. Each box holds the answer for "the problem, but only up to here". The first box or two you can fill in without thinking: zero stairs climbed, zero houses robbed. Every later box is filled using a short rule that looks only at a few boxes already filled to its left. When the last box is filled, it holds the answer.

Every DP solution is three decisions, and saying them out loud is most of the interview:

1. **The subproblem** — what one box means, in one sentence. "`ways[i]` is the number of ways to stand on stair i." Get this sentence right and the rest follows; get it vague and nothing works.
2. **The recurrence** — how one box is computed from earlier boxes. "`ways[i] = ways[i - 1] + ways[i - 2]`, because the last move was one stair or two."
3. **The base cases and the order** — which boxes are known up front, and a fill order in which every box's inputs are already filled.

There are two ways to fill the boxes:

- **Top-down (memoisation).** Write the recursion exactly as the recurrence reads, and keep a dictionary of answers already computed. Ask for the final box; it asks for smaller boxes; each is computed once and then looked up. Easy to write from the recurrence, but it uses the call stack.
- **Bottom-up (tabulation).** Make an array, fill the base cases, and loop from small to large. No recursion, no dictionary, and usually the version interviewers expect you to end on.

Then, often, a third step: if each box only reads the last one or two boxes, you don't need the whole row — keep **two rolling variables** and the space drops from O(n) to O(1).

## The template in Swift

The toy problem: each stair has a price you pay when you step off it; you may start on stair 0 or 1, climb one or two stairs at a time, and want to reach the top (just past the last stair) as cheaply as possible.

```swift
// Top-down: the recurrence as written, with a memo so each step is solved once.
func cheapestClimbTopDown(_ price: [Int]) -> Int {
    var memo: [Int: Int] = [:]
    func cheapest(_ step: Int) -> Int {            // subproblem: cheapest way to stand on `step`
        if step <= 1 { return 0 }                  // base cases: you may start on 0 or 1 for free
        if let known = memo[step] { return known }
        let answer = min(cheapest(step - 1) + price[step - 1],
                         cheapest(step - 2) + price[step - 2])
        memo[step] = answer
        return answer
    }
    return cheapest(price.count)                   // "the top" is one past the last stair
}

// Bottom-up: the same boxes, filled left to right.
func cheapestClimbTable(_ price: [Int]) -> Int {
    guard price.count > 1 else { return 0 }
    var cheapest = [Int](repeating: 0, count: price.count + 1)   // base cases are already 0
    for step in 2...price.count {
        cheapest[step] = min(cheapest[step - 1] + price[step - 1],
                             cheapest[step - 2] + price[step - 2])
    }
    return cheapest[price.count]
}

// Rolling: each box reads only the two before it, so keep just those two.
func cheapestClimb(_ price: [Int]) -> Int {
    var twoBelow = 0, oneBelow = 0
    for step in price.indices.dropFirst() {
        (twoBelow, oneBelow) = (oneBelow, min(oneBelow + price[step], twoBelow + price[step - 1]))
    }
    return oneBelow
}

let cost = cheapestClimb([10, 15, 20])   // 15: start on stair 1, pay 15, jump two to the top
```

All three return the same answer; the tests compare them on random prices.

## Variations

- **Count the ways.** Boxes hold counts and the recurrence **adds**: Climbing Stairs, Decode Ways.
- **Take it or skip it.** Each position is either used or not, and using it forbids its neighbour; the recurrence is a `max` of "skip" and "take": House Robber, House Robber II (run it twice to break a circle).
- **Best over every earlier box.** The recurrence looks back at **all** earlier boxes, not just one or two, so it is O(n²) or O(n·k): Coin Change (one look-back per coin), Word Break (one per cut point), Longest Increasing Subsequence (one per earlier element).
- **Carry two numbers per box.** One number isn't enough to decide the next box, so carry two — the largest and the smallest product so far: Maximum Product Subarray.
- **Grow from a centre.** Palindromes are built from smaller palindromes in the middle; the DP table exists, but expanding around each centre does the same work with O(1) memory: Longest Palindromic Substring, Palindromic Substrings.

## Complexity

Time is (number of boxes) × (work to fill one box). The template has n boxes and looks at two earlier boxes each, so O(n). If a box looks at every earlier box, it is O(n²); at one box per coin, O(n·k). Space is the number of boxes you keep: O(n) for the table or the memo, O(1) once you roll the variables. Top-down also uses O(n) call-stack frames on top of the memo.

## Swift traps

- **Recursion depth.** Memoised recursion goes as deep as the input is long. A few thousand frames are fine on the main thread, but threads other than the main one (including the ones test runners use) have much smaller stacks, and a deep enough recursion crashes with no Swift error. Bottom-up never has this problem; it's the main reason to convert.
- **`Int.max` as "infinity" overflows.** A minimum-cost table initialised with `Int.max` traps on the first `+ 1`. Use a value just above any real answer — `amount + 1` coins, say — so adding to it is safe.
- **`1...n` crashes when n is 0.** A closed range whose end is below its start traps at runtime. Guard the small cases first (as the bottom-up template does), or loop over `indices`.
- **Update rolling variables together.** Writing `twoBelow = oneBelow` and then `oneBelow = twoBelow + …` reads the value you just overwrote. A tuple assignment `(a, b) = (b, a + b)` evaluates the whole right side first.
- **No integer subscript on `String`.** String DP (Word Break, Decode Ways, palindromes) indexes positions constantly; convert once with `Array(text)`.
- **Counts grow fast.** Ways-counting answers grow exponentially; past a certain n they exceed `Int.max` and Swift traps instead of wrapping. If the statement asks for the answer modulo 1,000,000,007, take the remainder at every addition.

## The problems in this topic

- [72 · Climbing Stairs](#/dsa/climbing-stairs) — Easy
- [73 · House Robber](#/dsa/house-robber) — Medium
- [74 · House Robber II](#/dsa/house-robber-ii) — Medium
- [75 · Coin Change](#/dsa/coin-change) — Medium
- [76 · Maximum Product Subarray](#/dsa/maximum-product-subarray) — Medium
- [77 · Word Break](#/dsa/word-break) — Medium
- [78 · Decode Ways](#/dsa/decode-ways) — Medium
- [79 · Longest Increasing Subsequence](#/dsa/longest-increasing-subsequence) — Medium
- [80 · Longest Palindromic Substring](#/dsa/longest-palindromic-substring) — Medium
- [81 · Palindromic Substrings](#/dsa/palindromic-substrings) — Medium
