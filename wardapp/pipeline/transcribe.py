import os
import time
from typing import Generator
from django.conf import settings
from django.utils import timezone
from ..models import Interview, RunLog

TRANSCRIBE_SYSTEM_PROMPT = (
    "Transcribe the following Telugu audio interview faithfully. "
    "Keep names, house numbers, phone numbers and numbers of voters exactly as spoken. "
    "Do not translate into English. Mark unclear words as [అస్పష్టం]. "
    "Output only the Telugu transcript."
)

MOCK_TELUGU_TRANSCRIPT = (
    "నమస్కారం అండి, నా పేరు సురేష్ కుమార్. మేము అంజయ్య నగర్ లో ఉంటున్నాము. "
    "మా బస్తీలో ముఖ్యంగా రెండు పెద్ద సమస్యలు ఉన్నాయి. మొదటిది డ్రైనేజీ ఓవర్ ఫ్లో. "
    "వర్షాకాలం రాకముందే డ్రైనేజీ లైన్లు నిండిపోయి రోడ్లపైకి మురుగునీరు వస్తోంది. "
    "జిహెచ్ఎంసి శానిటేషన్ వర్కర్లు డ్రైనేజీ పూడిక తీసి ఆ మట్టిని రోడ్డు పక్కనే వదిలేస్తున్నారు. "
    "ఆ మట్టి తీయడానికి వచ్చి మా దగ్గర డబ్బులు డిమాండ్ చేస్తున్నారు. "
    "ఇది వర్కర్ల నిర్లక్ష్యం మరియు అవినీతి. ప్రజలు చాలా ఇబ్బందులు పడుతున్నారు, రోగాల భయం ఉంది. "
    "మేము స్థానిక కార్పొరేటర్ కి మరియు వార్డ్ ఆఫీస్ లో కంప్లైంట్ ఇచ్చాము కానీ ఎవరూ పట్టించుకోలేదు. "
    "రెండోది తాగునీటి సరఫరా. వారానికి రెండు రోజులే మంచి నీళ్లు వస్తున్నాయి. "
    "పైపు లైన్ లీకేజీల వల్ల తాగే నీటిలో మురుగు నీరు కలుస్తోంది. దీనిపై వెంటనే చర్యలు తీసుకోవాలి."
)

def stream_transcribe(interview: Interview) -> Generator[str, None, str]:
    """
    Streams Telugu transcription from Gemini File API using google-genai SDK.
    Yields chunks of text as they arrive from Gemini.
    Returns the complete accumulated transcript.
    """
    run_log = RunLog.objects.create(
        interview=interview,
        step="transcribe",
        started_at=timezone.now(),
        message="Starting audio transcription stream"
    )

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')

    full_transcript = []

    # If no API key is configured, yield a realistic mock transcript for seamless offline testing
    if not api_key:
        run_log.message = "No GEMINI_API_KEY found; streaming mock Telugu interview for local testing"
        run_log.save()
        words = MOCK_TELUGU_TRANSCRIPT.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            full_transcript.append(chunk)
            yield chunk
            time.sleep(0.04)

        complete_text = "".join(full_transcript)
        interview.transcript = complete_text
        interview.raw_transcript_response = complete_text
        interview.save(update_fields=['transcript', 'raw_transcript_response'])

        run_log.ended_at = timezone.now()
        run_log.tokens_in = 120
        run_log.tokens_out = len(words)
        run_log.message = "Completed mock transcription"
        run_log.save()
        return complete_text

    # Real Gemini execution with retry
    retries = 1
    last_error = None

    for attempt in range(retries + 1):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            # Upload audio file to Gemini Files API
            audio_path = interview.audio_file.path
            file_upload = client.files.upload(file=audio_path)

            response_stream = client.models.generate_content_stream(
                model=model_name,
                contents=[
                    file_upload,
                    TRANSCRIBE_SYSTEM_PROMPT
                ]
            )

            for chunk in response_stream:
                text_part = chunk.text or ""
                if text_part:
                    full_transcript.append(text_part)
                    yield text_part

            complete_text = "".join(full_transcript)
            interview.transcript = complete_text
            interview.raw_transcript_response = complete_text
            interview.save(update_fields=['transcript', 'raw_transcript_response'])

            run_log.ended_at = timezone.now()
            run_log.message = f"Transcription completed successfully (attempt {attempt + 1})"
            run_log.save()
            return complete_text

        except Exception as e:
            last_error = e
            time.sleep(1)

    # If all attempts failed
    err_msg = f"Transcription failed after {retries + 1} attempts: {str(last_error)}"
    interview.error = err_msg
    interview.status = 'failed'
    interview.save(update_fields=['error', 'status'])

    run_log.ended_at = timezone.now()
    run_log.message = err_msg
    run_log.save()
    raise RuntimeError(err_msg)
