from ryu.app.simple_switch_13 import SimpleSwitch13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.lib import hub
import csv
import time

class FlowStatsRealTime(SimpleSwitch13):
    """
    Real-time SDN Flow Statistics Collector
    Extends simple_switch_13 to ensure correct packet forwarding
    while periodically collecting flow-level statistics.
    """

    def __init__(self, *args, **kwargs):
        super(FlowStatsRealTime, self).__init__(*args, **kwargs)

        # Store connected switches
        self.datapaths = {}

        # Start monitoring thread
        self.monitor_thread = hub.spawn(self.monitor)

        # Open CSV file for real-time dataset creation
        self.csv_file = open("flow_stats.csv", "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)

        # CSV header
        self.csv_writer.writerow([
            "timestamp",
            "dpid",
            "packet_count",
            "byte_count",
            "duration_sec"
        ])

    # Track datapath (switch) state
    @set_ev_cls(ofp_event.EventOFPStateChange, MAIN_DISPATCHER)
    def state_change_handler(self, ev):
        datapath = ev.datapath
        self.datapaths[datapath.id] = datapath

    # Periodically request flow statistics (REAL-TIME)
    def monitor(self):
        while True:
            for dp in self.datapaths.values():
                self.request_flow_stats(dp)
            hub.sleep(1)   # 🔴 Real-time polling every 1 second

    def request_flow_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    # Receive flow statistics reply
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        now = time.time()
        dpid = ev.msg.datapath.id

        for flow in ev.msg.body:
            if flow.priority == 0:
                continue

            self.csv_writer.writerow([
                now,
                dpid,
                flow.packet_count,
                flow.byte_count,
                flow.duration_sec
            ])

        self.csv_file.flush()
