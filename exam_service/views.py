import json
from datetime import UTC, datetime

from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import JsonResponse
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .models import Choice, Exam, ExamAttempt, Question, gen_choice_id


def _format_iso(dt):
    if not dt:
        return None
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_json(request):
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


@login_not_required
@require_GET
def health(request):
    try:
        connection.ensure_connection()
    except Exception as exc:
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)

    return JsonResponse({"status": "ok"}, status=200)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def exams_collection(request):
    if request.method == "GET":
        exams = Exam.objects.all().order_by("-created_at")
        data = [
            {
                "examId": exam.id,
                "title": exam.title,
                "duration": exam.duration,
                "startTime": _format_iso(exam.start_time),
                "endTime": _format_iso(exam.end_time),
            }
            for exam in exams
        ]
        return JsonResponse(data, safe=False, status=200)

    try:
        payload = _parse_json(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    required = ["title", "duration", "passingScore", "instructorId"]
    missing = [field for field in required if payload.get(field) is None]
    if missing:
        return JsonResponse(
            {"error": f"Missing required fields: {', '.join(missing)}"}, status=400
        )

    start_time = (
        parse_datetime(payload["startTime"]) if payload.get("startTime") else None
    )
    end_time = parse_datetime(payload["endTime"]) if payload.get("endTime") else None

    exam = Exam.objects.create(
        title=payload["title"],
        description=payload.get("description"),
        instruction=payload.get("instruction"),
        term=payload.get("term"),
        year=payload.get("year"),
        duration=payload["duration"],
        passing_score=payload["passingScore"],
        item=payload.get("item"),
        start_time=start_time,
        end_time=end_time,
        instructor_id=payload["instructorId"],
        status=payload.get("status", "PENDING"),
        block=payload.get("block", []),
        year_level=payload.get("yearLevel", []),
        specific_student_id=payload.get("specificStudentId", []),
    )

    return JsonResponse(
        {
            "examId": exam.id,
            "title": exam.title,
            "createdAt": _format_iso(exam.created_at),
            "status": exam.status,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def add_question(request, exam_id):
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return JsonResponse({"error": "Exam not found"}, status=404)

    try:
        payload = _parse_json(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    question = Question.objects.create(
        exam=exam,
        question_text=payload["questionText"],
        question_type=payload["questionType"],
        order_number=payload["orderNumber"],
    )

    choices_data = payload.get("choices", [])
    if choices_data:
        Choice.objects.bulk_create(
            [
                Choice(
                    id=c.get("choiceId") or gen_choice_id(),
                    question=question,
                    choice_text=c["choiceText"],
                    is_correct=c.get("isCorrect", False),
                )
                for c in choices_data
            ]
        )

    return JsonResponse(
        {
            "questionId": question.id,
            "examId": exam.id,
            "orderNumber": question.order_number,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def start_session(request, exam_id):
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        return JsonResponse({"error": "Exam not found"}, status=404)

    try:
        payload = _parse_json(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    student_id = payload.get("studentId")
    if not student_id:
        return JsonResponse({"error": "studentId is required"}, status=400)

    attempt = ExamAttempt.objects.create(
        exam=exam,
        student_id=student_id,
        status="IN_PROGRESS",
        time_remaining=exam.duration * 60,
    )

    return JsonResponse(
        {
            "attemptId": attempt.id,
            "examId": exam.id,
            "startedAt": _format_iso(attempt.started_at),
            "timeRemaining": attempt.time_remaining,
            "status": attempt.status,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["PATCH"])
def autosave_session(request, attempt_id):
    try:
        attempt = ExamAttempt.objects.get(id=attempt_id)
    except ExamAttempt.DoesNotExist:
        return JsonResponse({"error": "Attempt not found"}, status=404)

    try:
        payload = _parse_json(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    now = datetime.now(UTC)
    if "timeRemaining" in payload:
        attempt.time_remaining = payload["timeRemaining"]
    if "answers" in payload:
        attempt.answers = payload["answers"]
    attempt.saved_at = now
    attempt.save()

    return JsonResponse(
        {
            "attemptId": attempt.id,
            "savedAt": _format_iso(attempt.saved_at),
            "status": attempt.status,
        },
        status=200,
    )
