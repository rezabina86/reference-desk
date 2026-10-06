---
title: 65 · Course Schedule
summary: An app is split into numbered modules, some of which must be built before others; decide whether every module can be built at all.
group: Graphs
minutes: 25
sources:
- LeetCode 207 · Course Schedule | https://leetcode.com/problems/course-schedule/
- Wikipedia · Topological sorting (Kahn's algorithm) | https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
---

*Medium · G*

An app is split into modules numbered `0` to `n − 1` — think Swift packages in a workspace. You get a list of pairs `[module, dependency]`, each meaning *module* imports *dependency*, so *dependency* has to be built first. The build system builds one module at a time, and only once everything it depends on is built. Return `true` if every module can eventually be built, and `false` if the dependencies make that impossible.

| Modules | Dependencies | Answer |
|---|---|---|
| `4` | `[[1, 0], [2, 1], [3, 1], [3, 2]]` | `true` — build 0, 1, 2, 3 in that order |
| `3` | `[[0, 1], [1, 2], [2, 0]]` | `false` — 0 needs 1, 1 needs 2, 2 needs 0: a circle |
| `1` | `[]` | `true` — one module, nothing to wait for |

Constraints that matter: up to 2,000 modules and 5,000 pairs, no pair listed twice. Modules with no dependencies at all are allowed. The target is O(n + p), with p the number of pairs.

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct CourseScheduleTests {

    @Test(arguments: [
        (4, [[1, 0], [2, 1], [3, 1], [3, 2]], true),
        (3, [[0, 1], [1, 2], [2, 0]], false),
        (1, [], true),
    ])
    func decidesWhetherEveryModuleCanBeBuilt(moduleCount: Int, dependencies: [[Int]], expected: Bool) {
        #expect(canBuildAll(moduleCount, dependencies) == expected)
    }

    // MARK: - Privates
    private func canBuildAll(_ moduleCount: Int, _ dependencies: [[Int]]) -> Bool {
        false
    }
}
```

In a playground:

```swift
func canBuildAll(_ moduleCount: Int, _ dependencies: [[Int]]) -> Bool {
    false // your solution
}

let cases: [(Int, [[Int]], Bool)] = [
    (4, [[1, 0], [2, 1], [3, 1], [3, 2]], true),
    (3, [[0, 1], [1, 2], [2, 0]], false),
    (1, [], true),
]
for (moduleCount, dependencies, expected) in cases {
    let got = canBuildAll(moduleCount, dependencies)
    print(got == expected ? "PASS" : "FAIL", moduleCount, dependencies, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Topological sort (Kahn's algorithm) to detect a cycle.** The cue is *"must be built before"* — an ordering constraint between items — plus *"can all of them"* be done. Modules are nodes, each dependency is an arrow from the module that must come first to the one that waits for it, and the answer is `false` exactly when the arrows form a loop.
:::

::: Approach
For each module, count how many dependencies it is still waiting on, and list which modules are waiting on it. Every module waiting on nothing can be built right away, so put those in a "ready" list. Then take ready modules one at a time and build them: for each module that depended on the one just built, lower its waiting count by one, and when that count reaches zero, it joins the ready list. When the ready list runs out, count how many modules were built. If it's all of them, the answer is `true`. If some were never built, each of those is still waiting on another unbuilt module — they wait on each other in a circle, so the answer is `false`.

Time O(n + p): every module enters the ready list at most once, and every pair is looked at once when it's set up and once when its dependency is built. Space O(n + p) for the lists of dependents.
:::

::: Swift solution
```swift
func canBuildAll(_ moduleCount: Int, _ dependencies: [[Int]]) -> Bool {
    var dependents = Array(repeating: [Int](), count: moduleCount)
    var waitingOn = Array(repeating: 0, count: moduleCount)
    for pair in dependencies {
        let module = pair[0], dependency = pair[1]
        dependents[dependency].append(module)    // dependency → module: build dependency first
        waitingOn[module] += 1
    }

    var ready = (0..<moduleCount).filter { waitingOn[$0] == 0 }
    var head = 0
    while head < ready.count {
        let module = ready[head]; head += 1
        for dependent in dependents[module] {
            waitingOn[dependent] -= 1
            if waitingOn[dependent] == 0 { ready.append(dependent) }
        }
    }
    return ready.count == moduleCount            // anything left over sits on a cycle
}
```

`ready` is never shrunk: `head` walks along it, so when the loop ends `ready` holds every module that got built, in a valid build order — return it instead of the `Bool` and you've answered the follow-up.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (a module depending on itself, five modules with no pairs, the same pair listed twice, a cycle of two next to an unrelated valid chain), and 2,000 random dependency lists checked against a brute force that repeatedly deletes a module nobody is waiting on.
:::

::: Walk it through
**4 modules, `[[1, 0], [2, 1], [3, 1], [3, 2]]`** — waiting counts start at 0: 0, 1: 1, 2: 1, 3: 2.

| Build | Its dependents | Counts after | Ready list |
|---|---|---|---|
| — | — | 0, 1, 1, 2 | 0 |
| 0 | 1 | 1 → 0 | 0, 1 |
| 1 | 2, 3 | 2 → 0, 3 → 1 | 0, 1, 2 |
| 2 | 3 | 3 → 0 | 0, 1, 2, 3 |
| 3 | none | — | 0, 1, 2, 3 |

Four built out of four: `true`.

**3 modules, `[[0, 1], [1, 2], [2, 0]]`** — each module waits on exactly one other, so no count starts at zero. The ready list is empty from the start, nothing is built, and 0 ≠ 3: `false`.
:::

::: The Swift trap
**In the DFS version, passing the state array as a parameter turns O(n + p) into exponential time.** The other common solution colours each module *unvisited*, *in progress* or *done*, and reports a cycle when the search meets an *in progress* module. Write it as a separate helper `func visit(_ module: Int, _ state: [State]) -> Bool` and it still gives the right answer — but Swift arrays are values, the parameter is a constant, and the `var state = state` you add to make it compile is a private copy. Every *done* mark made deeper in the recursion vanishes on return, so each module is searched again from every path that leads to it. On a ladder of 44 modules in pairs, each depending on both modules of the next pair, that version made 16.7 million calls on Swift 6.4; the Kahn's loop above touches each pair once. In Java or Python the array would be shared by reference. Mark it `inout`, or write `visit` as a nested function that captures the outer `var state`.
:::

::: What they ask next
- **"Give me a valid build order."** → Return `ready` when its count is n, or an empty array otherwise. That's Course Schedule II.
- **"Which modules can be built in parallel?"** → Process the ready list in rounds: everything ready at the same time forms one parallel stage, and the number of rounds is the shortest possible build in stages.
- **"Report the cycle itself."** → Use the DFS with three colours and keep the current path on a stack; when you meet an *in progress* module, the path from that module to the top of the stack is the cycle.
:::
