# 80by24

See https://80by24.net and the READMEs for [client](run80by24-client/README.rst) and [server](run80by24-server/README.rst).

The directory structure for this repo is a little elaborate.
The client, server and common files each have the structure of a standard Python distribution. Their top-level names
`run80by24-client`, `run80by24-server` and `run80by24-common` correspond to the names under which they are known by `pip`.
Within these, the source files reside under a namespace directory `run80by24` and subpackage directory `client`,
`server` or `common`.

So, the client source is at [run80by24-client/run80by24/client/\_\_main\_\_.py](run80by24-client/run80by24/client/__main__.py)
