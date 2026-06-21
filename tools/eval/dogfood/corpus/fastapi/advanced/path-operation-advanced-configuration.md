# Path Operation Advanced Configuration { #path-operation-advanced-configuration }
<!-- stay:K4o0m0nD hash=sha256:2c93b177c75e -->

## OpenAPI operationId { #openapi-operationid }
<!-- stay:eNcj244e hash=sha256:af7976ee6b3c -->

/// warning
<!-- stay:eKjaVbDs hash=sha256:98e5a9621bab -->

If you are not an "expert" in OpenAPI, you probably don't need this.
<!-- stay:KoxPr1bl hash=sha256:fd3e3b9d6b60 -->

///
<!-- stay:zmI2X6gf hash=sha256:732c4e971163 -->

You can set the OpenAPI `operationId` to be used in your *path operation* with the parameter `operation_id`.
<!-- stay:jH27MW8L hash=sha256:f2f7c1cfd723 -->

You would have to make sure that it is unique for each operation.
<!-- stay:sF8F3JI4 hash=sha256:169542ee0411 -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial001_py310.py hl[6] *}
<!-- stay:tiOyE1Qm hash=sha256:c614e3ac9046 -->

### Using the *path operation function* name as the operationId { #using-the-path-operation-function-name-as-the-operationid }
<!-- stay:Es2Zb1ca hash=sha256:082cc47ae4f2 -->

If you want to use your APIs' function names as `operationId`s, you can pass a custom `generate_unique_id_function` to `FastAPI`.
<!-- stay:OC5leLgh hash=sha256:3b9c69261341 -->

The function receives each `APIRoute` and returns the `operationId` to use for that path operation.
<!-- stay:v6xsjkoE hash=sha256:f896fc6f8fde -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial002_py310.py hl[2,5:6,9] *}
<!-- stay:3i9LxDx5 hash=sha256:b8a26b56b888 -->

/// warning
<!-- stay:eqeuYQez hash=sha256:98e5a9621bab -->

If you do this, you have to make sure each one of your *path operation functions* has a unique name.
<!-- stay:siDqocUi hash=sha256:cb174781f7d4 -->

Even if they are in different modules (Python files).
<!-- stay:TzwMqdYG hash=sha256:6699c5dbd9bf -->

///
<!-- stay:YkXWq2Tm hash=sha256:732c4e971163 -->

## Exclude from OpenAPI { #exclude-from-openapi }
<!-- stay:ePcFyfID hash=sha256:da07741e81cf -->

To exclude a *path operation* from the generated OpenAPI schema (and thus, from the automatic documentation systems), use the parameter `include_in_schema` and set it to `False`:
<!-- stay:oADihLsK hash=sha256:6642e2a66f26 -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial003_py310.py hl[6] *}
<!-- stay:xO1D8bdi hash=sha256:d426da4c4461 -->

## Advanced description from docstring { #advanced-description-from-docstring }
<!-- stay:Km9RtQZ5 hash=sha256:22406a8bff23 -->

You can limit the lines used from the docstring of a *path operation function* for OpenAPI.
<!-- stay:K5pZNmLn hash=sha256:3e9aa125f558 -->

Adding an `\f` (an escaped "form feed" character) causes **FastAPI** to truncate the output used for OpenAPI at this point.
<!-- stay:CsaeyXHn hash=sha256:c2cce7166c44 -->

It won't show up in the documentation, but other tools (such as Sphinx) will be able to use the rest.
<!-- stay:7xImauqq hash=sha256:bf9490fd8b19 -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial004_py310.py hl[17:27] *}
<!-- stay:DGmGAF5U hash=sha256:e37f17fed7be -->

## Additional Responses { #additional-responses }
<!-- stay:XC3xHs8G hash=sha256:d125245f764f -->

You probably have seen how to declare the `response_model` and `status_code` for a *path operation*.
<!-- stay:7jtwnhTD hash=sha256:8ef6781d33dc -->

That defines the metadata about the main response of a *path operation*.
<!-- stay:5ourqp5X hash=sha256:fcc6f7c6d4c7 -->

You can also declare additional responses with their models, status codes, etc.
<!-- stay:7nWsRGjh hash=sha256:0031d78a1a18 -->

There's a whole chapter here in the documentation about it, you can read it at [Additional Responses in OpenAPI](additional-responses.md).
<!-- stay:Wy7FwWTr hash=sha256:d5410efb1afd -->

## OpenAPI Extra { #openapi-extra }
<!-- stay:OLDZQUM1 hash=sha256:93a7bebb97e5 -->

When you declare a *path operation* in your application, **FastAPI** automatically generates the relevant metadata about that *path operation* to be included in the OpenAPI schema.
<!-- stay:CIXUwWMf hash=sha256:3ad7ad5687c9 -->

/// note | Technical details
<!-- stay:h5MnvCzU hash=sha256:f59f48b7c140 -->

In the OpenAPI specification it is called the [Operation Object](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#operation-object).
<!-- stay:QE2fycsO hash=sha256:4dad70782e29 -->

///
<!-- stay:FkBT5X5s hash=sha256:732c4e971163 -->

It has all the information about the *path operation* and is used to generate the automatic documentation.
<!-- stay:EhlFUuAP hash=sha256:89b86761414f -->

It includes the `tags`, `parameters`, `requestBody`, `responses`, etc.
<!-- stay:pMbtyku2 hash=sha256:23eb25678651 -->

This *path operation*-specific OpenAPI schema is normally generated automatically by **FastAPI**, but you can also extend it.
<!-- stay:e9y7jEem hash=sha256:bf004825374a -->

/// tip
<!-- stay:jLn4ZiwS hash=sha256:35fc886a93b5 -->

This is a low level extension point.
<!-- stay:ZnR2ODjO hash=sha256:1f6c2115b61d -->

If you only need to declare additional responses, a more convenient way to do it is with [Additional Responses in OpenAPI](additional-responses.md).
<!-- stay:7IGdIvKc hash=sha256:60c82aa6ed41 -->

///
<!-- stay:pSomZUhV hash=sha256:732c4e971163 -->

You can extend the OpenAPI schema for a *path operation* using the parameter `openapi_extra`.
<!-- stay:IxFukty3 hash=sha256:1324ce4da1e6 -->

### OpenAPI Extensions { #openapi-extensions }
<!-- stay:eax8oqp7 hash=sha256:be9bc9c1dffd -->

This `openapi_extra` can be helpful, for example, to declare [OpenAPI Extensions](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#specificationExtensions):
<!-- stay:xREIyJWq hash=sha256:d116613f4417 -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial005_py310.py hl[6] *}
<!-- stay:MHWhW9Yc hash=sha256:598f86882763 -->

If you open the automatic API docs, your extension will show up at the bottom of the specific *path operation*.
<!-- stay:WZfQsJlW hash=sha256:b415f5592ad8 -->

<img src="/img/tutorial/path-operation-advanced-configuration/image01.png">
<!-- stay:0LeRwzZL hash=sha256:263f6d52230f -->

And if you see the resulting OpenAPI (at `/openapi.json` in your API), you will see your extension as part of the specific *path operation* too:
<!-- stay:ZUic6YUh hash=sha256:a5192e4588d0 -->

```JSON hl_lines="22"
{
    "openapi": "3.1.0",
    "info": {
        "title": "FastAPI",
        "version": "0.1.0"
    },
    "paths": {
        "/items/": {
            "get": {
                "summary": "Read Items",
                "operationId": "read_items_items__get",
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {}
                            }
                        }
                    }
                },
                "x-aperture-labs-portal": "blue"
            }
        }
    }
}
```
<!-- stay:9692GWWT hash=sha256:5141ff15989e -->

### Custom OpenAPI *path operation* schema { #custom-openapi-path-operation-schema }
<!-- stay:K6yt4N36 hash=sha256:93557ee0d36f -->

The dictionary in `openapi_extra` will be deeply merged with the automatically generated OpenAPI schema for the *path operation*.
<!-- stay:3cqbd4eg hash=sha256:f971f642d8f1 -->

So, you could add additional data to the automatically generated schema.
<!-- stay:cLpW7q3u hash=sha256:c50e68884951 -->

For example, you could decide to read and validate the request with your own code, without using the automatic features of FastAPI with Pydantic, but you could still want to define the request in the OpenAPI schema.
<!-- stay:eRe7GxXi hash=sha256:f1040e09491f -->

You could do that with `openapi_extra`:
<!-- stay:Thjwpum7 hash=sha256:d250669118a3 -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial006_py310.py hl[19:36, 39:40] *}
<!-- stay:en5MDtSs hash=sha256:55ad1711572c -->

In this example, we didn't declare any Pydantic model. In fact, the request body is not even <dfn title="converted from some plain format, like bytes, into Python objects">parsed</dfn> as JSON, it is read directly as `bytes`, and the function `magic_data_reader()` would be in charge of parsing it in some way.
<!-- stay:33aJiQx4 hash=sha256:416a9111c488 -->

Nevertheless, we can declare the expected schema for the request body.
<!-- stay:JC26SiJ7 hash=sha256:a28c872f3adc -->

### Custom OpenAPI content type { #custom-openapi-content-type }
<!-- stay:8PI3rMxF hash=sha256:c637b4f930dc -->

Using this same trick, you could use a Pydantic model to define the JSON Schema that is then included in the custom OpenAPI schema section for the *path operation*.
<!-- stay:paT0CGL9 hash=sha256:fd49a8f87007 -->

And you could do this even if the data type in the request is not JSON.
<!-- stay:ZDUo60YX hash=sha256:76b41ed45229 -->

For example, in this application we don't use FastAPI's integrated functionality to extract the JSON Schema from Pydantic models nor the automatic validation for JSON. In fact, we are declaring the request content type as YAML, not JSON:
<!-- stay:BzYdzmtP hash=sha256:d136b9b19f8d -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial007_py310.py hl[15:20, 22] *}
<!-- stay:z0JwgueS hash=sha256:1fb1f30fa37c -->

Nevertheless, although we are not using the default integrated functionality, we are still using a Pydantic model to manually generate the JSON Schema for the data that we want to receive in YAML.
<!-- stay:2TNzDeY0 hash=sha256:a2346791fabb -->

Then we use the request directly, and extract the body as `bytes`. This means that FastAPI won't even try to parse the request payload as JSON.
<!-- stay:G7YLQ1FF hash=sha256:d05b6cc73874 -->

And then in our code, we parse that YAML content directly, and then we are again using the same Pydantic model to validate the YAML content:
<!-- stay:l4utH3RW hash=sha256:f8d46756b32e -->

{* ../../docs_src/path_operation_advanced_configuration/tutorial007_py310.py hl[24:31] *}
<!-- stay:c1c8qwDg hash=sha256:c59a8eb3206c -->

/// tip
<!-- stay:JAgHKCGZ hash=sha256:35fc886a93b5 -->

Here we reuse the same Pydantic model.
<!-- stay:qYK0hRRu hash=sha256:0dd36c14d496 -->

But the same way, we could have validated it in some other way.
<!-- stay:Z5iSVInJ hash=sha256:4c01f5b533c0 -->

///
<!-- stay:bTy1wbJC hash=sha256:732c4e971163 -->
