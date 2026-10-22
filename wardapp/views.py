import csv
import json
import os
import time
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .constants import (
    AREAS,
    CATEGORIES_AND_SUBCATEGORIES,
    CELL_FIELDS,
    FIELD_LABELS,
    REVIEW_REASONS,
)
from .models import Area, CellReview, Interview, PromptVersion, Row, RunLog
from pipeline import transcribe
from pipeline.extract import stream_extract_rows
from pipeline.sse import sse_comment, sse_message
from pipeline.validator import validate_cell
import queue
import threading


# ---------------------------------------------------------
# AUTH VIEWS
# ---------------------------------------------------------
def login_view(request):
    error = ""
    if request.method == "POST":
        password = request.POST.get("password", "")
        expected_pwd = getattr(settings, "APP_PASSWORD", "ward119")
        if password == expected_pwd:
            request.session["is_authenticated"] = True
            next_url = request.GET.get("next") or "/"
            return redirect(next_url)
        else:
            error = "Invalid password. Please check APP_PASSWORD."
    return render(request, "wardapp/login.html", {"error": error})


def logout_view(request):
    request.session.flush()
    return redirect("/login/")


# ---------------------------------------------------------
# 1. UPLOAD VIEW (/)
# ---------------------------------------------------------
def upload_view(request):
    if request.method == "POST":
        area_id = request.POST.get("area")
        speaker_name = request.POST.get("speaker_name", "").strip()
        speaker_phone = request.POST.get("speaker_phone", "").strip()
        prompt_version_id = request.POST.get("prompt_version")
        audio_file = request.FILES.get("audio_file")
        pasted_transcript = request.POST.get("pasted_transcript", "").strip()

        transcript_file = request.FILES.get("transcript_file")
        if transcript_file and not pasted_transcript:
            pasted_transcript = transcript_file.read().decode("utf-8", errors="ignore").strip()

        if not audio_file and not pasted_transcript:
            areas = Area.objects.all().order_by("name")
            prompts = PromptVersion.objects.all().order_by("-created_at")
            return render(
                request,
                "wardapp/upload.html",
                {
                    "areas": areas,
                    "prompts": prompts,
                    "error": "Please provide an audio file OR paste the Telugu transcript/field notes.",
                },
            )

        if not speaker_name:
            speaker_name = "Ward 119 Field Survey"

        area = Area.objects.filter(id=area_id).first() if area_id else None
        prompt_version = (
            PromptVersion.objects.filter(id=prompt_version_id).first()
            if prompt_version_id
            else None
        )
        if not prompt_version:
            prompt_version = PromptVersion.objects.order_by("id").first()

        interview = Interview.objects.create(
            area=area,
            speaker_name=speaker_name,
            speaker_phone=speaker_phone,
            audio_file=audio_file,
            transcript=pasted_transcript,
            raw_transcript_response=pasted_transcript if pasted_transcript else "",
            prompt_version=prompt_version,
            model_name=getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
            status="uploaded",
        )
        return redirect(f"/run/{interview.id}/")

    areas = Area.objects.all().order_by("name")
    prompts = PromptVersion.objects.all().order_by("-created_at")
    recent_interviews = (
        Interview.objects.prefetch_related("rows", "area")
        .all()
        .order_by("-created_at")[:20]
    )
    return render(
        request,
        "wardapp/upload.html",
        {
            "areas": areas,
            "prompts": prompts,
            "recent_interviews": recent_interviews,
        },
    )


# ---------------------------------------------------------
# 2. LIVE RUN VIEW (/run/<id>/) & SSE STREAM
# ---------------------------------------------------------
def live_run_view(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    existing_rows = interview.rows.all().order_by("order_no")
    return render(
        request,
        "wardapp/live_run.html",
        {
            "interview": interview,
            "existing_rows": existing_rows,
            "cell_fields": CELL_FIELDS,
            "field_labels": FIELD_LABELS,
        },
    )


def live_run_stream(request, interview_id):
    """
    Server-Sent Events endpoint streaming transcript chunks and incremental rows.
    """
    interview = get_object_or_404(Interview, id=interview_id)

    is_retry = request.GET.get("retry") == "1" or request.GET.get("retry") == "true"

    def event_stream():
        # Heartbeat initial message
        yield sse_comment("connected")

        # If already successfully done and not explicitly retrying, push existing state and close
        if interview.status == "done" and not is_retry:
            yield sse_message(
                "status",
                {
                    "status": interview.status,
                    "transcript": interview.transcript,
                    "error": interview.error,
                },
            )
            for row in interview.rows.all().order_by("order_no"):
                row_dict = {
                    "id": row.id,
                    "category": row.category,
                    "sub_category": row.sub_category,
                    "order_no": row.order_no,
                    "source_quote": row.source_quote,
                    "source_time": row.source_time,
                }
                for f in CELL_FIELDS:
                    row_dict[f] = getattr(row, f)
                yield sse_message("row_created", {"row": row_dict})
            yield sse_message(
                "done",
                {
                    "status": interview.status,
                    "total_rows": interview.rows.count(),
                },
            )
            return

        # If failed or retrying, clean any partial rows and reset error
        if interview.status == "failed" or is_retry:
            interview.rows.all().delete()
            interview.error = ""
            interview.status = "extracting"
            interview.save(update_fields=["error", "status"])

        try:
            # STEP 1: Transcribe via contract
            if not interview.transcript:
                interview.status = "transcribing"
                interview.save(update_fields=["status"])
                yield sse_message("status", {"status": "transcribing"})

                log = RunLog.objects.create(
                    interview=interview,
                    step="transcribe",
                    started_at=timezone.now(),
                    message="Starting transcription stream"
                )

                chunk_queue = queue.Queue()

                def on_chunk(chunk_text):
                    chunk_queue.put(('CHUNK', chunk_text))

                def run_transcribe_worker():
                    try:
                        res = transcribe(
                            audio_path=interview.audio_file.path if interview.audio_file else "",
                            speaker_hint=interview.speaker_name,
                            on_chunk=on_chunk
                        )
                        chunk_queue.put(('DONE', res))
                    except Exception as exc:
                        chunk_queue.put(('ERROR', exc))

                worker_thread = threading.Thread(target=run_transcribe_worker, daemon=True)
                worker_thread.start()

                while True:
                    msg_type, payload = chunk_queue.get()
                    if msg_type == 'CHUNK':
                        yield sse_message("transcript_chunk", {"text": payload})
                    elif msg_type == 'DONE':
                        transcript_res = payload
                        interview.transcript = transcript_res.text
                        interview.raw_transcript_response = transcript_res.raw_response
                        interview.save(update_fields=["transcript", "raw_transcript_response"])

                        log.ended_at = timezone.now()
                        log.tokens_in = transcript_res.tokens_in
                        log.tokens_out = transcript_res.tokens_out
                        log.message = f"Transcription finished ({transcript_res.model}, latency: {transcript_res.latency_seconds}s)"
                        log.save()
                        break
                    elif msg_type == 'ERROR':
                        log.ended_at = timezone.now()
                        log.message = f"Transcription failed: {str(payload)}"
                        log.save()
                        raise payload

            # STEP 2: Extract
            interview.status = "extracting"
            interview.save(update_fields=["status"])
            yield sse_message("status", {"status": "extracting"})

            for event in stream_extract_rows(interview):
                if event.get("type") == "row_created":
                    row = event["row"]
                    row_data = event["data"]
                    row_dict = {
                        "id": row.id,
                        "category": row.category,
                        "sub_category": row.sub_category,
                        "order_no": row.order_no,
                        "source_quote": row.source_quote,
                        "source_time": row.source_time,
                    }
                    for f in CELL_FIELDS:
                        row_dict[f] = getattr(row, f)

                    # Emit row_created event
                    yield sse_message("row_created", {"row": row_dict})

                    # Emit cell_filled events in column order to simulate typewriter progression
                    for f in CELL_FIELDS:
                        val = row_dict[f]
                        if val:
                            yield sse_message(
                                "cell_filled",
                                {
                                    "row_id": row.id,
                                    "field": f,
                                    "text": val,
                                },
                            )
                            time.sleep(0.04)

            yield sse_message(
                "done",
                {"status": "done", "total_rows": interview.rows.count()},
            )

        except Exception as e:
            yield sse_message(
                "error",
                {"message": str(e), "raw_response": interview.raw_extract_response},
            )

    response = StreamingHttpResponse(
        event_stream(), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # Disable proxy buffering
    return response


# ---------------------------------------------------------
# 3. SHEET VIEW (/sheet/) & INLINE UPDATE
# ---------------------------------------------------------
def sheet_view(request):
    area_filter = request.GET.get("area", "")
    speaker_filter = request.GET.get("speaker", "")
    interview_filter = request.GET.get("interview", "")

    # Default to latest interview if none specified to avoid mixing multiple runs
    if interview_filter == "":
        latest_inv = Interview.objects.order_by("-created_at").first()
        if latest_inv:
            interview_filter = str(latest_inv.id)
    elif interview_filter == "all":
        interview_filter = ""

    rows_qs = Row.objects.select_related("interview", "area").all()

    if area_filter:
        rows_qs = rows_qs.filter(area_id=area_filter)
    if speaker_filter:
        rows_qs = rows_qs.filter(speaker_name__icontains=speaker_filter)
    if interview_filter:
        rows_qs = rows_qs.filter(interview_id=interview_filter)

    # Group by Category > Sub-category
    grouped_data = {}
    for row in rows_qs:
        cat = row.category or "Other"
        sub = row.sub_category or "General"
        if cat not in grouped_data:
            grouped_data[cat] = {}
        if sub not in grouped_data[cat]:
            grouped_data[cat][sub] = []

        # Validate cells for error highlighting
        transcript = row.interview.transcript or ""
        cell_validations = {}
        for f in CELL_FIELDS:
            cell_validations[f] = validate_cell(
                f, getattr(row, f), transcript
            )

        grouped_data[cat][sub].append(
            {
                "row": row,
                "validations": cell_validations,
            }
        )

    areas = Area.objects.all().order_by("name")
    interviews = Interview.objects.prefetch_related("rows").all().order_by("-created_at")
    total_all_rows = Row.objects.count()
    active_interview = None
    if interview_filter:
        active_interview = Interview.objects.filter(id=interview_filter).first()

    return render(
        request,
        "wardapp/sheet.html",
        {
            "grouped_data": grouped_data,
            "total_rows": rows_qs.count(),
            "total_all_rows": total_all_rows,
            "areas": areas,
            "interviews": interviews,
            "active_interview": active_interview,
            "selected_area": area_filter,
            "selected_speaker": speaker_filter,
            "selected_interview": interview_filter,
            "cell_fields": CELL_FIELDS,
            "field_labels": FIELD_LABELS,
        },
    )


@csrf_exempt
def api_row_update(request, row_id):
    """Inline cell edit autosave with 500ms debounce."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    row = get_object_or_404(Row, id=row_id)
    try:
        data = json.loads(request.body)
        field_name = data.get("field")
        value = data.get("value", "")

        if field_name not in CELL_FIELDS and field_name not in [
            "category",
            "sub_category",
            "source_quote",
            "source_time",
        ]:
            return JsonResponse({"error": "Invalid field"}, status=400)

        setattr(row, field_name, value)
        row.save()

        # Re-validate cell for immediate UI update
        val_result = validate_cell(
            field_name, value, row.interview.transcript or ""
        )
        return JsonResponse(
            {
                "success": True,
                "row_id": row.id,
                "field": field_name,
                "value": value,
                "validation": val_result,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def export_sheet_csv(request):
    """Exports sheet rows as CSV with UTF-8 BOM for Microsoft Excel compatibility."""
    interview_filter = request.GET.get("interview", "")
    area_filter = request.GET.get("area", "")
    speaker_filter = request.GET.get("speaker", "")

    # Default to latest interview if not specified so we don't mix duplicate runs
    if interview_filter == "":
        latest_inv = Interview.objects.order_by("-created_at").first()
        if latest_inv:
            interview_filter = str(latest_inv.id)
    elif interview_filter == "all":
        interview_filter = ""

    rows = Row.objects.select_related("interview", "area").all()
    if interview_filter:
        rows = rows.filter(interview_id=interview_filter)
    if area_filter:
        rows = rows.filter(area_id=area_filter)
    if speaker_filter:
        rows = rows.filter(speaker_name__icontains=speaker_filter)

    rows = rows.order_by("category", "sub_category", "order_no")

    filename_suffix = f"interview_{interview_filter}" if interview_filter else "all"
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="ward119_civic_sheet_{filename_suffix}_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'
    )

    # Write UTF-8 BOM so Excel opens Telugu text correctly without garbled symbols
    response.write("\ufeff".encode("utf-8"))

    writer = csv.writer(response, quoting=csv.QUOTE_MINIMAL)
    header = [
        "#",
        "Run ID",
        "Category",
        "Sub-category",
        "Speaker Name",
        "Speaker Phone",
        "Area / Colony",
        "Where Details",
        "What is happening",
        "Why (Root Cause)",
        "To People",
        "How it happens",
        "Solution",
        "Solution Impact",
        "Voter Impact",
        "+ done",
        "- not done",
        "Urgency (1-5)",
        "Scale",
        "Responsible Dept & Official",
        "Key Influencer / Contact",
        "Law / Authority Route",
        "Work Done?",
        "Past Complaint Given?",
        "Source Time",
        "Source Quote",
    ]
    writer.writerow(header)

    def safe_cell(val):
        s = str(val or "")
        # Prevent formula injection in Excel for cells starting with '=' or '@'
        if s.startswith(("=", "@")):
            return "'" + s
        return s

    for r in rows:
        area_name = r.area.name if r.area else (r.where if r.where else "Ward 119")
        row_vals = [
            r.order_no,
            r.interview_id,
            safe_cell(r.category),
            safe_cell(r.sub_category),
            safe_cell(r.speaker_name),
            safe_cell(r.speaker_phone),
            safe_cell(area_name),
            safe_cell(r.where),
            safe_cell(r.what),
            safe_cell(r.why),
            safe_cell(r.to_people),
            safe_cell(r.how),
            safe_cell(r.solution),
            safe_cell(r.solution_impact),
            safe_cell(r.voter_impact),
            safe_cell(r.vote_plus),
            safe_cell(r.vote_minus),
            safe_cell(r.urgency),
            safe_cell(r.scale),
            safe_cell(r.dept_official),
            safe_cell(r.influencer),
            safe_cell(r.law_route),
            safe_cell(r.work_done),
            safe_cell(r.past_complaint),
            safe_cell(r.source_time),
            safe_cell(r.source_quote),
        ]
        writer.writerow(row_vals)

    return response


def export_interview_json(request, interview_id):
    """Exports one interview and all its rows as JSON."""
    interview = get_object_or_404(Interview, id=interview_id)
    rows_data = []
    for r in interview.rows.all().order_by("order_no"):
        item = {
            "id": r.id,
            "category": r.category,
            "sub_category": r.sub_category,
            "source_quote": r.source_quote,
            "source_time": r.source_time,
        }
        for f in CELL_FIELDS:
            item[f] = getattr(r, f)
        rows_data.append(item)

    data = {
        "interview_id": interview.id,
        "area": interview.area.name if interview.area else "",
        "speaker_name": interview.speaker_name,
        "speaker_phone": interview.speaker_phone,
        "status": interview.status,
        "transcript": interview.transcript,
        "created_at": interview.created_at.isoformat(),
        "finished_at": interview.finished_at.isoformat()
        if interview.finished_at
        else None,
        "rows": rows_data,
        "raw_extract_response": interview.raw_extract_response,
    }
    return JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 2})


@csrf_exempt
def delete_interview_view(request, interview_id):
    """Deletes an interview run, all its extracted rows, and associated audio file."""
    if request.method in ["POST", "DELETE"]:
        interview = get_object_or_404(Interview, id=interview_id)
        run_id = interview.id
        speaker_name = interview.speaker_name
        row_count = interview.rows.count()

        if interview.audio_file:
            try:
                if os.path.isfile(interview.audio_file.path):
                    os.remove(interview.audio_file.path)
            except Exception:
                pass

        interview.delete()

        is_ajax = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
            or request.content_type == "application/json"
        )
        if is_ajax:
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Run #{run_id} ({speaker_name}) and its {row_count} rows deleted successfully.",
                    "deleted_id": run_id,
                }
            )

        referrer = request.META.get("HTTP_REFERER", "")
        if "/sheet/" in referrer:
            return redirect("/sheet/")
        return redirect("/")

    return JsonResponse({"error": "POST or DELETE required"}, status=405)


@csrf_exempt
def delete_all_interviews_view(request):
    """Deletes all interview runs and rows."""
    if request.method in ["POST", "DELETE"]:
        interviews = Interview.objects.all()
        count = interviews.count()
        for inv in interviews:
            if inv.audio_file:
                try:
                    if os.path.isfile(inv.audio_file.path):
                        os.remove(inv.audio_file.path)
                except Exception:
                    pass
        interviews.delete()

        is_ajax = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
            or request.content_type == "application/json"
        )
        if is_ajax:
            return JsonResponse(
                {
                    "success": True,
                    "message": f"All {count} runs and their rows deleted successfully.",
                }
            )
        return redirect("/")

    return JsonResponse({"error": "POST or DELETE required"}, status=405)


# ---------------------------------------------------------
# 4. REVIEW VIEW (/review/<id>/) & REVIEW API
# ---------------------------------------------------------
def review_view(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    rows = interview.rows.all().order_by("order_no")

    # Fetch all existing cell reviews
    existing_reviews = CellReview.objects.filter(row__interview=interview)
    review_map = {f"{r.row_id}_{r.field_name}": r for r in existing_reviews}

    # Build row review info
    rows_with_reviews = []
    total_ticked = 0
    total_crossed = 0
    reason_counts = {}

    for r in rows:
        fields_info = []
        for f in CELL_FIELDS:
            key = f"{r.id}_{f}"
            rev = review_map.get(key)
            status = None
            reason = ""
            note = ""
            if rev:
                if rev.is_correct:
                    status = "ticked"
                    total_ticked += 1
                else:
                    status = "crossed"
                    total_crossed += 1
                    reason = rev.reason
                    note = rev.note
                    reason_counts[rev.reason] = (
                        reason_counts.get(rev.reason, 0) + 1
                    )

            fields_info.append(
                {
                    "field_name": f,
                    "label": FIELD_LABELS[f],
                    "value": getattr(r, f),
                    "status": status,
                    "reason": reason,
                    "note": note,
                }
            )

        rows_with_reviews.append(
            {
                "row": r,
                "fields": fields_info,
            }
        )

    # Calculate most common reason
    most_common_reason = "None yet"
    if reason_counts:
        top_reason_code = max(reason_counts, key=reason_counts.get)
        reason_label_dict = dict(REVIEW_REASONS)
        most_common_reason = f"{reason_label_dict.get(top_reason_code, top_reason_code)} ({reason_counts[top_reason_code]})"

    return render(
        request,
        "wardapp/review.html",
        {
            "interview": interview,
            "rows_with_reviews": rows_with_reviews,
            "total_ticked": total_ticked,
            "total_crossed": total_crossed,
            "most_common_reason": most_common_reason,
            "review_reasons": REVIEW_REASONS,
            "run_logs": interview.logs.all().order_by("started_at"),
        },
    )


@csrf_exempt
def api_cell_review_save(request):
    """Save or update tick/cross and reason note for a cell."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        row_id = data.get("row_id")
        field_name = data.get("field_name")
        is_correct = data.get("is_correct", True)
        reason = data.get("reason", "")
        note = data.get("note", "")

        row = get_object_or_404(Row, id=row_id)
        review, created = CellReview.objects.update_or_create(
            row=row,
            field_name=field_name,
            defaults={
                "is_correct": is_correct,
                "reason": reason if not is_correct else "",
                "note": note if not is_correct else "",
                "created_at": timezone.now(),
            },
        )
        return JsonResponse({"success": True, "created": created})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ---------------------------------------------------------
# 5. PROMPTS VIEW (/prompts/)
# ---------------------------------------------------------
def prompts_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            name = request.POST.get("name", "New Prompt").strip()
            text = request.POST.get("text", "").strip()
            if name and text:
                PromptVersion.objects.create(name=name, text=text)
        elif action == "edit":
            prompt_id = request.POST.get("prompt_id")
            pv = get_object_or_404(PromptVersion, id=prompt_id)
            pv.name = request.POST.get("name", pv.name).strip()
            pv.text = request.POST.get("text", pv.text).strip()
            pv.save()
        return redirect("/prompts/")

    prompts = PromptVersion.objects.all().order_by("-created_at")
    return render(request, "wardapp/prompts.html", {"prompts": prompts})


# ---------------------------------------------------------
# 6. COMPARE RUNS VIEW (/compare/)
# ---------------------------------------------------------
def compare_runs_view(request):
    run1_id = request.GET.get("run1")
    run2_id = request.GET.get("run2")

    interviews = Interview.objects.all().order_by("-created_at")
    run1 = Interview.objects.filter(id=run1_id).first() if run1_id else None
    run2 = Interview.objects.filter(id=run2_id).first() if run2_id else None

    run1_rows = run1.rows.all().order_by("order_no") if run1 else []
    run2_rows = run2.rows.all().order_by("order_no") if run2 else []

    return render(
        request,
        "wardapp/compare.html",
        {
            "interviews": interviews,
            "run1": run1,
            "run2": run2,
            "run1_rows": run1_rows,
            "run2_rows": run2_rows,
            "cell_fields": CELL_FIELDS,
            "field_labels": FIELD_LABELS,
        },
    )
