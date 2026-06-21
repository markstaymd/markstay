# Request Files { #request-files }
<!-- stay:xpKm3nXg hash=sha256:287446ff36af -->

You can define files to be uploaded by the client using `File`.
<!-- stay:cyfinVG7 hash=sha256:bc289bf036d8 -->

/// note
<!-- stay:Mq5yQTy2 hash=sha256:35f4d438b538 -->

To receive uploaded files, first install [`python-multipart`](https://github.com/Kludex/python-multipart).
<!-- stay:f9mV7hz5 hash=sha256:742773c98f73 -->

Make sure you create a [virtual environment](../virtual-environments.md), activate it, and then install it, for example:
<!-- stay:JaUZIup8 hash=sha256:86cd34776499 -->

```console
$ pip install python-multipart
```
<!-- stay:lA8qLjJj hash=sha256:4d9355a2800b -->

This is because uploaded files are sent as "form data".
<!-- stay:OeTebsyG hash=sha256:0bcb0e6d1ad7 -->

///
<!-- stay:YIoaCLjy hash=sha256:732c4e971163 -->

## Import `File` { #import-file }
<!-- stay:s7fhyY9e hash=sha256:5b238cc5d588 -->

Import `File` and `UploadFile` from `fastapi`:
<!-- stay:doTxLHPx hash=sha256:5a12091f21d6 -->

{* ../../docs_src/request_files/tutorial001_an_py310.py hl[3] *}
<!-- stay:sOuTj9kN hash=sha256:34e45405eae6 -->

## Define `File` Parameters { #define-file-parameters }
<!-- stay:pRHwbEYN hash=sha256:9e3f50670a3e -->

Create file parameters the same way you would for `Body` or `Form`:
<!-- stay:NG3zL3Ms hash=sha256:82ebb6d6f3cd -->

{* ../../docs_src/request_files/tutorial001_an_py310.py hl[9] *}
<!-- stay:OcEcGgAF hash=sha256:f337cf710eb7 -->

/// note
<!-- stay:6WKVv05e hash=sha256:35f4d438b538 -->

`File` is a class that inherits directly from `Form`.
<!-- stay:f0YlxZsj hash=sha256:56afb22624cf -->

But remember that when you import `Query`, `Path`, `File` and others from `fastapi`, those are actually functions that return special classes.
<!-- stay:0pbe3ptI hash=sha256:e350aa9e8e08 -->

///
<!-- stay:oPSfKA5v hash=sha256:732c4e971163 -->

/// tip
<!-- stay:KM1zpJ9J hash=sha256:35fc886a93b5 -->

To declare File bodies, you need to use `File`, because otherwise the parameters would be interpreted as query parameters or body (JSON) parameters.
<!-- stay:GrVP1LHQ hash=sha256:bee689e9d3bf -->

///
<!-- stay:n0Paa56B hash=sha256:732c4e971163 -->

The files will be uploaded as "form data".
<!-- stay:b95TDi8J hash=sha256:889b61f59168 -->

If you declare the type of your *path operation function* parameter as `bytes`, **FastAPI** will read the file for you and you will receive the contents as `bytes`.
<!-- stay:l3kgX99J hash=sha256:10615a2cbc28 -->

Keep in mind that this means that the whole contents will be stored in memory. This will work well for small files.
<!-- stay:iYXB8vB7 hash=sha256:f511c96ecffe -->

But there are several cases in which you might benefit from using `UploadFile`.
<!-- stay:ySwUmrhy hash=sha256:4e9faa270631 -->

## File Parameters with `UploadFile` { #file-parameters-with-uploadfile }
<!-- stay:veW4xUjk hash=sha256:6bd2891b7dd2 -->

Define a file parameter with a type of `UploadFile`:
<!-- stay:J9r17UMc hash=sha256:88c18193318b -->

{* ../../docs_src/request_files/tutorial001_an_py310.py hl[14] *}
<!-- stay:BZS6ico9 hash=sha256:047815dfd2b1 -->

Using `UploadFile` has several advantages over `bytes`:
<!-- stay:cIhNMJJy hash=sha256:99f9ff2a32e4 -->

* You don't have to use `File()` in the default value of the parameter.
* It uses a "spooled" file:
    * A file stored in memory up to a maximum size limit, and after passing this limit it will be stored on disk.
* This means that it will work well for large files like images, videos, large binaries, etc. without consuming all the memory.
* You can get metadata from the uploaded file.
* It has a [file-like](https://docs.python.org/3/glossary.html#term-file-like-object) `async` interface.
* It exposes an actual Python [`SpooledTemporaryFile`](https://docs.python.org/3/library/tempfile.html#tempfile.SpooledTemporaryFile) object that you can pass directly to other libraries that expect a file-like object.
<!-- stay:n6JA3PS4 hash=sha256:b2cc2274b639 -->

### `UploadFile` { #uploadfile }
<!-- stay:SdLZD2fu hash=sha256:566e16d06eef -->

`UploadFile` has the following attributes:
<!-- stay:vYwI3Bb0 hash=sha256:dd817cbe7600 -->

* `filename`: A `str` with the original file name that was uploaded (e.g. `myimage.jpg`).
* `content_type`: A `str` with the content type (MIME type / media type) (e.g. `image/jpeg`).
* `file`: A [`SpooledTemporaryFile`](https://docs.python.org/3/library/tempfile.html#tempfile.SpooledTemporaryFile) (a [file-like](https://docs.python.org/3/glossary.html#term-file-like-object) object). This is the actual Python file object that you can pass directly to other functions or libraries that expect a "file-like" object.
<!-- stay:SXgnnKkm hash=sha256:0187e3a1699b -->

`UploadFile` has the following `async` methods. They all call the corresponding file methods underneath (using the internal `SpooledTemporaryFile`).
<!-- stay:kSNlmniL hash=sha256:c1bf1d9f69fe -->

* `write(data)`: Writes `data` (`str` or `bytes`) to the file.
* `read(size)`: Reads `size` (`int`) bytes/characters of the file.
* `seek(offset)`: Goes to the byte position `offset` (`int`) in the file.
    * E.g., `await myfile.seek(0)` would go to the start of the file.
    * This is especially useful if you run `await myfile.read()` once and then need to read the contents again.
* `close()`: Closes the file.
<!-- stay:IsfqVQZ8 hash=sha256:7c8da01b7a7c -->

As all these methods are `async` methods, you need to "await" them.
<!-- stay:Dkv8ZOtI hash=sha256:3285cc051825 -->

For example, inside of an `async` *path operation function* you can get the contents with:
<!-- stay:j3zQ22Ro hash=sha256:34879a4777ea -->

```Python
contents = await myfile.read()
```
<!-- stay:qkl9OKiz hash=sha256:4e1d820f052f -->

If you are inside of a normal `def` *path operation function*, you can access the `UploadFile.file` directly, for example:
<!-- stay:4nvrfYDl hash=sha256:c27da66d0f05 -->

```Python
contents = myfile.file.read()
```
<!-- stay:8hFrTvIY hash=sha256:143f330fd568 -->

/// note | `async` Technical Details
<!-- stay:VQo13Uy4 hash=sha256:77b2e193e6c8 -->

When you use the `async` methods, **FastAPI** runs the file methods in a threadpool and awaits for them.
<!-- stay:q2FdjLpM hash=sha256:89eeb006a2c6 -->

///
<!-- stay:O7EnrM1I hash=sha256:732c4e971163 -->

/// note | Starlette Technical Details
<!-- stay:CrCasair hash=sha256:02fa2b30ff2e -->

**FastAPI**'s `UploadFile` inherits directly from **Starlette**'s `UploadFile`, but adds some necessary parts to make it compatible with **Pydantic** and the other parts of FastAPI.
<!-- stay:TRMCIIhK hash=sha256:5f8fad3c1619 -->

///
<!-- stay:gCKExfqV hash=sha256:732c4e971163 -->

## What is "Form Data" { #what-is-form-data }
<!-- stay:vVXDNGMz hash=sha256:bb916b00aa4e -->

The way HTML forms (`<form></form>`) send the data to the server normally uses a "special" encoding for that data, it's different from JSON.
<!-- stay:lNTIg1TO hash=sha256:8c66f697de4d -->

**FastAPI** will make sure to read that data from the right place instead of JSON.
<!-- stay:gfuGEEkn hash=sha256:d112c060cdad -->

/// note | Technical Details
<!-- stay:OYVP7LpQ hash=sha256:28fbbcad08d1 -->

Data from forms is normally encoded using the "media type" `application/x-www-form-urlencoded` when it doesn't include files.
<!-- stay:ullznkLz hash=sha256:2e9260d09c74 -->

But when the form includes files, it is encoded as `multipart/form-data`. If you use `File`, **FastAPI** will know it has to get the files from the correct part of the body.
<!-- stay:R78oS4wN hash=sha256:2eb9c2782104 -->

If you want to read more about these encodings and form fields, head to the [<abbr title="Mozilla Developer Network">MDN</abbr> web docs for `POST`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST).
<!-- stay:5CiRPYsi hash=sha256:806909d5f517 -->

///
<!-- stay:P9il909K hash=sha256:732c4e971163 -->

/// warning
<!-- stay:QGZduOce hash=sha256:98e5a9621bab -->

You can declare multiple `File` and `Form` parameters in a *path operation*, but you can't also declare `Body` fields that you expect to receive as JSON, as the request will have the body encoded using `multipart/form-data` instead of `application/json`.
<!-- stay:XW3nmv4U hash=sha256:94e04531ad8a -->

This is not a limitation of **FastAPI**, it's part of the HTTP protocol.
<!-- stay:eLPcjmAk hash=sha256:9f0333b468cc -->

///
<!-- stay:tJzLFpYF hash=sha256:732c4e971163 -->

## Optional File Upload { #optional-file-upload }
<!-- stay:brCscb8T hash=sha256:3082b05b9f0c -->

You can make a file optional by using standard type annotations and setting a default value of `None`:
<!-- stay:kq29fY0H hash=sha256:7ca05a0a4298 -->

{* ../../docs_src/request_files/tutorial001_02_an_py310.py hl[9,17] *}
<!-- stay:GYhW5QPX hash=sha256:ead2ecad5f81 -->

## `UploadFile` with Additional Metadata { #uploadfile-with-additional-metadata }
<!-- stay:9NPth0Nq hash=sha256:7c20af254a7e -->

You can also use `File()` with `UploadFile`, for example, to set additional metadata:
<!-- stay:9OHSHaSl hash=sha256:f4bc9437936e -->

{* ../../docs_src/request_files/tutorial001_03_an_py310.py hl[9,15] *}
<!-- stay:kmfCysP4 hash=sha256:59ecc76281b6 -->

## Multiple File Uploads { #multiple-file-uploads }
<!-- stay:pfrzv7io hash=sha256:db531c5d8935 -->

It's possible to upload several files at the same time.
<!-- stay:wtyw0itB hash=sha256:305c81e86ebe -->

They would be associated to the same "form field" sent using "form data".
<!-- stay:Rwhk7CvG hash=sha256:88a22fa5d8ca -->

To use that, declare a list of `bytes` or `UploadFile`:
<!-- stay:UXMpQMVm hash=sha256:c216fb317cd4 -->

{* ../../docs_src/request_files/tutorial002_an_py310.py hl[10,15] *}
<!-- stay:9tLEEFM7 hash=sha256:fe9a463d9937 -->

You will receive, as declared, a `list` of `bytes` or `UploadFile`s.
<!-- stay:nQrDEXAz hash=sha256:bb845774085d -->

/// note | Technical Details
<!-- stay:OOeVILxY hash=sha256:28fbbcad08d1 -->

You could also use `from starlette.responses import HTMLResponse`.
<!-- stay:mnqYzfaX hash=sha256:cd26b890517a -->

**FastAPI** provides the same `starlette.responses` as `fastapi.responses` just as a convenience for you, the developer. But most of the available responses come directly from Starlette.
<!-- stay:1PObkpRk hash=sha256:1d9ba437732e -->

///
<!-- stay:XHPz0e5Z hash=sha256:732c4e971163 -->

### Multiple File Uploads with Additional Metadata { #multiple-file-uploads-with-additional-metadata }
<!-- stay:F2EKEE8Z hash=sha256:a319d1ad8fb7 -->

And the same way as before, you can use `File()` to set additional parameters, even for `UploadFile`:
<!-- stay:3iCTljsd hash=sha256:799ded965c69 -->

{* ../../docs_src/request_files/tutorial003_an_py310.py hl[11,18:20] *}
<!-- stay:na9FHb5i hash=sha256:b14e4c6d2304 -->

## Recap { #recap }
<!-- stay:Dv7OKly7 hash=sha256:40a194d2a8b0 -->

Use `File`, `bytes`, and `UploadFile` to declare files to be uploaded in the request, sent as form data.
<!-- stay:bg3NXT9I hash=sha256:24512e58d0b1 -->
