---
title: 11 · Best Time to Buy and Sell Stock
summary: Given a share's price on each day, find the most you could make by buying once and selling once later.
minutes: 25
sources:
- LeetCode 121 · Best Time to Buy and Sell Stock | https://leetcode.com/problems/best-time-to-buy-and-sell-stock/
---

*Easy · G — the warm-up for this block*

You get an array of prices, one per day, in order. You may buy one share on one day and sell it on a **later** day. Return the largest profit that plan can make. If prices only ever fall, the best plan is not to trade at all, and the answer is 0 — never a negative number.

| Prices | Answer |
|---|---|
| `[8, 3, 6, 2, 7, 4]` | `5` — buy at 2 on day 3, sell at 7 on day 4 |
| `[4, 10, 1, 5]` | `6` — buy at 4, sell at 10; the cheapest day, 1, comes too late to beat it |
| `[9, 7, 4, 1]` | `0` — prices only fall, so don't trade |

Constraints that matter: between 1 and 100,000 days, each price between 0 and 10,000. Checking every buy day against every later sell day is O(n²), about five billion pairs at the top end; the target is a single pass, O(n), with O(1) memory.

::: Pattern and cue
**Sliding window with a running minimum.** The cue is *"buy on one day, sell on a later day"*: a pair of positions where the left one must come first, scanned once from left to right. The left edge of the window sits on the cheapest day seen so far; the right edge is today. The left edge only ever jumps forward, to a new low.
:::

::: Approach
Walk through the days once and remember two numbers: the cheapest price seen so far, and the best profit seen so far. On each day, first ask "is today the cheapest day yet?" and update the cheapest price if so. Then ask "if I sold today, having bought on the cheapest day before it, would that beat my best?" and update the best profit if so. At the end, the best profit is the answer.

That covers every useful plan: for any sell day, the best buy day is simply the cheapest day before it, and the running minimum is exactly that.

Time O(n): one look at each day. Space O(1): two numbers.
:::

::: Swift solution
```swift
func maxProfit(_ prices: [Int]) -> Int {
    var cheapest = Int.max
    var best = 0

    for price in prices {
        cheapest = min(cheapest, price)          // best day to have bought, up to today
        best = max(best, price - cheapest)       // sell today against that day
    }
    return best
}
```

Updating `cheapest` before computing the profit means a same-day buy and sell is considered, which is worth 0 and so never wins — harmless, and it removes a special case. `best` starts at 0, so falling prices and an empty array both return 0.

Verified with `swift test` on Swift 6.2.3 in Swift 6 mode: the three examples above, five more (empty, one day, flat prices, a single 0-to-10,000 jump, and a zigzag), and 3,000 random arrays checked against a brute-force search over every buy and sell pair.
:::

::: Walk it through
**`[4, 10, 1, 5]`**

| Day | Price | Cheapest so far | Profit selling today | Best |
|---|---|---|---|---|
| 0 | 4 | 4 | 0 | 0 |
| 1 | 10 | 4 | 6 | 6 |
| 2 | 1 | 1 | 0 | 6 |
| 3 | 5 | 1 | 4 | 6 |

Answer 6. This is the example that sinks "find the lowest price, then the highest price after it": the lowest price is 1, and the best you can do from there is 4.

**`[9, 7, 4, 1]`** — every day is a new low, so every "profit selling today" is 0 and `best` never moves off 0.
:::

::: The Swift trap
**A one-liner that is secretly O(n²).** Swift makes it tempting to write `prices.indices.map { prices[$0] - (prices[...$0].min() ?? 0) }.max()`. It reads like one pass and it compiles cleanly, but `prices[...$0]` is an `ArraySlice` and `.min()` walks the whole slice every time, so the work grows with the square of the length — the brute force with nicer spelling. Slicing is O(1); anything you call on the slice is not. The other half of the trap is `prices.min()` returning an `Optional`: starting from `prices[0]` or `prices.first!` crashes on an empty array, which is why the solution starts `cheapest` at `Int.max`. `price - Int.max` is negative, not an overflow, so it is safe here.
:::

::: What they ask next
- **"Return the two days, not the profit."** → Keep the index of the cheapest day alongside its price, and record that index plus today's index whenever `best` improves.
- **"You can trade as many times as you like, one share at a time."** → Add up every rise from one day to the next: `max(0, prices[i] − prices[i − 1])` summed. Greedy, O(n).
- **"At most two trades."** → Four running numbers — best after first buy, first sell, second buy, second sell — updated in that order each day. Still O(n), O(1); it's the step towards dynamic programming.
:::
