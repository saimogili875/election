import time
from dataclasses import dataclass
from typing import Callable, Optional, List

@dataclass
class Segment:
    start_seconds: float
    speaker: str  # "Speaker 1" or ""
    text: str

@dataclass
class TranscriptResult:
    text: str  # full Telugu transcript
    segments: List[Segment]
    raw_response: str
    model: str
    latency_seconds: float
    tokens_in: int
    tokens_out: int

STUB_SAMPLE_TEXT = (
    "[STUB RUN] నమస్కారం అండి, నా పేరు సురేష్ కుమార్. మేము అంజయ్య నగర్ లో ఉంటున్నాము. "
    "మా బస్తీలో ముఖ్యంగా రెండు పెద్ద సమస్యలు ఉన్నాయి. మొదటిది డ్రైనేజీ ఓవర్ ఫ్లో. "
    "వర్షాకాలం రాకముందే డ్రైనేజీ లైన్లు నిండిపోయి రోడ్లపైకి మురుగునీరు వస్తోంది. "
    "జిహెచ్ఎంసి శానిటేషన్ వర్కర్లు డ్రైనేజీ పూడిక తీసి ఆ మట్టిని రోడ్డు పక్కనే వదిలేస్తున్నారు. "
    "ఆ మట్టి తీయడానికి వచ్చి మా దగ్గర డబ్బులు డిమాండ్ చేస్తున్నారు. "
    "ఇది వర్కర్ల నిర్లక్ష్యం మరియు అవినీతి. ప్రజలు చాలా ఇబ్బందులు పడుతున్నారు, రోగాల భయం ఉంది. "
    "మేము స్థానిక కార్పొరేటర్ కి మరియు వార్డ్ ఆఫీస్ లో కంప్లైంట్ ఇచ్చాము కానీ ఎవరూ పట్టించుకోలేదు. "
    "రెండోది తాగునీటి సరఫరా. వారానికి రెండు రోజులే మంచి నీళ్లు వస్తున్నాయి. "
    "పైపు లైన్ లీకేజీల వల్ల తాగే నీటిలో మురుగు నీరు కలుస్తోంది. దీనిపై వెంటనే చర్యలు తీసుకోవాలి."
)

def transcribe(
    audio_path: str,
    speaker_hint: Optional[str] = None,
    on_chunk: Optional[Callable[[str], None]] = None
) -> TranscriptResult:
    """
    Stub transcriber that returns a fixed Telugu sample text,
    calls on_chunk with small delays, and clearly marks the output as STUB.
    """
    start_time = time.time()
    words = STUB_SAMPLE_TEXT.split(" ")
    
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        if on_chunk:
            on_chunk(chunk)
        time.sleep(0.04)

    latency = round(time.time() - start_time, 2)

    segments = [
        Segment(start_seconds=0.0, speaker=speaker_hint or "Speaker 1", text=STUB_SAMPLE_TEXT[:120]),
        Segment(start_seconds=12.0, speaker=speaker_hint or "Speaker 1", text=STUB_SAMPLE_TEXT[120:250]),
        Segment(start_seconds=28.0, speaker=speaker_hint or "Speaker 1", text=STUB_SAMPLE_TEXT[250:]),
    ]

    return TranscriptResult(
        text=STUB_SAMPLE_TEXT,
        segments=segments,
        raw_response=f'{{"status": "stub", "text": "{STUB_SAMPLE_TEXT}"}}',
        model="stub-transcriber",
        latency_seconds=latency,
        tokens_in=len(words) * 2,
        tokens_out=len(words) * 2
    )
