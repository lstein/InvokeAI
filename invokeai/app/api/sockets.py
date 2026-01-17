# Copyright (c) 2022 Kyle Schouviller (https://github.com/kyle0654)

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel
from socketio import ASGIApp, AsyncServer

from invokeai.app.services.auth.token_service import verify_token
from invokeai.app.services.events.events_common import (
    BatchEnqueuedEvent,
    BulkDownloadCompleteEvent,
    BulkDownloadErrorEvent,
    BulkDownloadEventBase,
    BulkDownloadStartedEvent,
    DownloadCancelledEvent,
    DownloadCompleteEvent,
    DownloadErrorEvent,
    DownloadEventBase,
    DownloadProgressEvent,
    DownloadStartedEvent,
    FastAPIEvent,
    InvocationCompleteEvent,
    InvocationErrorEvent,
    InvocationProgressEvent,
    InvocationStartedEvent,
    ModelEventBase,
    ModelInstallCancelledEvent,
    ModelInstallCompleteEvent,
    ModelInstallDownloadProgressEvent,
    ModelInstallDownloadsCompleteEvent,
    ModelInstallErrorEvent,
    ModelInstallStartedEvent,
    ModelLoadCompleteEvent,
    ModelLoadStartedEvent,
    QueueClearedEvent,
    QueueEventBase,
    QueueItemEventBase,
    QueueItemStatusChangedEvent,
    register_events,
)


class QueueSubscriptionEvent(BaseModel):
    """Event data for subscribing to the socket.io queue room.
    This is a pydantic model to ensure the data is in the correct format."""

    queue_id: str


class BulkDownloadSubscriptionEvent(BaseModel):
    """Event data for subscribing to the socket.io bulk downloads room.
    This is a pydantic model to ensure the data is in the correct format."""

    bulk_download_id: str


QUEUE_EVENTS = {
    InvocationStartedEvent,
    InvocationProgressEvent,
    InvocationCompleteEvent,
    InvocationErrorEvent,
    QueueItemStatusChangedEvent,
    BatchEnqueuedEvent,
    QueueClearedEvent,
}

MODEL_EVENTS = {
    DownloadCancelledEvent,
    DownloadCompleteEvent,
    DownloadErrorEvent,
    DownloadProgressEvent,
    DownloadStartedEvent,
    ModelLoadStartedEvent,
    ModelLoadCompleteEvent,
    ModelInstallDownloadProgressEvent,
    ModelInstallDownloadsCompleteEvent,
    ModelInstallStartedEvent,
    ModelInstallCompleteEvent,
    ModelInstallCancelledEvent,
    ModelInstallErrorEvent,
}

BULK_DOWNLOAD_EVENTS = {BulkDownloadStartedEvent, BulkDownloadCompleteEvent, BulkDownloadErrorEvent}


class SocketIO:
    _sub_queue = "subscribe_queue"
    _unsub_queue = "unsubscribe_queue"

    _sub_bulk_download = "subscribe_bulk_download"
    _unsub_bulk_download = "unsubscribe_bulk_download"

    def __init__(self, app: FastAPI):
        self._sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
        self._app = ASGIApp(socketio_server=self._sio, socketio_path="/ws/socket.io")
        app.mount("/ws", self._app)

        # Set up authentication middleware
        self._sio.on("connect", handler=self._handle_connect)
        
        self._sio.on(self._sub_queue, handler=self._handle_sub_queue)
        self._sio.on(self._unsub_queue, handler=self._handle_unsub_queue)
        self._sio.on(self._sub_bulk_download, handler=self._handle_sub_bulk_download)
        self._sio.on(self._unsub_bulk_download, handler=self._handle_unsub_bulk_download)

        register_events(QUEUE_EVENTS, self._handle_queue_event)
        register_events(MODEL_EVENTS, self._handle_model_event)
        register_events(BULK_DOWNLOAD_EVENTS, self._handle_bulk_image_download_event)
    
    async def _handle_connect(self, sid: str, environ: dict, auth: dict | None) -> bool:
        """Handle socket connection and authenticate the user.
        
        Returns True to accept the connection, False to reject it.
        Stores user_id in the socket session data for later use.
        """
        # Extract token from auth data or headers
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get("token")
        
        if not token and environ:
            # Try to get token from headers
            headers = environ.get("HTTP_AUTHORIZATION", "")
            if headers.startswith("Bearer "):
                token = headers[7:]
        
        # Verify the token
        if token:
            token_data = verify_token(token)
            if token_data:
                # Store user_id and is_admin in socket session
                await self._sio.save_session(sid, {
                    "user_id": token_data.user_id,
                    "is_admin": token_data.is_admin,
                })
                return True
        
        # If no valid token, store system user for backward compatibility
        await self._sio.save_session(sid, {
            "user_id": "system",
            "is_admin": False,
        })
        return True

    async def _handle_sub_queue(self, sid: str, data: Any) -> None:
        await self._sio.enter_room(sid, QueueSubscriptionEvent(**data).queue_id)

    async def _handle_unsub_queue(self, sid: str, data: Any) -> None:
        await self._sio.leave_room(sid, QueueSubscriptionEvent(**data).queue_id)

    async def _handle_sub_bulk_download(self, sid: str, data: Any) -> None:
        await self._sio.enter_room(sid, BulkDownloadSubscriptionEvent(**data).bulk_download_id)

    async def _handle_unsub_bulk_download(self, sid: str, data: Any) -> None:
        await self._sio.leave_room(sid, BulkDownloadSubscriptionEvent(**data).bulk_download_id)

    async def _handle_queue_event(self, event: FastAPIEvent[QueueEventBase]):
        """Handle queue events with user isolation.
        
        For queue item events, only emit to the user who owns the queue item,
        or to all admins. For other queue events, emit to all subscribers.
        """
        event_name, event_data = event
        
        # Check if this is a queue item event that should be filtered by user
        if isinstance(event_data, QueueItemEventBase) and hasattr(event_data, "user_id"):
            # Get all socket IDs in the queue room
            room_name = event_data.queue_id
            room_sids = await self._sio.manager.get_participants("/", room_name)
            
            # Filter sids based on user_id or admin status
            for sid in room_sids:
                session = await self._sio.get_session(sid)
                if session:
                    session_user_id = session.get("user_id", "system")
                    is_admin = session.get("is_admin", False)
                    
                    # Emit to the owner or to admins
                    if session_user_id == event_data.user_id or is_admin:
                        await self._sio.emit(
                            event=event_name,
                            data=event_data.model_dump(mode="json"),
                            room=sid,  # Emit to specific socket
                        )
        else:
            # For non-item events (like queue status), emit to all subscribers
            await self._sio.emit(
                event=event_name,
                data=event_data.model_dump(mode="json"),
                room=event_data.queue_id
            )

    async def _handle_model_event(self, event: FastAPIEvent[ModelEventBase | DownloadEventBase]) -> None:
        await self._sio.emit(event=event[0], data=event[1].model_dump(mode="json"))

    async def _handle_bulk_image_download_event(self, event: FastAPIEvent[BulkDownloadEventBase]) -> None:
        await self._sio.emit(event=event[0], data=event[1].model_dump(mode="json"), room=event[1].bulk_download_id)
