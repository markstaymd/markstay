# Custom Docs UI Static Assets (Self-Hosting) { #custom-docs-ui-static-assets-self-hosting }
<!-- stay:LhYgD5ZB hash=sha256:eb2bfad87401 -->

The API docs use **Swagger UI** and **ReDoc**, and each of those need some JavaScript and CSS files.
<!-- stay:tdp9JykK hash=sha256:2dac6f8ae2eb -->

By default, those files are served from a <abbr title="Content Delivery Network: A service, normally composed of several servers, that provides static files, like JavaScript and CSS. It's commonly used to serve those files from the server closer to the client, improving performance.">CDN</abbr>.
<!-- stay:C61X9kfJ hash=sha256:1263a69f7e04 -->

But it's possible to customize it, you can set a specific CDN, or serve the files yourself.
<!-- stay:kfiSzpv1 hash=sha256:d708d29cc469 -->

## Custom CDN for JavaScript and CSS { #custom-cdn-for-javascript-and-css }
<!-- stay:42ve1qeq hash=sha256:3d7843bbf4b5 -->

Let's say that you want to use a different <abbr title="Content Delivery Network">CDN</abbr>, for example you want to use `https://unpkg.com/`.
<!-- stay:31wGwYSs hash=sha256:5d3c85ecb01f -->

This could be useful if for example you live in a country that restricts some URLs.
<!-- stay:CIFxKx3g hash=sha256:ac0a803b9c22 -->

### Disable the automatic docs { #disable-the-automatic-docs }
<!-- stay:thXiHwjz hash=sha256:c08cea031d86 -->

The first step is to disable the automatic docs, as by default, those use the default CDN.
<!-- stay:cq3uHjKq hash=sha256:7d3322518134 -->

To disable them, set their URLs to `None` when creating your `FastAPI` app:
<!-- stay:4HqByosx hash=sha256:7301b7fa1015 -->

{* ../../docs_src/custom_docs_ui/tutorial001_py310.py hl[8] *}
<!-- stay:QM8aa0A9 hash=sha256:dcb68c640fb5 -->

### Include the custom docs { #include-the-custom-docs }
<!-- stay:1CGqDWQ5 hash=sha256:11c564d46259 -->

Now you can create the *path operations* for the custom docs.
<!-- stay:x9f6FRrN hash=sha256:072070282852 -->

You can reuse FastAPI's internal functions to create the HTML pages for the docs, and pass them the needed arguments:
<!-- stay:UZWEGKdC hash=sha256:b72326505761 -->

* `openapi_url`: the URL where the HTML page for the docs can get the OpenAPI schema for your API. You can use here the attribute `app.openapi_url`.
* `title`: the title of your API.
* `oauth2_redirect_url`: you can use `app.swagger_ui_oauth2_redirect_url` here to use the default.
* `swagger_js_url`: the URL where the HTML for your Swagger UI docs can get the **JavaScript** file. This is the custom CDN URL.
* `swagger_css_url`: the URL where the HTML for your Swagger UI docs can get the **CSS** file. This is the custom CDN URL.
<!-- stay:FbVRWfdy hash=sha256:3e01ccba5c13 -->

And similarly for ReDoc...
<!-- stay:umE4EFAp hash=sha256:ce4d4ab3207f -->

{* ../../docs_src/custom_docs_ui/tutorial001_py310.py hl[2:6,11:19,22:24,27:33] *}
<!-- stay:dyyw2cWV hash=sha256:f7fe9db85230 -->

/// tip
<!-- stay:GfdIhaWJ hash=sha256:35fc886a93b5 -->

The *path operation* for `swagger_ui_redirect` is a helper for when you use OAuth2.
<!-- stay:Hgz3TaTJ hash=sha256:994fdcc81e23 -->

If you integrate your API with an OAuth2 provider, you will be able to authenticate and come back to the API docs with the acquired credentials. And interact with it using the real OAuth2 authentication.
<!-- stay:BsuWyVjf hash=sha256:847de5e23047 -->

Swagger UI will handle it behind the scenes for you, but it needs this "redirect" helper.
<!-- stay:CxZGvTxw hash=sha256:36d3a5a40c14 -->

///
<!-- stay:6XGNp7XF hash=sha256:732c4e971163 -->

### Create a *path operation* to test it { #create-a-path-operation-to-test-it }
<!-- stay:Xjuunipr hash=sha256:ce0b2359f4cc -->

Now, to be able to test that everything works, create a *path operation*:
<!-- stay:Rch2TjeG hash=sha256:3bb15d8b4270 -->

{* ../../docs_src/custom_docs_ui/tutorial001_py310.py hl[36:38] *}
<!-- stay:aZkOijaD hash=sha256:419d17e8a003 -->

### Test it { #test-it }
<!-- stay:v3rD6E98 hash=sha256:985bcf0f1cb6 -->

Now, you should be able to go to your docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), and reload the page, it will load those assets from the new CDN.
<!-- stay:mKNiXtiH hash=sha256:d64f6d47f35f -->

## Self-hosting JavaScript and CSS for docs { #self-hosting-javascript-and-css-for-docs }
<!-- stay:7ASr3wHM hash=sha256:89928e949376 -->

Self-hosting the JavaScript and CSS could be useful if, for example, you need your app to keep working even while offline, without open Internet access, or in a local network.
<!-- stay:msFSzLlv hash=sha256:ef6cc7ff63d4 -->

Here you'll see how to serve those files yourself, in the same FastAPI app, and configure the docs to use them.
<!-- stay:RiQiefeA hash=sha256:3df58c881e72 -->

### Project file structure { #project-file-structure }
<!-- stay:4YKoAFAK hash=sha256:a993ca32ed83 -->

Let's say your project file structure looks like this:
<!-- stay:OXXJaMPO hash=sha256:d673a9c0732a -->

```
.
├── app
│   ├── __init__.py
│   ├── main.py
```
<!-- stay:oCEpfX29 hash=sha256:193291045b1a -->

Now create a directory to store those static files.
<!-- stay:OINlgmkf hash=sha256:856454f98428 -->

Your new file structure could look like this:
<!-- stay:sBLR0wrd hash=sha256:4c2c3faf1f61 -->

```
.
├── app
│   ├── __init__.py
│   ├── main.py
└── static/
```
<!-- stay:Jksk08TF hash=sha256:1434da451554 -->

### Download the files { #download-the-files }
<!-- stay:4oYgZqw4 hash=sha256:15ce406503e0 -->

Download the static files needed for the docs and put them on that `static/` directory.
<!-- stay:07R1cJNJ hash=sha256:8d2e0fcfdc71 -->

You can probably right-click each link and select an option similar to "Save link as...".
<!-- stay:1aBq0FSZ hash=sha256:1b23036339d2 -->

**Swagger UI** uses the files:
<!-- stay:pKb2YtuK hash=sha256:22519584d960 -->

* [`swagger-ui-bundle.js`](https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js)
* [`swagger-ui.css`](https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css)
<!-- stay:L71jptxI hash=sha256:a60cc449938d -->

And **ReDoc** uses the file:
<!-- stay:6UJVmfQq hash=sha256:480466423e23 -->

* [`redoc.standalone.js`](https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js)
<!-- stay:WbHfNhIh hash=sha256:402b8bbdef1b -->

After that, your file structure could look like:
<!-- stay:n3XUDCR6 hash=sha256:4d0cb52c615d -->

```
.
├── app
│   ├── __init__.py
│   ├── main.py
└── static
    ├── redoc.standalone.js
    ├── swagger-ui-bundle.js
    └── swagger-ui.css
```
<!-- stay:CnXd8crP hash=sha256:e643ffdf8bf1 -->

### Serve the static files { #serve-the-static-files }
<!-- stay:CiM4Qvtz hash=sha256:6f725aa0e09f -->

* Import `StaticFiles`.
* "Mount" a `StaticFiles()` instance in a specific path.
<!-- stay:H0LT4yDn hash=sha256:5813824bd923 -->

{* ../../docs_src/custom_docs_ui/tutorial002_py310.py hl[7,11] *}
<!-- stay:huD67sIb hash=sha256:c796b2fe6db7 -->

### Test the static files { #test-the-static-files }
<!-- stay:54eCpuqJ hash=sha256:4cd4a4535fd2 -->

Start your application and go to [http://127.0.0.1:8000/static/redoc.standalone.js](http://127.0.0.1:8000/static/redoc.standalone.js).
<!-- stay:kjod0HeJ hash=sha256:66ade671c946 -->

You should see a very long JavaScript file for **ReDoc**.
<!-- stay:4kAR0lqw hash=sha256:c1e5a74d5eff -->

It could start with something like:
<!-- stay:0aFDBBW7 hash=sha256:babb40f40526 -->

```JavaScript
/*! For license information please see redoc.standalone.js.LICENSE.txt */
!function(e,t){"object"==typeof exports&&"object"==typeof module?module.exports=t(require("null")):
...
```
<!-- stay:L9IkaiZT hash=sha256:6771cdcd0171 -->

That confirms that you are being able to serve static files from your app, and that you placed the static files for the docs in the correct place.
<!-- stay:Y7tVzuB9 hash=sha256:f9174058bbcb -->

Now we can configure the app to use those static files for the docs.
<!-- stay:PFElTsqf hash=sha256:9850b04ffd9f -->

### Disable the automatic docs for static files { #disable-the-automatic-docs-for-static-files }
<!-- stay:ZkSyaM1x hash=sha256:50f4f2ffa470 -->

The same as when using a custom CDN, the first step is to disable the automatic docs, as those use the CDN by default.
<!-- stay:uThSKQiz hash=sha256:417fdb47c66e -->

To disable them, set their URLs to `None` when creating your `FastAPI` app:
<!-- stay:EPCvVZQY hash=sha256:7301b7fa1015 -->

{* ../../docs_src/custom_docs_ui/tutorial002_py310.py hl[9] *}
<!-- stay:70vzrZ5I hash=sha256:33d0d38cf85c -->

### Include the custom docs for static files { #include-the-custom-docs-for-static-files }
<!-- stay:0ZBOZ06l hash=sha256:e535ce38743c -->

And the same way as with a custom CDN, now you can create the *path operations* for the custom docs.
<!-- stay:Hf9lbi0I hash=sha256:6cbdedd07d5a -->

Again, you can reuse FastAPI's internal functions to create the HTML pages for the docs, and pass them the needed arguments:
<!-- stay:3d0y3THb hash=sha256:575c2f14ae02 -->

* `openapi_url`: the URL where the HTML page for the docs can get the OpenAPI schema for your API. You can use here the attribute `app.openapi_url`.
* `title`: the title of your API.
* `oauth2_redirect_url`: you can use `app.swagger_ui_oauth2_redirect_url` here to use the default.
* `swagger_js_url`: the URL where the HTML for your Swagger UI docs can get the **JavaScript** file. **This is the one that your own app is now serving**.
* `swagger_css_url`: the URL where the HTML for your Swagger UI docs can get the **CSS** file. **This is the one that your own app is now serving**.
<!-- stay:sFmdT9Pg hash=sha256:4984d1b8894f -->

And similarly for ReDoc...
<!-- stay:KWJIFAOG hash=sha256:ce4d4ab3207f -->

{* ../../docs_src/custom_docs_ui/tutorial002_py310.py hl[2:6,14:22,25:27,30:36] *}
<!-- stay:AI5Zh2tG hash=sha256:7f8b7990b2d7 -->

/// tip
<!-- stay:X9LZ5yVN hash=sha256:35fc886a93b5 -->

The *path operation* for `swagger_ui_redirect` is a helper for when you use OAuth2.
<!-- stay:QJprnb2Q hash=sha256:994fdcc81e23 -->

If you integrate your API with an OAuth2 provider, you will be able to authenticate and come back to the API docs with the acquired credentials. And interact with it using the real OAuth2 authentication.
<!-- stay:xxpQnc1v hash=sha256:847de5e23047 -->

Swagger UI will handle it behind the scenes for you, but it needs this "redirect" helper.
<!-- stay:TT4CB2sn hash=sha256:36d3a5a40c14 -->

///
<!-- stay:KaJaIvZ5 hash=sha256:732c4e971163 -->

### Create a *path operation* to test static files { #create-a-path-operation-to-test-static-files }
<!-- stay:0JlF3PVu hash=sha256:45443ab0f83b -->

Now, to be able to test that everything works, create a *path operation*:
<!-- stay:Q9W4fpzf hash=sha256:3bb15d8b4270 -->

{* ../../docs_src/custom_docs_ui/tutorial002_py310.py hl[39:41] *}
<!-- stay:r0xP3K8Q hash=sha256:f7f0f2082f0d -->

### Test Static Files UI { #test-static-files-ui }
<!-- stay:Bif1rvPo hash=sha256:401cc368ae81 -->

Now, you should be able to disconnect your WiFi, go to your docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), and reload the page.
<!-- stay:I4nMgrij hash=sha256:441ead3cbc9b -->

And even without Internet, you would be able to see the docs for your API and interact with it.
<!-- stay:34VlmZq4 hash=sha256:090c9a11b1ff -->
