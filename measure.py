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

from dateutil import tz
import requests
import speedtest

DEFAULTS = dict(
    LOGLEVEL='info',
    GRAPH_FNAME='/data/graph.png',
    RRD_FNAME='/data/speed.rrd',
    GRAPH_WIDTH=600,
    GRAPH_HEIGHT=300,
    UPLOAD_MAX=50,
    DOWNLOAD_MAX=1000,
    LINE_POS=600,
    UPLOAD_GRAPH=True
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
    subprocess.run(
        [
            'rrdtool', 'graph',
            SETTINGS['GRAPH_FNAME'],
            '-w {}'.format(SETTINGS['GRAPH_WIDTH']),
            '-h {}'.format(SETTINGS['GRAPH_HEIGHT']),
            '-u {}'.format(SETTINGS['DOWNLOAD_MAX']),
            '--start=end-1w',
            'DEF:ping={}:ping:MAX'.format(SETTINGS['RRD_FNAME']),
            'DEF:upload={}:upload:MAX'.format(SETTINGS['RRD_FNAME']),
            'DEF:download={}:download:MAX'.format(SETTINGS['RRD_FNAME']),
            'LINE1:ping#0000FF:Ping (s)',
            'LINE1:upload#FF0000:Upload (Mbit/s)',
            'LINE1:download#99FF00:Download (Mbit/s)',
            'HRULE:{}#FF0000'.format(SETTINGS['LINE_POS'])
        ]
    )


def upload_graph():
    '''upload the graph image using HTTP PUT, i.e. using WebDAV

    return the HTTP status code. For NextCloud, 204 is ok '''
    http_request = requests.put(
        SETTINGS['TARGET_URL'],
        auth=(SETTINGS['TARGET_USER'], SETTINGS['TARGET_PASS']),
        data=open(SETTINGS['GRAPH_FNAME'], 'rb').read()
    )
    return http_request.status_code


SETTINGS = {}


def main():
    '''when started from cli'''
    for setting in (
            'LOGLEVEL',
            'GRAPH_FNAME', 'RRD_FNAME',
            'GRAPH_WIDTH', 'GRAPH_HEIGHT',
            'UPLOAD_MAX', 'DOWNLOAD_MAX', 'LINE_POS',
            'TARGET_URL', 'TARGET_USER', 'TARGET_PASS'
    ):
        SETTINGS[setting] = os.environ.get(setting, DEFAULTS.get(setting))
    SETTINGS['UPLOAD_GRAPH'] = not os.environ.get('UPLOAD_GRAPH') == 'false'

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
    graph_rrd_file()
    if SETTINGS['UPLOAD_GRAPH']:
        main_logger.debug('Uploading graph')
        response_code = upload_graph()
        main_logger.debug('Upload response code: %s', response_code)
    else:
        main_logger.debug('Not uploading graph')


if __name__ == '__main__':
    main()
