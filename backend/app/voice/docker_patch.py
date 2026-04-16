"""Make WebRTC work inside a Docker bridge network.

aiortc / aioice enumerates the container's local network interfaces and
advertises them as ICE host candidates. On a bridge network that yields only
the 172.x.x.x bridge IP, which the browser on the host cannot reach, so the
peer connection never establishes.

When ``WEBRTC_HOST_IP`` is set, this module patches aioice so that for each
new peer connection it:

  1. binds the host UDP socket to ``0.0.0.0`` on the first free port from a
     small range (``WEBRTC_UDP_PORT_MIN``..``WEBRTC_UDP_PORT_MAX``, default
     7880..7889). A range (rather than one pinned port) is required so that
     a new PC started while the previous one's socket is still lingering
     doesn't hit ``EADDRINUSE`` and close its ICE transport.
  2. advertises ``WEBRTC_HOST_IP`` (e.g. ``127.0.0.1``) as the candidate host
     address so the browser dials the forwarded Docker port instead of the
     unreachable bridge IP.

Pair this with publishing the UDP port range in docker-compose, e.g.::

    ports:
      - "7880-7889:7880-7889/udp"

Limitation: the range size caps concurrent peer connections. For multi-user
deployments use a TURN server instead.
"""

import os
import socket

from loguru import logger


_APPLIED = False


def apply_webrtc_docker_patch() -> None:
    global _APPLIED
    if _APPLIED:
        return

    host_ip = os.environ.get("WEBRTC_HOST_IP", "").strip()
    if not host_ip:
        return

    try:
        port_min = int(os.environ.get("WEBRTC_UDP_PORT_MIN", "7880"))
        port_max = int(os.environ.get("WEBRTC_UDP_PORT_MAX", "7889"))
    except ValueError:
        logger.warning("[voice] Invalid WEBRTC_UDP_PORT_{MIN,MAX}, skipping docker patch")
        return
    if port_min > port_max:
        logger.warning("[voice] WEBRTC_UDP_PORT_MIN > _MAX, skipping docker patch")
        return

    try:
        from aioice import ice as aioice_ice
        from aioice import turn as aioice_turn
        from aioice.candidate import (
            Candidate,
            candidate_foundation,
            candidate_priority,
        )
    except ImportError:
        return

    import asyncio

    def _bind_in_range():
        last_exc: OSError | None = None
        for port in range(port_min, port_max + 1):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_RCVBUF,
                    aioice_turn.UDP_SOCKET_BUFFER_SIZE,
                )
                sock.bind(("0.0.0.0", port))
                return sock
            except OSError as exc:
                sock.close()
                last_exc = exc
                continue
        raise last_exc or OSError("no free WebRTC UDP port")

    async def get_component_candidates(self, component, addresses, timeout=5):
        # Pick the first free port in our configured range and bind it
        # ourselves so the container publishes a predictable set of UDP
        # ports — aioice's default path binds to port 0 on each enumerated
        # interface, which Docker cannot forward.
        loop = asyncio.get_event_loop()
        try:
            sock = _bind_in_range()
        except OSError as exc:
            logger.warning(
                f"[voice] No free WebRTC UDP port in "
                f"{port_min}-{port_max}: {exc}"
            )
            return []

        try:
            _, protocol = await loop.create_datagram_endpoint(
                lambda: aioice_ice.StunProtocol(self), sock=sock
            )
        except Exception as exc:
            sock.close()
            logger.warning(f"[voice] create_datagram_endpoint failed: {exc}")
            return []

        sockname = protocol.transport.get_extra_info("sockname")
        protocol.local_candidate = Candidate(
            foundation=candidate_foundation("host", "udp", host_ip),
            component=component,
            transport="udp",
            priority=candidate_priority(component, "host"),
            host=host_ip,
            port=sockname[1],
            type="host",
        )
        self._protocols.append(protocol)
        return [protocol.local_candidate]

    aioice_ice.Connection.get_component_candidates = get_component_candidates
    _APPLIED = True
    logger.info(
        f"[voice] WebRTC docker patch applied — advertising "
        f"{host_ip}:{port_min}-{port_max}"
    )
