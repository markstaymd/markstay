# OpenAPI Callbacks { #openapi-callbacks }
<!-- stay:6i7Ug6KP hash=sha256:487b53d1c18d -->

You could create an API with a *path operation* that could trigger a request to an *external API* created by someone else (probably the same developer that would be *using* your API).
<!-- stay:Ui4l0lLu hash=sha256:77d1488f7f19 -->

The process that happens when your API app calls the *external API* is named a "callback". Because the software that the external developer wrote sends a request to your API and then your API *calls back*, sending a request to an *external API* (that was probably created by the same developer).
<!-- stay:Yyl3ueFO hash=sha256:909afe493eba -->

In this case, you could want to document how that external API *should* look. What *path operation* it should have, what body it should expect, what response it should return, etc.
<!-- stay:Zxxbn5hH hash=sha256:f1ea3b6d9863 -->

## An app with callbacks { #an-app-with-callbacks }
<!-- stay:UoQg2gk0 hash=sha256:a81dae4376f3 -->

Let's see all this with an example.
<!-- stay:W84Lh8nK hash=sha256:81c9eec43ce9 -->

Imagine you develop an app that allows creating invoices.
<!-- stay:uSN1PWQ9 hash=sha256:fed8b9a47de5 -->

These invoices will have an `id`, `title` (optional), `customer`, and `total`.
<!-- stay:8CJNh3uX hash=sha256:3f9af8e7ab3e -->

The user of your API (an external developer) will create an invoice in your API with a POST request.
<!-- stay:rGGbWwkS hash=sha256:c6f7a5963f15 -->

Then your API will (let's imagine):
<!-- stay:hBEhFeRE hash=sha256:9b4bef19b243 -->

* Send the invoice to some customer of the external developer.
* Collect the money.
* Send a notification back to the API user (the external developer).
    * This will be done by sending a POST request (from *your API*) to some *external API* provided by that external developer (this is the "callback").
<!-- stay:opuYmjRc hash=sha256:6eddd9d5a8a9 -->

## The normal **FastAPI** app { #the-normal-fastapi-app }
<!-- stay:hUgtxeb7 hash=sha256:3d75c42cfa69 -->

Let's first see how the normal API app would look before adding the callback.
<!-- stay:iIcXLizO hash=sha256:f0dfec777308 -->

It will have a *path operation* that will receive an `Invoice` body, and a query parameter `callback_url` that will contain the URL for the callback.
<!-- stay:s6BJEKhm hash=sha256:14eeff43f48a -->

This part is pretty normal, most of the code is probably already familiar to you:
<!-- stay:sHXoBINV hash=sha256:61ba8a5c3e1f -->

{* ../../docs_src/openapi_callbacks/tutorial001_py310.py hl[7:11,34:51] *}
<!-- stay:eteTbVcU hash=sha256:324dedcafed9 -->

/// tip
<!-- stay:t76rs8lq hash=sha256:35fc886a93b5 -->

The `callback_url` query parameter uses a Pydantic [Url](https://docs.pydantic.dev/latest/api/networks/) type.
<!-- stay:dnjQEdTJ hash=sha256:4451188b03a8 -->

///
<!-- stay:x6yiMjMh hash=sha256:732c4e971163 -->

The only new thing is the `callbacks=invoices_callback_router.routes` as an argument to the *path operation decorator*. We'll see what that is next.
<!-- stay:BTzGC0Xc hash=sha256:47625aeb8196 -->

## Documenting the callback { #documenting-the-callback }
<!-- stay:1kx662KW hash=sha256:578ed6780abe -->

The actual callback code will depend heavily on your own API app.
<!-- stay:Ffbjsnj4 hash=sha256:80a9aa3f2fe3 -->

And it will probably vary a lot from one app to the next.
<!-- stay:2CXWs9HJ hash=sha256:fa8f6c43d2e4 -->

It could be just one or two lines of code, like:
<!-- stay:IK1Qjhg7 hash=sha256:7fe335044cc8 -->

```Python
callback_url = "https://example.com/api/v1/invoices/events/"
httpx.post(callback_url, json={"description": "Invoice paid", "paid": True})
```
<!-- stay:FIJ8gtq7 hash=sha256:660c12d1aaad -->

But possibly the most important part of the callback is making sure that your API user (the external developer) implements the *external API* correctly, according to the data that *your API* is going to send in the request body of the callback, etc.
<!-- stay:IaXajK15 hash=sha256:a0cbe2e3688d -->

So, what we will do next is add the code to document how that *external API* should look to receive the callback from *your API*.
<!-- stay:WIuWLKuQ hash=sha256:0315b66d29b5 -->

That documentation will show up in the Swagger UI at `/docs` in your API, and it will let external developers know how to build the *external API*.
<!-- stay:YnuNLBhW hash=sha256:5591ff20f92e -->

This example doesn't implement the callback itself (that could be just a line of code), only the documentation part.
<!-- stay:NzpLbHdE hash=sha256:efbc8f34b2fe -->

/// tip
<!-- stay:mUcsjFzi hash=sha256:35fc886a93b5 -->

The actual callback is just an HTTP request.
<!-- stay:pBn3Wp6Z hash=sha256:38bf5f35c536 -->

When implementing the callback yourself, you could use something like [HTTPX](https://www.python-httpx.org) or [Requests](https://requests.readthedocs.io/).
<!-- stay:z0sKNdzf hash=sha256:d1d754dda0fd -->

///
<!-- stay:c65Q6aFJ hash=sha256:732c4e971163 -->

## Write the callback documentation code { #write-the-callback-documentation-code }
<!-- stay:smhnYvxW hash=sha256:beaaf9db2fab -->

This code won't be executed in your app, we only need it to *document* how that *external API* should look.
<!-- stay:sKmTEyVK hash=sha256:2fbc3af857b2 -->

But, you already know how to easily create automatic documentation for an API with **FastAPI**.
<!-- stay:8JKns9mK hash=sha256:014bb63fb55b -->

So we are going to use that same knowledge to document how the *external API* should look... by creating the *path operation(s)* that the external API should implement (the ones your API will call).
<!-- stay:XJcyrYSB hash=sha256:36bd83cb84d3 -->

/// tip
<!-- stay:qaqBDj36 hash=sha256:35fc886a93b5 -->

When writing the code to document a callback, it might be useful to imagine that you are that *external developer*. And that you are currently implementing the *external API*, not *your API*.
<!-- stay:JqMfizEF hash=sha256:9064a8c47254 -->

Temporarily adopting this point of view (of the *external developer*) can help you feel like it's more obvious where to put the parameters, the Pydantic model for the body, for the response, etc. for that *external API*.
<!-- stay:xpAqX6t1 hash=sha256:6672336f7915 -->

///
<!-- stay:fhhRlL7F hash=sha256:732c4e971163 -->

### Create a callback `APIRouter` { #create-a-callback-apirouter }
<!-- stay:ATKRko1j hash=sha256:6392f379c0f9 -->

First create a new `APIRouter` that will contain one or more callbacks.
<!-- stay:lbsdhRBL hash=sha256:82750b0c8df8 -->

{* ../../docs_src/openapi_callbacks/tutorial001_py310.py hl[1,23] *}
<!-- stay:2ADcRTWt hash=sha256:284598de3b64 -->

### Create the callback *path operation* { #create-the-callback-path-operation }
<!-- stay:NmPvm5hD hash=sha256:70d428f09b20 -->

To create the callback *path operation* use the same `APIRouter` you created above.
<!-- stay:Uz8rW6rK hash=sha256:35ec7fc89337 -->

It should look just like a normal FastAPI *path operation*:
<!-- stay:8PbpJBnU hash=sha256:a4552718255b -->

* It should probably have a declaration of the body it should receive, e.g. `body: InvoiceEvent`.
* And it could also have a declaration of the response it should return, e.g. `response_model=InvoiceEventReceived`.
<!-- stay:PFfZYhYZ hash=sha256:756f318a3d28 -->

{* ../../docs_src/openapi_callbacks/tutorial001_py310.py hl[14:16,19:20,26:30] *}
<!-- stay:cbNtHeUQ hash=sha256:7270a37897fc -->

There are 2 main differences from a normal *path operation*:
<!-- stay:JGB9yjcD hash=sha256:91293dfd521d -->

* It doesn't need to have any actual code, because your app will never call this code. It's only used to document the *external API*. So, the function could just have `pass`.
* The *path* can contain an [OpenAPI 3 expression](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.1.0.md#key-expression) (see more below) where it can use variables with parameters and parts of the original request sent to *your API*.
<!-- stay:iKI8dqgb hash=sha256:c0e07039896f -->

### The callback path expression { #the-callback-path-expression }
<!-- stay:BdcUic4z hash=sha256:e0dec0bbc960 -->

The callback *path* can have an [OpenAPI 3 expression](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.1.0.md#key-expression) that can contain parts of the original request sent to *your API*.
<!-- stay:3ci3l74t hash=sha256:76e6314fe387 -->

In this case, it's the `str`:
<!-- stay:GuXj7osa hash=sha256:3d2eb1d0fa58 -->

```Python
"{$callback_url}/invoices/{$request.body.id}"
```
<!-- stay:twMglO7i hash=sha256:f77c79a33c2b -->

So, if your API user (the external developer) sends a request to *your API* to:
<!-- stay:A2XYB6H0 hash=sha256:26a5f6e4f652 -->

```
https://yourapi.com/invoices/?callback_url=https://www.external.org/events
```
<!-- stay:zCuHQOEK hash=sha256:9f56c5f8fd49 -->

with a JSON body of:
<!-- stay:tbBjcXVC hash=sha256:ddbe1adde0a3 -->

```JSON
{
    "id": "2expen51ve",
    "customer": "Mr. Richie Rich",
    "total": "9999"
}
```
<!-- stay:b7gewBMn hash=sha256:18ec92f29a92 -->

then *your API* will process the invoice, and at some point later, send a callback request to the `callback_url` (the *external API*):
<!-- stay:H9X2ULgq hash=sha256:7d682ebcca7a -->

```
https://www.external.org/events/invoices/2expen51ve
```
<!-- stay:boeVaVbQ hash=sha256:93bff22b66b6 -->

with a JSON body containing something like:
<!-- stay:qMR5khuy hash=sha256:0ab025d8dcf9 -->

```JSON
{
    "description": "Payment celebration",
    "paid": true
}
```
<!-- stay:Wj7vFF2M hash=sha256:8456d82bd252 -->

and it would expect a response from that *external API* with a JSON body like:
<!-- stay:O8U2uIuK hash=sha256:5985193d3405 -->

```JSON
{
    "ok": true
}
```
<!-- stay:aRNZs8st hash=sha256:c459ebe66341 -->

/// tip
<!-- stay:WwUolxUe hash=sha256:35fc886a93b5 -->

Notice how the callback URL used contains the URL received as a query parameter in `callback_url` (`https://www.external.org/events`) and also the invoice `id` from inside of the JSON body (`2expen51ve`).
<!-- stay:Akj8PX2l hash=sha256:d77a35638196 -->

///
<!-- stay:lOckNIyk hash=sha256:732c4e971163 -->

### Add the callback router { #add-the-callback-router }
<!-- stay:tG3Vq4pN hash=sha256:4b2bc854f3fd -->

At this point you have the *callback path operation(s)* needed (the one(s) that the *external developer*  should implement in the *external API*) in the callback router you created above.
<!-- stay:j57mSPnN hash=sha256:b7874ffe0963 -->

Now use the parameter `callbacks` in *your API's path operation decorator* to pass the attribute `.routes` from that callback router:
<!-- stay:cppl5UG3 hash=sha256:fd0457d0129a -->

{* ../../docs_src/openapi_callbacks/tutorial001_py310.py hl[33] *}
<!-- stay:qQZJW2CI hash=sha256:c22912e7f4c9 -->

/// tip
<!-- stay:NYMscgrs hash=sha256:35fc886a93b5 -->

Notice that you are not passing the router itself (`invoices_callback_router`) to `callbacks=`, but its `.routes`, as in `invoices_callback_router.routes`. FastAPI will use those routes to generate the callback OpenAPI documentation.
<!-- stay:4EgsKXYg hash=sha256:e8fb8157f9d0 -->

///
<!-- stay:CVpt3YJi hash=sha256:732c4e971163 -->

### Check the docs { #check-the-docs }
<!-- stay:HAOrCQPo hash=sha256:6226260e5e1e -->

Now you can start your app and go to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
<!-- stay:dKoegXcy hash=sha256:4ed11083c90d -->

You will see your docs including a "Callbacks" section for your *path operation* that shows how the *external API* should look:
<!-- stay:9XpYHFgw hash=sha256:8b4575745583 -->

<img src="/img/tutorial/openapi-callbacks/image01.png">
<!-- stay:bk7zvQ5p hash=sha256:79c64f91104a -->
