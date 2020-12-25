import argparse
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import math

from matplotlib.ticker import StrMethodFormatter
from collections import deque
from pathlib import Path
from glob import glob

BLUE = deque(['#0000FF', '#0000B3', '#0081B3',
              '#14293D', '#A7DFE2', '#8ED9CD'])
RED = deque(['#FF0000', '#950000', '#FF005A',
             '#A9385A', '#C95DB4', 'orange',
             '#FF0000', '#950000', '#FF005A',
             '#A9385A', '#C95DB4', 'orange'])
GREEN = deque(['#00FF00', '#008D00', '#005300',
               '#00FF72', '#76FF00', '#24A547',
               '#00FF00', '#008D00', ])
ORANGE = deque(['#FF8100', '#FFA700', '#FF6D26'])
YELLOW = deque(['#FFFF00', '#DCFF20', '#DCC05A'])
PURPLE = deque(['#6A00CD', '#A100CD', '#7653DE'])


def analyze_pcap(filename: str) -> (dict, str):
    tx_packets = 0
    rx_packets = 0

    with open(filename) as f:
        data = json.load(f)

        # Associate each ACK offset with a timestamp
        for packet in data:
            udp = packet['_source']['layers']['udp']
            srcport = udp['udp.srcport']
            dstport = udp['udp.dstport']
            time = float(udp['Timestamps']['udp.time_relative']) * 1000

            # receive packet
            if srcport == '30000':
                rx_packets += 1

            # send packet
            else:
                tx_packets += 1

    return {
        'tx_packets': tx_packets,
        'rx_packets': rx_packets
    }, filename


def analyze_qlog(filename: str) -> (dict, str):
    tx_packets = 0
    rx_packets = 0
    lost_packets = []

    with open(filename) as f:
        data = json.load(f)
        traces = data['traces'][0]
        events = traces['events']
        if 'configuration' in traces:
            time_units = traces['configuration']['time_units']
        else:
            time_units = 'ms'

        prev_rx_ptype = None
        prev_rx_pn = None
        first_time = None

        # Store all stream packets received by client
        for event in events:
            if not event:
                continue

            if time_units == 'ms':
                ts = int(event[0])
            else:
                ts = int(event[0]) / 1000

            event_type = event[2]
            event_data = event[3]

            if event_type.lower() == 'packet_sent' and first_time is None:
                first_time = ts

            if first_time is None:
                continue

            ts -= first_time

            if event_type.lower() == 'packet_received':
                rx_packets += 1

                ptype = event_data['packet_type']
                pn = int(event_data['header']['packet_number'])

                if prev_rx_pn is not None \
                        and ptype == prev_rx_ptype \
                        and pn != prev_rx_pn + 1:
                    lost_packets.append(prev_rx_pn + 1)

                prev_rx_ptype = ptype
                prev_rx_pn = pn

            if event_type.lower() == 'packet_sent':
                tx_packets += 1

    return {
        'tx_packets': tx_packets,
        'rx_packets': rx_packets,
        'lost_packets': lost_packets
    }, filename


def analyze_netlog(filename: str) -> (dict, str):
    tx_packets = 0
    rx_packets = 0
    lost_packets = []

    with open(filename) as f:
        data = json.load(f)

        constants = data['constants']
        events = data['events']
        event_types = {v: k for k,
                       v in constants['logEventTypes'].items()}
        source_types = {v: k for k,
                        v in constants['logSourceType'].items()}
        phases = {v: k for k,
                  v in constants['logEventPhase'].items()}

        start_time = None
        prev_rx_pn = None
        prev_rx_pt = None

        for event in events:
            # source_type in string
            source_type = source_types[event['source']['type']]
            # source id
            source_id = event['source']['id']
            # event_type in string
            event_type = event_types[event['type']]
            # phase in string
            phase = phases[event['phase']]

            if 'params' not in event:
                continue

            # params
            params = event['params']
            # event time
            event_time = int(event['time'])

            if start_time is not None:
                ts = event_time - start_time

            if (event_type == 'TCP_CONNECT' or event_type == 'QUIC_SESSION') and phase == 'PHASE_BEGIN':
                if start_time is None:
                    start_time = event_time

            if event_type == 'QUIC_SESSION_PACKET_SENT':
                tx_packets += 1

            if event_type == 'QUIC_SESSION_UNAUTHENTICATED_PACKET_HEADER_RECEIVED':
                pn = params['packet_number']
                pt = params['long_header_type'] if 'long_header_type' in params else '1-RTT'

                if prev_rx_pn is not None \
                        and prev_rx_pt is not None \
                        and pt == prev_rx_pt \
                        and pn != prev_rx_pn + 1:
                    lost_packets.append(prev_rx_pn + 1)

                prev_rx_pt = pt
                prev_rx_pn = pn

                rx_packets += 1

            if event_type == 'QUIC_SESSION_STREAM_FRAME_RECEIVED':
                if params['stream_id'] != 0:
                    continue

    return {
        'tx_packets': tx_packets,
        'rx_packets': rx_packets,
        'lost_packets': lost_packets
    }, filename


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qlog")
    parser.add_argument("--netlog")
    parser.add_argument("--pcap")

    args = parser.parse_args()

    qlog_data = None
    pcap_data = None
    netlog_data = None

    if args.qlog is not None:
        qlogpath = Path.joinpath(Path.cwd(), args.qlog)
        qlog_data = analyze_qlog(qlogpath)

    if args.netlog is not None:
        netlogpath = Path.joinpath(Path.cwd(), args.netlog)
        netlog_data = analyze_netlog(netlogpath)

    if args.pcap is not None:
        pcappath = Path.joinpath(Path.cwd(), args.pcap)
        pcap_data = analyze_pcap(pcappath)

    print('qlog', qlog_data)
    print('netlog', netlog_data)
    print('pcap', pcap_data)


if __name__ == "__main__":
    main()
