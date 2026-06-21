# Request Files { #request-files }
<!-- stay:BWtSeeze hash=sha256:287446ff36af -->

You can define files to be uploaded by the client using `File`.
<!-- stay:Jkfs5jMO hash=sha256:bc289bf036d8 -->

/// note
<!-- stay:U0h4sNd7 hash=sha256:35f4d438b538 -->

To receive uploaded files, first install [`python-multipart`](https://github.com/Kludex/python-multipart).
<!-- stay:0diCZDwu hash=sha256:742773c98f73 -->

Make sure you create a [virtual environment](../virtual-environments.md), activate it, and then install it, for example:
<!-- stay:wbNaicEM hash=sha256:86cd34776499 -->

```console
$ pip install python-multipart
```
<!-- stay:2LxdvRxJ hash=sha256:4d9355a2800b -->

This is because uploaded files are sent as "form data".
<!-- stay:FsZ1nonM hash=sha256:0bcb0e6d1ad7 -->

///
<!-- stay:DTQ8YpUT hash=sha256:732c4e971163 -->

## Import `File` { #import-file }
<!-- stay:NjSWnVuK hash=sha256:5b238cc5d588 -->

Import `File` and `UploadFile` from `fastapi`:
<!-- stay:tNHbBOzB hash=sha256:5a12091f21d6 -->

{* ../../docs_src/request_files/tutorial001_an_py310.py hl[3] *}
<!-- stay:7IdarrHY hash=sha256:34e45405eae6 -->

## Define `File` Parameters { #define-file-parameters }
<!-- stay:xWYPdoM7 hash=sha256:9e3f50670a3e -->

Create file parameters the same way you would for `Body` or `Form`:
<!-- stay:VbuMoGwG hash=sha256:82ebb6d6f3cd -->

{* ../../docs_src/request_files/tutorial001_an_py310.py hl[9] *}
<!-- stay:gmTznkD5 hash=sha256:f337cf710eb7 -->

/// note
<!-- stay:KLar2v0S hash=sha256:35f4d438b538 -->

`File` is a class that inherits directly from `Form`.
<!-- stay:IhAT5J4v hash=sha256:56afb22624cf -->

But remember that when you import `Query`, `Path`, `File` and others from `fastapi`, those are actually functions that return special classes.
<!-- stay:N0Jg5lgg hash=sha256:e350aa9e8e08 -->

///
<!-- stay:BuwwlKte hash=sha256:732c4e971163 -->

/// tip
<!-- stay:ka9BQvXW hash=sha256:35fc886a93b5 -->

To declare File bodies, you need to use `File`, because otherwise the parameters would be interpreted as query parameters or body (JSON) parameters.
<!-- stay:qA4gczwl hash=sha256:bee689e9d3bf -->

///
<!-- stay:f3W1SbM4 hash=sha256:732c4e971163 -->

The files will be uploaded as "form data".
<!-- stay:T3lippiT hash=sha256:889b61f59168 -->

If you declare the type of your *path operation function* parameter as `bytes`, **FastAPI** will read the file for you and you will receive the contents as `bytes`.
<!-- stay:Mua02Tpu hash=sha256:10615a2cbc28 -->

Keep in mind that this means that the whole contents will be stored in memory. This will work well for small files.
<!-- stay:lQBui68t hash=sha256:f511c96ecffe -->

But there are several cases in which you might benefit from using `UploadFile`.
<!-- stay:HJLRchNy hash=sha256:4e9faa270631 -->

## File Parameters with `UploadFile` { #file-parameters-with-uploadfile }
<!-- stay:hEACQpaT hash=sha256:6bd2891b7dd2 -->

Define a file parameter with a type of `UploadFile`:
<!-- stay:fAgVx4IB hash=sha256:88c18193318b -->

{* ../../docs_src/request_files/tutorial001_an_py310.py hl[14] *}
<!-- stay:7JVdW8H0 hash=sha256:047815dfd2b1 -->

Using `UploadFile` has several advantages over `bytes`:
<!-- stay:WGVp7ovw hash=sha256:99f9ff2a32e4 -->

* You don't have to use `File()` in the default value of the parameter.
* It uses a "spooled" file:
    * A file stored in memory up to a maximum size limit, and after passing this limit it will be stored on disk.
* This means that it will work well for large files like images, videos, large binaries, etc. without consuming all the memory.
* You can get metadata from the uploaded file.
* It has a [file-like](https://docs.python.org/3/glossary.html#term-file-like-object) `async` interface.
* It exposes an actual Python [`SpooledTemporaryFile`](https://docs.python.org/3/library/tempfile.html#tempfile.SpooledTemporaryFile) object that you can pass directly to other libraries that expect a file-like object.
<!-- stay:6t5Rmpzc hash=sha256:b2cc2274b639 -->

### `UploadFile` { #uploadfile }
<!-- stay:UobSzFqy hash=sha256:566e16d06eef -->

`UploadFile` has the following attributes:
<!-- stay:GPqOc0hy hash=sha256:dd817cbe7600 -->

* `filename`: A `str` with the original file name that was uploaded (e.g. `myimage.jpg`).
* `content_type`: A `str` with the content type (MIME type / media type) (e.g. `image/jpeg`).
* `file`: A [`SpooledTemporaryFile`](https://docs.python.org/3/library/tempfile.html#tempfile.SpooledTemporaryFile) (a [file-like](https://docs.python.org/3/glossary.html#term-file-like-object) object). This is the actual Python file object that you can pass directly to other functions or libraries that expect a "file-like" object.
<!-- stay:3Hjkqv3h hash=sha256:0187e3a1699b -->

`UploadFile` has the following `async` methods. They all call the corresponding file methods underneath (using the internal `SpooledTemporaryFile`).
<!-- stay:Ia8JjGXi hash=sha256:c1bf1d9f69fe -->

* `write(data)`: Writes `data` (`str` or `bytes`) to the file.
* `read(size)`: Reads `size` (`int`) bytes/characters of the file.
* `seek(offset)`: Goes to the byte position `offset` (`int`) in the file.
    * E.g., `await myfile.seek(0)` would go to the start of the file.
    * This is especially useful if you run `await myfile.read()` once and then need to read the contents again.
* `close()`: Closes the file.
<!-- stay:6CXQl8TW hash=sha256:7c8da01b7a7c -->

As all these methods are `async` methods, you need to "await" them.
<!-- stay:4LLjdeAN hash=sha256:3285cc051825 -->

For example, inside of an `async` *path operation function* you can get the contents with:
<!-- stay:4M3siyft hash=sha256:34879a4777ea -->

```Python
contents = await myfile.read()
```
<!-- stay:FieXBtTn hash=sha256:4e1d820f052f -->

If you are inside of a normal `def` *path operation function*, you can access the `UploadFile.file` directly, for example:
<!-- stay:4i63DzBc hash=sha256:c27da66d0f05 -->

```Python
contents = myfile.file.read()
```
<!-- stay:1MA83J1b hash=sha256:143f330fd568 -->

/// note | `async` Technical Details
<!-- stay:n7xa8nAy hash=sha256:77b2e193e6c8 -->

When you use the `async` methods, **FastAPI** runs the file methods in a threadpool and awaits for them.
<!-- stay:tBB1DmrR hash=sha256:89eeb006a2c6 -->

///
<!-- stay:FLmUqrbE hash=sha256:732c4e971163 -->

/// note | Starlette Technical Details
<!-- stay:GfmQnMNF hash=sha256:02fa2b30ff2e -->

**FastAPI**'s `UploadFile` inherits directly from **Starlette**'s `UploadFile`, but adds some necessary parts to make it compatible with **Pydantic** and the other parts of FastAPI.
<!-- stay:8898whN9 hash=sha256:5f8fad3c1619 -->

///
<!-- stay:S9BeiuIg hash=sha256:732c4e971163 -->

## What is "Form Data" { #what-is-form-data }
<!-- stay:mroL62cF hash=sha256:bb916b00aa4e -->

The way HTML forms (`<form></form>`) send the data to the server normally uses a "special" encoding for that data, it's different from JSON.
<!-- stay:E65koL2w hash=sha256:8c66f697de4d -->

**FastAPI** will make sure to read that data from the right place instead of JSON.
<!-- stay:AD8rUmHu hash=sha256:d112c060cdad -->

/// note | Technical Details
<!-- stay:bOWd16NZ hash=sha256:28fbbcad08d1 -->

Data from forms is normally encoded using the "media type" `application/x-www-form-urlencoded` when it doesn't include files.
<!-- stay:kg5Coog6 hash=sha256:2e9260d09c74 -->

But when the form includes files, it is encoded as `multipart/form-data`. If you use `File`, **FastAPI** will know it has to get the files from the correct part of the body.
<!-- stay:s0BmqTy1 hash=sha256:2eb9c2782104 -->

If you want to read more about these encodings and form fields, head to the [<abbr title="Mozilla Developer Network">MDN</abbr> web docs for `POST`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST).
<!-- stay:6Do75qKm hash=sha256:806909d5f517 -->

///
<!-- stay:zvOW3r19 hash=sha256:732c4e971163 -->

/// warning
<!-- stay:i5VvQsX5 hash=sha256:98e5a9621bab -->

You can declare multiple `File` and `Form` parameters in a *path operation*, but you can't also declare `Body` fields that you expect to receive as JSON, as the request will have the body encoded using `multipart/form-data` instead of `application/json`.
<!-- stay:IjIpd8mr hash=sha256:94e04531ad8a -->

This is not a limitation of **FastAPI**, it's part of the HTTP protocol.
<!-- stay:O5TE6Kkr hash=sha256:9f0333b468cc -->

///
<!-- stay:3loObTn5 hash=sha256:732c4e971163 -->

## Optional File Upload { #optional-file-upload }
<!-- stay:xyKCaxN2 hash=sha256:3082b05b9f0c -->

You can make a file optional by using standard type annotations and setting a default value of `None`:
<!-- stay:EzpZqQjl hash=sha256:7ca05a0a4298 -->

{* ../../docs_src/request_files/tutorial001_02_an_py310.py hl[9,17] *}
<!-- stay:2EEwtUuj hash=sha256:ead2ecad5f81 -->

## `UploadFile` with Additional Metadata { #uploadfile-with-additional-metadata }
<!-- stay:dIFxI5ex hash=sha256:7c20af254a7e -->

You can also use `File()` with `UploadFile`, for example, to set additional metadata:
<!-- stay:kCSJCQF4 hash=sha256:f4bc9437936e -->

{* ../../docs_src/request_files/tutorial001_03_an_py310.py hl[9,15] *}
<!-- stay:PYyRIuj7 hash=sha256:59ecc76281b6 -->

## Multiple File Uploads { #multiple-file-uploads }
<!-- stay:F1lcAZUW hash=sha256:db531c5d8935 -->

It's possible to upload several files at the same time.
<!-- stay:5fr26Er8 hash=sha256:305c81e86ebe -->

They would be associated to the same "form field" sent using "form data".
<!-- stay:LGGLeqMA hash=sha256:88a22fa5d8ca -->

To use that, declare a list of `bytes` or `UploadFile`:
<!-- stay:cJTLkahx hash=sha256:c216fb317cd4 -->

{* ../../docs_src/request_files/tutorial002_an_py310.py hl[10,15] *}
<!-- stay:ZEVXXT36 hash=sha256:fe9a463d9937 -->

You will receive, as declared, a `list` of `bytes` or `UploadFile`s.
<!-- stay:bQP2J4N9 hash=sha256:bb845774085d -->

/// note | Technical Details
<!-- stay:REX8PUO8 hash=sha256:28fbbcad08d1 -->

You could also use `from starlette.responses import HTMLResponse`.
<!-- stay:cS4ISGmR hash=sha256:cd26b890517a -->

**FastAPI** provides the same `starlette.responses` as `fastapi.responses` just as a convenience for you, the developer. But most of the available responses come directly from Starlette.
<!-- stay:8pCGWn1F hash=sha256:1d9ba437732e -->

///
<!-- stay:K20vuWEd hash=sha256:732c4e971163 -->

### Multiple File Uploads with Additional Metadata { #multiple-file-uploads-with-additional-metadata }
<!-- stay:zL8Wf11d hash=sha256:a319d1ad8fb7 -->

And the same way as before, you can use `File()` to set additional parameters, even for `UploadFile`:
<!-- stay:pLTmpMsV hash=sha256:799ded965c69 -->

{* ../../docs_src/request_files/tutorial003_an_py310.py hl[11,18:20] *}
<!-- stay:6me1TYLE hash=sha256:b14e4c6d2304 -->

## Recap { #recap }
<!-- stay:OEsuklN4 hash=sha256:40a194d2a8b0 -->

Use `File`, `bytes`, and `UploadFile` to declare files to be uploaded in the request, sent as form data.
<!-- stay:Om4X0ggG hash=sha256:24512e58d0b1 -->
