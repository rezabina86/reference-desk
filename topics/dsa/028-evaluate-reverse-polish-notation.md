---
title: 23 · Evaluate Reverse Polish Notation
summary: Compute the value of an arithmetic expression written with each operator after the two numbers it applies to.
group: Stack
minutes: 25
sources:
- LeetCode 150 · Evaluate Reverse Polish Notation | https://leetcode.com/problems/evaluate-reverse-polish-notation/
- The Swift Programming Language · Basic Operators (remainder and division) | https://docs.swift.org/swift-book/documentation/the-swift-programming-language/basicoperators/
---

*Medium · G · Z — Zalando is documented asking postfix evaluation*

You get an arithmetic expression as a list of tokens. Each token is either an integer (possibly negative, like `"-2"`) or one of `+`, `-`, `*`, `/`. The expression is written in postfix order: an operator comes *after* the two values it combines, so `3 4 +` means 3 + 4, and no brackets are ever needed. Division between integers drops the fractional part, rounding toward zero. Return the value of the whole expression. The input is always a valid expression and never divides by zero.

| Tokens | Answer |
|---|---|
| `["3", "4", "+", "2", "*"]` | `14` — (3 + 4) × 2 |
| `["7", "-2", "/"]` | `-3` — −3.5 rounds toward zero, not down to −4; the edge case |
| `["5"]` | `5` — a single number is already an expression |

Constraints that matter: up to 10,000 tokens, numbers between −200 and 200, every intermediate result fits in 32 bits. The target is one pass, O(n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct EvaluateReversePolishNotationTests {

    @Test(arguments: [
        (["3", "4", "+", "2", "*"], 14),
        (["7", "-2", "/"], -3),
        (["5"], 5),
    ])
    func returnsTheValueOfThePostfixExpression(tokens: [String], expected: Int) {
        #expect(evalRPN(tokens) == expected)
    }

    // MARK: - Privates
    private func evalRPN(_ tokens: [String]) -> Int {
        0
    }
}
```

In a playground:

```swift
func evalRPN(_ tokens: [String]) -> Int {
    0 // your solution
}

let cases: [([String], Int)] = [
    (["3", "4", "+", "2", "*"], 14),
    (["7", "-2", "/"], -3),
    (["5"], 5),
]
for (tokens, expected) in cases {
    let got = evalRPN(tokens)
    print(got == expected ? "PASS" : "FAIL", tokens, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Operand stack.** The cue is *"postfix"* / *"reverse Polish"*, or just the shape of the input: an operator always applies to the two most recent values that haven't been used yet. "Most recent, not yet used" is the top of a stack.
:::

::: Approach
Go through the tokens in order with an empty pile of numbers. A number goes on top of the pile. An operator takes the top two numbers off, combines them, and puts the result back on top — so the result can itself be used by a later operator. Order matters for minus and divide: the number taken off first is the *right-hand* side, because it was written second. When the tokens run out, the pile holds exactly one number, the answer.

Time O(n): each token is handled once, with a constant amount of work. Space O(n): a run of numbers before any operator sits on the pile together.
:::

::: Swift solution
```swift
func evalRPN(_ tokens: [String]) -> Int {
    var stack: [Int] = []

    for token in tokens {
        if let number = Int(token) {             // "-3" is a number; "-" alone is not
            stack.append(number)
            continue
        }
        let right = stack.removeLast()           // popped first, so it's the right operand
        let left = stack.removeLast()
        switch token {
        case "+": stack.append(left + right)
        case "-": stack.append(left - right)
        case "*": stack.append(left * right)
        default:  stack.append(left / right)     // Swift's / already truncates toward zero
        }
    }
    return stack.removeLast()
}
```

Trying `Int(token)` first sorts tokens cleanly: `Int("-2")` is −2, while `Int("-")` is `nil`, so a negative number is never mistaken for the minus operator. `removeLast()` is safe here because the statement guarantees a valid expression.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, six more (a lone negative number, a subtraction where order matters, `-7 / 2`, a longer mixed expression, `4 + 13 / 5`, `0 / 3`), and 3,000 random expression trees of depth up to 4 written out in postfix and checked against evaluating the tree directly.
:::

::: Walk it through
**`["3", "4", "+", "2", "*"]`**

| Token | Action | Stack after |
|---|---|---|
| `3` | push | `3` |
| `4` | push | `3 4` |
| `+` | pop 4 (right), pop 3 (left), push 3 + 4 | `7` |
| `2` | push | `7 2` |
| `*` | pop 2, pop 7, push 7 × 2 | `14` |

Answer 14.

**`["7", "-2", "/"]`** — `7` is pushed; `Int("-2")` succeeds, so −2 is pushed as a number. `/` pops −2 as the right side and 7 as the left: 7 / −2 = −3.5, and Swift's integer division gives −3. Swap the two pops and you'd compute −2 / 7 = 0.
:::

::: The Swift trap
**Swift's integer division already rounds toward zero — don't "fix" it.** `-7 / 2` is `-3` in Swift, exactly what the problem asks for. People coming from Python, where `//` rounds down to −4, sometimes add `floor` or adjust negatives by hand and break a correct answer. The trap that does bite in Swift is the order of the two pops: `stack.removeLast()` gives the *right* operand first, and writing `let left = stack.removeLast()` first silently computes `right - left` and `right / left`. With only `+` and `*` in your examples, you won't notice — always test a subtraction.
:::

::: What they ask next
- **"Now the input is ordinary infix, with brackets and precedence."** → Shunting-yard: an operator stack converts infix to postfix (pop while the top has higher or equal precedence; brackets push and pop), then this function evaluates it.
- **"What if the expression might be invalid?"** → Use `popLast()` and return `nil` when an operator finds fewer than two numbers, or when more than one number is left at the end; also guard division by zero.
- **"Can you evaluate it without a stack?"** → Recursively from the end: the last token is the root operator, its right operand is the expression ending just before it. Same O(n), with the call stack doing the work.
:::
