## Improving Our I/O Project
<!-- stay:Uslkt6yJ hash=sha256:09703775a123 -->

With this new knowledge about iterators, we can improve the I/O project in
Chapter 12 by using iterators to make places in the code clearer and more
concise. Let’s look at how iterators can improve our implementation of the
`Config::build` function and the `search` function.
<!-- stay:gAmGPDgs hash=sha256:9c0f982af5dc -->

### Removing a `clone` Using an Iterator
<!-- stay:JpoIOXoB hash=sha256:e956aea23a88 -->

In Listing 12-6, we added code that took a slice of `String` values and created
an instance of the `Config` struct by indexing into the slice and cloning the
values, allowing the `Config` struct to own those values. In Listing 13-17,
we’ve reproduced the implementation of the `Config::build` function as it was
in Listing 12-23.
<!-- stay:G3hjEVmQ hash=sha256:39b10e4f9718 -->

<Listing number="13-17" file-name="src/main.rs" caption="Reproduction of the `Config::build` function from Listing 12-23">
<!-- stay:RFikVQ5c hash=sha256:5bdb090673d0 -->

```rust,ignore
{{#rustdoc_include ../listings/ch13-functional-features/listing-12-23-reproduced/src/main.rs:ch13}}
```
<!-- stay:qDsi0pzZ hash=sha256:29f150166a05 -->

</Listing>
<!-- stay:XK9QuyMH hash=sha256:b58d16a1f9c0 -->

At the time, we said not to worry about the inefficient `clone` calls because
we would remove them in the future. Well, that time is now!
<!-- stay:igB9s8n2 hash=sha256:19433569b103 -->

We needed `clone` here because we have a slice with `String` elements in the
parameter `args`, but the `build` function doesn’t own `args`. To return
ownership of a `Config` instance, we had to clone the values from the `query`
and `file_path` fields of `Config` so that the `Config` instance can own its
values.
<!-- stay:l654Taex hash=sha256:b23952fa4542 -->

With our new knowledge about iterators, we can change the `build` function to
take ownership of an iterator as its argument instead of borrowing a slice.
We’ll use the iterator functionality instead of the code that checks the length
of the slice and indexes into specific locations. This will clarify what the
`Config::build` function is doing because the iterator will access the values.
<!-- stay:6bUFZZum hash=sha256:ea72a710d9a3 -->

Once `Config::build` takes ownership of the iterator and stops using indexing
operations that borrow, we can move the `String` values from the iterator into
`Config` rather than calling `clone` and making a new allocation.
<!-- stay:VN0u1mSA hash=sha256:1e9c79631e05 -->

#### Using the Returned Iterator Directly
<!-- stay:3Q1kgjMH hash=sha256:a8ef1456ff1a -->

Open your I/O project’s _src/main.rs_ file, which should look like this:
<!-- stay:riEkzjtF hash=sha256:0ce4e7af81d7 -->

<span class="filename">Filename: src/main.rs</span>
<!-- stay:7bgJaBFU hash=sha256:ebb0dc5db82a -->

```rust,ignore
{{#rustdoc_include ../listings/ch13-functional-features/listing-12-24-reproduced/src/main.rs:ch13}}
```
<!-- stay:cGqMsmWd hash=sha256:224db637ccc6 -->

We’ll first change the start of the `main` function that we had in Listing
12-24 to the code in Listing 13-18, which this time uses an iterator. This
won’t compile until we update `Config::build` as well.
<!-- stay:ZO3QOZUf hash=sha256:07035c13dacd -->

<Listing number="13-18" file-name="src/main.rs" caption="Passing the return value of `env::args` to `Config::build`">
<!-- stay:CtA8VjWS hash=sha256:1c34e42560d7 -->

```rust,ignore,does_not_compile
{{#rustdoc_include ../listings/ch13-functional-features/listing-13-18/src/main.rs:here}}
```
<!-- stay:oE4L2O66 hash=sha256:ae0de28792c7 -->

</Listing>
<!-- stay:6oGalq0B hash=sha256:b58d16a1f9c0 -->

The `env::args` function returns an iterator! Rather than collecting the
iterator values into a vector and then passing a slice to `Config::build`, now
we’re passing ownership of the iterator returned from `env::args` to
`Config::build` directly.
<!-- stay:2BfMH0h2 hash=sha256:c2f52f8a7590 -->

Next, we need to update the definition of `Config::build`. Let’s change the
signature of `Config::build` to look like Listing 13-19. This still won’t
compile, because we need to update the function body.
<!-- stay:DcvPbDeH hash=sha256:18eb1fbd8cc1 -->

<Listing number="13-19" file-name="src/main.rs" caption="Updating the signature of `Config::build` to expect an iterator">
<!-- stay:r6XaKRTW hash=sha256:291e509cecca -->

```rust,ignore,does_not_compile
{{#rustdoc_include ../listings/ch13-functional-features/listing-13-19/src/main.rs:here}}
```
<!-- stay:YoHpMaof hash=sha256:5de90d28222d -->

</Listing>
<!-- stay:JzQ9ZMQI hash=sha256:b58d16a1f9c0 -->

The standard library documentation for the `env::args` function shows that the
type of the iterator it returns is `std::env::Args`, and that type implements
the `Iterator` trait and returns `String` values.
<!-- stay:A5TcIVZf hash=sha256:30ba6b987b1c -->

We’ve updated the signature of the `Config::build` function so that the
parameter `args` has a generic type with the trait bounds `impl Iterator<Item =
String>` instead of `&[String]`. This usage of the `impl Trait` syntax we
discussed in the [“Using Traits as Parameters”][impl-trait]<!-- ignore -->
section of Chapter 10 means that `args` can be any type that implements the
`Iterator` trait and returns `String` items.
<!-- stay:RA9sa7kz hash=sha256:d4646ab3cc6c -->

Because we’re taking ownership of `args` and we’ll be mutating `args` by
iterating over it, we can add the `mut` keyword into the specification of the
`args` parameter to make it mutable.
<!-- stay:VSyIjRny hash=sha256:d4f5589f931c -->

<!-- Old headings. Do not remove or links may break. -->
<!-- stay:mU2SnrZa hash=sha256:5c2d65695c1a -->

<a id="using-iterator-trait-methods-instead-of-indexing"></a>
<!-- stay:ux4gppLA hash=sha256:5cdda7eccb83 -->

#### Using `Iterator` Trait Methods
<!-- stay:34dSLtnG hash=sha256:ba4a0ec3aca2 -->

Next, we’ll fix the body of `Config::build`. Because `args` implements the
`Iterator` trait, we know we can call the `next` method on it! Listing 13-20
updates the code from Listing 12-23 to use the `next` method.
<!-- stay:xx7Bv2cy hash=sha256:601447eacb3b -->

<Listing number="13-20" file-name="src/main.rs" caption="Changing the body of `Config::build` to use iterator methods">
<!-- stay:gV1f6Bxk hash=sha256:615f89f075e6 -->

```rust,ignore,noplayground
{{#rustdoc_include ../listings/ch13-functional-features/listing-13-20/src/main.rs:here}}
```
<!-- stay:TLI0pxmr hash=sha256:83dfc93c29d1 -->

</Listing>
<!-- stay:0qPChCWT hash=sha256:b58d16a1f9c0 -->

Remember that the first value in the return value of `env::args` is the name of
the program. We want to ignore that and get to the next value, so first we call
`next` and do nothing with the return value. Then, we call `next` to get the
value we want to put in the `query` field of `Config`. If `next` returns
`Some`, we use a `match` to extract the value. If it returns `None`, it means
not enough arguments were given, and we return early with an `Err` value. We do
the same thing for the `file_path` value.
<!-- stay:J32bq0qE hash=sha256:543c52c5a7b8 -->

<!-- Old headings. Do not remove or links may break. -->
<!-- stay:L3PtK6Mp hash=sha256:5c2d65695c1a -->

<a id="making-code-clearer-with-iterator-adapters"></a>
<!-- stay:nMGRfix4 hash=sha256:e0cf826ea9dd -->

### Clarifying Code with Iterator Adapters
<!-- stay:bEvV69nI hash=sha256:752fe63ce092 -->

We can also take advantage of iterators in the `search` function in our I/O
project, which is reproduced here in Listing 13-21 as it was in Listing 12-19.
<!-- stay:yD7qMnPc hash=sha256:9c41d2fb50d1 -->

<Listing number="13-21" file-name="src/lib.rs" caption="The implementation of the `search` function from Listing 12-19">
<!-- stay:W6y4nK69 hash=sha256:54e0abb358af -->

```rust,ignore
{{#rustdoc_include ../listings/ch12-an-io-project/listing-12-19/src/lib.rs:ch13}}
```
<!-- stay:fwVIiQS6 hash=sha256:a71bcfe0b486 -->

</Listing>
<!-- stay:fhkMwJJB hash=sha256:b58d16a1f9c0 -->

We can write this code in a more concise way using iterator adapter methods.
Doing so also lets us avoid having a mutable intermediate `results` vector. The
functional programming style prefers to minimize the amount of mutable state to
make code clearer. Removing the mutable state might enable a future enhancement
to make searching happen in parallel because we wouldn’t have to manage
concurrent access to the `results` vector. Listing 13-22 shows this change.
<!-- stay:F4BaO9JA hash=sha256:561a6de1aa28 -->

<Listing number="13-22" file-name="src/lib.rs" caption="Using iterator adapter methods in the implementation of the `search` function">
<!-- stay:APBkJNpn hash=sha256:9d0ec3fa1eeb -->

```rust,ignore
{{#rustdoc_include ../listings/ch13-functional-features/listing-13-22/src/lib.rs:here}}
```
<!-- stay:qOGcFhZD hash=sha256:8705e7d0e82c -->

</Listing>
<!-- stay:fAfWkeM4 hash=sha256:b58d16a1f9c0 -->

Recall that the purpose of the `search` function is to return all lines in
`contents` that contain the `query`. Similar to the `filter` example in Listing
13-16, this code uses the `filter` adapter to keep only the lines for which
`line.contains(query)` returns `true`. We then collect the matching lines into
another vector with `collect`. Much simpler! Feel free to make the same change
to use iterator methods in the `search_case_insensitive` function as well.
<!-- stay:HBKUx35r hash=sha256:c7a270561a3b -->

For a further improvement, return an iterator from the `search` function by
removing the call to `collect` and changing the return type to `impl
Iterator<Item = &'a str>` so that the function becomes an iterator adapter.
Note that you’ll also need to update the tests! Search through a large file
using your `minigrep` tool before and after making this change to observe the
difference in behavior. Before this change, the program won’t print any results
until it has collected all of the results, but after the change, the results
will be printed as each matching line is found because the `for` loop in the
`run` function is able to take advantage of the laziness of the iterator.
<!-- stay:td6XelvD hash=sha256:6e5be69e1da5 -->

<!-- Old headings. Do not remove or links may break. -->
<!-- stay:3gt4dy8z hash=sha256:5c2d65695c1a -->

<a id="choosing-between-loops-or-iterators"></a>
<!-- stay:PRoSft67 hash=sha256:e0df5a3703ca -->

### Choosing Between Loops and Iterators
<!-- stay:weRtcrrY hash=sha256:6a95de884224 -->

The next logical question is which style you should choose in your own code and
why: the original implementation in Listing 13-21 or the version using
iterators in Listing 13-22 (assuming we’re collecting all the results before
returning them rather than returning the iterator). Most Rust programmers
prefer to use the iterator style. It’s a bit tougher to get the hang of at
first, but once you get a feel for the various iterator adapters and what they
do, iterators can be easier to understand. Instead of fiddling with the various
bits of looping and building new vectors, the code focuses on the high-level
objective of the loop. This abstracts away some of the commonplace code so that
it’s easier to see the concepts that are unique to this code, such as the
filtering condition each element in the iterator must pass.
<!-- stay:dmPCQ0mv hash=sha256:be2819b57b98 -->

But are the two implementations truly equivalent? The intuitive assumption
might be that the lower-level loop will be faster. Let’s talk about performance.
<!-- stay:Cn1Y4vhy hash=sha256:71b9487aeab2 -->

[impl-trait]: ch10-02-traits.html#traits-as-parameters
<!-- stay:J7JS1L0u hash=sha256:d3d8d1401901 -->
