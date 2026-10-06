---
title: 75 · Coin Change
summary: Given coin values you can use as often as you like, find the fewest coins that add up to an amount exactly, or report that no combination does.
group: 1-D dynamic programming
minutes: 25
sources:
- LeetCode 322 · Coin Change | https://leetcode.com/problems/coin-change/
- Swift standard library · Int.max | https://developer.apple.com/documentation/swift/int/max
---

*Medium · G*

You get a list of coin values and an amount. You have an unlimited supply of every coin. Return the smallest number of coins whose values add up to the amount exactly. If no combination reaches it, return −1. An amount of 0 needs no coins at all.

| Coins | Amount | Answer |
|---|---|---|
| `[1, 4, 5]` | `8` | `2` — 4 + 4; taking the biggest coin first gives 5 + 1 + 1 + 1, four coins |
| `[3]` | `7` | `-1` — multiples of 3 skip 7 |
| `[2]` | `0` | `0` — nothing to pay |

Constraints that matter: up to 12 coin values, each between 1 and 2³¹ − 1; the amount is between 0 and 10,000. Trying combinations is exponential; the target is O(amount × coins) time and O(amount) space.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct CoinChangeTests {

    @Test(arguments: [
        ([1, 4, 5], 8, 2),
        ([3], 7, -1),
        ([2], 0, 0),
    ])
    func returnsTheFewestCoinsOrMinusOne(coins: [Int], amount: Int, expected: Int) {
        #expect(coinChange(coins, amount) == expected)
    }

    // MARK: - Privates
    private func coinChange(_ coins: [Int], _ amount: Int) -> Int {
        0
    }
}
```

In a playground:

```swift
func coinChange(_ coins: [Int], _ amount: Int) -> Int {
    0 // your solution
}

let cases: [([Int], Int, Int)] = [
    ([1, 4, 5], 8, 2),
    ([3], 7, -1),
    ([2], 0, 0),
]
for (coins, amount, expected) in cases {
    let got = coinChange(coins, amount)
    print(got == expected ? "PASS" : "FAIL", coins, amount, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**1-D dynamic programming over the amount.** The cue is *"the fewest"* plus *"as many of each as you like"*, and the first example breaks the greedy idea of always taking the biggest coin. Whatever the best handful for an amount is, removing its last coin leaves the best handful for a smaller amount — so the answers for small amounts build the answers for large ones.
:::

::: Approach
Subproblem: the fewest coins that make the total t, for every t from 0 up to the amount. Recurrence: fewest for t = 1 + the smallest of (fewest for t − c) over every coin c that is no bigger than t.

Make a list with one entry per total from 0 to the amount. Total 0 needs 0 coins. Fill every other total in increasing order: try each coin as the last one paid, look up the already-known best for what remains, and keep the smallest. Totals that can't be made hold a marker meaning "impossible", chosen bigger than any real answer — `amount + 1` works, since even all 1-coins need only `amount` coins. At the end, if the amount still holds the marker, return −1.

Time O(amount × coins): every total tries every coin. Space O(amount): the list of totals.
:::

::: Swift solution
```swift
func coinChange(_ coins: [Int], _ amount: Int) -> Int {
    guard amount > 0 else { return 0 }
    let impossible = amount + 1                  // more coins than any real answer can need
    var fewest = [Int](repeating: impossible, count: amount + 1)
    fewest[0] = 0
    for total in 1...amount {
        for coin in coins where coin <= total {
            fewest[total] = min(fewest[total], fewest[total - coin] + 1)
        }
    }
    return fewest[amount] == impossible ? -1 : fewest[amount]
}
```

`impossible + 1` is at most `amount + 2`, so the `+ 1` can never overflow, and `min` keeps a real answer over it whenever one exists. The `where coin <= total` filter keeps `total - coin` from going negative, which would crash on the array read.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (a single 1-coin, 13 with `[1, 4, 5]`, duplicate coin values, a coin of 2³¹ − 1 with amount 2, a 6,249 amount with four mixed coins), the 10,000 amount with only 1-coins, and 2,000 random cases checked against a breadth-first search over reachable totals.
:::

::: Walk it through
**Coins `[1, 4, 5]`, amount 8**

| Total | Using 1 | Using 4 | Using 5 | Fewest |
|---|---|---|---|---|
| 0 | | | | 0 |
| 1 | f[0] + 1 = 1 | | | 1 |
| 2 | f[1] + 1 = 2 | | | 2 |
| 3 | f[2] + 1 = 3 | | | 3 |
| 4 | f[3] + 1 = 4 | f[0] + 1 = 1 | | 1 |
| 5 | f[4] + 1 = 2 | f[1] + 1 = 2 | f[0] + 1 = 1 | 1 |
| 6 | f[5] + 1 = 2 | f[2] + 1 = 3 | f[1] + 1 = 2 | 2 |
| 7 | f[6] + 1 = 3 | f[3] + 1 = 4 | f[2] + 1 = 3 | 3 |
| 8 | f[7] + 1 = 4 | f[4] + 1 = 2 | f[3] + 1 = 4 | 2 |

Answer 2.

**Coins `[3]`, amount 7** — totals 3 and 6 get 1 and 2; every other total, 7 included, keeps the marker 8 because the total three below it is also the marker. Answer −1.
:::

::: The Swift trap
**`Int.max` as "infinity" crashes on the first `+ 1`.** The natural first draft fills the list with `Int.max` and writes `min(fewest[total], fewest[total - coin] + 1)`. In C that addition wraps to a huge negative number and gives a wrong answer; in Swift it **traps** — the program stops with an overflow error the first time an unreachable total is read, which happens on almost every input (total 1 with coins `[2]`). The fix is a smaller sentinel: `amount + 1` is bigger than any real answer and adding 1 to it is harmless. Guarding with `if fewest[total - coin] != Int.max` also works but is easier to forget in one of the branches.

A second, quieter trap: the top-down version, `fewest(total)` calling itself on `total - coin`, recurses up to 10,000 levels deep with the 1-coin. That's fine on the main thread, but on a background thread with a small stack it can crash without a Swift error message — another reason to write the table.
:::

::: What they ask next
- **"Count the number of combinations instead (Coin Change II)."** → Same list, but `ways[t] += ways[t - c]`, and loop **coins outside, totals inside** so each combination is counted once regardless of order.
- **"Return the coins themselves."** → Store, for each total, the coin that gave its best; then follow those coins back from the amount to 0.
- **"Why not greedy?"** → Greedy works for some coin systems (euros, dollars) but not in general: `[1, 4, 5]` for 8 is the counter-example, and saying it out loud is the expected first move.
:::
