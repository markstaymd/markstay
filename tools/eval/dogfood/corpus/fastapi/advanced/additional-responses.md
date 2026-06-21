# Additional Responses in OpenAPI { #additional-responses-in-openapi }
<!-- stay:vBnjWfG1 hash=sha256:2007a69af6ae -->

/// warning
<!-- stay:IRVH8p6V hash=sha256:98e5a9621bab -->

This is a rather advanced topic.
<!-- stay:sHDrrHKR hash=sha256:b78c40b68412 -->

If you are starting with **FastAPI**, you might not need this.
<!-- stay:8fnzKZAE hash=sha256:9b91c0a9fa7e -->

///
<!-- stay:cSkBIFZg hash=sha256:732c4e971163 -->

You can declare additional responses, with additional status codes, media types, descriptions, etc.
<!-- stay:FAwQrsDz hash=sha256:9a24c8d5a2e4 -->

Those additional responses will be included in the OpenAPI schema, so they will also appear in the API docs.
<!-- stay:CqU4bkR6 hash=sha256:66ef62e2bb07 -->

But for those additional responses you have to make sure you return a `Response` like `JSONResponse` directly, with your status code and content.
<!-- stay:jufpNsi9 hash=sha256:907b03019e4a -->

## Additional Response with `model` { #additional-response-with-model }
<!-- stay:KCtGdLdw hash=sha256:32ea0aebd075 -->

You can pass to your *path operation decorators* a parameter `responses`.
<!-- stay:qSVJI53q hash=sha256:fa8f422b91e1 -->

It receives a `dict`: the keys are status codes for each response (like `200`), and the values are other `dict`s with the information for each of them.
<!-- stay:orZBSsGv hash=sha256:877f38438913 -->

Each of those response `dict`s can have a key `model`, containing a Pydantic model, just like `response_model`.
<!-- stay:vZBQMh9k hash=sha256:c38919d57f2d -->

**FastAPI** will take that model, generate its JSON Schema and include it in the correct place in OpenAPI.
<!-- stay:36FB9VzZ hash=sha256:a1b6323b7c67 -->

For example, to declare another response with a status code `404` and a Pydantic model `Message`, you can write:
<!-- stay:JyhR4c8z hash=sha256:bd911ae4e723 -->

{* ../../docs_src/additional_responses/tutorial001_py310.py hl[18,22] *}
<!-- stay:RTXxxhay hash=sha256:bcc383ba3a36 -->

/// note
<!-- stay:GHdb9qrC hash=sha256:35f4d438b538 -->

Keep in mind that you have to return the `JSONResponse` directly.
<!-- stay:9P4TBhg3 hash=sha256:444d85e35617 -->

///
<!-- stay:bDdqEUvK hash=sha256:732c4e971163 -->

/// note
<!-- stay:Tf8UNhXW hash=sha256:35f4d438b538 -->

The `model` key is not part of OpenAPI.
<!-- stay:UyvVd2wH hash=sha256:1ac718190cd5 -->

**FastAPI** will take the Pydantic model from there, generate the JSON Schema, and put it in the correct place.
<!-- stay:H4FmJ3sb hash=sha256:3539316cb6fa -->

The correct place is:
<!-- stay:o97YsL3I hash=sha256:88263ed6aea2 -->

* In the key `content`, that has as value another JSON object (`dict`) that contains:
    * A key with the media type, e.g. `application/json`, that contains as value another JSON object, that contains:
        * A key `schema`, that has as the value the JSON Schema from the model, here's the correct place.
            * **FastAPI** adds a reference here to the global JSON Schemas in another place in your OpenAPI instead of including it directly. This way, other applications and clients can use those JSON Schemas directly, provide better code generation tools, etc.
<!-- stay:63SeA6jp hash=sha256:f5ea13d5fb9e -->

///
<!-- stay:KItwbnkU hash=sha256:732c4e971163 -->

The generated responses in the OpenAPI for this *path operation* will be:
<!-- stay:05B6noox hash=sha256:beccedec4377 -->

```JSON hl_lines="3-12"
{
    "responses": {
        "404": {
            "description": "Additional Response",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/Message"
                    }
                }
            }
        },
        "200": {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/Item"
                    }
                }
            }
        },
        "422": {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/HTTPValidationError"
                    }
                }
            }
        }
    }
}
```
<!-- stay:Kqb8MIvu hash=sha256:396c44f0270c -->

The schemas are referenced to another place inside the OpenAPI schema:
<!-- stay:Laftwuqy hash=sha256:e436106ca0e5 -->

```JSON hl_lines="4-16"
{
    "components": {
        "schemas": {
            "Message": {
                "title": "Message",
                "required": [
                    "message"
                ],
                "type": "object",
                "properties": {
                    "message": {
                        "title": "Message",
                        "type": "string"
                    }
                }
            },
            "Item": {
                "title": "Item",
                "required": [
                    "id",
                    "value"
                ],
                "type": "object",
                "properties": {
                    "id": {
                        "title": "Id",
                        "type": "string"
                    },
                    "value": {
                        "title": "Value",
                        "type": "string"
                    }
                }
            },
            "ValidationError": {
                "title": "ValidationError",
                "required": [
                    "loc",
                    "msg",
                    "type"
                ],
                "type": "object",
                "properties": {
                    "loc": {
                        "title": "Location",
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "msg": {
                        "title": "Message",
                        "type": "string"
                    },
                    "type": {
                        "title": "Error Type",
                        "type": "string"
                    }
                }
            },
            "HTTPValidationError": {
                "title": "HTTPValidationError",
                "type": "object",
                "properties": {
                    "detail": {
                        "title": "Detail",
                        "type": "array",
                        "items": {
                            "$ref": "#/components/schemas/ValidationError"
                        }
                    }
                }
            }
        }
    }
}
```
<!-- stay:2Dy3PATF hash=sha256:2f48b507db4c -->

## Additional media types for the main response { #additional-media-types-for-the-main-response }
<!-- stay:0skXayZY hash=sha256:6b6063a26983 -->

You can use this same `responses` parameter to add different media types for the same main response.
<!-- stay:tK9NvysL hash=sha256:6a4dd8d33375 -->

For example, you can add an additional media type of `image/png`, declaring that your *path operation* can return a JSON object (with media type `application/json`) or a PNG image:
<!-- stay:Y1B6ewYi hash=sha256:05a0b5870efc -->

{* ../../docs_src/additional_responses/tutorial002_py310.py hl[17:22,26] *}
<!-- stay:F4pbPlpB hash=sha256:360455cf5263 -->

/// note
<!-- stay:RzDecyLZ hash=sha256:35f4d438b538 -->

Notice that you have to return the image using a `FileResponse` directly.
<!-- stay:MhQPN7et hash=sha256:ce622796862e -->

///
<!-- stay:flOOGBak hash=sha256:732c4e971163 -->

/// note
<!-- stay:uPEJJ9pJ hash=sha256:35f4d438b538 -->

Unless you specify a different media type explicitly in your `responses` parameter, FastAPI will assume the response has the same media type as the main response class (default `application/json`).
<!-- stay:A61iYMFm hash=sha256:1cbe23f9d003 -->

But if you have specified a custom response class with `None` as its media type, FastAPI will use `application/json` for any additional response that has an associated model.
<!-- stay:Wd08FEy3 hash=sha256:4c139107526d -->

///
<!-- stay:DuaHtSOL hash=sha256:732c4e971163 -->

## Combining information { #combining-information }
<!-- stay:X9OhtcEz hash=sha256:02bf567111bf -->

You can also combine response information from multiple places, including the `response_model`, `status_code`, and `responses` parameters.
<!-- stay:5eMXMx3o hash=sha256:8d3ec081d2b6 -->

You can declare a `response_model`, using the default status code `200` (or a custom one if you need), and then declare additional information for that same response in `responses`, directly in the OpenAPI schema.
<!-- stay:VUacvufv hash=sha256:45a7b01ea68c -->

**FastAPI** will keep the additional information from `responses`, and combine it with the JSON Schema from your model.
<!-- stay:GNxDuh2r hash=sha256:42100e1c8158 -->

For example, you can declare a response with a status code `404` that uses a Pydantic model and has a custom `description`.
<!-- stay:5cJUb1aK hash=sha256:3b65b725d483 -->

And a response with a status code `200` that uses your `response_model`, but includes a custom `example`:
<!-- stay:Lnh9Z6Hp hash=sha256:876680ae3321 -->

{* ../../docs_src/additional_responses/tutorial003_py310.py hl[20:31] *}
<!-- stay:Lweo6IMs hash=sha256:47d45ae4ded4 -->

It will all be combined and included in your OpenAPI, and shown in the API docs:
<!-- stay:vAA1Udix hash=sha256:72edf6889b4d -->

<img src="/img/tutorial/additional-responses/image01.png">
<!-- stay:baPMVeJM hash=sha256:3b7ae5caae71 -->

## Combine predefined responses and custom ones { #combine-predefined-responses-and-custom-ones }
<!-- stay:USlHrwAZ hash=sha256:594e3d5219ac -->

You might want to have some predefined responses that apply to many *path operations*, but you want to combine them with custom responses needed by each *path operation*.
<!-- stay:KmMIPfWb hash=sha256:94247de582f0 -->

For those cases, you can use the Python technique of "unpacking" a `dict` with `**dict_to_unpack`:
<!-- stay:xN84sfKJ hash=sha256:86cb9aff7da3 -->

```Python
old_dict = {
    "old key": "old value",
    "second old key": "second old value",
}
new_dict = {**old_dict, "new key": "new value"}
```
<!-- stay:rsVgKaHT hash=sha256:d52d0324083b -->

Here, `new_dict` will contain all the key-value pairs from `old_dict` plus the new key-value pair:
<!-- stay:bnyN6k1p hash=sha256:d13e46761137 -->

```Python
{
    "old key": "old value",
    "second old key": "second old value",
    "new key": "new value",
}
```
<!-- stay:C8RkD41F hash=sha256:7d61e5d2f187 -->

You can use that technique to reuse some predefined responses in your *path operations* and combine them with additional custom ones.
<!-- stay:m25HMuQn hash=sha256:2f150c1454f0 -->

For example:
<!-- stay:bAAYqHWu hash=sha256:652744a2ab28 -->

{* ../../docs_src/additional_responses/tutorial004_py310.py hl[11:15,24] *}
<!-- stay:s3tbEKKJ hash=sha256:ea3a6552a654 -->

## More information about OpenAPI responses { #more-information-about-openapi-responses }
<!-- stay:DeyDw36H hash=sha256:89de8c711510 -->

To see what exactly you can include in the responses, you can check these sections in the OpenAPI specification:
<!-- stay:CBJj6k7P hash=sha256:f941d26d2b43 -->

* [OpenAPI Responses Object](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.1.0.md#responses-object), it includes the `Response Object`.
* [OpenAPI Response Object](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.1.0.md#response-object), you can include anything from this directly in each response inside your `responses` parameter. Including `description`, `headers`, `content` (inside of this is that you declare different media types and JSON Schemas), and `links`.
<!-- stay:SxL2GKDj hash=sha256:c25453be7aba -->
