#!/usr/bin/env python3

"""
measure internet speed and graph with rrdtool


Florian Heinle <launchpad@planet-tiax.de>
MIT Licence
"""


import configparser
import datetime
import logging
import os
import subprocess
import tempfile

from dateutil import tz
from PIL import Image
import requests
import speedtest


def create_rrd_file():
    '''create the rrd database with values from settings'''
    subprocess.run(
        [
            'rrdtool', 'create',
            RRD_FNAME,
            '--step=1800',
            'DS:ping:GAUGE:3600:0:{}'.format(SETTINGS['ping']['max']),
            'DS:upload:GAUGE:3600:0:{}'.format(SETTINGS['upload']['max']),
            'DS:download:GAUGE:3600:0:{}'.format(SETTINGS['download']['max']),
            'RRA:MAX:0.5:2:168'
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
            RRD_FNAME,
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
            '-w {}'.format(SETTINGS['graph']['width']),
            '-h {}'.format(SETTINGS['graph']['height']),
            '-u {}'.format(SETTINGS[data_set]['max']),
            '--start=end-1w',
            'DEF:{}={}:{}:MAX'.format(data_set, RRD_FNAME, data_set),
            'LINE1:{}#{}:{}'.format(data_set, SETTINGS[data_set]['color'], data_set.capitalize()),
            'HRULE:{}#FF0000'.format(SETTINGS[data_set]['min'])
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
    combined_path = GRAPH_FNAME
    combined_image.save(combined_path)

    for no_longer_needed in (ping_graph, download_graph, upload_graph):
        os.unlink(no_longer_needed)
    return combined_path


def upload(fname):
    '''upload the graph image using HTTP PUT, i.e. using WebDAV

    return the HTTP status code. For NextCloud, 204 is ok '''
    http_request = requests.put(SETTINGS['graph_upload']['url'] + '/graph.png',
        auth=(SETTINGS['graph_upload']['user'], SETTINGS['graph_upload']['password']),
        data=open(fname, 'rb').read()
    )
    return http_request.status_code


def load_settings(settings_fname='settings.ini'):
    '''load config settings from ini file'''
    ini_file = configparser.ConfigParser()
    ini_file.read('settings.ini')

    # dependencies
    # uploading needs upload settings
    if ini_file.getboolean('graph_upload', 'enable'):
        for setting in ('url', 'user', 'password'):
            if not ini_file.has_option('graph_upload', setting):
                raise RuntimeError('Uploading enabled but not all upload settings present')
    return ini_file

SETTINGS = load_settings()
RRD_FNAME = './data/speed.rrd'
GRAPH_FNAME = './data/graph.png'

def main():
    '''when started from cli'''
 
    logging.basicConfig(
        level=getattr(logging, SETTINGS['general']['log_level'].upper()),
        format='%(asctime)s %(message)s'
    )
    main_logger = logging.getLogger('speedchart')

    if not os.path.isfile(RRD_FNAME):
        main_logger.debug(
            "RRD file %s not found, creating",
            RRD_FNAME
        )
        create_rrd_file()
    else:
        main_logger.debug(
            "RRD file %s present, continuing",
            RRD_FNAME
        )

    if SETTINGS.getboolean('general', 'measure'):
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

    if SETTINGS.getboolean('graph_upload', 'enable'):
        main_logger.debug('Uploading graph')
        response_code = upload(final_graph)
        main_logger.debug('Upload response code: %s', response_code)
    else:
        main_logger.debug('Not uploading graph')


if __name__ == '__main__':
    main()
