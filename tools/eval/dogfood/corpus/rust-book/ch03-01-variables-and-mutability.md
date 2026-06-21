## Variables and Mutability
<!-- stay:sGzdFmdG hash=sha256:447542ee0c82 -->

As mentioned in the [“Storing Values with
Variables”][storing-values-with-variables]<!-- ignore --> section, by default,
variables are immutable. This is one of many nudges Rust gives you to write
your code in a way that takes advantage of the safety and easy concurrency that
Rust offers. However, you still have the option to make your variables mutable.
Let’s explore how and why Rust encourages you to favor immutability and why
sometimes you might want to opt out.
<!-- stay:IiyO71ML hash=sha256:2ccc9ec5e14f -->

When a variable is immutable, once a value is bound to a name, you can’t change
that value. To illustrate this, generate a new project called _variables_ in
your _projects_ directory by using `cargo new variables`.
<!-- stay:UIsceLEt hash=sha256:3f52592d6876 -->

Then, in your new _variables_ directory, open _src/main.rs_ and replace its
code with the following code, which won’t compile just yet:
<!-- stay:oXFom3FJ hash=sha256:dcf5c23d69ed -->

<span class="filename">Filename: src/main.rs</span>
<!-- stay:oebHthdg hash=sha256:ebb0dc5db82a -->

```rust,ignore,does_not_compile
{{#rustdoc_include ../listings/ch03-common-programming-concepts/no-listing-01-variables-are-immutable/src/main.rs}}
```
<!-- stay:uc6jtHA8 hash=sha256:bda1f7908e68 -->

Save and run the program using `cargo run`. You should receive an error message
regarding an immutability error, as shown in this output:
<!-- stay:PjDHKVyL hash=sha256:ad328e3f3a47 -->

```console
{{#include ../listings/ch03-common-programming-concepts/no-listing-01-variables-are-immutable/output.txt}}
```
<!-- stay:qPbxFWLz hash=sha256:764781c3ac94 -->

This example shows how the compiler helps you find errors in your programs.
Compiler errors can be frustrating, but really they only mean your program
isn’t safely doing what you want it to do yet; they do _not_ mean that you’re
not a good programmer! Experienced Rustaceans still get compiler errors.
<!-- stay:LvbDQeGa hash=sha256:65749f151139 -->

You received the error message `` cannot assign twice to immutable variable `x` `` because you tried to assign a second value to the immutable `x` variable.
<!-- stay:Ce0KkBPr hash=sha256:c4c9d27a5b24 -->

It’s important that we get compile-time errors when we attempt to change a
value that’s designated as immutable, because this very situation can lead to
bugs. If one part of our code operates on the assumption that a value will
never change and another part of our code changes that value, it’s possible
that the first part of the code won’t do what it was designed to do. The cause
of this kind of bug can be difficult to track down after the fact, especially
when the second piece of code changes the value only _sometimes_. The Rust
compiler guarantees that when you state that a value won’t change, it really
won’t change, so you don’t have to keep track of it yourself. Your code is thus
easier to reason through.
<!-- stay:SDRDNc0y hash=sha256:d8fe4648b950 -->

But mutability can be very useful and can make code more convenient to write.
Although variables are immutable by default, you can make them mutable by
adding `mut` in front of the variable name as you did in [Chapter
2][storing-values-with-variables]<!-- ignore -->. Adding `mut` also conveys
intent to future readers of the code by indicating that other parts of the code
will be changing this variable’s value.
<!-- stay:dZUYMYHb hash=sha256:56c1a38a8422 -->

For example, let’s change _src/main.rs_ to the following:
<!-- stay:j67XYSd6 hash=sha256:3080344429a2 -->

<span class="filename">Filename: src/main.rs</span>
<!-- stay:JE6VFn5l hash=sha256:ebb0dc5db82a -->

```rust
{{#rustdoc_include ../listings/ch03-common-programming-concepts/no-listing-02-adding-mut/src/main.rs}}
```
<!-- stay:qJVIDiV0 hash=sha256:4c2e6df1cb53 -->

When we run the program now, we get this:
<!-- stay:FuVhHQNP hash=sha256:6255347be289 -->

```console
{{#include ../listings/ch03-common-programming-concepts/no-listing-02-adding-mut/output.txt}}
```
<!-- stay:RDrLqJK7 hash=sha256:cadfaae49878 -->

We’re allowed to change the value bound to `x` from `5` to `6` when `mut` is
used. Ultimately, deciding whether to use mutability or not is up to you and
depends on what you think is clearest in that particular situation.
<!-- stay:CJG3b8l3 hash=sha256:fbde0eae1d11 -->

<!-- Old headings. Do not remove or links may break. -->
<a id="constants"></a>
<!-- stay:wh2vHvhC hash=sha256:7ede4a408808 -->

### Declaring Constants
<!-- stay:Uq9qQx71 hash=sha256:c542e19cee08 -->

Like immutable variables, _constants_ are values that are bound to a name and
are not allowed to change, but there are a few differences between constants
and variables.
<!-- stay:O31Z5MBf hash=sha256:f1e01f30de3f -->

First, you aren’t allowed to use `mut` with constants. Constants aren’t just
immutable by default—they’re always immutable. You declare constants using the
`const` keyword instead of the `let` keyword, and the type of the value _must_
be annotated. We’ll cover types and type annotations in the next section,
[“Data Types”][data-types]<!-- ignore -->, so don’t worry about the details
right now. Just know that you must always annotate the type.
<!-- stay:iQofWRXz hash=sha256:cc5b2917c848 -->

Constants can be declared in any scope, including the global scope, which makes
them useful for values that many parts of code need to know about.
<!-- stay:D36IjNJ6 hash=sha256:f476fe7db5e5 -->

The last difference is that constants may be set only to a constant expression,
not the result of a value that could only be computed at runtime.
<!-- stay:2AR6zaPz hash=sha256:6825641157b8 -->

Here’s an example of a constant declaration:
<!-- stay:3zzdTGoQ hash=sha256:d55d367e4f62 -->

```rust
const THREE_HOURS_IN_SECONDS: u32 = 60 * 60 * 3;
```
<!-- stay:Bz8S1ji5 hash=sha256:dfefdd751797 -->

The constant’s name is `THREE_HOURS_IN_SECONDS`, and its value is set to the
result of multiplying 60 (the number of seconds in a minute) by 60 (the number
of minutes in an hour) by 3 (the number of hours we want to count in this
program). Rust’s naming convention for constants is to use all uppercase with
underscores between words. The compiler is able to evaluate a limited set of
operations at compile time, which lets us choose to write out this value in a
way that’s easier to understand and verify, rather than setting this constant
to the value 10,800. See the [Rust Reference’s section on constant
evaluation][const-eval] for more information on what operations can be used
when declaring constants.
<!-- stay:lZFpRcWQ hash=sha256:4c56febe19e4 -->

Constants are valid for the entire time a program runs, within the scope in
which they were declared. This property makes constants useful for values in
your application domain that multiple parts of the program might need to know
about, such as the maximum number of points any player of a game is allowed to
earn, or the speed of light.
<!-- stay:wUAGui2R hash=sha256:bb32520a8f8d -->

Naming hardcoded values used throughout your program as constants is useful in
conveying the meaning of that value to future maintainers of the code. It also
helps to have only one place in your code that you would need to change if the
hardcoded value needed to be updated in the future.
<!-- stay:1onZYRA9 hash=sha256:ad830eed1730 -->

### Shadowing
<!-- stay:SL4bO5B0 hash=sha256:a362ccd58eb5 -->

As you saw in the guessing game tutorial in [Chapter
2][comparing-the-guess-to-the-secret-number]<!-- ignore -->, you can declare a
new variable with the same name as a previous variable. Rustaceans say that the
first variable is _shadowed_ by the second, which means that the second
variable is what the compiler will see when you use the name of the variable.
In effect, the second variable overshadows the first, taking any uses of the
variable name to itself until either it itself is shadowed or the scope ends.
We can shadow a variable by using the same variable’s name and repeating the
use of the `let` keyword as follows:
<!-- stay:Bl9ZtXWW hash=sha256:4e5aa22a7064 -->

<span class="filename">Filename: src/main.rs</span>
<!-- stay:IpQQpgFm hash=sha256:ebb0dc5db82a -->

```rust
{{#rustdoc_include ../listings/ch03-common-programming-concepts/no-listing-03-shadowing/src/main.rs}}
```
<!-- stay:lSRDZNgr hash=sha256:874bcb7114a1 -->

This program first binds `x` to a value of `5`. Then, it creates a new variable
`x` by repeating `let x =`, taking the original value and adding `1` so that
the value of `x` is `6`. Then, within an inner scope created with the curly
brackets, the third `let` statement also shadows `x` and creates a new
variable, multiplying the previous value by `2` to give `x` a value of `12`.
When that scope is over, the inner shadowing ends and `x` returns to being `6`.
When we run this program, it will output the following:
<!-- stay:QSxA2W1Y hash=sha256:6a79ee498890 -->

```console
{{#include ../listings/ch03-common-programming-concepts/no-listing-03-shadowing/output.txt}}
```
<!-- stay:u10tQFjA hash=sha256:a8988b5396b2 -->

Shadowing is different from marking a variable as `mut` because we’ll get a
compile-time error if we accidentally try to reassign to this variable without
using the `let` keyword. By using `let`, we can perform a few transformations
on a value but have the variable be immutable after those transformations have
completed.
<!-- stay:50H5l1kW hash=sha256:16b7ffded11c -->

The other difference between `mut` and shadowing is that because we’re
effectively creating a new variable when we use the `let` keyword again, we can
change the type of the value but reuse the same name. For example, say our
program asks a user to show how many spaces they want between some text by
inputting space characters, and then we want to store that input as a number:
<!-- stay:HJtWfyE6 hash=sha256:bb4557c0585b -->

```rust
{{#rustdoc_include ../listings/ch03-common-programming-concepts/no-listing-04-shadowing-can-change-types/src/main.rs:here}}
```
<!-- stay:8dAqEm4L hash=sha256:8a08e9084848 -->

The first `spaces` variable is a string type, and the second `spaces` variable
is a number type. Shadowing thus spares us from having to come up with
different names, such as `spaces_str` and `spaces_num`; instead, we can reuse
the simpler `spaces` name. However, if we try to use `mut` for this, as shown
here, we’ll get a compile-time error:
<!-- stay:AmwUnv6Q hash=sha256:b4b659c210e7 -->

```rust,ignore,does_not_compile
{{#rustdoc_include ../listings/ch03-common-programming-concepts/no-listing-05-mut-cant-change-types/src/main.rs:here}}
```
<!-- stay:n5iG22Ln hash=sha256:0a6b378a5bcd -->

The error says we’re not allowed to mutate a variable’s type:
<!-- stay:dmISB8Nc hash=sha256:80de46afae88 -->

```console
{{#include ../listings/ch03-common-programming-concepts/no-listing-05-mut-cant-change-types/output.txt}}
```
<!-- stay:Dk55MifH hash=sha256:ebdd29822a20 -->

Now that we’ve explored how variables work, let’s look at more data types they
can have.
<!-- stay:iEzPFLBF hash=sha256:a39cc9f22ade -->

[comparing-the-guess-to-the-secret-number]: ch02-00-guessing-game-tutorial.html#comparing-the-guess-to-the-secret-number
[data-types]: ch03-02-data-types.html#data-types
[storing-values-with-variables]: ch02-00-guessing-game-tutorial.html#storing-values-with-variables
[const-eval]: ../reference/const_eval.html
<!-- stay:6FuvYSGs hash=sha256:079d39dbc233 -->
