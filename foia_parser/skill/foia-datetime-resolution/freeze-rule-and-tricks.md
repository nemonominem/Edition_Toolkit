# The freeze rule and the tricks that go with it

(Rule stated by the owner of the PO data; validated on the PO release, where applying
it moved 104 + 9 email times and turned 36 backwards reply links into ordered ones.)

## 1. The rule

Every printed stamp is a time on someone's clock. Which clock?

- **Top-level message** (the message itself, as it sits in the mailbox): the clock of
  the mailbox that holds it (the page owner).
- **Quoted or forwarded block** (the "From/Sent" header inside a reply): the clock of
  the **author of the message that quotes it**, because the quote was frozen by the
  quoter's mail client at the moment of replying.
- **Nesting needs no iteration.** Each block depends only on the author of the message
  directly above it.
- **Dangling last message.** The last message of a thread is quoted by nothing, so the
  rule cannot apply to it: use mailbox-owner evidence only.
- **An inferred ("same conversation") link proves nothing.** Only an explicit quote
  or forward shows that a block exists inside another message.
- An explicit zone/offset in the stamp always wins.

### Example (Holmes in Sydney, Rambaut in London; Sydney is 9 h ahead)

True chain: H1 at T, R1 = T+1h (reply), H2 = T+2h, R2 = T+3h.

| message | true time | local clock reading |
|---|---|---|
| H1 | T | T (Sydney) |
| R1 | T+1h | T-8h (London) |
| H2 | T+2h | T+2h (Sydney) |
| R2 | T+3h | T-6h (London) |

What the stamps show once each is frozen by the message that quotes it (Rambaut
quotes Holmes; Holmes quotes Rambaut; London is 9 h behind Sydney):

- H1 is quoted by Rambaut: printed on London's clock, T-9h.
- R1 is quoted by Holmes: printed on Sydney's clock, T+1h.
- H2 is quoted by Rambaut: printed on London's clock, T-7h.
- R2: depends on who quotes it; if nobody does, it is dangling.

A quoted Holmes message therefore looks hours *earlier* than its parent, and a
naive reply-order test reports a reply "before" its parent. Read each stamp on the
quoter's clock and the chain orders itself.

## 2. Tricks

1. **Anchor sentences.** Text such as "It is 10pm now UK" beside a printed time fixes
   both the time and its clock.
2. **Exact copy.** The same message elsewhere with an explicit offset gives the instant.
3. **Reply order under the freeze rule.** Test each reply pair with both stamps read on
   their own clocks (rule above). Zero violations supports the clock assumption.
4. **Page-code continuity.** The code at the bottom right of each page (`REV0000nnn`,
   `GARRY0000nnn`, `LIP-000nnn`) tells whose mailbox a page is. If the previous PDF page
   is not code nnn-1 of the same series, or the subject changes, the page is not the
   natural continuation: do not link across it.
5. **Bracketing.** If a message M lies, in true reply order, between two precisely
   timed messages A and B that are within about an hour of each other, M was sent
   inside that hour. The whole-hour UTC offset that puts M's printed time inside that
   window is the offset of the clock that froze M's stamp.
   Worked example: A is exactly 14:00 UTC, B exactly 14:40 UTC, M prints "9:20 AM".
   Only 14:20 UTC fits, so M's clock is UTC-5.
   On the PO release 24 stamps in one mailbox were bracketed this way and all allowed
   only UTC-8/-7, agreeing with the rule-based answer.
6. **Dangling last message.** Remember that the final message has no quoting message;
   do not apply rule 4 to it. Look for a forward of it elsewhere in the dump, or settle
   by bracketing or page-code continuity.

## 3. Reporting

Mark freeze-rule results **supported** (not settled) unless an explicit offset, exact
copy or bracketing narrows the clock to one zone. Re-run the reply-order test, the
explicit-link count and your audit file after every change to the rule.
