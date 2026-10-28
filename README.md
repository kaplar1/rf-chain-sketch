# RF chain sketch

A small design skeleton for detecting drones from their radio signals with GNU Radio.
It shows the structure of the chain, not working software: real GNU Radio blocks where
they exist, named placeholders for the parts still to be built.

```
SDR front-end -> capture -> channelise -> detect -> segment -> characterise
    -> direction finding -> report -> decision module
```

| # | Stage | Where | Status |
| --- | --- | --- | --- |
| 1 | SDR front-end: tune, gain, rate, GPSDO timing | `rf_chain.py` (`uhd.usrp_source`) | GNU Radio block |
| 2 | Capture: recent raw I/Q, all channels | `stages.CaptureRing` | Placeholder |
| 3 | Channelise into sub-bands | `rf_chain.py` (`pfb.channelizer_ccf`) | GNU Radio block |
| 4 | Detect: spectrum frames, then CFAR | `fft_vcc` + `stages.Detector` | FFT real, CFAR placeholder |
| 5 | Segment detections into bursts | `stages.Segmenter` | Placeholder |
| 6 | Characterise: carrier, bandwidth, type | `stages.Characteriser` | Placeholder |
| 7 | Direction finding with calibration | `stages.DirectionFinder` | Placeholder |
| 8 | Report: compact detection message | `stages.Reporter` | Placeholder |
| 9 | Decision module | `decision.py` via ZeroMQ | Placeholder |

## Design choices

- **Streams until detection, messages after.** Samples flow as streams through the
  front-end and FFT; from detection on, each signal travels as a small dictionary.
- **Heavy work on the node, small reports upstream.** The decision module gets
  detections, never raw I/Q, so it works over weak links.
- **Capture ring.** Later stages fetch raw I/Q by time only for signals that matter.
- **Fixed gain, shared timing, calibration after retune**: needed for stable thresholds
  and accurate bearings.

## Next steps

1. Implement `Detector` as a C++ block (CFAR), test it on simulated signals.
2. Replace the SDR source with a file source to replay recordings.
3. Fill in the remaining stages one at a time.