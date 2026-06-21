# Extra Models { #extra-models }
<!-- stay:WqThT22z hash=sha256:be0dfeb44837 -->

Continuing with the previous example, it will be common to have more than one related model.
<!-- stay:g0oxGucu hash=sha256:1bbf93cc6c7c -->

This is especially the case for user models, because:
<!-- stay:vVFsMwig hash=sha256:32bc2ebe7653 -->

* The **input model** needs to be able to have a password.
* The **output model** should not have a password.
* The **database model** would probably need to have a hashed password.
<!-- stay:iKrPeSVH hash=sha256:1c365db903da -->

/// danger
<!-- stay:FCIb24oi hash=sha256:41785566f21b -->

Never store user's plaintext passwords. Always store a "secure hash" that you can then verify.
<!-- stay:TqVnlqKt hash=sha256:aac00deb77cb -->

If you don't know, you will learn what a "password hash" is in the [security chapters](security/simple-oauth2.md#password-hashing).
<!-- stay:IthIoGff hash=sha256:35ead8f68023 -->

///
<!-- stay:UGNlhphB hash=sha256:732c4e971163 -->

## Multiple models { #multiple-models }
<!-- stay:xJ1z5lrS hash=sha256:1195eb21088b -->

Here's a general idea of what the models could look like with their password fields and the places where they are used:
<!-- stay:8erN9AHq hash=sha256:9e3a15f02a36 -->

{* ../../docs_src/extra_models/tutorial001_py310.py hl[7,9,14,20,22,27:28,31:33,38:39] *}
<!-- stay:TZqYvb2t hash=sha256:042aa6c2581d -->

### About `**user_in.model_dump()` { #about-user-in-model-dump }
<!-- stay:b3sUYXHp hash=sha256:c8e88136082d -->

#### Pydantic's `.model_dump()` { #pydantics-model-dump }
<!-- stay:01W3KnRe hash=sha256:ca4bbc9e9304 -->

`user_in` is a Pydantic model of class `UserIn`.
<!-- stay:dr7OxRGs hash=sha256:66b8d017b435 -->

Pydantic models have a `.model_dump()` method that returns a `dict` with the model's data.
<!-- stay:FOtZBNZK hash=sha256:095d81d824bc -->

So, if we create a Pydantic object `user_in` like:
<!-- stay:NStubDVh hash=sha256:1ee003872221 -->

```Python
user_in = UserIn(username="john", password="secret", email="john.doe@example.com")
```
<!-- stay:6z0z2k7m hash=sha256:1227c5ce4ea3 -->

and then we call:
<!-- stay:jIEZCycM hash=sha256:2fafa6722d0b -->

```Python
user_dict = user_in.model_dump()
```
<!-- stay:be7OJE0z hash=sha256:3c0991ee665a -->

we now have a `dict` with the data in the variable `user_dict` (it's a `dict` instead of a Pydantic model object).
<!-- stay:jap0raNF hash=sha256:a0b4d3cfe22a -->

And if we call:
<!-- stay:5pvxQXs2 hash=sha256:cf67cb9f6d55 -->

```Python
print(user_dict)
```
<!-- stay:OecTQ7DT hash=sha256:243a8cf96810 -->

we would get a Python `dict` with:
<!-- stay:eIei9ypV hash=sha256:ea4c5859def5 -->

```Python
{
    'username': 'john',
    'password': 'secret',
    'email': 'john.doe@example.com',
    'full_name': None,
}
```
<!-- stay:GPDeUKvj hash=sha256:49414bd88371 -->

#### Unpacking a `dict` { #unpacking-a-dict }
<!-- stay:y4wFEeYf hash=sha256:7e405e1b2690 -->

If we take a `dict` like `user_dict` and pass it to a function (or class) with `**user_dict`, Python will "unpack" it. It will pass the keys and values of the `user_dict` directly as key-value arguments.
<!-- stay:Wsc4sdGI hash=sha256:4a61db09fb59 -->

So, continuing with the `user_dict` from above, writing:
<!-- stay:2Mf724eP hash=sha256:003d7dd8371e -->

```Python
UserInDB(**user_dict)
```
<!-- stay:gSGvuvyr hash=sha256:915f8e85f0cc -->

would result in something equivalent to:
<!-- stay:4mJrf3x4 hash=sha256:a6351c3881c7 -->

```Python
UserInDB(
    username="john",
    password="secret",
    email="john.doe@example.com",
    full_name=None,
)
```
<!-- stay:Cpellu58 hash=sha256:85c2460757ee -->

Or more exactly, using `user_dict` directly, with whatever contents it might have in the future:
<!-- stay:bsnNfh2H hash=sha256:979f01ccf1ae -->

```Python
UserInDB(
    username = user_dict["username"],
    password = user_dict["password"],
    email = user_dict["email"],
    full_name = user_dict["full_name"],
)
```
<!-- stay:ahqLbZlM hash=sha256:eaf0389734ee -->

#### A Pydantic model from the contents of another { #a-pydantic-model-from-the-contents-of-another }
<!-- stay:leyPr7Kc hash=sha256:391e396a1afc -->

As in the example above we got `user_dict` from `user_in.model_dump()`, this code:
<!-- stay:1S3bgLtm hash=sha256:d64e2cb46d3f -->

```Python
user_dict = user_in.model_dump()
UserInDB(**user_dict)
```
<!-- stay:sYc6at3l hash=sha256:872094535ebc -->

would be equivalent to:
<!-- stay:fUxD5gNh hash=sha256:247bd91b7640 -->

```Python
UserInDB(**user_in.model_dump())
```
<!-- stay:jmlLRiCc hash=sha256:19c502f0a16d -->

...because `user_in.model_dump()` is a `dict`, and then we make Python "unpack" it by passing it to `UserInDB` prefixed with `**`.
<!-- stay:F3tj14ix hash=sha256:347c32645bdc -->

So, we get a Pydantic model from the data in another Pydantic model.
<!-- stay:XXMS8Tbo hash=sha256:1af534ead58e -->

#### Unpacking a `dict` and extra keywords { #unpacking-a-dict-and-extra-keywords }
<!-- stay:2kgcz4IT hash=sha256:d438672d6ccd -->

And then adding the extra keyword argument `hashed_password=hashed_password`, like in:
<!-- stay:wJQRf7Tx hash=sha256:7e6facbe0a0c -->

```Python
UserInDB(**user_in.model_dump(), hashed_password=hashed_password)
```
<!-- stay:aGfS97YB hash=sha256:3eac131f6307 -->

...ends up being like:
<!-- stay:7jV4IVHW hash=sha256:c7c963a6f9bf -->

```Python
UserInDB(
    username = user_dict["username"],
    password = user_dict["password"],
    email = user_dict["email"],
    full_name = user_dict["full_name"],
    hashed_password = hashed_password,
)
```
<!-- stay:x0a5nQvJ hash=sha256:eb3626557654 -->

/// warning
<!-- stay:OYulwdcp hash=sha256:98e5a9621bab -->

The supporting additional functions `fake_password_hasher` and `fake_save_user` are just to demo a possible flow of the data, but they of course are not providing any real security.
<!-- stay:XX8kNuFi hash=sha256:441419e7342d -->

///
<!-- stay:kkvCsMzP hash=sha256:732c4e971163 -->

## Reduce duplication { #reduce-duplication }
<!-- stay:LQohpCDP hash=sha256:1954143103ee -->

Reducing code duplication is one of the core ideas in **FastAPI**.
<!-- stay:JyNfujWP hash=sha256:a03361c5ec69 -->

As code duplication increases the chances of bugs, security issues, code desynchronization issues (when you update in one place but not in the others), etc.
<!-- stay:bmMOBfa8 hash=sha256:60e2da1c31d2 -->

And these models are all sharing a lot of the data and duplicating attribute names and types.
<!-- stay:Ah4w2lq3 hash=sha256:2f9741992aff -->

We could do better.
<!-- stay:OdTjR486 hash=sha256:02b9ee5e7e68 -->

We can declare a `UserBase` model that serves as a base for our other models. And then we can make subclasses of that model that inherit its attributes (type declarations, validation, etc).
<!-- stay:EMFoxHKb hash=sha256:3c09617af9d1 -->

All the data conversion, validation, documentation, etc. will still work as normally.
<!-- stay:aNwavPMr hash=sha256:4152c83fce98 -->

That way, we can declare just the differences between the models (with plaintext `password`, with `hashed_password` and without password):
<!-- stay:ATijbxuk hash=sha256:11fed64cf618 -->

{* ../../docs_src/extra_models/tutorial002_py310.py hl[7,13:14,17:18,21:22] *}
<!-- stay:VZDTdTql hash=sha256:a2d5b30eca0b -->

## `Union` or `anyOf` { #union-or-anyof }
<!-- stay:GCax3hur hash=sha256:ba640c460a52 -->

You can declare a response to be the `Union` of two or more types, that means, that the response would be any of them.
<!-- stay:IUPh7NwM hash=sha256:8e2210161238 -->

It will be defined in OpenAPI with `anyOf`.
<!-- stay:KVtF3SsG hash=sha256:eb322766a04b -->

To do that, use the standard Python type hint [`typing.Union`](https://docs.python.org/3/library/typing.html#typing.Union):
<!-- stay:GXjt4twR hash=sha256:f1f0107414a3 -->

/// note
<!-- stay:FutxUpNt hash=sha256:35f4d438b538 -->

When defining a [`Union`](https://docs.pydantic.dev/latest/concepts/types/#unions), include the most specific type first, followed by the less specific type. In the example below, the more specific `PlaneItem` comes before `CarItem` in `Union[PlaneItem, CarItem]`.
<!-- stay:fCNHoudJ hash=sha256:d7dca75e3415 -->

///
<!-- stay:I0Om07SI hash=sha256:732c4e971163 -->

{* ../../docs_src/extra_models/tutorial003_py310.py hl[1,14:15,18:20,33] *}
<!-- stay:a7WaAuXL hash=sha256:7bb8bf65b50f -->

### `Union` in Python 3.10 { #union-in-python-3-10 }
<!-- stay:vvM0lAfm hash=sha256:50e928a95019 -->

In this example we pass `Union[PlaneItem, CarItem]` as the value of the argument `response_model`.
<!-- stay:sNv2G85J hash=sha256:69e0ef396767 -->

Because we are passing it as a **value to an argument** instead of putting it in a **type annotation**, we have to use `Union` even in Python 3.10.
<!-- stay:TKrIZLXO hash=sha256:81c7e20963ef -->

If it was in a type annotation we could have used the vertical bar, as:
<!-- stay:gzidTCZT hash=sha256:44713ab70928 -->

```Python
some_variable: PlaneItem | CarItem
```
<!-- stay:CnEHEVJB hash=sha256:453e59db9bda -->

But if we put that in the assignment `response_model=PlaneItem | CarItem` we would get an error, because Python would try to perform an **invalid operation** between `PlaneItem` and `CarItem` instead of interpreting that as a type annotation.
<!-- stay:heE8x7Q1 hash=sha256:95e4cf942d46 -->

## List of models { #list-of-models }
<!-- stay:ImTpVgaP hash=sha256:7e920f966bcd -->

The same way, you can declare responses of lists of objects.
<!-- stay:8rTkfFiB hash=sha256:1f70b321c81c -->

For that, use the standard Python `list`:
<!-- stay:nkwScJuh hash=sha256:7e05df727532 -->

{* ../../docs_src/extra_models/tutorial004_py310.py hl[18] *}
<!-- stay:lvGy4ARk hash=sha256:53646a344077 -->

## Response with arbitrary `dict` { #response-with-arbitrary-dict }
<!-- stay:hxvMysMC hash=sha256:b734ca0a4320 -->

You can also declare a response using a plain arbitrary `dict`, declaring just the type of the keys and values, without using a Pydantic model.
<!-- stay:R04zR5J9 hash=sha256:64d2497ed7ca -->

This is useful if you don't know the valid field/attribute names (that would be needed for a Pydantic model) beforehand.
<!-- stay:RHjc2USn hash=sha256:ce444b370b1c -->

In this case, you can use `dict`:
<!-- stay:0ufUdBbB hash=sha256:7f1ce854050f -->

{* ../../docs_src/extra_models/tutorial005_py310.py hl[6] *}
<!-- stay:ixB0SlO3 hash=sha256:1479e7ca0443 -->

## Recap { #recap }
<!-- stay:zo8NC4yp hash=sha256:40a194d2a8b0 -->

Use multiple Pydantic models and inherit freely for each case.
<!-- stay:Ar2jIUBD hash=sha256:38e8572aa36b -->

You don't need to have a single data model per entity if that entity must be able to have different "states". The **user** "entity" is an example, with states that include `password`, `password_hash`, or no password.
<!-- stay:aYqZYtMN hash=sha256:15fe349083d6 -->
