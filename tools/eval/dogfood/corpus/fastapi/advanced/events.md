# Lifespan Events { #lifespan-events }
<!-- stay:4LkIeKkA hash=sha256:43c87784f265 -->

You can define logic (code) that should be executed before the application **starts up**. This means that this code will be executed **once**, **before** the application **starts receiving requests**.
<!-- stay:OEu4dVLc hash=sha256:6171d88d3ad9 -->

The same way, you can define logic (code) that should be executed when the application is **shutting down**. In this case, this code will be executed **once**, **after** having handled possibly **many requests**.
<!-- stay:PDA9chpn hash=sha256:cb935eb0bf87 -->

Because this code is executed before the application **starts** taking requests, and right after it **finishes** handling requests, it covers the whole application **lifespan** (the word "lifespan" will be important in a second 😉).
<!-- stay:u9E8T7WW hash=sha256:f37137825d47 -->

This can be very useful for setting up **resources** that you need to use for the whole app, and that are **shared** among requests, and/or that you need to **clean up** afterwards. For example, a database connection pool, or loading a shared machine learning model.
<!-- stay:wRmRoyXE hash=sha256:5c54fafbd592 -->

## Use Case { #use-case }
<!-- stay:GwLoea1l hash=sha256:aea75aacf23a -->

Let's start with an example **use case** and then see how to solve it with this.
<!-- stay:xX6W4K8q hash=sha256:642a7aaef083 -->

Let's imagine that you have some **machine learning models** that you want to use to handle requests. 🤖
<!-- stay:tXzY1rll hash=sha256:01bb9510d720 -->

The same models are shared among requests, so, it's not one model per request, or one per user or something similar.
<!-- stay:MJHOhcuG hash=sha256:318c45bf2736 -->

Let's imagine that loading the model can **take quite some time**, because it has to read a lot of **data from disk**. So you don't want to do it for every request.
<!-- stay:A8EmHqJy hash=sha256:f32f65c996e8 -->

You could load it at the top level of the module/file, but that would also mean that it would **load the model** even if you are just running a simple automated test, then that test would be **slow** because it would have to wait for the model to load before being able to run an independent part of the code.
<!-- stay:kG82w7Ek hash=sha256:208802b6a814 -->

That's what we'll solve, let's load the model before the requests are handled, but only right before the application starts receiving requests, not while  the code is being loaded.
<!-- stay:TpgZo3K3 hash=sha256:06670b7ec660 -->

## Lifespan { #lifespan }
<!-- stay:FbnMO5AW hash=sha256:e5b980ca3b0d -->

You can define this *startup* and *shutdown* logic using the `lifespan` parameter of the `FastAPI` app, and a "context manager" (I'll show you what that is in a second).
<!-- stay:2SnYpp3J hash=sha256:ea7960b94126 -->

Let's start with an example and then see it in detail.
<!-- stay:dRaZG3Hj hash=sha256:40d757e688c5 -->

We create an async function `lifespan()` with `yield` like this:
<!-- stay:7dhgxycm hash=sha256:599716d8f68c -->

{* ../../docs_src/events/tutorial003_py310.py hl[16,19] *}
<!-- stay:q8B5QhuJ hash=sha256:07a81e489552 -->

Here we are simulating the expensive *startup* operation of loading the model by putting the (fake) model function in the dictionary with machine learning models before the `yield`. This code will be executed **before** the application **starts taking requests**, during the *startup*.
<!-- stay:yD9OieNK hash=sha256:f97f2541295f -->

And then, right after the `yield`, we unload the model. This code will be executed **after** the application **finishes handling requests**, right before the *shutdown*. This could, for example, release resources like memory or a GPU.
<!-- stay:s6kInaAC hash=sha256:0a43de25eec4 -->

/// tip
<!-- stay:Bczgu6wa hash=sha256:35fc886a93b5 -->

The `shutdown` would happen when you are **stopping** the application.
<!-- stay:c7NsAGVv hash=sha256:deef8499158d -->

Maybe you need to start a new version, or you just got tired of running it. 🤷
<!-- stay:VeHsFhwX hash=sha256:29bfa1557e6b -->

///
<!-- stay:ZBay0jSt hash=sha256:732c4e971163 -->

### Lifespan function { #lifespan-function }
<!-- stay:ApYx4CLx hash=sha256:3c577fe69fef -->

The first thing to notice, is that we are defining an async function with `yield`. This is very similar to Dependencies with `yield`.
<!-- stay:q1J7e5l4 hash=sha256:ee6147686f33 -->

{* ../../docs_src/events/tutorial003_py310.py hl[14:19] *}
<!-- stay:KyNYi9zn hash=sha256:a51ccd0c4775 -->

The first part of the function, before the `yield`, will be executed **before** the application starts.
<!-- stay:vvyHWGqM hash=sha256:f7a92785489e -->

And the part after the `yield` will be executed **after** the application has finished.
<!-- stay:eLKfd0o4 hash=sha256:cc9c202d6d44 -->

### Async Context Manager { #async-context-manager }
<!-- stay:TqOpm6h8 hash=sha256:375fedf03447 -->

If you check, the function is decorated with an `@asynccontextmanager`.
<!-- stay:xpeXX8Wm hash=sha256:aaf05787e5d0 -->

That converts the function into something called an "**async context manager**".
<!-- stay:B19CdvrW hash=sha256:60d1787942cc -->

{* ../../docs_src/events/tutorial003_py310.py hl[1,13] *}
<!-- stay:RAmo1WCP hash=sha256:822a39ae2e7e -->

A **context manager** in Python is something that you can use in a `with` statement, for example, `open()` can be used as a context manager:
<!-- stay:D0e8317N hash=sha256:6e3e9f588e91 -->

```Python
with open("file.txt") as file:
    file.read()
```
<!-- stay:hiucf8Tt hash=sha256:e662e7644bd6 -->

In recent versions of Python, there's also an **async context manager**. You would use it with `async with`:
<!-- stay:2n2a7WUx hash=sha256:4bfcd4e4d19a -->

```Python
async with lifespan(app):
    await do_stuff()
```
<!-- stay:XBcXQk81 hash=sha256:f9d0cc2640f0 -->

When you create a context manager or an async context manager like above, what it does is that, before entering the `with` block, it will execute the code before the `yield`, and after exiting the `with` block, it will execute the code after the `yield`.
<!-- stay:4xqUJwBs hash=sha256:885b8ffa31d4 -->

In our code example above, we don't use it directly, but we pass it to FastAPI for it to use it.
<!-- stay:XYXckTop hash=sha256:2ce10c317ce5 -->

The `lifespan` parameter of the `FastAPI` app takes an **async context manager**, so we can pass our new `lifespan` async context manager to it.
<!-- stay:hTVbzFMM hash=sha256:81f7cfdc9537 -->

{* ../../docs_src/events/tutorial003_py310.py hl[22] *}
<!-- stay:mhm813ST hash=sha256:38c0aaf2a036 -->

## Alternative Events (deprecated) { #alternative-events-deprecated }
<!-- stay:1xBDAAJq hash=sha256:c6b2cc8b5665 -->

/// warning
<!-- stay:djZRKp9C hash=sha256:98e5a9621bab -->

The recommended way to handle the *startup* and *shutdown* is using the `lifespan` parameter of the `FastAPI` app as described above. If you provide a `lifespan` parameter, `startup` and `shutdown` event handlers will no longer be called. It's all `lifespan` or all events, not both.
<!-- stay:56t2kJXv hash=sha256:c0a1d3f79e59 -->

You can probably skip this part.
<!-- stay:tyonAJDr hash=sha256:07a19fb2c7b1 -->

///
<!-- stay:wqI2nShm hash=sha256:732c4e971163 -->

There's an alternative way to define this logic to be executed during *startup* and during *shutdown*.
<!-- stay:dAowA1ld hash=sha256:8e4f8e28678b -->

You can define event handlers (functions) that need to be executed before the application starts up, or when the application is shutting down.
<!-- stay:7YOm2opt hash=sha256:1492175b7b5c -->

These functions can be declared with `async def` or normal `def`.
<!-- stay:JJiTWYMp hash=sha256:328a7d9db250 -->

### `startup` event { #startup-event }
<!-- stay:4fpNtJTf hash=sha256:8c94d56b5159 -->

To add a function that should be run before the application starts, declare it with the event `"startup"`:
<!-- stay:YHmC7RNu hash=sha256:73779333f150 -->

{* ../../docs_src/events/tutorial001_py310.py hl[8] *}
<!-- stay:0P6tbwoV hash=sha256:c814f67767c7 -->

In this case, the `startup` event handler function will initialize the items "database" (just a `dict`) with some values.
<!-- stay:r3YpzdZf hash=sha256:779fc27112b8 -->

You can add more than one event handler function.
<!-- stay:tFiR4MJg hash=sha256:038b60fbff75 -->

And your application won't start receiving requests until all the `startup` event handlers have completed.
<!-- stay:tAcApZQq hash=sha256:22afd769c136 -->

### `shutdown` event { #shutdown-event }
<!-- stay:VAXlP04d hash=sha256:a678d88d798c -->

To add a function that should be run when the application is shutting down, declare it with the event `"shutdown"`:
<!-- stay:ByOh9rfS hash=sha256:1331135e7ca6 -->

{* ../../docs_src/events/tutorial002_py310.py hl[6] *}
<!-- stay:Qt9gKF33 hash=sha256:ba114646144f -->

Here, the `shutdown` event handler function will write a text line `"Application shutdown"` to a file `log.txt`.
<!-- stay:3y39V5dE hash=sha256:64336212d683 -->

/// note
<!-- stay:m0LVYfsg hash=sha256:35f4d438b538 -->

In the `open()` function, the `mode="a"` means "append", so, the line will be added after whatever is on that file, without overwriting the previous contents.
<!-- stay:PhOKDXMR hash=sha256:8f3269f402db -->

///
<!-- stay:K5zkTObJ hash=sha256:732c4e971163 -->

/// tip
<!-- stay:cESthyFl hash=sha256:35fc886a93b5 -->

Notice that in this case we are using a standard Python `open()` function that interacts with a file.
<!-- stay:j8LQFaIi hash=sha256:7940ef5f948e -->

So, it involves I/O (input/output), that requires "waiting" for things to be written to disk.
<!-- stay:7fMbXHyg hash=sha256:4f0e3d9172d3 -->

But `open()` doesn't use `async` and `await`.
<!-- stay:YKD22M3b hash=sha256:3aeea22d1005 -->

So, we declare the event handler function with standard `def` instead of `async def`.
<!-- stay:FgZ7K0VV hash=sha256:7604dab46d8a -->

///
<!-- stay:QTxmMa4i hash=sha256:732c4e971163 -->

### `startup` and `shutdown` together { #startup-and-shutdown-together }
<!-- stay:vL0MHGKj hash=sha256:8853545614fc -->

There's a high chance that the logic for your *startup* and *shutdown* is connected, you might want to start something and then finish it, acquire a resource and then release it, etc.
<!-- stay:pKk1fVvL hash=sha256:7ca327834c0f -->

Doing that in separate functions that don't share logic or variables together is more difficult as you would need to store values in global variables or similar tricks.
<!-- stay:NfCK9cVZ hash=sha256:81bb50a3c741 -->

Because of that, it's now recommended to instead use the `lifespan` as explained above.
<!-- stay:PPccw9VJ hash=sha256:4ffa1c6edbbb -->

## Technical Details { #technical-details }
<!-- stay:O7ZyofqL hash=sha256:2d3e15c416fa -->

Just a technical detail for the curious nerds. 🤓
<!-- stay:XkYSwGyh hash=sha256:ecb16615fde1 -->

Underneath, in the ASGI technical specification, this is part of the [Lifespan Protocol](https://asgi.readthedocs.io/en/latest/specs/lifespan.html), and it defines events called `startup` and `shutdown`.
<!-- stay:ngM0RNVw hash=sha256:40bf0a0b9f16 -->

/// note
<!-- stay:pBIHtZqU hash=sha256:35f4d438b538 -->

You can read more about the Starlette `lifespan` handlers in [Starlette's  Lifespan' docs](https://www.starlette.dev/lifespan/).
<!-- stay:zxNtSeYi hash=sha256:bbdf4847b454 -->

Including how to handle lifespan state that can be used in other areas of your code.
<!-- stay:aVuUsYOZ hash=sha256:344bf46cb05f -->

///
<!-- stay:PZ608wUB hash=sha256:732c4e971163 -->

## Sub Applications { #sub-applications }
<!-- stay:oLBhZZgr hash=sha256:3c1ef8adb388 -->

🚨 Keep in mind that these lifespan events (startup and shutdown) will only be executed for the main application, not for [Sub Applications - Mounts](sub-applications.md).
<!-- stay:ox6VDmcL hash=sha256:960a09019c7a -->
