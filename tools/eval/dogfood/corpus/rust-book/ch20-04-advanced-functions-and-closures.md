## Advanced Functions and Closures
<!-- stay:3seMLehn hash=sha256:e0fd07957550 -->

This section explores some advanced features related to functions and closures,
including function pointers and returning closures.
<!-- stay:Uupx6tUo hash=sha256:37752b764687 -->

### Function Pointers
<!-- stay:MId4NoCe hash=sha256:9ffbf02bc848 -->

We’ve talked about how to pass closures to functions; you can also pass regular
functions to functions! This technique is useful when you want to pass a
function you’ve already defined rather than defining a new closure. Functions
coerce to the type `fn` (with a lowercase _f_), not to be confused with the
`Fn` closure trait. The `fn` type is called a _function pointer_. Passing
functions with function pointers will allow you to use functions as arguments
to other functions.
<!-- stay:UnzLBe50 hash=sha256:4c90836e8fd0 -->

The syntax for specifying that a parameter is a function pointer is similar to
that of closures, as shown in Listing 20-28, where we’ve defined a function
`add_one` that adds 1 to its parameter. The function `do_twice` takes two
parameters: a function pointer to any function that takes an `i32` parameter
and returns an `i32`, and one `i32` value. The `do_twice` function calls the
function `f` twice, passing it the `arg` value, then adds the two function call
results together. The `main` function calls `do_twice` with the arguments
`add_one` and `5`.
<!-- stay:cqGYay6B hash=sha256:94b4a8847fe9 -->

<Listing number="20-28" file-name="src/main.rs" caption="Using the `fn` type to accept a function pointer as an argument">
<!-- stay:DUHG9aa4 hash=sha256:d35c771b9a17 -->

```rust
{{#rustdoc_include ../listings/ch20-advanced-features/listing-20-28/src/main.rs}}
```
<!-- stay:7aQ5QkH8 hash=sha256:3981a79f818d -->

</Listing>
<!-- stay:2tFVeRLo hash=sha256:b58d16a1f9c0 -->

This code prints `The answer is: 12`. We specify that the parameter `f` in
`do_twice` is an `fn` that takes one parameter of type `i32` and returns an
`i32`. We can then call `f` in the body of `do_twice`. In `main`, we can pass
the function name `add_one` as the first argument to `do_twice`.
<!-- stay:dmBq3WdI hash=sha256:64f1dbda574c -->

Unlike closures, `fn` is a type rather than a trait, so we specify `fn` as the
parameter type directly rather than declaring a generic type parameter with one
of the `Fn` traits as a trait bound.
<!-- stay:ZMQ8ypkh hash=sha256:40c79d817736 -->

Function pointers implement all three of the closure traits (`Fn`, `FnMut`, and
`FnOnce`), meaning you can always pass a function pointer as an argument for a
function that expects a closure. It’s best to write functions using a generic
type and one of the closure traits so that your functions can accept either
functions or closures.
<!-- stay:negBbga9 hash=sha256:5b5dd013c1cf -->

That said, one example of where you would want to only accept `fn` and not
closures is when interfacing with external code that doesn’t have closures: C
functions can accept functions as arguments, but C doesn’t have closures.
<!-- stay:ml9pMxLz hash=sha256:c897cc005da6 -->

As an example of where you could use either a closure defined inline or a named
function, let’s look at a use of the `map` method provided by the `Iterator`
trait in the standard library. To use the `map` method to turn a vector of
numbers into a vector of strings, we could use a closure, as in Listing 20-29.
<!-- stay:J8uRHhof hash=sha256:c721791014a1 -->

<Listing number="20-29" caption="Using a closure with the `map` method to convert numbers to strings">
<!-- stay:FqUmPj69 hash=sha256:415fe6563953 -->

```rust
{{#rustdoc_include ../listings/ch20-advanced-features/listing-20-29/src/main.rs:here}}
```
<!-- stay:MlPK73Mm hash=sha256:641f167ea3aa -->

</Listing>
<!-- stay:h6pbj3QK hash=sha256:b58d16a1f9c0 -->

Or we could name a function as the argument to `map` instead of the closure.
Listing 20-30 shows what this would look like.
<!-- stay:R0JpoPNM hash=sha256:1619d96436ef -->

<Listing number="20-30" caption="Using the `String::to_string` function with the `map` method to convert numbers to strings">
<!-- stay:RsWn4lFv hash=sha256:d39b776978e0 -->

```rust
{{#rustdoc_include ../listings/ch20-advanced-features/listing-20-30/src/main.rs:here}}
```
<!-- stay:SzIPXzT0 hash=sha256:df78f0f7b262 -->

</Listing>
<!-- stay:D5l7NB7L hash=sha256:b58d16a1f9c0 -->

Note that we must use the fully qualified syntax that we talked about in the
[“Advanced Traits”][advanced-traits]<!-- ignore --> section because there are
multiple functions available named `to_string`.
<!-- stay:jzk88Oi6 hash=sha256:2d8c29e39b61 -->

Here, we’re using the `to_string` function defined in the `ToString` trait,
which the standard library has implemented for any type that implements
`Display`.
<!-- stay:8xplcyDV hash=sha256:3ca6e8e8af2c -->

Recall from the [“Enum Values”][enum-values]<!-- ignore --> section in Chapter
6 that the name of each enum variant that we define also becomes an initializer
function. We can use these initializer functions as function pointers that
implement the closure traits, which means we can specify the initializer
functions as arguments for methods that take closures, as seen in Listing 20-31.
<!-- stay:NTGySNS3 hash=sha256:c154bbca4dd3 -->

<Listing number="20-31" caption="Using an enum initializer with the `map` method to create a `Status` instance from numbers">
<!-- stay:YlOOk1az hash=sha256:d8d3ce0f0b1f -->

```rust
{{#rustdoc_include ../listings/ch20-advanced-features/listing-20-31/src/main.rs:here}}
```
<!-- stay:8fWadXlP hash=sha256:b0dfd65a2042 -->

</Listing>
<!-- stay:M7z24v8y hash=sha256:b58d16a1f9c0 -->

Here, we create `Status::Value` instances using each `u32` value in the range
that `map` is called on by using the initializer function of `Status::Value`.
Some people prefer this style and some people prefer to use closures. They
compile to the same code, so use whichever style is clearer to you.
<!-- stay:bP7OxbJm hash=sha256:31943bbe4488 -->

### Returning Closures
<!-- stay:qKIeLLjd hash=sha256:a3c67c972e4a -->

Closures are represented by traits, which means you can’t return closures
directly. In most cases where you might want to return a trait, you can instead
use the concrete type that implements the trait as the return value of the
function. However, you can’t usually do that with closures because they don’t
have a concrete type that is returnable; you’re not allowed to use the function
pointer `fn` as a return type if the closure captures any values from its
scope, for example.
<!-- stay:p3EeQRkq hash=sha256:2e3ef6028fdc -->

Instead, you will normally use the `impl Trait` syntax we learned about in
Chapter 10. You can return any function type, using `Fn`, `FnOnce`, and `FnMut`.
For example, the code in Listing 20-32 will compile just fine.
<!-- stay:ihrNkWkR hash=sha256:eacd5ba32237 -->

<Listing number="20-32" caption="Returning a closure from a function using the `impl Trait` syntax">
<!-- stay:ZTrigs0m hash=sha256:3c9691fdd852 -->

```rust
{{#rustdoc_include ../listings/ch20-advanced-features/listing-20-32/src/lib.rs}}
```
<!-- stay:0NWRKegD hash=sha256:04e93c93b5ff -->

</Listing>
<!-- stay:BFYQWxev hash=sha256:b58d16a1f9c0 -->

However, as we noted in the [“Inferring and Annotating Closure
Types”][closure-types]<!-- ignore --> section in Chapter 13, each closure is
also its own distinct type. If you need to work with multiple functions that
have the same signature but different implementations, you will need to use a
trait object for them. Consider what happens if you write code like that shown
in Listing 20-33.
<!-- stay:u7BwYOX1 hash=sha256:d2e3dc1212b6 -->

<Listing file-name="src/main.rs" number="20-33" caption="Creating a `Vec<T>` of closures defined by functions that return `impl Fn` types">
<!-- stay:ndkBcNrw hash=sha256:8e34954ccf41 -->

```rust,ignore,does_not_compile
{{#rustdoc_include ../listings/ch20-advanced-features/listing-20-33/src/main.rs}}
```
<!-- stay:yJPGNari hash=sha256:203cbfd895cb -->

</Listing>
<!-- stay:GvwykeEz hash=sha256:b58d16a1f9c0 -->

Here we have two functions, `returns_closure` and `returns_initialized_closure`,
which both return `impl Fn(i32) -> i32`. Notice that the closures that they
return are different, even though they implement the same type. If we try to
compile this, Rust lets us know that it won’t work:
<!-- stay:2EtIanUx hash=sha256:6d01b2b2d154 -->

```text
{{#include ../listings/ch20-advanced-features/listing-20-33/output.txt}}
```
<!-- stay:lNA4XLP2 hash=sha256:ac1e0beab7e1 -->

The error message tells us that whenever we return an `impl Trait`, Rust
creates a unique _opaque type_, a type where we cannot see into the details of
what Rust constructs for us, nor can we guess the type Rust will generate to
write ourselves. So, even though these functions return closures that implement
the same trait, `Fn(i32) -> i32`, the opaque types Rust generates for each are
distinct. (This is similar to how Rust produces different concrete types for
distinct async blocks even when they have the same output type, as we saw in
[“The `Pin` Type and the `Unpin` Trait”][future-types]<!-- ignore --> in
Chapter 17.) We have seen a solution to this problem a few times now: We can
use a trait object, as in Listing 20-34.
<!-- stay:Owwoe6n8 hash=sha256:6d02427093c1 -->

<Listing number="20-34" caption="Creating a `Vec<T>` of closures defined by functions that return `Box<dyn Fn>` so that they have the same type">
<!-- stay:eVPBg1BP hash=sha256:1f1cc2584219 -->

```rust
{{#rustdoc_include ../listings/ch20-advanced-features/listing-20-34/src/main.rs:here}}
```
<!-- stay:KUhwKH9z hash=sha256:bdc6a065e441 -->

</Listing>
<!-- stay:YDHk84iK hash=sha256:b58d16a1f9c0 -->

This code will compile just fine. For more about trait objects, refer to the
section [“Using Trait Objects To Abstract over Shared
Behavior”][trait-objects]<!-- ignore --> in Chapter 18.
<!-- stay:KtCb4sQQ hash=sha256:3675e6f898c7 -->

Next, let’s look at macros!
<!-- stay:x1VTe67e hash=sha256:dcbeccd52f82 -->

[advanced-traits]: ch20-02-advanced-traits.html#advanced-traits
[enum-values]: ch06-01-defining-an-enum.html#enum-values
[closure-types]: ch13-01-closures.html#closure-type-inference-and-annotation
[future-types]: ch17-03-more-futures.html
[trait-objects]: ch18-02-trait-objects.html
<!-- stay:ecAS1rZs hash=sha256:abd4b3b3386d -->
