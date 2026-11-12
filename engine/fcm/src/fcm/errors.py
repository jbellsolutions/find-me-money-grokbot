"""Error types for the Funding Affiliate Manager core."""


class FcmError(Exception):
    """A rule, validation, or upstream failure the caller should see verbatim."""


class ApprovalRequired(FcmError):
    """The requested action is outbound and must go through the approvals surface."""


class GHLError(FcmError):
    """A GoHighLevel call that failed. `status` is the HTTP code (0 when no response came back at all)."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status

    @property
    def rejected(self) -> bool:
        """GoHighLevel answered and refused the request, so a send definitely did not go out. A timeout, a
        dropped connection, a 5xx, a 408 or a 429 might have been accepted before the response was lost."""
        return 400 <= self.status < 500 and self.status not in (408, 429)
