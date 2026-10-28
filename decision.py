"""9. Decision module: a separate process that receives reports from RF nodes.

It is where RF reports meet other sensors (acoustic, camera, radar) before an
alert. Placeholder only.
"""

import pmt
import zmq

ADDR = "tcp://localhost:5555"  # the RF chain publishes here


def decide(report):
    """TODO: associate with other sensors' reports, confirm over time (M-of-N),
    then raise, update or drop an alert."""
    print("report:", report)


if __name__ == "__main__":
    sock = zmq.Context().socket(zmq.SUB)
    sock.connect(ADDR)
    sock.setsockopt(zmq.SUBSCRIBE, b"")
    while True:
        decide(pmt.to_python(pmt.deserialize_str(sock.recv())))
