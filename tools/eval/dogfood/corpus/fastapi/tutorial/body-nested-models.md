# Body - Nested Models { #body-nested-models }
<!-- stay:SdKdVrsy hash=sha256:10f2ee573113 -->

With **FastAPI**, you can define, validate, document, and use arbitrarily deeply nested models (thanks to Pydantic).
<!-- stay:PFbaw6m7 hash=sha256:20ddb2fd9fcf -->

## List fields { #list-fields }
<!-- stay:9gnfrnnm hash=sha256:243e3a40f78d -->

You can define an attribute to be a subtype. For example, a Python `list`:
<!-- stay:Zm0ouWoP hash=sha256:66e2ed6d5018 -->

{* ../../docs_src/body_nested_models/tutorial001_py310.py hl[12] *}
<!-- stay:DoulJ3Ks hash=sha256:2507a5dc47b2 -->

This will make `tags` be a list, although it doesn't declare the type of the elements of the list.
<!-- stay:FMCa54iu hash=sha256:9d6af6b29723 -->

## List fields with type parameter { #list-fields-with-type-parameter }
<!-- stay:9xTomtgt hash=sha256:7d134b55d660 -->

But Python has a specific way to declare lists with internal types, or "type parameters":
<!-- stay:LEJZcxNl hash=sha256:f919205452b4 -->

### Declare a `list` with a type parameter { #declare-a-list-with-a-type-parameter }
<!-- stay:QxbhfaIe hash=sha256:64fbbe5ed5be -->

To declare types that have type parameters (internal types), like `list`, `dict`, `tuple`,
pass the internal type(s) as "type parameters" using square brackets: `[` and `]`
<!-- stay:rG2MEd10 hash=sha256:1974fee31476 -->

```Python
my_list: list[str]
```
<!-- stay:LBdx09KG hash=sha256:a014de3aa024 -->

That's all standard Python syntax for type declarations.
<!-- stay:JNPsBA2z hash=sha256:4c6b1119b24d -->

Use that same standard syntax for model attributes with internal types.
<!-- stay:h6ZXNTkz hash=sha256:148aaebd31b0 -->

So, in our example, we can make `tags` be specifically a "list of strings":
<!-- stay:r0jsjVdL hash=sha256:4cc96f4462d3 -->

{* ../../docs_src/body_nested_models/tutorial002_py310.py hl[12] *}
<!-- stay:BuVa0p4T hash=sha256:5a20107c4977 -->

## Set types { #set-types }
<!-- stay:tbzoAWLG hash=sha256:d38e8620a2fb -->

But then we think about it, and realize that tags shouldn't repeat, they would probably be unique strings.
<!-- stay:zu3aTMqv hash=sha256:6f3cfc212b74 -->

And Python has a special data type for sets of unique items, the `set`.
<!-- stay:d41bKCSx hash=sha256:09450ecaea52 -->

Then we can declare `tags` as a set of strings:
<!-- stay:H00m9gMm hash=sha256:3beae77019ea -->

{* ../../docs_src/body_nested_models/tutorial003_py310.py hl[12] *}
<!-- stay:Zss52fSU hash=sha256:f21c2561f258 -->

With this, even if you receive a request with duplicate data, it will be converted to a set of unique items.
<!-- stay:DmKIZSXd hash=sha256:8c3d5acb82cd -->

And whenever you output that data, even if the source had duplicates, it will be output as a set of unique items.
<!-- stay:frbnYWmf hash=sha256:12db7a9b1f78 -->

And it will be annotated / documented accordingly too.
<!-- stay:vKZKdOvn hash=sha256:09d8af74d680 -->

## Nested Models { #nested-models }
<!-- stay:qclxK24H hash=sha256:b39910fb8999 -->

Each attribute of a Pydantic model has a type.
<!-- stay:N3c2OrhI hash=sha256:f24738dcad94 -->

But that type can itself be another Pydantic model.
<!-- stay:zkC1b6j3 hash=sha256:0650e52587c5 -->

So, you can declare deeply nested JSON "objects" with specific attribute names, types and validations.
<!-- stay:6Gi4Fayi hash=sha256:eb282c3a990e -->

All that, arbitrarily nested.
<!-- stay:43fSlXUi hash=sha256:6f9d320fa3d4 -->

### Define a submodel { #define-a-submodel }
<!-- stay:BeRxxzii hash=sha256:31e269b12932 -->

For example, we can define an `Image` model:
<!-- stay:IAESKAG6 hash=sha256:72c9cc49bc83 -->

{* ../../docs_src/body_nested_models/tutorial004_py310.py hl[7:9] *}
<!-- stay:TtrVUEYe hash=sha256:e4a0b600a81e -->

### Use the submodel as a type { #use-the-submodel-as-a-type }
<!-- stay:R8qOGvUM hash=sha256:f6fab453d626 -->

And then we can use it as the type of an attribute:
<!-- stay:FrvJ44E3 hash=sha256:2f6ec9796eb1 -->

{* ../../docs_src/body_nested_models/tutorial004_py310.py hl[18] *}
<!-- stay:Aw1qNQN9 hash=sha256:5a8568224c21 -->

This would mean that **FastAPI** would expect a body similar to:
<!-- stay:w78mid4b hash=sha256:b9263092a578 -->

```JSON
{
    "name": "Foo",
    "description": "The pretender",
    "price": 42.0,
    "tax": 3.2,
    "tags": ["rock", "metal", "bar"],
    "image": {
        "url": "http://example.com/baz.jpg",
        "name": "The Foo live"
    }
}
```
<!-- stay:915TQBc1 hash=sha256:e73c28a6191c -->

Again, doing just that declaration, with **FastAPI** you get:
<!-- stay:n8eDa1ha hash=sha256:ff4fa5f472af -->

* Editor support (completion, etc.), even for nested models
* Data conversion
* Data validation
* Automatic documentation
<!-- stay:zEaSlvKM hash=sha256:2d0ce3e2fa36 -->

## Special types and validation { #special-types-and-validation }
<!-- stay:DJkLuaYV hash=sha256:f5e59ec084c7 -->

Apart from normal singular types like `str`, `int`, `float`, etc. you can use more complex singular types that inherit from `str`.
<!-- stay:emlc5rKw hash=sha256:f909b99031e1 -->

To see all the options you have, check out [Pydantic's Type Overview](https://docs.pydantic.dev/latest/concepts/types/). You will see some examples in the next chapter.
<!-- stay:IIV50E66 hash=sha256:d41c5b7b96fa -->

For example, as in the `Image` model we have a `url` field, we can declare it to be an instance of Pydantic's `HttpUrl` instead of a `str`:
<!-- stay:s48dBqYi hash=sha256:be31487c9359 -->

{* ../../docs_src/body_nested_models/tutorial005_py310.py hl[2,8] *}
<!-- stay:rA2XJilE hash=sha256:9ee6e934a2ed -->

The string will be checked to be a valid URL, and documented in JSON Schema / OpenAPI as such.
<!-- stay:2fu1vWMv hash=sha256:eb7cd07f6602 -->

## Attributes with lists of submodels { #attributes-with-lists-of-submodels }
<!-- stay:7wMxqMNQ hash=sha256:a3a0dd216d99 -->

You can also use Pydantic models as subtypes of `list`, `set`, etc.:
<!-- stay:Vvm2eSDN hash=sha256:3d58aa2921a8 -->

{* ../../docs_src/body_nested_models/tutorial006_py310.py hl[18] *}
<!-- stay:ID64Geav hash=sha256:b1268a30faa7 -->

This will expect (convert, validate, document, etc.) a JSON body like:
<!-- stay:aCUqOyer hash=sha256:f498052b546e -->

```JSON hl_lines="11"
{
    "name": "Foo",
    "description": "The pretender",
    "price": 42.0,
    "tax": 3.2,
    "tags": [
        "rock",
        "metal",
        "bar"
    ],
    "images": [
        {
            "url": "http://example.com/baz.jpg",
            "name": "The Foo live"
        },
        {
            "url": "http://example.com/dave.jpg",
            "name": "The Baz"
        }
    ]
}
```
<!-- stay:43HuGZf7 hash=sha256:e91f3fdfc468 -->

/// note
<!-- stay:U6h0NIUC hash=sha256:35f4d438b538 -->

Notice how the `images` key now has a list of image objects.
<!-- stay:pfo7wOq1 hash=sha256:7e990794ff02 -->

///
<!-- stay:cmRMCPa2 hash=sha256:732c4e971163 -->

## Deeply nested models { #deeply-nested-models }
<!-- stay:25I37oBR hash=sha256:9bc802353e02 -->

You can define arbitrarily deeply nested models:
<!-- stay:Wc4D5Xeg hash=sha256:59deb9682620 -->

{* ../../docs_src/body_nested_models/tutorial007_py310.py hl[7,12,18,21,25] *}
<!-- stay:2PwmxizA hash=sha256:2ab20418fd0f -->

/// note
<!-- stay:eH5pNRW7 hash=sha256:35f4d438b538 -->

Notice how `Offer` has a list of `Item`s, which in turn have an optional list of `Image`s
<!-- stay:oPgsqJiD hash=sha256:0e6720e87154 -->

///
<!-- stay:ZvpysIYU hash=sha256:732c4e971163 -->

## Bodies of pure lists { #bodies-of-pure-lists }
<!-- stay:i6QGn0Sw hash=sha256:b9bd1c377f07 -->

If the top level value of the JSON body you expect is a JSON `array` (a Python `list`), you can declare the type in the parameter of the function, the same as in Pydantic models:
<!-- stay:CC7RqWah hash=sha256:b4b06af44012 -->

```Python
images: list[Image]
```
<!-- stay:mWUod5B9 hash=sha256:3c19f6384298 -->

as in:
<!-- stay:n0TaGRBv hash=sha256:37f601544e56 -->

{* ../../docs_src/body_nested_models/tutorial008_py310.py hl[13] *}
<!-- stay:Si5HouQD hash=sha256:c3af77bc255a -->

## Editor support everywhere { #editor-support-everywhere }
<!-- stay:yP2YI3T7 hash=sha256:c9ca3d247299 -->

And you get editor support everywhere.
<!-- stay:eCttE4vF hash=sha256:c7752519d94a -->

Even for items inside of lists:
<!-- stay:dsUe4x8f hash=sha256:7c1b54976d1d -->

<img src="/img/tutorial/body-nested-models/image01.png">
<!-- stay:JlqwA2GV hash=sha256:8a75f6957027 -->

You couldn't get this kind of editor support if you were working directly with `dict` instead of Pydantic models.
<!-- stay:DprkteVY hash=sha256:06b482587277 -->

But you don't have to worry about them either, incoming dicts are converted automatically and your output is converted automatically to JSON too.
<!-- stay:ZYUevnoH hash=sha256:3ac3a943e693 -->

## Bodies of arbitrary `dict`s { #bodies-of-arbitrary-dicts }
<!-- stay:7ZJiX2EJ hash=sha256:834d2170a2aa -->

You can also declare a body as a `dict` with keys of some type and values of some other type.
<!-- stay:h6sGtxNQ hash=sha256:6a598dac3692 -->

This way, you don't have to know beforehand what the valid field/attribute names are (as would be the case with Pydantic models).
<!-- stay:sWx5MjnX hash=sha256:a933207a3c1b -->

This would be useful if you want to receive keys that you don't already know.
<!-- stay:PiBK54no hash=sha256:a0b87d04b2c7 -->

---
<!-- stay:S0QaXH4b hash=sha256:cb3f91d54eee -->

Another useful case is when you want to have keys of another type (e.g., `int`).
<!-- stay:zre8ZeLz hash=sha256:fbe0fde42144 -->

That's what we are going to see here.
<!-- stay:vnf8JyKe hash=sha256:0e3a0cbd163c -->

In this case, you would accept any `dict` as long as it has `int` keys with `float` values:
<!-- stay:b4fdJW9o hash=sha256:84daae49ee55 -->

{* ../../docs_src/body_nested_models/tutorial009_py310.py hl[7] *}
<!-- stay:Iqe5rOYF hash=sha256:6c3de90fc183 -->

/// tip
<!-- stay:6Mj5W6oT hash=sha256:35fc886a93b5 -->

Keep in mind that JSON only supports `str` as keys.
<!-- stay:7vKXz3af hash=sha256:17698760922e -->

But Pydantic has automatic data conversion.
<!-- stay:M2kYJtm3 hash=sha256:b512a081fe4d -->

This means that, even though your API clients can only send strings as keys, as long as those strings contain pure integers, Pydantic will convert them and validate them.
<!-- stay:piETzeEU hash=sha256:aef29acaa4bb -->

And the `dict` you receive as `weights` will actually have `int` keys and `float` values.
<!-- stay:S2wEoEou hash=sha256:b8cfc026db17 -->

///
<!-- stay:EusaNJzx hash=sha256:732c4e971163 -->

## Recap { #recap }
<!-- stay:yZXA3zEX hash=sha256:40a194d2a8b0 -->

With **FastAPI** you have the maximum flexibility provided by Pydantic models, while keeping your code simple, short and elegant.
<!-- stay:SqQHG1cb hash=sha256:02f6e332e092 -->

But with all the benefits:
<!-- stay:EmfuvNH1 hash=sha256:d11c57f9e2d4 -->

* Editor support (completion everywhere!)
* Data conversion (a.k.a. parsing / serialization)
* Data validation
* Schema documentation
* Automatic docs
<!-- stay:TurlTahE hash=sha256:b03f810ad92d -->
