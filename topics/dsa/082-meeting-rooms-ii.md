---
title: 69 · Meeting Rooms II
summary: Given a day's meetings as start and end times, find the smallest number of rooms that lets every meeting happen.
group: Intervals
minutes: 25
sources:
- LeetCode 253 · Meeting Rooms II (premium) | https://leetcode.com/problems/meeting-rooms-ii/
- LintCode 919 · Meeting Rooms II (free) | https://www.lintcode.com/problem/919/
- Swift standard library · sorted() | https://developer.apple.com/documentation/swift/array/sorted()
---

*Medium · G*

You get a list of meetings, each `[start, end]` with start < end. A room holds one meeting at a time. A meeting that ends at 10 frees its room for a meeting that starts at 10. Return the fewest rooms needed so that every meeting gets a room for its whole length.

| Meetings | Answer |
|---|---|
| `[[9, 12], [10, 11], [11, 13], [13, 14]]` | `2` — from 10 to 11 two meetings run; at 11 one ends as the next begins |
| `[[1, 5], [5, 9]]` | `1` — back to back share a room |
| `[]` | `0` — no meetings, no rooms |

Constraints that matter: up to 10,000 meetings, times from 0 to 1,000,000. Walking through every moment of the day is too slow at that range; the target is O(n log n).

::: Starter code and tests
In an Xcode test target:

```swift
import Testing

struct MeetingRoomsIITests {

    @Test(arguments: [
        ([[9, 12], [10, 11], [11, 13], [13, 14]], 2),
        ([[1, 5], [5, 9]], 1),
        ([], 0),
    ])
    func findsTheFewestRoomsForAllMeetings(meetings: [[Int]], expected: Int) {
        #expect(minMeetingRooms(meetings) == expected)
    }

    // MARK: - Privates
    private func minMeetingRooms(_ meetings: [[Int]]) -> Int {
        0
    }
}
```

In a playground:

```swift
func minMeetingRooms(_ meetings: [[Int]]) -> Int {
    0 // your solution
}

let cases: [([[Int]], Int)] = [
    ([[9, 12], [10, 11], [11, 13], [13, 14]], 2),
    ([[1, 5], [5, 9]], 1),
    ([], 0),
]
for (meetings, expected) in cases {
    let got = minMeetingRooms(meetings)
    print(got == expected ? "PASS" : "FAIL", meetings, "→", got, "expected", expected)
}
```
:::

::: Pattern and cue
**Interval sweep over start and end events.** The cue is *meetings* with start and end times plus *"how many at the same time"* — rooms needed is the largest number of meetings running at any one moment. Sort the starts and the ends separately and sweep through time.
:::

::: Approach
Write all the start times in one sorted list and all the end times in another; which start belongs to which end no longer matters. Go through the starts in order. For each meeting starting, look at the earliest end time not yet used: if that meeting has already finished by now, its room is free, so reuse it and move on to the next end time. If not, every room in use is still busy, so open a new room. The number of rooms opened is the answer.

Time O(n log n) for the two sorts; the sweep is O(n), because each start and each end is passed once. Space O(n) for the two lists.
:::

::: Swift solution
```swift
func minMeetingRooms(_ meetings: [[Int]]) -> Int {
    let starts = meetings.map { $0[0] }.sorted()
    let ends = meetings.map { $0[1] }.sorted()
    var rooms = 0
    var ended = 0                                // how many meetings have finished so far
    for start in starts {
        if start < ends[ended] {
            rooms += 1                           // nobody has left yet: open another room
        } else {
            ended += 1                           // the earliest-ending meeting is over: take its room
        }
    }
    return rooms
}
```

`start < ends[ended]` is the back-to-back rule: a meeting ending exactly at `start` counts as over, so its room is reused. `ends[ended]` can never run off the end of the array, because `ended` only moves when a start is processed, and there are as many ends as starts.

Verified with `swift test` on Swift 6.4 in Swift 6 mode: the three examples above, four more (a single meeting, three identical meetings, one long meeting over three short ones, meetings given out of order), and 3,000 random lists checked against a brute force that counts the meetings running at every moment of the day.
:::

::: Walk it through
**`[[9, 12], [10, 11], [11, 13], [13, 14]]`** — starts 9, 10, 11, 13; ends 11, 12, 13, 14.

| Start | Earliest unused end | Over by then? | Rooms | Ends used |
|---|---|---|---|---|
| 9 | 11 | no | 1 | 0 |
| 10 | 11 | no | 2 | 0 |
| 11 | 11 | yes, 11 ≤ 11 | 2 | 1 |
| 13 | 12 | yes | 2 | 2 |

Answer 2. The meeting that ended at 11 was `[10, 11]`, and `[11, 13]` takes its room; which one doesn't matter, only that one is free.

**`[]`** — there are no starts, so the loop never runs and `ends[0]` is never read: 0 rooms.
:::

::: The Swift trap
**There's no heap to hand, and you don't need one.** The textbook answer sorts meetings by start and keeps a min-heap of end times: pop it when the earliest end is ≤ the next start, push the new end, and the heap's size at the end is the answer. Swift's standard library has no `Heap` or priority queue; swift-collections has one, but you won't have it in an interview editor. Faking it with a sorted array and `insert(_:at:)` is O(n) per insert, O(n²) overall. The two-sorted-arrays sweep above gives the same answer in O(n log n) with nothing to build. Say both, and why you chose this one.
:::

::: What they ask next
- **"Which room does each meeting get?"** → Now identities matter: sort meetings by start and keep a min-heap of (end time, room number) for busy rooms plus a list of free rooms. That's the case where writing a small binary heap is worth it.
- **"Can one person attend all of them?"** → Meeting Rooms I: sort by start and check that each meeting starts at or after the previous one ends. O(n log n).
- **"At what time are the most rooms busy?"** → In the same sweep, record the `start` at which `rooms` was increased for the last time — the peak begins there.
:::
