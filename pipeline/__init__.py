import os

# Contract switch: controlled by USE_STUB_TRANSCRIBE (default '1' until real transcribe.py is merged)
if os.environ.get('USE_STUB_TRANSCRIBE', '1').lower() in ('1', 'true', 'yes'):
    from .transcribe_stub import transcribe, Segment, TranscriptResult
else:
    try:
        from .transcribe import transcribe, Segment, TranscriptResult
    except ImportError:
        # Fallback to stub if real transcribe is not yet created
        from .transcribe_stub import transcribe, Segment, TranscriptResult

__all__ = ['transcribe', 'Segment', 'TranscriptResult']
