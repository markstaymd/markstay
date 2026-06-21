## Characteristics of Object-Oriented Languages
<!-- stay:rYhwRVG6 hash=sha256:4b72363614ed -->

There is no consensus in the programming community about what features a
language must have to be considered object oriented. Rust is influenced by many
programming paradigms, including OOP; for example, we explored the features
that came from functional programming in Chapter 13. Arguably, OOP languages
share certain common characteristics—namely, objects, encapsulation, and
inheritance. Let’s look at what each of those characteristics means and whether
Rust supports it.
<!-- stay:9BXDws6o hash=sha256:894d22535b38 -->

### Objects Contain Data and Behavior
<!-- stay:GfgXNWdA hash=sha256:1ffa2fb5c406 -->

The book _Design Patterns: Elements of Reusable Object-Oriented Software_ by
Erich Gamma, Richard Helm, Ralph Johnson, and John Vlissides (Addison-Wesley,
1994), colloquially referred to as _The Gang of Four_ book, is a catalog of
object-oriented design patterns. It defines OOP in this way:
<!-- stay:9VA0aZ2g hash=sha256:6a4f53a2e3cf -->

> Object-oriented programs are made up of objects. An **object** packages both
> data and the procedures that operate on that data. The procedures are
> typically called **methods** or **operations**.
<!-- stay:fo1PsUMK hash=sha256:ceab5cf6db46 -->

Using this definition, Rust is object oriented: Structs and enums have data,
and `impl` blocks provide methods on structs and enums. Even though structs and
enums with methods aren’t _called_ objects, they provide the same
functionality, according to the Gang of Four’s definition of objects.
<!-- stay:0QDJ7ngl hash=sha256:0832d717b74c -->

### Encapsulation That Hides Implementation Details
<!-- stay:HyKGnHRN hash=sha256:0c8cbe5f0f41 -->

Another aspect commonly associated with OOP is the idea of _encapsulation_,
which means that the implementation details of an object aren’t accessible to
code using that object. Therefore, the only way to interact with an object is
through its public API; code using the object shouldn’t be able to reach into
the object’s internals and change data or behavior directly. This enables the
programmer to change and refactor an object’s internals without needing to
change the code that uses the object.
<!-- stay:1avyEGG0 hash=sha256:12dbc6752ce0 -->

We discussed how to control encapsulation in Chapter 7: We can use the `pub`
keyword to decide which modules, types, functions, and methods in our code
should be public, and by default everything else is private. For example, we
can define a struct `AveragedCollection` that has a field containing a vector
of `i32` values. The struct can also have a field that contains the average of
the values in the vector, meaning the average doesn’t have to be computed on
demand whenever anyone needs it. In other words, `AveragedCollection` will
cache the calculated average for us. Listing 18-1 has the definition of the
`AveragedCollection` struct.
<!-- stay:GE69oZsM hash=sha256:2ebddbe16230 -->

<Listing number="18-1" file-name="src/lib.rs" caption="An `AveragedCollection` struct that maintains a list of integers and the average of the items in the collection">
<!-- stay:YrqkT7MM hash=sha256:dd1ec7c74654 -->

```rust,noplayground
{{#rustdoc_include ../listings/ch18-oop/listing-18-01/src/lib.rs}}
```
<!-- stay:pPA4lQd7 hash=sha256:b1dde6efd82e -->

</Listing>
<!-- stay:gEfhEN76 hash=sha256:b58d16a1f9c0 -->

The struct is marked `pub` so that other code can use it, but the fields within
the struct remain private. This is important in this case because we want to
ensure that whenever a value is added or removed from the list, the average is
also updated. We do this by implementing `add`, `remove`, and `average` methods
on the struct, as shown in Listing 18-2.
<!-- stay:tHHPnsaW hash=sha256:eb5559f85a10 -->

<Listing number="18-2" file-name="src/lib.rs" caption="Implementations of the public methods `add`, `remove`, and `average` on `AveragedCollection`">
<!-- stay:bHhgdmZT hash=sha256:db2c7eb8e083 -->

```rust,noplayground
{{#rustdoc_include ../listings/ch18-oop/listing-18-02/src/lib.rs:here}}
```
<!-- stay:B6pQVt6c hash=sha256:8fa6103632d3 -->

</Listing>
<!-- stay:HDM9YDwQ hash=sha256:b58d16a1f9c0 -->

The public methods `add`, `remove`, and `average` are the only ways to access
or modify data in an instance of `AveragedCollection`. When an item is added to
`list` using the `add` method or removed using the `remove` method, the
implementations of each call the private `update_average` method that handles
updating the `average` field as well.
<!-- stay:U8CRrXTO hash=sha256:eae646a546b5 -->

We leave the `list` and `average` fields private so that there is no way for
external code to add or remove items to or from the `list` field directly;
otherwise, the `average` field might become out of sync when the `list`
changes. The `average` method returns the value in the `average` field,
allowing external code to read the `average` but not modify it.
<!-- stay:n5kKxygS hash=sha256:6d1c3edd1f16 -->

Because we’ve encapsulated the implementation details of the struct
`AveragedCollection`, we can easily change aspects, such as the data structure,
in the future. For instance, we could use a `HashSet<i32>` instead of a
`Vec<i32>` for the `list` field. As long as the signatures of the `add`,
`remove`, and `average` public methods stayed the same, code using
`AveragedCollection` wouldn’t need to change. If we made `list` public instead,
this wouldn’t necessarily be the case: `HashSet<i32>` and `Vec<i32>` have
different methods for adding and removing items, so the external code would
likely have to change if it were modifying `list` directly.
<!-- stay:UlnLkZu5 hash=sha256:1ac9dd4ca175 -->

If encapsulation is a required aspect for a language to be considered object
oriented, then Rust meets that requirement. The option to use `pub` or not for
different parts of code enables encapsulation of implementation details.
<!-- stay:2rk6MfSf hash=sha256:bdd7700d9c25 -->

### Inheritance as a Type System and as Code Sharing
<!-- stay:rV09ZTx8 hash=sha256:ddbc955e6bd7 -->

_Inheritance_ is a mechanism whereby an object can inherit elements from
another object’s definition, thus gaining the parent object’s data and behavior
without you having to define them again.
<!-- stay:EgkA6t68 hash=sha256:2bd453a8cbff -->

If a language must have inheritance to be object oriented, then Rust is not
such a language. There is no way to define a struct that inherits the parent
struct’s fields and method implementations without using a macro.
<!-- stay:NQdipHVw hash=sha256:2e1dea5df503 -->

However, if you’re used to having inheritance in your programming toolbox, you
can use other solutions in Rust, depending on your reason for reaching for
inheritance in the first place.
<!-- stay:PQEziJ2b hash=sha256:be56ca96b088 -->

You would choose inheritance for two main reasons. One is for reuse of code:
You can implement particular behavior for one type, and inheritance enables you
to reuse that implementation for a different type. You can do this in a limited
way in Rust code using default trait method implementations, which you saw in
Listing 10-14 when we added a default implementation of the `summarize` method
on the `Summary` trait. Any type implementing the `Summary` trait would have
the `summarize` method available on it without any further code. This is
similar to a parent class having an implementation of a method and an
inheriting child class also having the implementation of the method. We can
also override the default implementation of the `summarize` method when we
implement the `Summary` trait, which is similar to a child class overriding the
implementation of a method inherited from a parent class.
<!-- stay:XXAN8KCO hash=sha256:9c8a86579f42 -->

The other reason to use inheritance relates to the type system: to enable a
child type to be used in the same places as the parent type. This is also
called _polymorphism_, which means that you can substitute multiple objects for
each other at runtime if they share certain characteristics.
<!-- stay:NqSAfvTF hash=sha256:4e2ca7342c1a -->

> ### Polymorphism
>
> To many people, polymorphism is synonymous with inheritance. But it’s
> actually a more general concept that refers to code that can work with data of
> multiple types. For inheritance, those types are generally subclasses.
>
> Rust instead uses generics to abstract over different possible types and
> trait bounds to impose constraints on what those types must provide. This is
> sometimes called _bounded parametric polymorphism_.
<!-- stay:igwGdlLP hash=sha256:d2c8e5591171 -->

Rust has chosen a different set of trade-offs by not offering inheritance.
Inheritance is often at risk of sharing more code than necessary. Subclasses
shouldn’t always share all characteristics of their parent class but will do so
with inheritance. This can make a program’s design less flexible. It also
introduces the possibility of calling methods on subclasses that don’t make
sense or that cause errors because the methods don’t apply to the subclass. In
addition, some languages will only allow _single inheritance_ (meaning a
subclass can only inherit from one class), further restricting the flexibility
of a program’s design.
<!-- stay:xO7IGgSZ hash=sha256:9c9e274b327a -->

For these reasons, Rust takes the different approach of using trait objects
instead of inheritance to achieve polymorphism at runtime. Let’s look at how
trait objects work.
<!-- stay:tkGJpWas hash=sha256:f16c7de46fc2 -->
