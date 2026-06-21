# Advanced Dependencies { #advanced-dependencies }
<!-- stay:B5ttdbEe hash=sha256:582d17ccfaa5 -->

## Parameterized dependencies { #parameterized-dependencies }
<!-- stay:Ia83Lyhp hash=sha256:740a341f6ec8 -->

All the dependencies we have seen are a fixed function or class.
<!-- stay:4kEvHjwK hash=sha256:23be9e1691bb -->

But there could be cases where you want to be able to set parameters on the dependency, without having to declare many different functions or classes.
<!-- stay:M5OxDyuK hash=sha256:073b92383f95 -->

Let's imagine that we want to have a dependency that checks if the query parameter `q` contains some fixed content.
<!-- stay:dSXdBH9w hash=sha256:833db0a57376 -->

But we want to be able to parameterize that fixed content.
<!-- stay:QNMrn9ul hash=sha256:23a4ab710baf -->

## A "callable" instance { #a-callable-instance }
<!-- stay:MN7bLyRX hash=sha256:b2ffdb61afae -->

In Python there's a way to make an instance of a class a "callable".
<!-- stay:GGoR41cC hash=sha256:4dfaee052b08 -->

Not the class itself (which is already a callable), but an instance of that class.
<!-- stay:MHdw8pgw hash=sha256:de9fee52b5dc -->

To do that, we declare a method `__call__`:
<!-- stay:RRTo1zB5 hash=sha256:4f36986531ef -->

{* ../../docs_src/dependencies/tutorial011_an_py310.py hl[12] *}
<!-- stay:Futr6l0W hash=sha256:6279286fa709 -->

In this case, this `__call__` is what **FastAPI** will use to check for additional parameters and sub-dependencies, and this is what will be called to pass a value to the parameter in your *path operation function* later.
<!-- stay:RgBReBAP hash=sha256:bf6a7592e965 -->

## Parameterize the instance { #parameterize-the-instance }
<!-- stay:CWnsOr4z hash=sha256:965dc2743187 -->

And now, we can use `__init__` to declare the parameters of the instance that we can use to "parameterize" the dependency:
<!-- stay:C3JhV2Zg hash=sha256:5190e35dbc69 -->

{* ../../docs_src/dependencies/tutorial011_an_py310.py hl[9] *}
<!-- stay:hxfxkFEg hash=sha256:efb49f03d7dc -->

In this case, **FastAPI** won't ever touch or care about `__init__`, we will use it directly in our code.
<!-- stay:yesIoeov hash=sha256:5378b6994f1c -->

## Create an instance { #create-an-instance }
<!-- stay:sHg4HbD2 hash=sha256:08e2f9cb2b9e -->

We could create an instance of this class with:
<!-- stay:ZOp7FIU6 hash=sha256:56a557b8ac8a -->

{* ../../docs_src/dependencies/tutorial011_an_py310.py hl[18] *}
<!-- stay:UZMxKheM hash=sha256:fd4eb07020d5 -->

And that way we are able to "parameterize" our dependency, that now has `"bar"` inside of it, as the attribute `checker.fixed_content`.
<!-- stay:T7s7kEtC hash=sha256:6e98f4486c24 -->

## Use the instance as a dependency { #use-the-instance-as-a-dependency }
<!-- stay:kEwY0dv2 hash=sha256:b8ecf5fced83 -->

Then, we could use this `checker` in a `Depends(checker)`, instead of `Depends(FixedContentQueryChecker)`, because the dependency is the instance, `checker`, not the class itself.
<!-- stay:8xANpLIJ hash=sha256:8b8586ed3fb7 -->

And when solving the dependency, **FastAPI** will call this `checker` like:
<!-- stay:i0czbT71 hash=sha256:ed69c5aad702 -->

```Python
checker(q="somequery")
```
<!-- stay:OzACG0s1 hash=sha256:b57004afd056 -->

...and pass whatever that returns as the value of the dependency in our *path operation function* as the parameter `fixed_content_included`:
<!-- stay:6SyEfqKL hash=sha256:def082a0348c -->

{* ../../docs_src/dependencies/tutorial011_an_py310.py hl[22] *}
<!-- stay:qcQzjDO6 hash=sha256:c9f0bbd34622 -->

/// tip
<!-- stay:KsCj3umj hash=sha256:35fc886a93b5 -->

All this might seem contrived. And it might not be very clear how it is useful yet.
<!-- stay:qNJYml05 hash=sha256:1f35efd2083a -->

These examples are intentionally simple, but show how it all works.
<!-- stay:SwRdMjkt hash=sha256:b89f05e1962d -->

In the chapters about security, there are utility functions that are implemented in this same way.
<!-- stay:d4sxJPhh hash=sha256:c8eaac66c763 -->

If you understood all this, you already know how those utility tools for security work underneath.
<!-- stay:eZFxYzpE hash=sha256:91f75bb5f81b -->

///
<!-- stay:vyZuRfsp hash=sha256:732c4e971163 -->

## Dependencies with `yield`, `HTTPException`, `except` and Background Tasks { #dependencies-with-yield-httpexception-except-and-background-tasks }
<!-- stay:qLQIMX1W hash=sha256:4a0e66a37e43 -->

/// warning
<!-- stay:CRtDM9dj hash=sha256:98e5a9621bab -->

You most probably don't need these technical details.
<!-- stay:xourcdKe hash=sha256:3a960c3f7e0b -->

These details are useful mainly if you had a FastAPI application older than 0.121.0 and you are facing issues with dependencies with `yield`.
<!-- stay:lQO0NPgT hash=sha256:18f5827e0471 -->

///
<!-- stay:0Y1NiXcr hash=sha256:732c4e971163 -->

Dependencies with `yield` have evolved over time to account for the different use cases and to fix some issues, here's a summary of what has changed.
<!-- stay:f2EwxT1I hash=sha256:ebf864341f31 -->

### Dependencies with `yield` and `scope` { #dependencies-with-yield-and-scope }
<!-- stay:dU2Q4KeR hash=sha256:75a194a4cf33 -->

In version 0.121.0, FastAPI added support for `Depends(scope="function")` for dependencies with `yield`.
<!-- stay:5zaETeEh hash=sha256:c19e09c1583f -->

Using `Depends(scope="function")`, the exit code after `yield` is executed right after the *path operation function* is finished, before the response is sent back to the client.
<!-- stay:HJ3b0xuy hash=sha256:d46dcd2f0188 -->

And when using `Depends(scope="request")` (the default), the exit code after `yield` is executed after the response is sent.
<!-- stay:IZkJ3JqL hash=sha256:41e28f9dacd9 -->

You can read more about it in the docs for [Dependencies with `yield` - Early exit and `scope`](../tutorial/dependencies/dependencies-with-yield.md#early-exit-and-scope).
<!-- stay:i8JzTF7w hash=sha256:8efc6e4c3d93 -->

### Dependencies with `yield` and `StreamingResponse`, Technical Details { #dependencies-with-yield-and-streamingresponse-technical-details }
<!-- stay:M9xvcn8C hash=sha256:d0bdc845202c -->

Before FastAPI 0.118.0, if you used a dependency with `yield`, it would run the exit code after the *path operation function* returned but right before sending the response.
<!-- stay:4wpCkpPn hash=sha256:8b54eb0f61f6 -->

The intention was to avoid holding resources for longer than necessary, waiting for the response to travel through the network.
<!-- stay:cTmPemWf hash=sha256:6e4f513a917a -->

This change also meant that if you returned a `StreamingResponse`, the exit code of the dependency with `yield` would have been already run.
<!-- stay:BfRFCYaQ hash=sha256:0e0a91891a25 -->

For example, if you had a database session in a dependency with `yield`, the `StreamingResponse` would not be able to use that session while streaming data because the session would have already been closed in the exit code after `yield`.
<!-- stay:K8XZG3o1 hash=sha256:a495987558b9 -->

This behavior was reverted in 0.118.0, to make the exit code after `yield` be executed after the response is sent.
<!-- stay:R7jS9syo hash=sha256:ff327fb9327c -->

/// note
<!-- stay:uYK1lcts hash=sha256:35f4d438b538 -->

As you will see below, this is very similar to the behavior before version 0.106.0, but with several improvements and bug fixes for corner cases.
<!-- stay:bHqdefhg hash=sha256:97a0d636465c -->

///
<!-- stay:G23RI3xL hash=sha256:732c4e971163 -->

#### Use Cases with Early Exit Code { #use-cases-with-early-exit-code }
<!-- stay:edhLwC3Z hash=sha256:d6865187e4f5 -->

There are some use cases with specific conditions that could benefit from the old behavior of running the exit code of dependencies with `yield` before sending the response.
<!-- stay:0C1FaFfL hash=sha256:d9b393334414 -->

For example, imagine you have code that uses a database session in a dependency with `yield` only to verify a user, but the database session is never used again in the *path operation function*, only in the dependency, **and** the response takes a long time to be sent, like a `StreamingResponse` that sends data slowly, but for some reason doesn't use the database.
<!-- stay:BL1efGuk hash=sha256:8710800a6c39 -->

In this case, the database session would be held until the response is finished being sent, but if you don't use it, then it wouldn't be necessary to hold it.
<!-- stay:vmV0RRPq hash=sha256:4e8ae2f453da -->

Here's how it could look:
<!-- stay:XV2WdpEi hash=sha256:c07f6667c078 -->

{* ../../docs_src/dependencies/tutorial013_an_py310.py *}
<!-- stay:uOtU6Lz4 hash=sha256:781282617692 -->

The exit code, the automatic closing of the `Session` in:
<!-- stay:dRBeAxBa hash=sha256:12468db44a1c -->

{* ../../docs_src/dependencies/tutorial013_an_py310.py ln[19:21] *}
<!-- stay:v2yoZOgX hash=sha256:148e96515c68 -->

...would be run after the response finishes sending the slow data:
<!-- stay:Jnjab4nT hash=sha256:b93d98f5f416 -->

{* ../../docs_src/dependencies/tutorial013_an_py310.py ln[30:38] hl[31:33] *}
<!-- stay:gCll7jxY hash=sha256:c4ca0e0c4d82 -->

But as `generate_stream()` doesn't use the database session, it is not really necessary to keep the session open while sending the response.
<!-- stay:OFvNi39b hash=sha256:bfa5a5202d9e -->

If you have this specific use case using SQLModel (or SQLAlchemy), you could explicitly close the session after you don't need it anymore:
<!-- stay:vrsSD2FN hash=sha256:5aaeace85fdc -->

{* ../../docs_src/dependencies/tutorial014_an_py310.py ln[24:28] hl[28] *}
<!-- stay:Ft3NVs1T hash=sha256:7f020f78ffb8 -->

That way the session would release the database connection, so other requests could use it.
<!-- stay:nUJPWKQp hash=sha256:391b09bad7e6 -->

If you have a different use case that needs to exit early from a dependency with `yield`, please create a [GitHub Discussion Question](https://github.com/fastapi/fastapi/discussions/new?category=questions) with your specific use case and why you would benefit from having early closing for dependencies with `yield`.
<!-- stay:JNV4xORs hash=sha256:90272d495ed9 -->

If there are compelling use cases for early closing in dependencies with `yield`, I would consider adding a new way to opt in to early closing.
<!-- stay:Ye2dEszt hash=sha256:59cb5c0d45a0 -->

### Dependencies with `yield` and `except`, Technical Details { #dependencies-with-yield-and-except-technical-details }
<!-- stay:xSHaMuAQ hash=sha256:41ed3f5fc88b -->

Before FastAPI 0.110.0, if you used a dependency with `yield`, and then you captured an exception with `except` in that dependency, and you didn't raise the exception again, the exception would be automatically raised/forwarded to any exception handlers or the internal server error handler.
<!-- stay:tdccDjt2 hash=sha256:72d06434620e -->

This was changed in version 0.110.0 to fix unhandled memory consumption from forwarded exceptions without a handler (internal server errors), and to make it consistent with the behavior of regular Python code.
<!-- stay:Ghwb3LQ6 hash=sha256:78588a59a3fc -->

### Background Tasks and Dependencies with `yield`, Technical Details { #background-tasks-and-dependencies-with-yield-technical-details }
<!-- stay:cL5ev2xV hash=sha256:d89d04dd89de -->

Before FastAPI 0.106.0, raising exceptions after `yield` was not possible, the exit code in dependencies with `yield` was executed *after* the response was sent, so [Exception Handlers](../tutorial/handling-errors.md#install-custom-exception-handlers) would have already run.
<!-- stay:G3MUIJs1 hash=sha256:d814283f4c6c -->

This was designed this way mainly to allow using the same objects "yielded" by dependencies inside of background tasks, because the exit code would be executed after the background tasks were finished.
<!-- stay:C0UnLyOL hash=sha256:d930ea8a6d98 -->

This was changed in FastAPI 0.106.0 with the intention to not hold resources while waiting for the response to travel through the network.
<!-- stay:0EpRSPSN hash=sha256:74da764e60ab -->

/// tip
<!-- stay:uVTC8P0o hash=sha256:35fc886a93b5 -->

Additionally, a background task is normally an independent set of logic that should be handled separately, with its own resources (e.g. its own database connection).
<!-- stay:17uLSBni hash=sha256:d64a6de3a9d9 -->

So, this way you will probably have cleaner code.
<!-- stay:Xdur3HJi hash=sha256:e36868ee95e6 -->

///
<!-- stay:xTo8Q9J5 hash=sha256:732c4e971163 -->

If you used to rely on this behavior, now you should create the resources for background tasks inside the background task itself, and use internally only data that doesn't depend on the resources of dependencies with `yield`.
<!-- stay:PiF35Y4i hash=sha256:6cf6262dd0de -->

For example, instead of using the same database session, you would create a new database session inside of the background task, and you would obtain the objects from the database using this new session. And then instead of passing the object from the database as a parameter to the background task function, you would pass the ID of that object and then obtain the object again inside the background task function.
<!-- stay:0NZZWMx6 hash=sha256:e5ef7a99574d -->
