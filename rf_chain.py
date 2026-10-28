"""RF chain: the design at a glance.

    SDR front-end -> capture -> channelise -> detect -> segment -> characterise
        -> direction finding -> report -> decision module (separate process)

Read this file top to bottom: it is the wiring. Real GNU Radio blocks are used
where GNU Radio already provides the stage; everything else is a placeholder
in stages.py. This sketch shows the design; it is not meant to run yet.
"""

from gnuradio import blocks, fft, filter, gr, uhd, zeromq
from gnuradio.fft import window

import stages

# ---- Settings (illustrative values) -------------------------------------------
SAMP_RATE = 50e6        # complex samples per second, per channel
CENTER_FREQ = 2.44e9    # 2.4 GHz band: drone control and video links
GAIN_DB = 30            # fixed gain: thresholds and bearings need stable gain
N_CHANNELS = 4          # coherent receive channels for direction finding
FFT_LEN = 1024          # spectrum frames for detection
N_SUBBANDS = 8          # channeliser output bands
DECISION_ADDR = "tcp://*:5555"  # where detection reports are published


def make_sdr_source():
    """1. SDR front-end: tuning, gain, sample rate, timing (real UHD API)."""
    src = uhd.usrp_source(
        "",  # device address, e.g. "addr=192.168.10.2"
        uhd.stream_args(cpu_format="fc32", otw_format="sc16",
                        channels=list(range(N_CHANNELS))))
    src.set_clock_source("external")   # 10 MHz from a GPSDO
    src.set_time_source("external")    # PPS from the GPSDO
    src.set_samp_rate(SAMP_RATE)
    for ch in range(N_CHANNELS):
        src.set_center_freq(CENTER_FREQ, ch)
        src.set_gain(GAIN_DB, ch)
    # TODO: timed tuning so all channels retune together (phase coherence)
    # TODO: calibration after every retune (see stages.Calibration)
    return src


class RfChain(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self, "RF chain")

        # 1. Front-end
        sdr = make_sdr_source()

        # 2. Capture: keep recent raw I/Q of all channels for later analysis
        capture = stages.CaptureRing(N_CHANNELS, seconds=2.0)

        # 3. Channelise channel 0 into sub-bands (real GNU Radio block)
        channeliser = filter.pfb.channelizer_ccf(N_SUBBANDS, [], 2.0)  # TODO: design taps

        # 4. Detect: spectrum frames -> CFAR (FFT stages are real GNU Radio blocks)
        to_frames = blocks.stream_to_vector(gr.sizeof_gr_complex, FFT_LEN)
        spectrum = fft.fft_vcc(FFT_LEN, True, window.blackmanharris(FFT_LEN), True)
        power = blocks.complex_to_mag_squared(FFT_LEN)
        detector = stages.Detector(FFT_LEN, SAMP_RATE, CENTER_FREQ)

        # 5-8. Message stages: each detection flows on as a small dictionary
        segmenter = stages.Segmenter()
        characteriser = stages.Characteriser(capture)
        direction = stages.DirectionFinder(capture, N_CHANNELS)
        reporter = stages.Reporter()

        # 9. Out to the decision module (real GNU Radio ZeroMQ block)
        to_decision = zeromq.pub_msg_sink(DECISION_ADDR)

        # ---- Wiring: streams --------------------------------------------------
        for ch in range(N_CHANNELS):
            self.connect((sdr, ch), (capture, ch))
        self.connect((sdr, 0), channeliser)
        for band in range(N_SUBBANDS):
            self.connect((channeliser, band), blocks.null_sink(gr.sizeof_gr_complex))
            # TODO: per-band processing; detection below runs on the full band
        self.connect((sdr, 0), to_frames, spectrum, power, detector)

        # ---- Wiring: messages -------------------------------------------------
        self.msg_connect(detector, "detections", segmenter, "in")
        self.msg_connect(segmenter, "bursts", characteriser, "in")
        self.msg_connect(characteriser, "emitters", direction, "in")
        self.msg_connect(direction, "bearings", reporter, "in")
        self.msg_connect(reporter, "reports", to_decision, "in")


if __name__ == "__main__":
    RfChain().run()
