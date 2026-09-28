---
title: Why concurrency exists
summary: Cores, threads, and the two genuinely different reasons one thread isn't enough.
minutes: 6
sources:
- WWDC25 · Embracing Swift concurrency | https://developer.apple.com/videos/play/wwdc2025/268/
---

Nothing in this chapter is Swift. It is the ground everything else stands on, and skipping it is why so many explanations of actors don't land.

## What a computer actually does

A processor core does one thing: read an instruction, carry it out, read the next. One at a time, in order, very fast.

A modern iPhone has several cores — six is typical. An Apple Watch has two. Each core is an independent instruction-follower. Six cores means six instructions genuinely happening at the same instant, and not one more.

That is the hard limit everything else is built on top of. Whenever an app appears to be "doing many things at once", it is either doing at most six things at once, or taking turns very quickly.

> **In the office.** The office has **six desks**, and a desk is the only place work can actually happen. Six is the building's real capacity and it never changes. Everything that follows is about getting more done than six-things-at-once out of six desks. **The desks are the cores.** Hold onto that — people arrive in the next section, and people are a different thing.

## What a thread is

A **thread** is one stream of instructions with its own place to keep track of where it is — its stack of half-finished work. The operating system owns threads. It decides which thread runs on which core, and when to take a core away from one and give it to another.

Two things matter for everything that follows.

**A thread is expensive.** It has a stack — memory reserved up front, typically half a megabyte or more — plus bookkeeping inside the kernel. You can have thousands, but each costs real memory whether it is doing anything or not.

**Swapping threads is expensive.** When the OS takes a core from thread A and gives it to thread B, it saves everything A was doing and loads everything B was doing. That is a **context switch**. Individually microseconds; done constantly, it becomes the main thing the CPU is doing.

> **In the office.** **A thread is a worker.** That stays true for the whole of this topic — wherever you see *worker* or *staff*, it means a thread and nothing else ever does.
>
> A worker is a person the company employs. They have their own locker holding their own pile of half-finished paperwork, and the locker is theirs whether or not they are currently busy. That is what makes hiring expensive.
>
> **Workers and desks are not the same thing, and this is where people trip.** You can employ ninety people. You still have six desks. At any instant at most six of your employees are sitting down working; the rest stand around holding paperwork. Getting one up so another can sit means packing one pile away and unpacking another — **that shuffling is the context switch.**

## Why one thread isn't enough

Two reasons, and they are genuinely different problems. Keeping them apart is the single most useful distinction in the subject.

**Reason one: waiting.** Most of what an app does is wait. For a server. For a file. For the user. While a thread waits it occupies a core and does nothing. The work isn't slow — the *waiting* is slow, and the thread is stuck in it.

**Reason two: actual work.** Some things take real time because there is real computing to do. Decoding a large image. Running a model. Resizing ten thousand photos. Nothing makes that free; somebody has to do the arithmetic.

The fix for waiting is *don't sit there* — go and do something else, come back. The fix for real work is *use more cores*. Different problems, different mechanisms.

> **In the office.** Both are about a worker **sitting at one of your six desks**.
>
> A worker on hold to a supplier is at a desk producing nothing. One of six desks, wasted. The fix is not another person — it is *get up, let someone else sit, come back when the supplier answers*.
>
> A worker doing a long stocktake is at a desk producing something. Nothing is wasted; the job is simply large. More people doesn't help, because there are still six desks.
>
> Confusing the two is how a company ends up hiring ninety people to fix a problem that was never about headcount — which is exactly the next chapter.

> **Under the hood.** This is the distinction Apple draws in WWDC25 between `async` and `@concurrent`. `async` hides *latency* — it exists so a thread stops sitting in a wait. `@concurrent` moves *computation* — it exists so work happens somewhere other than where you called it. Asking "is this slow because it's waiting, or slow because it's working?" picks the tool, and picking the wrong one is the most common design error in this area.

## Concurrency is not parallelism

**Concurrency** is structuring a program so several things can be *in progress* at once. A chef with three pans going is concurrent, with two hands.

**Parallelism** is several things actually *executing* in the same instant. Two chefs. It needs more cores.

Concurrency is a way of organising; parallelism is a hardware capability. You can have concurrency on a single core — it is just taking turns — and it still helps enormously, because most turns are spent waiting.

## The two problems that follow

**Shared data.** Two threads change the same thing at the same moment and one change is lost, or the thing ends up in a state that should be impossible. That is a **data race**.

What makes data races dangerous is not how damaging they are. It is that they are *rare*. It doesn't go wrong in testing. It goes wrong once, on a busy day, on a customer's phone, and you cannot reproduce it on purpose.

**Too many threads.** Each waiting thread holds memory and generates context switches. Past a point, adding threads makes everything slower.

Everything in Swift concurrency answers one of those two. Chapter 3 answers the second; chapters 4 to 7 answer the first.

> **In the office.** One filing cabinet, open to the floor. Two workers pull the same page, both write on it, one change is lost — and nobody notices for months. Meanwhile the more people you hire, the more of them stand around waiting for that one cabinet.
