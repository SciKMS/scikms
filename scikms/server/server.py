import asyncio
import logging
from typing import Awaitable, Callable

from .data_structure import Request, Response
from .session import SessionLike
from .protocol import FuoServerProtocol, ProtocolType, PubsubProtocol


logger = logging.getLogger(__name__)


RequestHandler = Callable[[Request, SessionLike], Awaitable[Response]]


class FuoServer:
    """TCP server that speaks the scikms DSL/RPC protocol.

    Callers supply the request handler; the server is agnostic about what
    commands mean. See ``scikms.server.protocol`` for the wire format.
    """

    def __init__(self, handle_request: RequestHandler, protocol_type: ProtocolType):
        self._handle_request = handle_request
        self.protocol_type = protocol_type
        self._loop = None

    async def run(self, host, port):
        loop = asyncio.get_event_loop()
        self._loop = loop

        try:
            await loop.create_server(self.protocol_factory, host, port)
        except OSError as e:
            raise SystemExit(str(e)) from None

        name = 'unknown'
        if self.protocol_type is ProtocolType.rpc:
            name = 'RPC'
        elif self.protocol_type is ProtocolType.pubsub:
            name = 'Pub/Sub'
        logger.info('%s server run at %s:%d', name, host, port)

    def protocol_factory(self):
        if self.protocol_type is ProtocolType.rpc:
            protocol_cls = FuoServerProtocol
        else:
            protocol_cls = PubsubProtocol
        return protocol_cls(handle_req=self.handle_req,
                            loop=self._loop,)

    async def handle_req(self, req: Request, session: SessionLike) -> Response:
        return await self._handle_request(req, session)
