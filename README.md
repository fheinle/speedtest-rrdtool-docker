# speedchart

This repo contains a small script and a `Dockerfile` to use `speedtest-cli`
and record its results in a `rrdtool` database for record keeping and graphing.

Optionally results may be upload using `HTTP PUT` (WebDAV)

[There's a German blog post explaining things more in depth](https://blog.florianheinle.de/speedtest-rrdtool-docker).

## Version

This is in alpha development without any versioning whatsoever. Since it's
a hobby project to scratch an itch, sensible versioning will only start after
some stability has been reached.

## Getting started

```shell
$ git clone https://github.com/fheinle/speedtest-rrdtool-docker
$ cp settings.env.sample settings.env && vi settings.env
```

With Docker:

```shell
$ docker build -t speedchart .
$ docker create --name speedchart -v $(pwd)/data:/data --env-file=$(pwd)/settings.env speedchart
$ docker start speedchart
```

Or, without Docker:

```shell
$ sudo apt install rrdtool && sudo pip3 install requests python-dateutil speedtest-cli
$ vi settings.env
# add export= in front of everey line
$ ./measure.py
```


## Settings

Configuration takes place via environment variables for the script. You may set
those on the command line or enter them into a file, see examples above on how
to do that.

| Variable       | Default           | Beschreibung                                |
|----------------|-------------------|---------------------------------------------|
| `DOWNLOAD_MAX` | `1000`            | max download speed                          |
| `GRAPH_FNAME`  | `/data/graph.png` | where to save the graph png                 |
| `GRAPH_HEIGHT` | `300`             | graph height                                |
| `GRAPH_WIDTH`  | `600`             | graph width                                 |
| `LINE_POS`     | `600`             | where to put the red line                   |
| `LOGLEVEL`     | `INFO`            | output verbosity, can be `DEBUG`            |
| `RRD_FNAME`    | `/data/speed.rrd` | where to save the database file             |
| `TARGET_PASS`  | -                 | HTTP auth password                          |
| `TARGET_URL`   | -                 | where to upload the graph png               |
| `TARGET_USER`  | -                 | HTTP auth username                          |
| `UPLOAD_GRAPH` | True              | Everything except `false` uploads the graph |
| `UPLOAD_MAX`   | `50`              | max upload speed                            |

# Copyright

* Florian Heinle <launchpad@planet-tiax.de>

This project is licensed under the MIT License.
