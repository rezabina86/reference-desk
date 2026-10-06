---
title: 34 · Add Two Numbers
summary: Two whole numbers are stored as linked lists of digits, ones digit first; return their sum stored the same way.
group: Linked list
minutes: 25
sources:
- LeetCode 2 · Add Two Numbers | https://leetcode.com/problems/add-two-numbers/
---

*Medium*

Two non-negative whole numbers are each stored as a linked list of single digits, **lowest digit first**: the first node is the ones digit, the next the tens, and so on. So `4 → 0 → 9` is 904. Add the two numbers and return the sum as a new list in the same form. Neither number has leading zeros, except the number 0 itself, which is the single node `0`.

| First | Second | Answer |
|---|---|---|
| `4 → 0 → 9` (904) | `8 → 2` (28) | `2 → 3 → 9` (932) |
| `9 → 9` (99) | `1` (1) | `0 → 0 → 1` (100) |
| `0` | `0` | `0` |

Constraints that matter: each list has 1 to 100 nodes, so the numbers can have 100 digits — far more than any built-in integer holds. The target is one pass, O(max(m, n)).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct AddTwoNumbersTests {

    @Test(arguments: [
        ([4, 0, 9], [8, 2], [2, 3, 9]),
        ([9, 9], [1], [0, 0, 1]),
        ([0], [0], [0]),
    ])
    func returnsTheSumWithTheOnesDigitFirst(first: [Int], second: [Int], expected: [Int]) {
        #expect(values(of: addTwoNumbers(makeList(first), makeList(second))) == expected)
    }

    // MARK: - Privates
    private func addTwoNumbers(_ l1: ListNode?, _ l2: ListNode?) -> ListNode? {
        nil
    }
}

private final class ListNode {
    var value: Int
    var next: ListNode?
    init(_ value: Int, _ next: ListNode? = nil) { self.value = value; self.next = next }
}

private func makeList(_ values: [Int]) -> ListNode? {
    var head: ListNode?
    for value in values.reversed() { head = ListNode(value, head) }
    return head
}

private func values(of head: ListNode?) -> [Int] {
    var result: [Int] = []
    var node = head
    while let current = node { result.append(current.value); node = current.next }
    return result
}
```

In a playground:

```swift
final class ListNode {
    var value: Int
    var next: ListNode?
    init(_ value: Int, _ next: ListNode? = nil) { self.value = value; self.next = next }
}

func makeList(_ values: [Int]) -> ListNode? {
    var head: ListNode?
    for value in values.reversed() { head = ListNode(value, head) }
    return head
}

func values(of head: ListNode?) -> [Int] {
    var result: [Int] = []
    var node = head
    while let current = node { result.append(current.value); node = current.next }
    return result
}

func addTwoNumbers(_ l1: ListNode?, _ l2: ListNode?) -> ListNode? {
    nil // your solution
}

let cases: [([Int], [Int], [Int])] = [
    ([4, 0, 9], [8, 2], [2, 3, 9]),
    ([9, 9], [1], [0, 0, 1]),
    ([0], [0], [0]),
]
for (first, second, expected) in cases {
    let got = values(of: addTwoNumbers(makeList(first), makeList(second)))
    print(got == expected ? "PASS" : "FAIL", first, second, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Dummy head plus a carry, walking two lists side by side.** The cue is *"digits stored in reverse order"*: the lists already run in the order you add on paper, ones first, so you can add as you walk and build the answer behind a placeholder node.
:::

::: Approach
Add the way you learned at school, right to left, which here means front to back. Walk both lists together. At each step, add the two digits (a list that has run out counts as 0) and the carry from the step before. The digit to write down is that sum's last digit; the new carry is the sum divided by ten, which is 0 or 1. Append the digit to the result and move both lists on. Keep going while either list has digits **or there is still a carry**, so 99 + 1 gets its third digit.

Time O(max(m, n)): one step per digit of the longer number, plus one for a final carry. Space O(max(m, n)) for the answer itself; O(1) besides it.
:::

::: Swift solution
```swift
func addTwoNumbers(_ l1: ListNode?, _ l2: ListNode?) -> ListNode? {
    let dummy = ListNode(0)
    var tail = dummy
    var first = l1
    var second = l2
    var carry = 0

    while first != nil || second != nil || carry > 0 {
        let sum = (first?.value ?? 0) + (second?.value ?? 0) + carry
        carry = sum / 10
        let digit = ListNode(sum % 10)
        tail.next = digit
        tail = digit
        first = first?.next
        second = second?.next
    }
    return dummy.next
}
```

`carry > 0` in the loop condition is the line people forget: without it `9 → 9` plus `1` returns `0 → 0` and loses the hundred.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, five more (lists of different lengths, a carry that runs the full length, a 100-digit number plus 1, a single digit plus a long number, two 30-digit numbers that overflow `Int`), and 2,000 random pairs of up to 18 digits checked against `Int` addition.
:::

::: Walk it through
**`4 → 0 → 9` (904) plus `8 → 2` (28)**

| Step | Digits | Carry in | Sum | Write | Carry out |
|---|---|---|---|---|---|
| 1 | 4, 8 | 0 | 12 | 2 | 1 |
| 2 | 0, 2 | 1 | 3 | 3 | 0 |
| 3 | 9, — | 0 | 9 | 9 | 0 |

Both lists are used up and the carry is 0: `2 → 3 → 9`, which is 932.

**`9 → 9` plus `1`** — 9 + 1 = 10, write 0, carry 1; 9 + 0 + 1 = 10, write 0, carry 1; both lists are empty but the carry is 1, so one more step writes 1: `0 → 0 → 1`.
:::

::: The Swift trap
**Converting to `Int` and back doesn't just give a wrong answer, it crashes.** The tempting shortcut reads each list into an `Int`, adds, and writes the digits back. `Int.max` has 19 digits, and these numbers can have 100. In C or Java the multiplication would silently wrap to garbage; Swift checks arithmetic, so `number * 10 + digit` on the twentieth digit stops the program with an overflow error. The `&*` and `&+` operators would wrap instead, and still be wrong. Digit by digit is the only answer that holds.
:::

::: What they ask next
- **"The digits are stored highest first."** → Reverse both lists and reuse this, or push each list's digits onto two arrays used as stacks, add from the top, and prepend each new digit to the result.
- **"Same thing with numbers given as strings."** → The same carry loop over `Array(text)` from the end, with `Character.wholeNumberValue` for each digit; build the result reversed, then reverse it once.
- **"Why not build the result as an array and convert at the end?"** → It works, but costs a second O(n) pass and an array; the dummy head builds the list directly.
:::
