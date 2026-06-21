## Installation
<!-- stay:4M01rBGm hash=sha256:a15d12503bf0 -->

The first step is to install Rust. We’ll download Rust through `rustup`, a
command line tool for managing Rust versions and associated tools. You’ll need
an internet connection for the download.
<!-- stay:cFltuwhB hash=sha256:c04d0d5170e2 -->

> Note: If you prefer not to use `rustup` for some reason, please see the
> [Other Rust Installation Methods page][otherinstall] for more options.
<!-- stay:4YyAzIm5 hash=sha256:4e9d8993e848 -->

The following steps install the latest stable version of the Rust compiler.
Rust’s stability guarantees ensure that all the examples in the book that
compile will continue to compile with newer Rust versions. The output might
differ slightly between versions because Rust often improves error messages and
warnings. In other words, any newer, stable version of Rust you install using
these steps should work as expected with the content of this book.
<!-- stay:9fjikWpn hash=sha256:7e19f6b21935 -->

> ### Command Line Notation
>
> In this chapter and throughout the book, we’ll show some commands used in the
> terminal. Lines that you should enter in a terminal all start with `$`. You
> don’t need to type the `$` character; it’s the command line prompt shown to
> indicate the start of each command. Lines that don’t start with `$` typically
> show the output of the previous command. Additionally, PowerShell-specific
> examples will use `>` rather than `$`.
<!-- stay:NiDMy1GB hash=sha256:a28b92a05909 -->

### Installing `rustup` on Linux or macOS
<!-- stay:uDrR5pBQ hash=sha256:61b3dce85b86 -->

If you’re using Linux or macOS, open a terminal and enter the following command:
<!-- stay:08lITNCH hash=sha256:24187ddf5e6e -->

```console
$ curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
```
<!-- stay:G3Dh3jtU hash=sha256:ae89f3fab017 -->

The command downloads a script and starts the installation of the `rustup`
tool, which installs the latest stable version of Rust. You might be prompted
for your password. If the install is successful, the following line will appear:
<!-- stay:fvQGbWJl hash=sha256:2f6db3109c4b -->

```text
Rust is installed now. Great!
```
<!-- stay:cEeUgpe7 hash=sha256:f862062614ea -->

You will also need a _linker_, which is a program that Rust uses to join its
compiled outputs into one file. It is likely you already have one. If you get
linker errors, you should install a C compiler, which will typically include a
linker. A C compiler is also useful because some common Rust packages depend on
C code and will need a C compiler.
<!-- stay:FNNkgQk5 hash=sha256:d17a1853b8df -->

On macOS, you can get a C compiler by running:
<!-- stay:jjwAtc6v hash=sha256:949572b6d661 -->

```console
$ xcode-select --install
```
<!-- stay:sV8iFzs4 hash=sha256:8a32b6dd3f33 -->

Linux users should generally install GCC or Clang, according to their
distribution’s documentation. For example, if you use Ubuntu, you can install
the `build-essential` package.
<!-- stay:JiVL75Qj hash=sha256:4fbfd0f15a5f -->

### Installing `rustup` on Windows
<!-- stay:8vO7wNu0 hash=sha256:cf842ea1c858 -->

On Windows, go to [https://www.rust-lang.org/tools/install][install]<!-- ignore
--> and follow the instructions for installing Rust. At some point in the
installation, you’ll be prompted to install Visual Studio. This provides a
linker and the native libraries needed to compile programs. If you need more
help with this step, see
[https://rust-lang.github.io/rustup/installation/windows-msvc.html][msvc]<!--
ignore -->.
<!-- stay:g56katUF hash=sha256:d2431a9fdb68 -->

The rest of this book uses commands that work in both _cmd.exe_ and PowerShell.
If there are specific differences, we’ll explain which to use.
<!-- stay:Vd0HRtOT hash=sha256:2d7229a4da25 -->

### Troubleshooting
<!-- stay:eYWQwV0I hash=sha256:c6b72ab43705 -->

To check whether you have Rust installed correctly, open a shell and enter this
line:
<!-- stay:gv7gOIXe hash=sha256:82364d189b5e -->

```console
$ rustc --version
```
<!-- stay:NZn1aTEi hash=sha256:ca8550bb45f1 -->

You should see the version number, commit hash, and commit date for the latest
stable version that has been released, in the following format:
<!-- stay:NU3qmgxw hash=sha256:dcd33f32d780 -->

```text
rustc x.y.z (abcabcabc yyyy-mm-dd)
```
<!-- stay:3Geoqgkj hash=sha256:7b2ae084385a -->

If you see this information, you have installed Rust successfully! If you don’t
see this information, check that Rust is in your `%PATH%` system variable as
follows.
<!-- stay:hnEEFgvb hash=sha256:d05e1d0ccc5b -->

In Windows CMD, use:
<!-- stay:2Qy7DZpV hash=sha256:76824dbb3386 -->

```console
> echo %PATH%
```
<!-- stay:MDvRJRCR hash=sha256:4ef11fd4a7bd -->

In PowerShell, use:
<!-- stay:vpSr9tKy hash=sha256:21ae01108a70 -->

```powershell
> echo $env:Path
```
<!-- stay:7FTwirss hash=sha256:9b67c3c7e628 -->

In Linux and macOS, use:
<!-- stay:5Tw75AI7 hash=sha256:4d02426ee53a -->

```console
$ echo $PATH
```
<!-- stay:spZveAPw hash=sha256:0de32276c073 -->

If that’s all correct and Rust still isn’t working, there are a number of
places you can get help. Find out how to get in touch with other Rustaceans (a
silly nickname we call ourselves) on [the community page][community].
<!-- stay:MZ7vIyBI hash=sha256:59a9a2d951b8 -->

### Updating and Uninstalling
<!-- stay:WtUXjnFC hash=sha256:43c8e575daed -->

Once Rust is installed via `rustup`, updating to a newly released version is
easy. From your shell, run the following update script:
<!-- stay:LjvRvT6E hash=sha256:576ef7ce9416 -->

```console
$ rustup update
```
<!-- stay:8kIpkcKS hash=sha256:7341db41c368 -->

To uninstall Rust and `rustup`, run the following uninstall script from your
shell:
<!-- stay:Ng1bOKw8 hash=sha256:0411be706b89 -->

```console
$ rustup self uninstall
```
<!-- stay:DWIIOLWT hash=sha256:f2d7997f61ab -->

<!-- Old headings. Do not remove or links may break. -->
<a id="local-documentation"></a>
<!-- stay:lFmIX3Bq hash=sha256:06229ebfe415 -->

### Reading the Local Documentation
<!-- stay:X9OH9sbj hash=sha256:3f72414529f8 -->

The installation of Rust also includes a local copy of the documentation so
that you can read it offline. Run `rustup doc` to open the local documentation
in your browser.
<!-- stay:5HlBQyvI hash=sha256:84781f8c0007 -->

Any time a type or function is provided by the standard library and you’re not
sure what it does or how to use it, use the application programming interface
(API) documentation to find out!
<!-- stay:vmdBrPXF hash=sha256:6328983d4b79 -->

<!-- Old headings. Do not remove or links may break. -->
<a id="text-editors-and-integrated-development-environments"></a>
<!-- stay:eOHfC5Ff hash=sha256:64156ef7ae89 -->

### Using Text Editors and IDEs
<!-- stay:4tlycdvz hash=sha256:99d06e158609 -->

This book makes no assumptions about what tools you use to author Rust code.
Just about any text editor will get the job done! However, many text editors and
integrated development environments (IDEs) have built-in support for Rust. You
can always find a fairly current list of many editors and IDEs on [the tools
page][tools] on the Rust website.
<!-- stay:tl3qgnaW hash=sha256:ca2b03636f31 -->

### Working Offline with This Book
<!-- stay:SoGrVNTK hash=sha256:51fd7de8b64e -->

In several examples, we will use Rust packages beyond the standard library. To
work through those examples, you will either need to have an internet connection
or to have downloaded those dependencies ahead of time. To download the
dependencies ahead of time, you can run the following commands. (We’ll explain
what `cargo` is and what each of these commands does in detail later.)
<!-- stay:Pmezf7wR hash=sha256:1ba9e6d6718e -->

```console
$ cargo new get-dependencies
$ cd get-dependencies
$ cargo add rand@0.8.5 trpl@0.2.0
```
<!-- stay:SYa2JHrf hash=sha256:de2fbd44f99d -->

This will cache the downloads for these packages so you will not need to
download them later. Once you have run this command, you do not need to keep the
`get-dependencies` folder. If you have run this command, you can use the
`--offline` flag with all `cargo` commands in the rest of the book to use these
cached versions instead of attempting to use the network.
<!-- stay:FdnDqT9h hash=sha256:31f685f980d3 -->

[otherinstall]: https://forge.rust-lang.org/infra/other-installation-methods.html
[install]: https://www.rust-lang.org/tools/install
[msvc]: https://rust-lang.github.io/rustup/installation/windows-msvc.html
[community]: https://www.rust-lang.org/community
[tools]: https://www.rust-lang.org/tools
<!-- stay:xtQr61Xn hash=sha256:3ce04dfa3eab -->
