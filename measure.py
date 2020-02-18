#!/usr/bin/env python3

"""
measure internet speed and graph with rrdtool


Florian Heinle <launchpad@planet-tiax.de>
MIT Licence
"""


import datetime
import logging
import os
import subprocess
import tempfile

from dateutil import tz
from PIL import Image
import requests
import speedtest

DEFAULTS = dict(
    DOWNLOAD_MIN=600,
    DOWNLOAD_MAX=1000,
    GRAPH_PATH='/data/',
    GRAPH_HEIGHT=200,
    GRAPH_WIDTH=400,
    LINE_POS=600,
    LOGLEVEL='info',
    MEASURE=True,
    PING_MIN=30,
    PING_MAX=200,
    RRD_FNAME='/data/speed.rrd',
    UPLOAD_GRAPH=True,
    UPLOAD_MIN=15,
    UPLOAD_MAX=50,
)


def create_rrd_file():
    '''create the rrd database with values from settings'''
    subprocess.run(
        [
            'rrdtool', 'create',
            SETTINGS['RRD_FNAME'],
            'DS:ping:GAUGE:3600:0:200',
            'DS:upload:GAUGE:3600:0:{}'.format(SETTINGS['UPLOAD_MAX']),
            'DS:download:GAUGE:3600:0:{}'.format(SETTINGS['DOWNLOAD_MAX']),
            'RRA:MAX:0.5:1:168'
        ]
    )


def run_speedtest():
    '''perform the ping, download and upload test

    return the results as a dict'''
    speed_tester = speedtest.Speedtest()
    speed_tester.get_best_server()
    speed_tester.download()
    speed_tester.upload()

    utc_timestamp = datetime.datetime.strptime(
        speed_tester.results.timestamp,
        '%Y-%m-%dT%H:%M:%S.%fZ'
    ).replace(tzinfo=tz.tzutc())

    return dict(
        timestamp=utc_timestamp.astimezone(tz.tzlocal()).timestamp(),
        ping=round(speed_tester.results.ping),
        download=round(speed_tester.results.download / 1024 / 1024, 2),
        upload=round(speed_tester.results.upload / 1024 / 1024, 2)
    )


def update_rrd_file(timestamp, ping, download, upload):
    '''update the rrd file with a measurement from run_speedtest'''
    subprocess.run(
        [
            'rrdtool', 'update',
            SETTINGS['RRD_FNAME'],
            "{ts}:{ping}:{ul}:{dl}".format(
                ts=timestamp,
                ping=ping,
                ul=upload,
                dl=download
            )
        ]
    )


def graph_rrd_file():
    '''graph the rrd file according to settings'''
    graph_images = {}
    for data_set in ('ping', 'upload', 'download'):
        image_tmpfile_name = tempfile.mkstemp(suffix='.png', prefix=data_set)[1]
        graph_data_set(data_set, image_tmpfile_name)
        graph_images["{}_graph".format(data_set)] = image_tmpfile_name
    return graph_images


def graph_data_set(data_set, image_fname):
    '''graph the given dataset from the rrd file according to settings'''
    subprocess.run(
        [
            'rrdtool', 'graph',
            image_fname,
            '-w {}'.format(SETTINGS['GRAPH_WIDTH']),
            '-h {}'.format(SETTINGS['GRAPH_HEIGHT']),
            '-u {}'.format(SETTINGS["{}_MAX".format(data_set.upper())]),
            '--start=end-1w',
            'DEF:{}={}:{}:MAX'.format(data_set, SETTINGS['RRD_FNAME'], data_set),
            'LINE1:{}#0000FF:{}'.format(data_set, data_set.capitalize()),
            'HRULE:{}#FF0000'.format(SETTINGS["{}_MIN".format(data_set.upper())]),
        ],
        stdout=subprocess.PIPE
    )


def merge_images(ping_graph, download_graph, upload_graph):
    '''merge three graphs into one for easier handling'''
    ping_image = Image.open(ping_graph)
    download_image = Image.open(download_graph)
    upload_image = Image.open(upload_graph)
    combined_size = (
        ping_image.size[0],
        ping_image.size[1] + download_image.size[1] + upload_image.size[1]
    )
    combined_image = Image.new('RGB', combined_size)
    combined_image.paste(im=download_image, box=(0,0))
    combined_image.paste(im=upload_image, box=(0, download_image.size[1]))
    combined_image.paste(im=ping_image, box=(0, ping_image.size[1] + download_image.size[1]))
    combined_path = os.path.join(SETTINGS['GRAPH_PATH'], 'graph.png')
    combined_image.save(combined_path)

    for no_longer_needed in (ping_graph, download_graph, upload_graph):
        os.unlink(no_longer_needed)
    return combined_path


def upload(fname):
    '''upload the graph image using HTTP PUT, i.e. using WebDAV

    return the HTTP status code. For NextCloud, 204 is ok '''
    http_request = requests.put(SETTINGS['TARGET_URL'] + '/graph.png',
        auth=(SETTINGS['TARGET_USER'], SETTINGS['TARGET_PASS']),
        data=open(fname, 'rb').read()
    )
    return http_request.status_code


SETTINGS = {}


def main():
    '''when started from cli'''
    for setting in (
            'LOGLEVEL',
            'GRAPH_PATH', 'RRD_FNAME',
            'GRAPH_WIDTH', 'GRAPH_HEIGHT',
            'UPLOAD_MAX', 'DOWNLOAD_MAX', 'PING_MAX',
            'UPLOAD_MIN', 'DOWNLOAD_MIN', 'PING_MIN'
    ):
        SETTINGS[setting] = os.environ.get(setting, DEFAULTS.get(setting))
    SETTINGS['MEASURE'] = not os.environ.get('MEASURE') == 'false'
    SETTINGS['UPLOAD_GRAPH'] = not os.environ.get('UPLOAD_GRAPH') == 'false'
    if SETTINGS['UPLOAD_GRAPH']:
        for upload_setting in ('TARGET_URL', 'TARGET_USER', 'TARGET_PASS'):
            SETTINGS[upload_setting] = os.environ.get(upload_setting)

    logging.basicConfig(
        level=getattr(logging, SETTINGS['LOGLEVEL'].upper()),
        format='%(asctime)s %(message)s'
    )
    main_logger = logging.getLogger('speedchart')

    if not os.path.isfile(SETTINGS['RRD_FNAME']):
        main_logger.debug(
            "RRD file %s not found, creating",
            SETTINGS['RRD_FNAME']
        )
        create_rrd_file()
    else:
        main_logger.debug(
            "RRD file %s present, continuing",
            SETTINGS['RRD_FNAME']
        )

    if SETTINGS['MEASURE']:
        main_logger.debug('Starting speedtest')
        speedtest_results = run_speedtest()
        main_logger.info(
            "Download: %s Upload: %s Ping: %s",
            speedtest_results['download'],
            speedtest_results['upload'],
            speedtest_results['ping']
        )
        update_rrd_file(
            timestamp=speedtest_results['timestamp'],
            download=speedtest_results['download'],
            upload=speedtest_results['upload'],
            ping=speedtest_results['ping']
        )
    main_logger.debug('Updating graph')
    graph_images = graph_rrd_file()
    final_graph = merge_images(**graph_images)

    if SETTINGS['UPLOAD_GRAPH']:
        main_logger.debug('Uploading graph')
        response_code = upload(final_graph)
        main_logger.debug('Upload response code: %s', response_code)
    else:
        main_logger.debug('Not uploading graph')


if __name__ == '__main__':
    main()
