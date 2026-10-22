from django.test import TestCase
from pipeline.extract import parse_incremental_json_objects, sanitize_json_response
from pipeline.validator import check_invented_words, check_missing_info, validate_cell
from pipeline import transcribe, TranscriptResult

class JSONParserTests(TestCase):
    def test_parse_incremental_chunks(self):
        """Tests that objects split across small chunks are correctly parsed as soon as each completes."""
        chunks = [
            '[\n  {\n    "category": "Drain',
            'age & Flooding",\n    "what": "రోడ్డుపై మురు',
            'గు నీరు",\n    "urgency": "4"\n  },\n  {',
            '\n    "category": "Water Supply",\n    "what": "తాగునీటి సమ',
            'స్య"\n  }\n]'
        ]
        results = list(parse_incremental_json_objects(chunks))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["category"], "Drainage & Flooding")
        self.assertEqual(results[0]["what"], "రోడ్డుపై మురుగు నీరు")
        self.assertEqual(results[0]["urgency"], "4")
        self.assertEqual(results[1]["category"], "Water Supply")
        self.assertEqual(results[1]["what"], "తాగునీటి సమస్య")

    def test_parse_with_escaped_quotes_and_nested_content(self):
        chunks = [
            '[{"what": "He said \\"urgent\\" problem", "why": "నిర్లక్ష్యం"}]'
        ]
        results = list(parse_incremental_json_objects(chunks))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["what"], 'He said "urgent" problem')

    def test_bad_json_handling(self):
        """Malformed JSON should not raise an unhandled exception, and fallback parser should extract salvageable objects."""
        bad_stream = ['[ {broken_json', '... invalid text here', '{"category": "Health", "what": "ఆస్పత్రి"}']
        results = list(parse_incremental_json_objects(bad_stream))
        # The valid object at the end is extracted
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["category"], "Health")

    def test_sanitize_fallback_with_markdown(self):
        raw = "```json\n[\n{\"category\": \"Sanitation\", \"what\": \"చెత్త సమస్య\"}\n]\n```"
        parsed = sanitize_json_response(raw)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["category"], "Sanitation")


class ValidatorTests(TestCase):
    def setUp(self):
        self.transcript = (
            "అంజయ్య నగర్ లో డ్రైనేజీ సమస్య ఉంది. శానిటేషన్ వర్కర్లు డబ్బులు అడుగుతున్నారు. "
            "మేము కార్పొరేటర్ కి ఫిర్యాదు ఇచ్చాము."
        )

    def test_faithful_words_not_flagged(self):
        cell_text = "డ్రైనేజీ సమస్య"
        is_invented, missing = check_invented_words(cell_text, self.transcript)
        self.assertFalse(is_invented)
        self.assertEqual(len(missing), 0)

    def test_invented_words_flagged(self):
        # Spurious words not in transcript
        cell_text = "మెట్రో రైల్ ప్రాజెక్ట్ విమానాశ్రయం బస్సు పాస్ సమస్య"
        is_invented, missing = check_invented_words(cell_text, self.transcript)
        self.assertTrue(is_invented)
        self.assertTrue(len(missing) >= 2)

    def test_missing_info_detection(self):
        # The transcript contains "ఫిర్యాదు", so past_complaint should trigger missing info if empty
        self.assertTrue(check_missing_info("past_complaint", "", self.transcript))
        # If the cell already has text, it is not missing
        self.assertFalse(check_missing_info("past_complaint", "ఫిర్యాదు ఇచ్చారు", self.transcript))
        # Field without relevant keywords in transcript
        self.assertFalse(check_missing_info("urgency", "", self.transcript))

    def test_validate_cell_result(self):
        result_red = validate_cell("what", "మెట్రో రైల్ ప్రాజెక్ట్ విమానాశ్రయం", self.transcript)
        self.assertEqual(result_red['highlight'], 'red')

        result_yellow = validate_cell("past_complaint", "", self.transcript)
        self.assertEqual(result_yellow['highlight'], 'yellow')

        result_none = validate_cell("what", "డ్రైనేజీ సమస్య", self.transcript)
        self.assertEqual(result_none['highlight'], 'none')


class ViewAndExportTests(TestCase):
    def setUp(self):
        from wardapp.models import Area, PromptVersion, Interview, Row
        self.area, _ = Area.objects.get_or_create(name="అంజయ్య నగర్ & జయశంకర్ నగర్")
        self.prompt = PromptVersion.objects.create(name="Test Prompt v1", text="System prompt text")
        self.interview = Interview.objects.create(
            area=self.area,
            speaker_name="సురేష్ కుమార్",
            speaker_phone="9848011223",
            transcript="నమస్కారం, అంజయ్య నగర్ లో డ్రైనేజీ సమస్య ఉంది.",
            prompt_version=self.prompt,
            status="done"
        )
        self.row = Row.objects.create(
            interview=self.interview,
            area=self.area,
            speaker_name=self.interview.speaker_name,
            speaker_phone=self.interview.speaker_phone,
            category="Drainage & Flooding",
            sub_category="Drainage overflow",
            order_no=1,
            where="అంజయ్య నగర్",
            what="డ్రైనేజీ రోడ్డుపై మురుగు నీరు",
            why="నిర్లక్ష్యం",
            vote_minus="-"
        )

    def test_auth_protection_redirect(self):
        # Unauthenticated request to / should redirect to /login/
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_login_and_authenticated_access(self):
        # Post correct password
        session = self.client.session
        session['is_authenticated'] = True
        session.save()

        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_sheet_view_authenticated(self):
        session = self.client.session
        session['is_authenticated'] = True
        session.save()

        response = self.client.get('/sheet/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Drainage &amp; Flooding")

    def test_export_csv_utf8_bom(self):
        session = self.client.session
        session['is_authenticated'] = True
        session.save()

        response = self.client.get('/sheet/export/csv/')
        self.assertEqual(response.status_code, 200)
        # Check UTF-8 BOM
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))

    def test_export_interview_json(self):
        session = self.client.session
        session['is_authenticated'] = True
        session.save()

        response = self.client.get(f'/interview/{self.interview.id}/export/json/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["speaker_name"], "సురేష్ కుమార్")
        self.assertEqual(len(data["rows"]), 1)


class TranscribeContractTests(TestCase):
    def test_transcribe_stub_contract(self):
        chunks = []
        def on_chunk(chunk):
            chunks.append(chunk)

        result = transcribe("dummy_audio.mp3", speaker_hint="సురేష్", on_chunk=on_chunk)
        self.assertIsInstance(result, TranscriptResult)
        self.assertTrue(result.text.startswith("[STUB RUN]"))
        self.assertTrue(len(chunks) > 0)
        self.assertTrue(len(result.segments) > 0)
        self.assertEqual(result.segments[0].speaker, "సురేష్")


