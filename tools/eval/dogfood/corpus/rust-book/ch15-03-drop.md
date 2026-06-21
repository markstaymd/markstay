## Running Code on Cleanup with the `Drop` Trait
<!-- stay:KnjcXKJJ hash=sha256:fc188296ec49 -->

The second trait important to the smart pointer pattern is `Drop`, which lets
you customize what happens when a value is about to go out of scope. You can
provide an implementation for the `Drop` trait on any type, and that code can
be used to release resources like files or network connections.
<!-- stay:IIe5p1zB hash=sha256:9bb9814582ad -->

We’re introducing `Drop` in the context of smart pointers because the
functionality of the `Drop` trait is almost always used when implementing a
smart pointer. For example, when a `Box<T>` is dropped, it will deallocate the
space on the heap that the box points to.
<!-- stay:W5ZzIh1z hash=sha256:f0c19803e806 -->

In some languages, for some types, the programmer must call code to free memory
or resources every time they finish using an instance of those types. Examples
include file handles, sockets, and locks. If the programmer forgets, the system
might become overloaded and crash. In Rust, you can specify that a particular
bit of code be run whenever a value goes out of scope, and the compiler will
insert this code automatically. As a result, you don’t need to be careful about
placing cleanup code everywhere in a program that an instance of a particular
type is finished with—you still won’t leak resources!
<!-- stay:GXPRi9j8 hash=sha256:0eff62921f94 -->

You specify the code to run when a value goes out of scope by implementing the
`Drop` trait. The `Drop` trait requires you to implement one method named
`drop` that takes a mutable reference to `self`. To see when Rust calls `drop`,
let’s implement `drop` with `println!` statements for now.
<!-- stay:ATlnJptR hash=sha256:f22268ccb653 -->

Listing 15-14 shows a `CustomSmartPointer` struct whose only custom
functionality is that it will print `Dropping CustomSmartPointer!` when the
instance goes out of scope, to show when Rust runs the `drop` method.
<!-- stay:5yZ8bnKd hash=sha256:88590222e652 -->

<Listing number="15-14" file-name="src/main.rs" caption="A `CustomSmartPointer` struct that implements the `Drop` trait where we would put our cleanup code">
<!-- stay:y85OKRmJ hash=sha256:30a128ab3fa1 -->

```rust
{{#rustdoc_include ../listings/ch15-smart-pointers/listing-15-14/src/main.rs}}
```
<!-- stay:RPZQuTlX hash=sha256:d924af887f24 -->

</Listing>
<!-- stay:bqIb7nWi hash=sha256:b58d16a1f9c0 -->

The `Drop` trait is included in the prelude, so we don’t need to bring it into
scope. We implement the `Drop` trait on `CustomSmartPointer` and provide an
implementation for the `drop` method that calls `println!`. The body of the
`drop` method is where you would place any logic that you wanted to run when an
instance of your type goes out of scope. We’re printing some text here to
demonstrate visually when Rust will call `drop`.
<!-- stay:zU0qKeAF hash=sha256:b58cf9c41fc3 -->

In `main`, we create two instances of `CustomSmartPointer` and then print
`CustomSmartPointers created`. At the end of `main`, our instances of
`CustomSmartPointer` will go out of scope, and Rust will call the code we put
in the `drop` method, printing our final message. Note that we didn’t need to
call the `drop` method explicitly.
<!-- stay:N3rcxPry hash=sha256:57b9db26652c -->

When we run this program, we’ll see the following output:
<!-- stay:uBMvlSGd hash=sha256:5d233c3f90b7 -->

```console
{{#include ../listings/ch15-smart-pointers/listing-15-14/output.txt}}
```
<!-- stay:xCS4fkc4 hash=sha256:56ca6da0e937 -->

Rust automatically called `drop` for us when our instances went out of scope,
calling the code we specified. Variables are dropped in the reverse order of
their creation, so `d` was dropped before `c`. This example’s purpose is to
give you a visual guide to how the `drop` method works; usually you would
specify the cleanup code that your type needs to run rather than a print
message.
<!-- stay:FEYAT7DU hash=sha256:f201396d1dfa -->

<!-- Old headings. Do not remove or links may break. -->
<!-- stay:Bt3BNR4S hash=sha256:5c2d65695c1a -->

<a id="dropping-a-value-early-with-std-mem-drop"></a>
<!-- stay:UqyT5yCf hash=sha256:9b1a0f60c294 -->

Unfortunately, it’s not straightforward to disable the automatic `drop`
functionality. Disabling `drop` isn’t usually necessary; the whole point of the
`Drop` trait is that it’s taken care of automatically. Occasionally, however,
you might want to clean up a value early. One example is when using smart
pointers that manage locks: You might want to force the `drop` method that
releases the lock so that other code in the same scope can acquire the lock.
Rust doesn’t let you call the `Drop` trait’s `drop` method manually; instead,
you have to call the `std::mem::drop` function provided by the standard library
if you want to force a value to be dropped before the end of its scope.
<!-- stay:yAn6k6y6 hash=sha256:bd6f5533b679 -->

Trying to call the `Drop` trait’s `drop` method manually by modifying the
`main` function from Listing 15-14 won’t work, as shown in Listing 15-15.
<!-- stay:qCkNeK6F hash=sha256:9097dde85bc1 -->

<Listing number="15-15" file-name="src/main.rs" caption="Attempting to call the `drop` method from the `Drop` trait manually to clean up early">
<!-- stay:wTAJt4AE hash=sha256:62abc873366a -->

```rust,ignore,does_not_compile
{{#rustdoc_include ../listings/ch15-smart-pointers/listing-15-15/src/main.rs:here}}
```
<!-- stay:bZoa0I85 hash=sha256:781d89fe8861 -->

</Listing>
<!-- stay:9mSfvhKS hash=sha256:b58d16a1f9c0 -->

When we try to compile this code, we’ll get this error:
<!-- stay:0r5LH3hX hash=sha256:e2b7ba303da4 -->

```console
{{#include ../listings/ch15-smart-pointers/listing-15-15/output.txt}}
```
<!-- stay:NjfBF8AI hash=sha256:b49367d3381b -->

This error message states that we’re not allowed to explicitly call `drop`. The
error message uses the term _destructor_, which is the general programming term
for a function that cleans up an instance. A _destructor_ is analogous to a
_constructor_, which creates an instance. The `drop` function in Rust is one
particular destructor.
<!-- stay:wpi4kGrz hash=sha256:fc9faf27c45a -->

Rust doesn’t let us call `drop` explicitly, because Rust would still
automatically call `drop` on the value at the end of `main`. This would cause a
double free error because Rust would be trying to clean up the same value twice.
<!-- stay:L6HPfRae hash=sha256:3b1962b0d686 -->

We can’t disable the automatic insertion of `drop` when a value goes out of
scope, and we can’t call the `drop` method explicitly. So, if we need to force
a value to be cleaned up early, we use the `std::mem::drop` function.
<!-- stay:iT8k4I39 hash=sha256:57c64c44a2c5 -->

The `std::mem::drop` function is different from the `drop` method in the `Drop`
trait. We call it by passing as an argument the value we want to force-drop.
The function is in the prelude, so we can modify `main` in Listing 15-15 to
call the `drop` function, as shown in Listing 15-16.
<!-- stay:BEUru6yJ hash=sha256:fec73e7c54a4 -->

<Listing number="15-16" file-name="src/main.rs" caption="Calling `std::mem::drop` to explicitly drop a value before it goes out of scope">
<!-- stay:Id9AK7Tt hash=sha256:d2de77fe4a5f -->

```rust
{{#rustdoc_include ../listings/ch15-smart-pointers/listing-15-16/src/main.rs:here}}
```
<!-- stay:bNkSEIjg hash=sha256:1f77e0df49a3 -->

</Listing>
<!-- stay:ajUWCawC hash=sha256:b58d16a1f9c0 -->

Running this code will print the following:
<!-- stay:xwfDFKJf hash=sha256:9491953a0b33 -->

```console
{{#include ../listings/ch15-smart-pointers/listing-15-16/output.txt}}
```
<!-- stay:PqnOR4qi hash=sha256:9e4db315ba3b -->

The text ``Dropping CustomSmartPointer with data `some data`!`` is printed
between the `CustomSmartPointer created` and `CustomSmartPointer dropped before
the end of main` text, showing that the `drop` method code is called to drop
`c` at that point.
<!-- stay:FjPK1sBb hash=sha256:59d0d1ab14d2 -->

You can use code specified in a `Drop` trait implementation in many ways to
make cleanup convenient and safe: For instance, you could use it to create your
own memory allocator! With the `Drop` trait and Rust’s ownership system, you
don’t have to remember to clean up, because Rust does it automatically.
<!-- stay:N6yEpFuD hash=sha256:d9d265ea738d -->

You also don’t have to worry about problems resulting from accidentally
cleaning up values still in use: The ownership system that makes sure
references are always valid also ensures that `drop` gets called only once when
the value is no longer being used.
<!-- stay:uFy52Yg6 hash=sha256:76d75a54f288 -->

Now that we’ve examined `Box<T>` and some of the characteristics of smart
pointers, let’s look at a few other smart pointers defined in the standard
library.
<!-- stay:FMadoDcT hash=sha256:9997b829b560 -->
