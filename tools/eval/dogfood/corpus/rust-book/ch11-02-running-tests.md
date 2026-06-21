## Controlling How Tests Are Run
<!-- stay:TSWw6w9U hash=sha256:8610701ea772 -->

Just as `cargo run` compiles your code and then runs the resultant binary,
`cargo test` compiles your code in test mode and runs the resultant test
binary. The default behavior of the binary produced by `cargo test` is to run
all the tests in parallel and capture output generated during test runs,
preventing the output from being displayed and making it easier to read the
output related to the test results. You can, however, specify command line
options to change this default behavior.
<!-- stay:4aWTOi9L hash=sha256:e914ae8f3e42 -->

Some command line options go to `cargo test`, and some go to the resultant test
binary. To separate these two types of arguments, you list the arguments that
go to `cargo test` followed by the separator `--` and then the ones that go to
the test binary. Running `cargo test --help` displays the options you can use
with `cargo test`, and running `cargo test -- --help` displays the options you
can use after the separator. These options are also documented in [the “Tests”
section of _The `rustc` Book_][tests].
<!-- stay:NKqCBrtq hash=sha256:22a6de78dfc5 -->

[tests]: https://doc.rust-lang.org/rustc/tests/index.html
<!-- stay:KsJfa2Zp hash=sha256:a8cebf2bdc33 -->

### Running Tests in Parallel or Consecutively
<!-- stay:WIR45MBV hash=sha256:5ec9ad733cc1 -->

When you run multiple tests, by default they run in parallel using threads,
meaning they finish running more quickly and you get feedback sooner. Because
the tests are running at the same time, you must make sure your tests don’t
depend on each other or on any shared state, including a shared environment,
such as the current working directory or environment variables.
<!-- stay:CK1IqrWG hash=sha256:200da0e0ac25 -->

For example, say each of your tests runs some code that creates a file on disk
named _test-output.txt_ and writes some data to that file. Then, each test
reads the data in that file and asserts that the file contains a particular
value, which is different in each test. Because the tests run at the same time,
one test might overwrite the file in the time between when another test is
writing and reading the file. The second test will then fail, not because the
code is incorrect but because the tests have interfered with each other while
running in parallel. One solution is to make sure each test writes to a
different file; another solution is to run the tests one at a time.
<!-- stay:cA5O9ghn hash=sha256:c88b96978601 -->

If you don’t want to run the tests in parallel or if you want more fine-grained
control over the number of threads used, you can send the `--test-threads` flag
and the number of threads you want to use to the test binary. Take a look at
the following example:
<!-- stay:8xSpfT5u hash=sha256:b7f5f1eec5cb -->

```console
$ cargo test -- --test-threads=1
```
<!-- stay:a7ObDuLB hash=sha256:f000f5c156a5 -->

We set the number of test threads to `1`, telling the program not to use any
parallelism. Running the tests using one thread will take longer than running
them in parallel, but the tests won’t interfere with each other if they share
state.
<!-- stay:sR8b08qZ hash=sha256:b79fbd05e65f -->

### Showing Function Output
<!-- stay:4SlUU7nE hash=sha256:94dbbb882989 -->

By default, if a test passes, Rust’s test library captures anything printed to
standard output. For example, if we call `println!` in a test and the test
passes, we won’t see the `println!` output in the terminal; we’ll see only the
line that indicates the test passed. If a test fails, we’ll see whatever was
printed to standard output with the rest of the failure message.
<!-- stay:v7BTwsAf hash=sha256:245072030a47 -->

As an example, Listing 11-10 has a silly function that prints the value of its
parameter and returns 10, as well as a test that passes and a test that fails.
<!-- stay:deWmRy5q hash=sha256:bb02be130592 -->

<Listing number="11-10" file-name="src/lib.rs" caption="Tests for a function that calls `println!`">
<!-- stay:M59Nk4OD hash=sha256:25bd51dedb94 -->

```rust,panics,noplayground
{{#rustdoc_include ../listings/ch11-writing-automated-tests/listing-11-10/src/lib.rs}}
```
<!-- stay:wFb15z20 hash=sha256:d7ad9ba9d542 -->

</Listing>
<!-- stay:aoxV67gc hash=sha256:b58d16a1f9c0 -->

When we run these tests with `cargo test`, we’ll see the following output:
<!-- stay:GSAssAYp hash=sha256:352f3741da23 -->

```console
{{#include ../listings/ch11-writing-automated-tests/listing-11-10/output.txt}}
```
<!-- stay:7jfFqpUn hash=sha256:21468ab02b02 -->

Note that nowhere in this output do we see `I got the value 4`, which is
printed when the test that passes runs. That output has been captured. The
output from the test that failed, `I got the value 8`, appears in the section
of the test summary output, which also shows the cause of the test failure.
<!-- stay:N0OcVdyT hash=sha256:ae5618c8ba64 -->

If we want to see printed values for passing tests as well, we can tell Rust to
also show the output of successful tests with `--show-output`:
<!-- stay:tDH2dtnq hash=sha256:06183c21098b -->

```console
$ cargo test -- --show-output
```
<!-- stay:zDld5PU3 hash=sha256:27956807f61b -->

When we run the tests in Listing 11-10 again with the `--show-output` flag, we
see the following output:
<!-- stay:GvL9ezOk hash=sha256:f30af2a7c02d -->

```console
{{#include ../listings/ch11-writing-automated-tests/output-only-01-show-output/output.txt}}
```
<!-- stay:OfONAimY hash=sha256:823c9eaa0feb -->

### Running a Subset of Tests by Name
<!-- stay:F8dgval2 hash=sha256:14342aa4bbd6 -->

Running a full test suite can sometimes take a long time. If you’re working on
code in a particular area, you might want to run only the tests pertaining to
that code. You can choose which tests to run by passing `cargo test` the name
or names of the test(s) you want to run as an argument.
<!-- stay:ANElCB8k hash=sha256:7a3d9771bcee -->

To demonstrate how to run a subset of tests, we’ll first create three tests for
our `add_two` function, as shown in Listing 11-11, and choose which ones to run.
<!-- stay:Q43SNjrS hash=sha256:e301a47d467d -->

<Listing number="11-11" file-name="src/lib.rs" caption="Three tests with three different names">
<!-- stay:K0kcZhpq hash=sha256:6747e1dddf69 -->

```rust,noplayground
{{#rustdoc_include ../listings/ch11-writing-automated-tests/listing-11-11/src/lib.rs}}
```
<!-- stay:1PS2wyXh hash=sha256:c5925c8db080 -->

</Listing>
<!-- stay:isEjp9kL hash=sha256:b58d16a1f9c0 -->

If we run the tests without passing any arguments, as we saw earlier, all the
tests will run in parallel:
<!-- stay:qsr7p9oT hash=sha256:b5c0277ceba7 -->

```console
{{#include ../listings/ch11-writing-automated-tests/listing-11-11/output.txt}}
```
<!-- stay:fT37hfK1 hash=sha256:164edb03ea26 -->

#### Running Single Tests
<!-- stay:q4DuiNDq hash=sha256:98bb1dbbe478 -->

We can pass the name of any test function to `cargo test` to run only that test:
<!-- stay:2arzDb12 hash=sha256:2daa2f33a3d3 -->

```console
{{#include ../listings/ch11-writing-automated-tests/output-only-02-single-test/output.txt}}
```
<!-- stay:4Lnrv4Qy hash=sha256:48ac1f964405 -->

Only the test with the name `one_hundred` ran; the other two tests didn’t match
that name. The test output lets us know we had more tests that didn’t run by
displaying `2 filtered out` at the end.
<!-- stay:PBX5FAy5 hash=sha256:39a01e8794b9 -->

We can’t specify the names of multiple tests in this way; only the first value
given to `cargo test` will be used. But there is a way to run multiple tests.
<!-- stay:AmfhUk16 hash=sha256:191bbff25e96 -->

#### Filtering to Run Multiple Tests
<!-- stay:XbJiHGDo hash=sha256:22b88e53b00a -->

We can specify part of a test name, and any test whose name matches that value
will be run. For example, because two of our tests’ names contain `add`, we can
run those two by running `cargo test add`:
<!-- stay:pjZBEWEn hash=sha256:074138058a00 -->

```console
{{#include ../listings/ch11-writing-automated-tests/output-only-03-multiple-tests/output.txt}}
```
<!-- stay:kZWoGD1C hash=sha256:751a96573888 -->

This command ran all tests with `add` in the name and filtered out the test
named `one_hundred`. Also note that the module in which a test appears becomes
part of the test’s name, so we can run all the tests in a module by filtering
on the module’s name.
<!-- stay:Oh6WwyzU hash=sha256:11e6c9d65a45 -->

<!-- Old headings. Do not remove or links may break. -->
<!-- stay:kOiNLwT9 hash=sha256:5c2d65695c1a -->

<a id="ignoring-some-tests-unless-specifically-requested"></a>
<!-- stay:N1dyQhYM hash=sha256:da9dc8f8c303 -->

### Ignoring Tests Unless Specifically Requested
<!-- stay:AmHbJLEC hash=sha256:c8025baaf4ee -->

Sometimes a few specific tests can be very time-consuming to execute, so you
might want to exclude them during most runs of `cargo test`. Rather than
listing as arguments all tests you do want to run, you can instead annotate the
time-consuming tests using the `ignore` attribute to exclude them, as shown
here:
<!-- stay:hdgHSmqo hash=sha256:f10d5d838dfd -->

<span class="filename">Filename: src/lib.rs</span>
<!-- stay:L2edN5DQ hash=sha256:1563cb142810 -->

```rust,noplayground
{{#rustdoc_include ../listings/ch11-writing-automated-tests/no-listing-11-ignore-a-test/src/lib.rs:here}}
```
<!-- stay:JA8Wv0L2 hash=sha256:a007d0a8277e -->

After `#[test]`, we add the `#[ignore]` line to the test we want to exclude.
Now when we run our tests, `it_works` runs, but `expensive_test` doesn’t:
<!-- stay:5F9wmrfv hash=sha256:d1a38a07edd4 -->

```console
{{#include ../listings/ch11-writing-automated-tests/no-listing-11-ignore-a-test/output.txt}}
```
<!-- stay:JRZmlfIi hash=sha256:2e7f75eafc0d -->

The `expensive_test` function is listed as `ignored`. If we want to run only
the ignored tests, we can use `cargo test -- --ignored`:
<!-- stay:rW2y2Y6r hash=sha256:128f38dd50ed -->

```console
{{#include ../listings/ch11-writing-automated-tests/output-only-04-running-ignored/output.txt}}
```
<!-- stay:g8loqFfX hash=sha256:b53eae3bba47 -->

By controlling which tests run, you can make sure your `cargo test` results
will be returned quickly. When you’re at a point where it makes sense to check
the results of the `ignored` tests and you have time to wait for the results,
you can run `cargo test -- --ignored` instead. If you want to run all tests
whether they’re ignored or not, you can run `cargo test -- --include-ignored`.
<!-- stay:3gf7n6Km hash=sha256:20e3a0ffdda5 -->
