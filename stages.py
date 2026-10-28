"""Placeholder stages of the RF chain.

Each class states its job, its inputs and outputs, and where the real
implementation will come from. Bodies are TODOs: this file is the plan.
"""

import numpy as np
import pmt
from gnuradio import gr


class CaptureRing(gr.sync_block):
    """2. Capture: keep the last few seconds of raw I/Q from every channel.

    In:  N complex streams (one per antenna channel), timestamped by the SDR.
    Out: nothing on the stream; later stages ask it for snippets by time.
    Real version: C++, preallocated lock-free ring buffer, never blocks.
    """

    def __init__(self, n_channels, seconds):
        gr.sync_block.__init__(self, "capture_ring",
                               in_sig=[np.complex64] * n_channels, out_sig=None)

    def snippet(self, t_start, t_stop, channels):
        """Return raw I/Q between two times, for analysis or direction finding."""
        raise NotImplementedError  # TODO

    def work(self, input_items, output_items):
        # TODO: copy samples into the ring with their timestamps (rx_time tags)
        return len(input_items[0])


class Detector(gr.sync_block):
    """4. Detect: find energy above the local noise floor (CFAR).

    In:  power-spectrum frames (float vectors of fft_len).
    Out: message "detections": {time, freq_hz, bw_hz, snr_db} per signal found.
    Real version: C++ out-of-tree block (gr-burstsense).
    """

    def __init__(self, fft_len, samp_rate, center_freq):
        gr.sync_block.__init__(self, "detector", in_sig=[(np.float32, fft_len)], out_sig=None)
        self.message_port_register_out(pmt.intern("detections"))

    def work(self, input_items, output_items):
        # TODO: CFAR threshold per bin, group bins, publish one message per signal
        return len(input_items[0])


class MessageStage(gr.basic_block):
    """Base for stages that take one message in and send one message out."""

    def __init__(self, name, out_port):
        gr.basic_block.__init__(self, name, in_sig=None, out_sig=None)
        self.out_port = pmt.intern(out_port)
        self.message_port_register_in(pmt.intern("in"))
        self.message_port_register_out(self.out_port)
        self.set_msg_handler(pmt.intern("in"), self.handle)

    def handle(self, msg):
        result = self.process(pmt.to_python(msg))
        if result is not None:
            self.message_port_pub(self.out_port, pmt.to_pmt(result))

    def process(self, item):
        raise NotImplementedError


class Segmenter(MessageStage):
    """5. Segment: join per-frame detections into bursts (start, stop, band)."""

    def __init__(self):
        MessageStage.__init__(self, "segmenter", "bursts")

    def process(self, detection):
        return None  # TODO: track open bursts, emit one when it ends


class Characteriser(MessageStage):
    """6. Characterise: carrier, bandwidth, symbol rate, signal type (later: ML).

    Pulls the burst's raw I/Q from the capture ring.
    """

    def __init__(self, capture):
        MessageStage.__init__(self, "characteriser", "emitters")
        self.capture = capture

    def process(self, burst):
        return None  # TODO: estimate parameters, classify, attach confidence


class Calibration:
    """Per-channel phase and gain correction, refreshed after every retune.

    Real version: inject a common reference, measure each channel against channel 0.
    """

    def correct(self, multichannel_iq):
        raise NotImplementedError  # TODO


class DirectionFinder(MessageStage):
    """7. Direction finding: bearing from the coherent multi-channel snippet."""

    def __init__(self, capture, n_channels):
        MessageStage.__init__(self, "direction_finder", "bearings")
        self.capture = capture
        self.calibration = Calibration()

    def process(self, emitter):
        return None  # TODO: snippet -> calibrate -> MUSIC/Bartlett -> bearing + uncertainty


class Reporter(MessageStage):
    """8. Report: one compact, versioned message per emitter for the decision module."""

    def __init__(self):
        MessageStage.__init__(self, "reporter", "reports")

    def process(self, bearing):
        # Planned fields: time, freq_hz, bw_hz, type, confidence, bearing_deg,
        # bearing_uncertainty_deg, node_id, schema_version
        return None  # TODO
