# Request Body { #request-body }
<!-- stay:p2cqHDPS hash=sha256:c5366253bcd5 -->

When you need to send data from a client (let's say, a browser) to your API, you send it as a **request body**.
<!-- stay:mudqHK2o hash=sha256:f0d0cd410bef -->

A **request** body is data sent by the client to your API. A **response** body is the data your API sends to the client.
<!-- stay:uOgOApMO hash=sha256:5a40653f0c74 -->

Your API almost always has to send a **response** body. But clients don't necessarily need to send **request bodies** all the time, sometimes they only request a path, maybe with some query parameters, but don't send a body.
<!-- stay:V9RpXsrq hash=sha256:fb66eb0319b4 -->

To declare a **request** body, you use [Pydantic](https://docs.pydantic.dev/) models with all their power and benefits.
<!-- stay:1vWzS3jX hash=sha256:c8d486c36936 -->

/// note
<!-- stay:7Z2Riugc hash=sha256:35f4d438b538 -->

To send data, you should use one of: `POST` (the most common), `PUT`, `DELETE` or `PATCH`.
<!-- stay:rWZ6fgFb hash=sha256:0cdbec468597 -->

Sending a body with a `GET` request has an undefined behavior in the specifications, nevertheless, it is supported by FastAPI, only for very complex/extreme use cases.
<!-- stay:BCBES8pD hash=sha256:a0298aa06c9d -->

As it is discouraged, the interactive docs with Swagger UI won't show the documentation for the body when using `GET`, and proxies in the middle might not support it.
<!-- stay:6J4PcZlc hash=sha256:add413fd7fd9 -->

///
<!-- stay:DWxbyDKB hash=sha256:732c4e971163 -->

## Import Pydantic's `BaseModel` { #import-pydantics-basemodel }
<!-- stay:xG0YebQP hash=sha256:4ff348860bca -->

First, you need to import `BaseModel` from `pydantic`:
<!-- stay:t9jIAyac hash=sha256:51b9804e836c -->

{* ../../docs_src/body/tutorial001_py310.py hl[2] *}
<!-- stay:b6DZEWfx hash=sha256:73753f2f6b2b -->

## Create your data model { #create-your-data-model }
<!-- stay:7Dxz3zuK hash=sha256:efdf949f1250 -->

Then you declare your data model as a class that inherits from `BaseModel`.
<!-- stay:IqiLEsQT hash=sha256:868aee11eb43 -->

Use standard Python types for all the attributes:
<!-- stay:cvNOQX1o hash=sha256:fa117583effa -->

{* ../../docs_src/body/tutorial001_py310.py hl[5:9] *}
<!-- stay:1TNpMdZd hash=sha256:84b74adc1084 -->


The same as when declaring query parameters, when a model attribute has a default value, it is not required. Otherwise, it is required. Use `None` to make it just optional.
<!-- stay:dhdaNZZn hash=sha256:a49f66f9af45 -->

For example, this model above declares a JSON "`object`" (or Python `dict`) like:
<!-- stay:FCcO55Oe hash=sha256:3c61fb4a05dd -->

```JSON
{
    "name": "Foo",
    "description": "An optional description",
    "price": 45.2,
    "tax": 3.5
}
```
<!-- stay:zGtLHNki hash=sha256:6e13909a236c -->

...as `description` and `tax` are optional (with a default value of `None`), this JSON "`object`" would also be valid:
<!-- stay:HYLyhgnx hash=sha256:e53021699095 -->

```JSON
{
    "name": "Foo",
    "price": 45.2
}
```
<!-- stay:bN3rCIjx hash=sha256:cf5d4f17759e -->

## Declare it as a parameter { #declare-it-as-a-parameter }
<!-- stay:gSiPiM2d hash=sha256:5fcd3d356387 -->

To add it to your *path operation*, declare it the same way you declared path and query parameters:
<!-- stay:IRlzkNAp hash=sha256:467fb870ab61 -->

{* ../../docs_src/body/tutorial001_py310.py hl[16] *}
<!-- stay:A1bQKY4X hash=sha256:3d8e9c42a2a7 -->

...and declare its type as the model you created, `Item`.
<!-- stay:HRkvGpAv hash=sha256:aa4bc80d732f -->

## Results { #results }
<!-- stay:EhYnukNO hash=sha256:15583c668389 -->

With just that Python type declaration, **FastAPI** will:
<!-- stay:o4rBiY7d hash=sha256:4752c6e6f62c -->

* Read the body of the request as JSON.
* Convert the corresponding types (if needed).
* Validate the data.
    * If the data is invalid, it will return a nice and clear error, indicating exactly where and what was the incorrect data.
* Give you the received data in the parameter `item`.
    * As you declared it in the function to be of type `Item`, you will also have all the editor support (completion, etc) for all of the attributes and their types.
* Generate [JSON Schema](https://json-schema.org) definitions for your model, you can also use them anywhere else you like if it makes sense for your project.
* Those schemas will be part of the generated OpenAPI schema, and used by the automatic documentation <abbr title="User Interfaces">UIs</abbr>.
<!-- stay:n3eWShiY hash=sha256:edb41e7a41fb -->

## Automatic docs { #automatic-docs }
<!-- stay:xtKDiIaP hash=sha256:4464ded84748 -->

The JSON Schemas of your models will be part of your OpenAPI generated schema, and will be shown in the interactive API docs:
<!-- stay:pdkhyHQg hash=sha256:790a9b453ea5 -->

<img src="/img/tutorial/body/image01.png">
<!-- stay:WrMs61Ca hash=sha256:00cc10c675b5 -->

And will also be used in the API docs inside each *path operation* that needs them:
<!-- stay:22jgQ7Fm hash=sha256:62cec07c1a9c -->

<img src="/img/tutorial/body/image02.png">
<!-- stay:5GH09N2B hash=sha256:06a2cee8e3d8 -->

## Editor support { #editor-support }
<!-- stay:3f0WojHc hash=sha256:ed73cdd30c43 -->

In your editor, inside your function you will get type hints and completion everywhere (this wouldn't happen if you received a `dict` instead of a Pydantic model):
<!-- stay:m5ZwBBV3 hash=sha256:f70605968f11 -->

<img src="/img/tutorial/body/image03.png">
<!-- stay:bxSi9Lb7 hash=sha256:d70c8361c2d7 -->

You also get error checks for incorrect type operations:
<!-- stay:RTYgSS6g hash=sha256:f9fb4ce5f2e4 -->

<img src="/img/tutorial/body/image04.png">
<!-- stay:WTrkR0Cq hash=sha256:17bdf90f733d -->

This is not by chance, the whole framework was built around that design.
<!-- stay:fKqxG82R hash=sha256:31008f8cfa67 -->

And it was thoroughly tested at the design phase, before any implementation, to ensure it would work with all the editors.
<!-- stay:cf3QPLDl hash=sha256:8ac66fa12b13 -->

There were even some changes to Pydantic itself to support this.
<!-- stay:ALZFS08Y hash=sha256:e43326b5c466 -->

The previous screenshots were taken with [Visual Studio Code](https://code.visualstudio.com).
<!-- stay:FJyJByD2 hash=sha256:2105c7285484 -->

But you would get the same editor support with [PyCharm](https://www.jetbrains.com/pycharm/) and most of the other Python editors:
<!-- stay:1mW5Q5HL hash=sha256:17de9db6228c -->

<img src="/img/tutorial/body/image05.png">
<!-- stay:YfWkNr6F hash=sha256:20f966cc7ca4 -->

/// tip
<!-- stay:0ZrDLBjH hash=sha256:35fc886a93b5 -->

If you use [PyCharm](https://www.jetbrains.com/pycharm/) as your editor, you can use the [Pydantic PyCharm Plugin](https://github.com/koxudaxi/pydantic-pycharm-plugin/).
<!-- stay:Sj0LUwHj hash=sha256:26660e98c18f -->

It improves editor support for Pydantic models, with:
<!-- stay:E8QAxKUC hash=sha256:7e1100eaee15 -->

* auto-completion
* type checks
* refactoring
* searching
* inspections
<!-- stay:omZV5ErF hash=sha256:84002c285e3c -->

///
<!-- stay:OCfApQlv hash=sha256:732c4e971163 -->

## Use the model { #use-the-model }
<!-- stay:Npxk5C92 hash=sha256:7d2dac5e11de -->

Inside of the function, you can access all the attributes of the model object directly:
<!-- stay:sgZMmUUp hash=sha256:740e649c5a0c -->

{* ../../docs_src/body/tutorial002_py310.py *}
<!-- stay:bEeOsSML hash=sha256:4d032f437093 -->

## Request body + path parameters { #request-body-path-parameters }
<!-- stay:OxWUUKrb hash=sha256:84da690a31f4 -->

You can declare path parameters and request body at the same time.
<!-- stay:Ic4XqDos hash=sha256:21fea9e89671 -->

**FastAPI** will recognize that the function parameters that match path parameters should be **taken from the path**, and that function parameters that are declared to be Pydantic models should be **taken from the request body**.
<!-- stay:FC8M0Qb8 hash=sha256:3e9ce9cf7328 -->

{* ../../docs_src/body/tutorial003_py310.py hl[15:16] *}
<!-- stay:o0RHSVRx hash=sha256:14904b93d420 -->


## Request body + path + query parameters { #request-body-path-query-parameters }
<!-- stay:JjhLm9Z6 hash=sha256:377f41a8ad80 -->

You can also declare **body**, **path** and **query** parameters, all at the same time.
<!-- stay:w7Aru0pu hash=sha256:7a011072cd83 -->

**FastAPI** will recognize each of them and take the data from the correct place.
<!-- stay:B4UyGZUs hash=sha256:e15b62c21d9e -->

{* ../../docs_src/body/tutorial004_py310.py hl[16] *}
<!-- stay:ZzMD4X6p hash=sha256:3768a2f2ff36 -->

The function parameters will be recognized as follows:
<!-- stay:puSeoi7n hash=sha256:fd86d2a4c1ca -->

* If the parameter is also declared in the **path**, it will be used as a path parameter.
* If the parameter is of a **singular type** (like `int`, `float`, `str`, `bool`, etc) it will be interpreted as a **query** parameter.
* If the parameter is declared to be of the type of a **Pydantic model**, it will be interpreted as a request **body**.
<!-- stay:eIpNlh1J hash=sha256:00002fac1b04 -->

/// note
<!-- stay:nAV2opTO hash=sha256:35f4d438b538 -->

FastAPI will know that the value of `q` is not required because of the default value `= None`.
<!-- stay:sKsflHib hash=sha256:95ed0ab3502b -->

The `str | None` is not used by FastAPI to determine that the value is not required, it will know it's not required because it has a default value of `= None`.
<!-- stay:buExqGHK hash=sha256:5daf6a30eeec -->

But adding the type annotations will allow your editor to give you better support and detect errors.
<!-- stay:BSAkHtYS hash=sha256:13fc094d0c4b -->

///
<!-- stay:3OwmxkvT hash=sha256:732c4e971163 -->

## Without Pydantic { #without-pydantic }
<!-- stay:oFXtmlyQ hash=sha256:d5602e69039c -->

If you don't want to use Pydantic models, you can also use **Body** parameters. See the docs for [Body - Multiple Parameters: Singular values in body](body-multiple-params.md#singular-values-in-body).
<!-- stay:tqfrMelr hash=sha256:4f1ff78e1d0e -->
