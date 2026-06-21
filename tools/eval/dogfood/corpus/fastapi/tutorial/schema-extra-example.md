# Declare Request Example Data { #declare-request-example-data }
<!-- stay:2C09zXB5 hash=sha256:0aca7e836491 -->

You can declare examples of the data your app can receive.
<!-- stay:CkZvLY1r hash=sha256:fd3ec605409f -->

Here are several ways to do it.
<!-- stay:WiR4KJh8 hash=sha256:9b2c1cb07b6c -->

## Extra JSON Schema data in Pydantic models { #extra-json-schema-data-in-pydantic-models }
<!-- stay:0hX0Ay1A hash=sha256:b6d9fd79c028 -->

You can declare `examples` for a Pydantic model that will be added to the generated JSON Schema.
<!-- stay:zXfAmnIE hash=sha256:c300562fb3ac -->

{* ../../docs_src/schema_extra_example/tutorial001_py310.py hl[13:24] *}
<!-- stay:EPNwaDPr hash=sha256:99e38b2801db -->

That extra info will be added as-is to the output **JSON Schema** for that model, and it will be used in the API docs.
<!-- stay:aNgm88FV hash=sha256:785251174f26 -->

You can use the attribute `model_config` that takes a `dict` as described in [Pydantic's docs: Configuration](https://docs.pydantic.dev/latest/api/config/).
<!-- stay:G7gb56Tb hash=sha256:9ebdb199a950 -->

You can set `"json_schema_extra"` with a `dict` containing any additional data you would like to show up in the generated JSON Schema, including `examples`.
<!-- stay:UkMbtgnP hash=sha256:61d90f9bd2d0 -->

/// tip
<!-- stay:Q0i2I3Z1 hash=sha256:35fc886a93b5 -->

You could use the same technique to extend the JSON Schema and add your own custom extra info.
<!-- stay:SOP2kYud hash=sha256:32c6fd66b484 -->

For example you could use it to add metadata for a frontend user interface, etc.
<!-- stay:Y04vgvxB hash=sha256:44f36f44a1d6 -->

///
<!-- stay:DPi1z4V0 hash=sha256:732c4e971163 -->

/// note
<!-- stay:S8teLaej hash=sha256:35f4d438b538 -->

OpenAPI 3.1.0 (used since FastAPI 0.99.0) added support for `examples`, which is part of the **JSON Schema** standard.
<!-- stay:7rI5CSCn hash=sha256:b64b713bed8f -->

Before that, it only supported the keyword `example` with a single example. That is still supported by OpenAPI 3.1.0, but is deprecated and is not part of the JSON Schema standard. So you are encouraged to migrate `example` to `examples`. 🤓
<!-- stay:SLGH12sp hash=sha256:08ddbf4e2a7a -->

You can read more at the end of this page.
<!-- stay:fbaYSZRw hash=sha256:3542d42f75f5 -->

///
<!-- stay:VYRXpAkE hash=sha256:732c4e971163 -->

## `Field` additional arguments { #field-additional-arguments }
<!-- stay:tgzTvgGg hash=sha256:44d9a546f29b -->

When using `Field()` with Pydantic models, you can also declare additional `examples`:
<!-- stay:btD2W6gl hash=sha256:a65f4b5b801a -->

{* ../../docs_src/schema_extra_example/tutorial002_py310.py hl[2,8:11] *}
<!-- stay:6TYvi2d2 hash=sha256:a5f08b45b54d -->

## `examples` in JSON Schema - OpenAPI { #examples-in-json-schema-openapi }
<!-- stay:kSEOhhPH hash=sha256:c4963b45f535 -->

When using any of:
<!-- stay:lnoUvA9R hash=sha256:cbcc679dd2d3 -->

* `Path()`
* `Query()`
* `Header()`
* `Cookie()`
* `Body()`
* `Form()`
* `File()`
<!-- stay:YFzDUOrH hash=sha256:f1c19968c06d -->

you can also declare a group of `examples` with additional information that will be added to their **JSON Schemas** inside of **OpenAPI**.
<!-- stay:24a1NFZM hash=sha256:c6293cec6a9f -->

### `Body` with `examples` { #body-with-examples }
<!-- stay:rovdtagi hash=sha256:1dc6e17c536e -->

Here we pass `examples` containing one example of the data expected in `Body()`:
<!-- stay:BviW1eRC hash=sha256:484c35dba5a7 -->

{* ../../docs_src/schema_extra_example/tutorial003_an_py310.py hl[22:29] *}
<!-- stay:k3Rdhk87 hash=sha256:0b2d658ee7c7 -->

### Example in the docs UI { #example-in-the-docs-ui }
<!-- stay:1LLxP5wp hash=sha256:09c3a133f1cc -->

With any of the methods above it would look like this in the `/docs`:
<!-- stay:K1d9JBV3 hash=sha256:84bcb13a2503 -->

<img src="/img/tutorial/body-fields/image01.png">
<!-- stay:bKP62kSO hash=sha256:4f9ebe3ab9fc -->

### `Body` with multiple `examples` { #body-with-multiple-examples }
<!-- stay:ZWYSjszF hash=sha256:e6b9624797fb -->

You can of course also pass multiple `examples`:
<!-- stay:N0ggVWmT hash=sha256:53952d3d8eaf -->

{* ../../docs_src/schema_extra_example/tutorial004_an_py310.py hl[23:38] *}
<!-- stay:jT19kZO5 hash=sha256:1accae7cc9b8 -->

When you do this, the examples will be part of the internal **JSON Schema** for that body data.
<!-- stay:mAUt2lqa hash=sha256:146c9206bb20 -->

Nevertheless, at the <dfn title="2023-08-26">time of writing this</dfn>, Swagger UI, the tool in charge of showing the docs UI, doesn't support showing multiple examples for the data in **JSON Schema**. But read below for a workaround.
<!-- stay:CldxMOJe hash=sha256:189abfdf954b -->

### OpenAPI-specific `examples` { #openapi-specific-examples }
<!-- stay:5lFcWrTE hash=sha256:6a4f74829b58 -->

Since before **JSON Schema** supported `examples`, OpenAPI had support for a different field also called `examples`.
<!-- stay:j7r6zRvV hash=sha256:5be23cd47811 -->

This **OpenAPI-specific** `examples` goes in another section in the OpenAPI specification. It goes in the **details for each *path operation***, not inside each JSON Schema.
<!-- stay:V365pOLP hash=sha256:821710307fc5 -->

And Swagger UI has supported this particular `examples` field for a while. So, you can use it to **show** different **examples in the docs UI**.
<!-- stay:x5eQB2yU hash=sha256:34e40cc9bb7d -->

The shape of this OpenAPI-specific field `examples` is a `dict` with **multiple examples** (instead of a `list`), each with extra information that will be added to **OpenAPI** too.
<!-- stay:b4jQRWey hash=sha256:0ff6905843d6 -->

This doesn't go inside of each JSON Schema contained in OpenAPI, this goes outside, in the *path operation* directly.
<!-- stay:kuY52sDC hash=sha256:7c77ac61b3f2 -->

### Using the `openapi_examples` Parameter { #using-the-openapi-examples-parameter }
<!-- stay:mgzvGibZ hash=sha256:2a49e6f30b1b -->

You can declare the OpenAPI-specific `examples` in FastAPI with the parameter `openapi_examples` for:
<!-- stay:x0Ky7d89 hash=sha256:cb48754eea57 -->

* `Path()`
* `Query()`
* `Header()`
* `Cookie()`
* `Body()`
* `Form()`
* `File()`
<!-- stay:hwYstpIW hash=sha256:f1c19968c06d -->

The keys of the `dict` identify each example, and each value is another `dict`.
<!-- stay:jNdDo6Zb hash=sha256:619170061aa8 -->

Each specific example `dict` in the `examples` can contain:
<!-- stay:UIhfucFZ hash=sha256:d17d396ad892 -->

* `summary`: Short description for the example.
* `description`: A long description that can contain Markdown text.
* `value`: This is the actual example shown, e.g. a `dict`.
* `externalValue`: alternative to `value`, a URL pointing to the example. Although this might not be supported by as many tools as `value`.
<!-- stay:auMSzUSK hash=sha256:d3d6c9bf77f6 -->

You can use it like this:
<!-- stay:nxKYVLkR hash=sha256:27126e33ecc4 -->

{* ../../docs_src/schema_extra_example/tutorial005_an_py310.py hl[23:49] *}
<!-- stay:JX5HdgBS hash=sha256:232b44e53322 -->

### OpenAPI Examples in the Docs UI { #openapi-examples-in-the-docs-ui }
<!-- stay:BFj1grUa hash=sha256:7878da7037a1 -->

With `openapi_examples` added to `Body()` the `/docs` would look like:
<!-- stay:07I6i77Y hash=sha256:3df19a56b477 -->

<img src="/img/tutorial/body-fields/image02.png">
<!-- stay:kFPaQofC hash=sha256:8002c0ca1ff0 -->

## Technical Details { #technical-details }
<!-- stay:BOlDu0Fg hash=sha256:2d3e15c416fa -->

/// tip
<!-- stay:oVRTBBN3 hash=sha256:35fc886a93b5 -->

If you are already using **FastAPI** version **0.99.0 or above**, you can probably **skip** these details.
<!-- stay:OWDfEZTr hash=sha256:3d9d97bf1c6c -->

They are more relevant for older versions, before OpenAPI 3.1.0 was available.
<!-- stay:gV6KLg6s hash=sha256:43551f48a49a -->

You can consider this a brief OpenAPI and JSON Schema **history lesson**. 🤓
<!-- stay:VJqzx2Te hash=sha256:61bcd8c0c781 -->

///
<!-- stay:1M5ReaMw hash=sha256:732c4e971163 -->

/// warning
<!-- stay:y8e5b5A0 hash=sha256:98e5a9621bab -->

These are very technical details about the standards **JSON Schema** and **OpenAPI**.
<!-- stay:xkM1Xc3f hash=sha256:887c51af135b -->

If the ideas above already work for you, that might be enough, and you probably don't need these details, feel free to skip them.
<!-- stay:P1GjyjTB hash=sha256:a476b5debc57 -->

///
<!-- stay:nA0BeZM7 hash=sha256:732c4e971163 -->

Before OpenAPI 3.1.0, OpenAPI used an older and modified version of **JSON Schema**.
<!-- stay:JEMa6d8G hash=sha256:6a05eb87b0c8 -->

JSON Schema didn't have `examples`, so OpenAPI added its own `example` field to its own modified version.
<!-- stay:r0ZvrQl7 hash=sha256:a4371a2b64f5 -->

OpenAPI also added `example` and `examples` fields to other parts of the specification:
<!-- stay:OlQy4YWI hash=sha256:b2a25d6cdfe1 -->

* [`Parameter Object` (in the specification)](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#parameter-object) that was used by FastAPI's:
    * `Path()`
    * `Query()`
    * `Header()`
    * `Cookie()`
* [`Request Body Object`, in the field `content`, on the `Media Type Object` (in the specification)](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#media-type-object) that was used by FastAPI's:
    * `Body()`
    * `File()`
    * `Form()`
<!-- stay:mOT9Syoy hash=sha256:4bb1b05f38e2 -->

/// note
<!-- stay:TbbM56Ze hash=sha256:35f4d438b538 -->

This old OpenAPI-specific `examples` parameter is now `openapi_examples` since FastAPI `0.103.0`.
<!-- stay:lJ32tDl6 hash=sha256:f33e2e3e2fa5 -->

///
<!-- stay:Dola2KWZ hash=sha256:732c4e971163 -->

### JSON Schema's `examples` field { #json-schemas-examples-field }
<!-- stay:BKc2M45l hash=sha256:96a3c1a28778 -->

But then JSON Schema added an [`examples`](https://json-schema.org/draft/2019-09/json-schema-validation.html#rfc.section.9.5) field to a new version of the specification.
<!-- stay:XS5p5Xc0 hash=sha256:85163427d2b4 -->

And then the new OpenAPI 3.1.0 was based on the latest version (JSON Schema 2020-12) that included this new field `examples`.
<!-- stay:emej1jPh hash=sha256:a2443068e830 -->

And now this new `examples` field takes precedence over the old single (and custom) `example` field, that is now deprecated.
<!-- stay:6IBxwP4X hash=sha256:e7a3da4fd9ed -->

This new `examples` field in JSON Schema is **just a `list`** of examples, not a dict with extra metadata as in the other places in OpenAPI (described above).
<!-- stay:iaOgzZD4 hash=sha256:b204525c6dc8 -->

/// note
<!-- stay:8BWBOSc2 hash=sha256:35f4d438b538 -->

Even after OpenAPI 3.1.0 was released with this new simpler integration with JSON Schema, for a while, Swagger UI, the tool that provides the automatic docs, didn't support OpenAPI 3.1.0 (it does since version 5.0.0 🎉).
<!-- stay:zjDvmwGn hash=sha256:4ba12ffea2fb -->

Because of that, versions of FastAPI previous to 0.99.0 still used versions of OpenAPI lower than 3.1.0.
<!-- stay:kbrSrPA5 hash=sha256:89dcb3b6ea43 -->

///
<!-- stay:Zgsmyec8 hash=sha256:732c4e971163 -->

### Pydantic and FastAPI `examples` { #pydantic-and-fastapi-examples }
<!-- stay:zehV2VxC hash=sha256:6514ff661708 -->

When you add `examples` inside a Pydantic model, using `schema_extra` or `Field(examples=["something"])` that example is added to the **JSON Schema** for that Pydantic model.
<!-- stay:2GggqGp5 hash=sha256:5bf3fac35ed9 -->

And that **JSON Schema** of the Pydantic model is included in the **OpenAPI** of your API, and then it's used in the docs UI.
<!-- stay:nxDJ3fQx hash=sha256:d7d9b254812a -->

In versions of FastAPI before 0.99.0 (0.99.0 and above use the newer OpenAPI 3.1.0) when you used `example` or `examples` with any of the other utilities (`Query()`, `Body()`, etc.) those examples were not added to the JSON Schema that describes that data (not even to OpenAPI's own version of JSON Schema), they were added directly to the *path operation* declaration in OpenAPI (outside the parts of OpenAPI that use JSON Schema).
<!-- stay:ltzcyE0E hash=sha256:2496603f587e -->

But now that FastAPI 0.99.0 and above uses OpenAPI 3.1.0, that uses JSON Schema 2020-12, and Swagger UI 5.0.0 and above, everything is more consistent and the examples are included in JSON Schema.
<!-- stay:g3m1Qcq0 hash=sha256:fcb8df89a5e2 -->

### Swagger UI and OpenAPI-specific `examples` { #swagger-ui-and-openapi-specific-examples }
<!-- stay:GWCR7sdU hash=sha256:7dd120c7038c -->

Now, as Swagger UI didn't support multiple JSON Schema examples (as of 2023-08-26), users didn't have a way to show multiple examples in the docs.
<!-- stay:OOI22oJn hash=sha256:08fb941a753b -->

To solve that, FastAPI `0.103.0` **added support** for declaring the same old **OpenAPI-specific** `examples` field with the new parameter `openapi_examples`. 🤓
<!-- stay:0tRGchcp hash=sha256:609babe964a8 -->

### Summary { #summary }
<!-- stay:QBlpX5is hash=sha256:f4cb6a416ebb -->

I used to say I didn't like history that much... and look at me now giving "tech history" lessons. 😅
<!-- stay:Tv7PHkUO hash=sha256:9d632babd35d -->

In short, **upgrade to FastAPI 0.99.0 or above**, and things are much **simpler, consistent, and intuitive**, and you don't have to know all these historic details. 😎
<!-- stay:ygEg4xCa hash=sha256:f8c04a20d58c -->
