# speedchart

This repo contains a small script and a `Dockerfile` to use `speedtest-cli` and
record its results in a `rrdtool` database for record keeping and graphing.

Optionally results may be upload using `HTTP PUT` (WebDAV)

## Version

This is in alpha development without any versioning whatsoever. Since it's
a hobby project to scratch an itch, sensible versioning will only start after
some stability has been reached.

## Getting started

```shell
$ git clone https://github.com/fheinle/speedtest-rrdtool-docker
$ cp settings.ini.sample settings.ini && vi settings.ini
```

With Docker:

```shell
$ docker build -t speedchart .
$ docker create --name speedchart -v $(pwd)/data:/data -v $(pwd)/settings.ini:/settings.ini speedchart
$ docker start speedchart
```

Or, without Docker:

```shell
$ sudo apt install rrdtool && sudo pip3 install requests python-dateutil speedtest-cli
$ mkdir data # for the rrd file and graph.png
$ vi settings.ini
$ ./measure.py
```


## Uploading the graph

This script comes with basic upload functionality using `HTTP PUT`, good enough
to upload the resulting graph to say a NextCloud instance.

To enable uploading the graph, edit the `settings.ini` file:

```ini
[graph_upload]
enable = true
url = https://subdomain.domain.tld/directory/
user = username
password = password
```

Make sure to pass a *directory* for the URL since `graph.png` is appended
automatically.

## Settings

Configuration takes place via an ini file the script expects in the same
directory. When using docker, mount that ini file into the container. This
allows you to change the settings without re-building the container.

| Section                      | Setting     | Description                                                        |
|------------------------------|-------------|--------------------------------------------------------------------|
| `general`                    | `log_level` | Choose `debug` or `info`                                           |
|                              | `measure`   | Set to `false` if you want to skip measuring (for debugging)       |
| `graph`                      | `width`     | total width of the graph                                           |
|                              | `height`    | height of one graph, i.e. total height = 3x `height`               |
| `graph_upload`               | `enable`    | Enable uploading `graph.png` via webdav                            |
|                              | `url`       | The *directory* where `graph.png` will be uploaded to (`HTTP PUT`) |
|                              | `user`      | Username used for HTTP Authentication                              |
|                              | `password`  | Password used for HTTP Authentication                              |
| `download`, `upload`, `ping` | `min`       | Graphs start at 0 but there's a line at `min`                      |
|                              | `max`       | Graphs go up to this value                                         |
|                              | `color`     | Which color the graph line should have                             |

### Changing the `max` values

Be careful when changing the `max` values. The database `rrdtool` uses is
initialized with this value too and changing the `max` requires starting over
with the rrd database. 

# Copyright

* Florian Heinle <launchpad@planet-tiax.de>

This project is licensed under the MIT License.
