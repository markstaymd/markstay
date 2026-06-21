## Concise Control Flow with `if let` and `let...else`
<!-- stay:gEhUjjnI hash=sha256:3ed53c13e7b2 -->

The `if let` syntax lets you combine `if` and `let` into a less verbose way to
handle values that match one pattern while ignoring the rest. Consider the
program in Listing 6-6 that matches on an `Option<u8>` value in the
`config_max` variable but only wants to execute code if the value is the `Some`
variant.
<!-- stay:WZv74v62 hash=sha256:d7dba967dbf4 -->

<Listing number="6-6" caption="A `match` that only cares about executing code when the value is `Some`">
<!-- stay:BfUaf7O7 hash=sha256:f748c8e5b3e2 -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/listing-06-06/src/main.rs:here}}
```
<!-- stay:55nHxwi0 hash=sha256:c9e490ffcd77 -->

</Listing>
<!-- stay:A3QqPMY7 hash=sha256:b58d16a1f9c0 -->

If the value is `Some`, we print out the value in the `Some` variant by binding
the value to the variable `max` in the pattern. We don’t want to do anything
with the `None` value. To satisfy the `match` expression, we have to add `_ =>
()` after processing just one variant, which is annoying boilerplate code to
add.
<!-- stay:uljTR7Rg hash=sha256:ed97147f462a -->

Instead, we could write this in a shorter way using `if let`. The following
code behaves the same as the `match` in Listing 6-6:
<!-- stay:JbzFoiPe hash=sha256:122e48300821 -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/no-listing-12-if-let/src/main.rs:here}}
```
<!-- stay:v6Hmm0ls hash=sha256:7ca9c38292d4 -->

The syntax `if let` takes a pattern and an expression separated by an equal
sign. It works the same way as a `match`, where the expression is given to the
`match` and the pattern is its first arm. In this case, the pattern is
`Some(max)`, and the `max` binds to the value inside the `Some`. We can then
use `max` in the body of the `if let` block in the same way we used `max` in
the corresponding `match` arm. The code in the `if let` block only runs if the
value matches the pattern.
<!-- stay:EpPtxyLf hash=sha256:c76942b098a6 -->

Using `if let` means less typing, less indentation, and less boilerplate code.
However, you lose the exhaustive checking `match` enforces that ensures that
you aren’t forgetting to handle any cases. Choosing between `match` and `if
let` depends on what you’re doing in your particular situation and whether
gaining conciseness is an appropriate trade-off for losing exhaustive checking.
<!-- stay:XFxQjKsJ hash=sha256:3bc6e0c7ee0d -->

In other words, you can think of `if let` as syntax sugar for a `match` that
runs code when the value matches one pattern and then ignores all other values.
<!-- stay:97NYVbGi hash=sha256:90b2c96a2964 -->

We can include an `else` with an `if let`. The block of code that goes with the
`else` is the same as the block of code that would go with the `_` case in the
`match` expression that is equivalent to the `if let` and `else`. Recall the
`Coin` enum definition in Listing 6-4, where the `Quarter` variant also held a
`UsState` value. If we wanted to count all non-quarter coins we see while also
announcing the state of the quarters, we could do that with a `match`
expression, like this:
<!-- stay:Ck3UFKLS hash=sha256:8ffbf700300a -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/no-listing-13-count-and-announce-match/src/main.rs:here}}
```
<!-- stay:Xqkk3uzB hash=sha256:27f61a779270 -->

Or we could use an `if let` and `else` expression, like this:
<!-- stay:2w15VVa0 hash=sha256:518a42255ea9 -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/no-listing-14-count-and-announce-if-let-else/src/main.rs:here}}
```
<!-- stay:SJqa7PZc hash=sha256:86e85996a493 -->

## Staying on the “Happy Path” with `let...else`
<!-- stay:nl8uAMF1 hash=sha256:6cb08dbcef17 -->

The common pattern is to perform some computation when a value is present and
return a default value otherwise. Continuing with our example of coins with a
`UsState` value, if we wanted to say something funny depending on how old the
state on the quarter was, we might introduce a method on `UsState` to check the
age of a state, like so:
<!-- stay:wYJufWFk hash=sha256:c08d2878cb7c -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/listing-06-07/src/main.rs:state}}
```
<!-- stay:bg920Ngb hash=sha256:72c25fb4ac24 -->

Then, we might use `if let` to match on the type of coin, introducing a `state`
variable within the body of the condition, as in Listing 6-7.
<!-- stay:bxGAIh7c hash=sha256:2c9c74eabea6 -->

<Listing number="6-7" caption="Checking whether a state existed in 1900 by using conditionals nested inside an `if let`">
<!-- stay:MTYA9kpq hash=sha256:bc5b9eb9b061 -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/listing-06-07/src/main.rs:describe}}
```
<!-- stay:kK2mCHUs hash=sha256:e583398ed791 -->

</Listing>
<!-- stay:E7kdT9XT hash=sha256:b58d16a1f9c0 -->

That gets the job done, but it has pushed the work into the body of the `if
let` statement, and if the work to be done is more complicated, it might be
hard to follow exactly how the top-level branches relate. We could also take
advantage of the fact that expressions produce a value either to produce the
`state` from the `if let` or to return early, as in Listing 6-8. (You could do
something similar with a `match`, too.)
<!-- stay:U4vAHwpK hash=sha256:18cb08a3a830 -->

<Listing number="6-8" caption="Using `if let` to produce a value or return early">
<!-- stay:ml0MyLzF hash=sha256:9bd8d948087a -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/listing-06-08/src/main.rs:describe}}
```
<!-- stay:JzUry35u hash=sha256:0435cd749d16 -->

</Listing>
<!-- stay:QhoRrSL9 hash=sha256:b58d16a1f9c0 -->

This is a bit annoying to follow in its own way, though! One branch of the `if
let` produces a value, and the other one returns from the function entirely.
<!-- stay:WQeDDmmm hash=sha256:106a5cf710a0 -->

To make this common pattern nicer to express, Rust has `let...else`. The
`let...else` syntax takes a pattern on the left side and an expression on the
right, very similar to `if let`, but it does not have an `if` branch, only an
`else` branch. If the pattern matches, it will bind the value from the pattern
in the outer scope. If the pattern does _not_ match, the program will flow into
the `else` arm, which must return from the function.
<!-- stay:c5JuJjG5 hash=sha256:3daf24157e28 -->

In Listing 6-9, you can see how Listing 6-8 looks when using `let...else` in
place of `if let`.
<!-- stay:ku7AA61L hash=sha256:d26c6b7c8039 -->

<Listing number="6-9" caption="Using `let...else` to clarify the flow through the function">
<!-- stay:2xaNYldf hash=sha256:e9b47d400511 -->

```rust
{{#rustdoc_include ../listings/ch06-enums-and-pattern-matching/listing-06-09/src/main.rs:describe}}
```
<!-- stay:1CDmV4jN hash=sha256:539edb73f438 -->

</Listing>
<!-- stay:Hpmunzz7 hash=sha256:b58d16a1f9c0 -->

Notice that it stays on the “happy path” in the main body of the function this
way, without having significantly different control flow for two branches the
way the `if let` did.
<!-- stay:mPD1kVHP hash=sha256:81477150279e -->

If you have a situation in which your program has logic that is too verbose to
express using a `match`, remember that `if let` and `let...else` are in your
Rust toolbox as well.
<!-- stay:irt45PQf hash=sha256:803296626474 -->

## Summary
<!-- stay:QIb8JxPD hash=sha256:30ac03ff3373 -->

We’ve now covered how to use enums to create custom types that can be one of a
set of enumerated values. We’ve shown how the standard library’s `Option<T>`
type helps you use the type system to prevent errors. When enum values have
data inside them, you can use `match` or `if let` to extract and use those
values, depending on how many cases you need to handle.
<!-- stay:gxlVqgM8 hash=sha256:fdeccfd1bb5d -->

Your Rust programs can now express concepts in your domain using structs and
enums. Creating custom types to use in your API ensures type safety: The
compiler will make certain your functions only get values of the type each
function expects.
<!-- stay:dzDALgQB hash=sha256:9a5333ac4641 -->

In order to provide a well-organized API to your users that is straightforward
to use and only exposes exactly what your users will need, let’s now turn to
Rust’s modules.
<!-- stay:1TFvEDKK hash=sha256:b1ac411ceb94 -->
