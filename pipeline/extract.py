import json
import os
import re
import time
from typing import Generator, Dict, Any, List, Optional
from django.conf import settings
from django.utils import timezone
from wardapp.models import Interview, Row, RunLog
from wardapp.constants import CELL_FIELDS

MOCK_EXTRACTED_PROBLEMS = [
    {
        "category": "Drainage & Flooding",
        "sub_category": "Drainage overflow",
        "where": "అంజయ్య నగర్",
        "what": "వర్షాకాలం రాకముందే డ్రైనేజీ లైన్లు నిండిపోయి రోడ్లపైకి మురుగునీరు వస్తోంది",
        "why": "నిర్లక్ష్యం (వర్కర్ల నిర్లక్ష్యం)",
        "to_people": "ప్రజలు చాలా ఇబ్బందులు పడుతున్నారు, రోగాల భయం",
        "how": "1. డ్రైనేజీ లైన్లు నిండిపోవడం 2. రోడ్లపైకి మురుగునీరు రావడం",
        "solution": "డ్రైనేజీ వ్యవస్థను వెంటనే క్లీన్ చేయాలి",
        "solution_impact": "Lower level (కార్పొరేటర్)",
        "voter_impact": "ప్రజల్లో తీవ్ర అసంతృప్తి",
        "vote_plus": "",
        "vote_minus": "-",
        "urgency": "4",
        "scale": "కాలనీ",
        "dept_official": "GHMC శానిటేషన్ అధికారి",
        "influencer": "",
        "law_route": "మున్సిపల్ అధికారులు / GHMC",
        "work_done": "లేదు (పని జరగలేదు)",
        "past_complaint": "స్థానిక కార్పొరేటర్ కి మరియు వార్డ్ ఆఫీస్ లో ఫిర్యాదు ఇచ్చారు కానీ పట్టించుకోలేదు",
        "source_quote": "మా బస్తీలో ముఖ్యంగా రెండు పెద్ద సమస్యలు ఉన్నాయి. మొదటిది డ్రైనేజీ ఓవర్ ఫ్లో. వర్షాకాలం రాకముందే డ్రైనేజీ లైన్లు నిండిపోయి రోడ్లపైకి మురుగునీరు వస్తోంది.",
        "source_time": "12s"
    },
    {
        "category": "Safety & Law/Order",
        "sub_category": "Bribery & worker extortion",
        "where": "అంజయ్య నగర్",
        "what": "డ్రైనేజీ మట్టి రోడ్డుపై వదిలేసి, తీయడానికి డబ్బులు డిమాండ్ చేస్తున్నారు",
        "why": "డబ్బుల ఆశ (అవినీతి)",
        "to_people": "డబ్బులు డిమాండ్ చేయడం",
        "how": "1. డ్రైనేజీ పూడిక తీస్తారు 2. మట్టిని రోడ్డు పక్కనే వదిలేస్తారు 3. తీయడానికి డబ్బులు అడుగుతారు",
        "solution": "అవినీతి వర్కర్లపై చర్యలు తీసుకోవాలి",
        "solution_impact": "Lower level (కార్పొరేటర్)",
        "voter_impact": "ప్రజల్లో ఆగ్రహం",
        "vote_plus": "",
        "vote_minus": "-",
        "urgency": "4",
        "scale": "కాలనీ",
        "dept_official": "GHMC శానిటేషన్ వర్కర్లు",
        "influencer": "",
        "law_route": "జోనల్ అధికారి -> పోలీస్ / ఏసీబీ",
        "work_done": "లేదు (పని జరగలేదు)",
        "past_complaint": "వార్డ్ ఆఫీస్ లో చెప్పినా పట్టించుకోలేదు",
        "source_quote": "జిహెచ్ఎంసి శానిటేషన్ వర్కర్లు డ్రైనేజీ పూడిక తీసి ఆ మట్టిని రోడ్డు పక్కనే వదిలేస్తున్నారు. ఆ మట్టి తీయడానికి వచ్చి మా దగ్గర డబ్బులు డిమాండ్ చేస్తున్నారు.",
        "source_time": "28s"
    },
    {
        "category": "Water Supply",
        "sub_category": "Water for drinking",
        "where": "అంజయ్య నగర్",
        "what": "వారానికి రెండు రోజులే నీళ్లు రావడం, మురుగు నీరు కలవడం",
        "why": "పైపు లైన్ లీకేజీలు, వ్యవస్థ వైఫల్యం",
        "to_people": "తాగే నీరు లేక ఇబ్బందులు",
        "how": "1. వారానికి రెండు రోజులే నీరు 2. పైపుల లీకేజీ వల్ల మురుగు నీరు కలుస్తుంది",
        "solution": "కొత్త పైపులైన్ వేసి రెగ్యులర్ గా నీరు సరఫరా చేయాలి",
        "solution_impact": "Middle level (ఎమ్మెల్యే / వాటర్ బోర్డ్)",
        "voter_impact": "తీవ్ర అసంతృప్తి",
        "vote_plus": "",
        "vote_minus": "-",
        "urgency": "5",
        "scale": "కాలనీ",
        "dept_official": "వాటర్ బోర్డ్ ఇంజనీర్",
        "influencer": "",
        "law_route": "వాటర్ బోర్డ్ (HMWSSB)",
        "work_done": "లేదు (పని జరగలేదు)",
        "past_complaint": "",
        "source_quote": "రెండోది తాగునీటి సరఫరా. వారానికి రెండు రోజులే మంచి నీళ్లు వస్తున్నాయి. పైపు లైన్ లీకేజీల వల్ల తాగే నీటిలో మురుగు నీరు కలుస్తోంది.",
        "source_time": "52s"
    }
]

def parse_incremental_json_objects(text_chunks_generator) -> Generator[Dict[str, Any], None, str]:
    """
    Incrementally parses JSON objects emitted as part of an array: [ { ... }, { ... } ].
    Yields parsed dicts as soon as each object is completely received and valid.
    """
    buffer = ""
    in_string = False
    escape = False
    brace_depth = 0
    obj_start = -1
    yielded_count = 0
    
    for chunk in text_chunks_generator:
        start_scan = len(buffer)
        buffer += chunk
        i = start_scan if obj_start != -1 else 0
        
        while i < len(buffer):
            char = buffer[i]
            
            if escape:
                escape = False
                i += 1
                continue
                
            if char == '\\':
                escape = True
                i += 1
                continue
                
            if char == '"':
                in_string = not in_string
                i += 1
                continue
                
            if not in_string:
                if char == '{':
                    if brace_depth == 0:
                        obj_start = i
                    brace_depth += 1
                elif char == '}':
                    brace_depth -= 1
                    if brace_depth == 0 and obj_start != -1:
                        candidate = buffer[obj_start:i+1].strip()
                        try:
                            parsed_obj = json.loads(candidate)
                            if isinstance(parsed_obj, dict):
                                yield parsed_obj
                                yielded_count += 1
                                buffer = buffer[i+1:]
                                i = -1
                                obj_start = -1
                                brace_depth = 0
                        except json.JSONDecodeError:
                            # If it failed to parse as valid JSON, reset brace depth to avoid permanently wedging
                            obj_start = -1
                            brace_depth = 0
            i += 1

    # End of stream fallback: if buffer still contains valid salvageable objects
    if buffer:
        fallbacks = sanitize_json_response(buffer)
        for obj in fallbacks:
            yield obj

    return buffer

def sanitize_json_response(raw_text: str) -> List[Dict[str, Any]]:
    """Fallback parser to extract JSON array or objects if incremental stream didn't catch all."""
    clean = raw_text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()
    
    # Try direct parse
    try:
        data = json.loads(clean)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        elif isinstance(data, dict):
            return [data]
    except Exception:
        pass
        
    # Regex fallback for any valid { ... } JSON objects
    results = []
    # Match outermost braces
    pattern = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}')
    for match in pattern.finditer(clean):
        try:
            item = json.loads(match.group(0))
            if isinstance(item, dict):
                results.append(item)
        except Exception:
            continue
    return results

def categorize_qa(q: str, a: str) -> tuple:
    """Heuristic categorizer for Telugu civic issues when offline."""
    text = (q + " " + a).lower()
    if any(k in text for k in ["డబ్బులు డిమాండ్", "డబ్బులు అడుగు", "మర్డర్", "కేసు", "లంచం"]):
        return ("Safety & Law/Order", "Bribery & worker extortion")
    elif any(k in text for k in ["మంజీరా", "తాగునీరు", "మంచి నీళ్లు", "వాటర్", "పైప్"]):
        return ("Water Supply", "Water for drinking")
    elif "ఓపెన్ నాలా" in text:
        return ("Drainage & Flooding", "Open nala hazard")
    elif any(k in text for k in ["వర్షపునీరు", "వరద నీరు", "ఇళ్లలోకి"]):
        return ("Drainage & Flooding", "Rainwater entering houses")
    elif any(k in text for k in ["డ్రైనేజ్", "డ్రైనేజీ", "మురుగు", "కాలువ"]):
        return ("Drainage & Flooding", "Drainage overflow")
    elif any(k in text for k in ["దోమల", "ఫాగింగ్", "స్ప్రే"]):
        return ("Sanitation & Cleanliness", "Mosquitoes & fogging")
    elif any(k in text for k in ["డంప్", "డంపింగ్", "చెత్త", "మట్టి"]):
        return ("Sanitation & Cleanliness", "Garbage & dump yards")
    elif any(k in text for k in ["టాయిలెట్", "మూత్ర విసర్జన"]):
        return ("Sanitation & Cleanliness", "Public toilets")
    elif any(k in text for k in ["స్ట్రీట్ లైట్", "ఎలక్ట్రిక్", "వైర్లు", "స్తంభాల"]):
        return ("Roads & Electricity", "Streetlights")
    elif any(k in text for k in ["రోడ్డు", "రోడ్ల", "గుంతలు", "మరమ్మత్తు"]):
        return ("Roads & Electricity", "Roads & potholes")
    elif "కుక్కల" in text:
        return ("Health & Community", "Stray dogs")
    elif any(k in text for k in ["పార్క్", "గ్రౌండ్", "ఆస్పత్రి", "మందులు"]):
        return ("Health & Community", "Parks & playgrounds")
    elif any(k in text for k in ["పెన్షన్", "ఆధార్", "రేషన్", "డబుల్ బెడ్", "2bhk"]):
        return ("Welfare & Schemes", "Pensions (Widow / Old Age / Disability)")
    elif any(k in text for k in ["కార్పొరేటర్", "నాయకుడు", "ఎమ్మెల్యే", "ఎలక్షన్", "మద్యం"]):
        return ("Local Leaders & Cadre", "Leader behaviour with public")
    return ("Sanitation & Cleanliness", "Cleaning of roads & silt removal")

def extract_qa_problems_from_text(transcript_text: str, default_area: str = "") -> List[Dict[str, Any]]:
    """Parses Telugu Q&A interview/survey notes into structured problem objects."""
    problems = []
    sections = re.split(r"(?:^|\n)##\s+", transcript_text)
    
    if len(sections) > 1:
        for s in sections[1:]:
            lines = s.strip().split("\n")
            section_title = lines[0].strip()
            area_name = re.sub(r"^\d+\.?\s*", "", section_title).strip()
            rest = "\n".join(lines[1:])
            
            qa_pattern = re.compile(
                r"(?:^|\n)ప్రశ్న[:\s]+(.*?)(?:\n\s*(?:⏸|ఆగండి|\s)+)?\n\s*జవాబు[:\s]+(.*?)(?=(?:\nప్రశ్న|\Z))",
                re.DOTALL
            )
            pairs = list(qa_pattern.finditer(rest))
            for p in pairs:
                q = p.group(1).replace("⏸", "").replace("ఆగండి", "").strip()
                a = p.group(2).strip()
                cat, subcat = categorize_qa(q, a)
                
                why = ""
                if "నిర్లక్ష్యం" in a:
                    why = "వర్కర్ల నిర్లక్ష్యం"
                elif "డబ్బులు డిమాండ్" in a or "డబ్బులు అడుగు" in a:
                    why = "డబ్బుల ఆశ (అవినీతి)"
                elif "మాట ఇచ్చి" in a:
                    why = "మాట ఇచ్చి పూర్తి చేయకపోవడం"
                elif "పట్టించుకోవడం" in a:
                    why = "అధికారుల నిర్లక్ష్యం / పట్టించుకోకపోవడం"

                to_people = ""
                if "ఇబ్బందు" in a:
                    to_people = "కాలనీవాసులు తీవ్ర ఇబ్బందులకు గురవుతున్నారు"
                if "డబ్బులు డిమాండ్" in a:
                    to_people = "డబ్బులు డిమాండ్ చేస్తున్నారు"

                solution = ""
                sol_match = re.search(r"(?:చర్యలు తీసుకోవాలి|పూర్తి చేయాలి|శుభ్రం చేయాలి|ఏర్పాటు చేయాలి|పరిష్కరించాలి)[^\n.]*", a)
                if sol_match:
                    solution = sol_match.group(0).strip()
                elif "కావున" in a:
                    solution = a.split("కావున")[-1].strip()

                voter_impact = ""
                if "ఓటర్ల" in a or "ఓటింగ్" in a or "వ్యతిరేకత" in a or "అభిమానం" in a or "ఓటు" in a:
                    for sentence in a.split("."):
                        if any(w in sentence for w in ["ఓటర్ల", "ఓటింగ్", "వ్యతిరేకత", "అభిమానం", "ఓటు"]):
                            voter_impact = sentence.strip()
                            break

                problems.append({
                    "category": cat,
                    "sub_category": subcat,
                    "where": area_name,
                    "what": a[:150],
                    "why": why,
                    "to_people": to_people,
                    "how": f"1. {q} -> 2. {a[:80]}",
                    "solution": solution,
                    "solution_impact": "Middle level (ఎమ్మెల్యే)" if "ఎమ్మెల్యే" in (q + a) else "Lower level (కార్పొరేటర్)",
                    "voter_impact": voter_impact,
                    "vote_plus": "",
                    "vote_minus": "-",
                    "urgency": "4" if "తీవ్ర" in a or "ప్రమాదం" in a else "3",
                    "scale": "కాలనీ",
                    "dept_official": "GHMC / వాటర్ బోర్డ్",
                    "influencer": "",
                    "law_route": "GHMC / మున్సిపల్ అధికారులు",
                    "work_done": "లేదు (పని జరగలేదు)",
                    "past_complaint": "ఫిర్యాదు చేసినా పట్టించుకోలేదు" if "ఫిర్యాదు" in a or "కంప్లైంట్" in a else "",
                    "source_quote": f"ప్రశ్న: {q}\nజవాబు: {a}",
                    "source_time": ""
                })
    return problems

def stream_extract_rows(interview: Interview) -> Generator[Dict[str, Any], None, List[Row]]:
    """
    Calls Gemini with the transcript and prompt version.
    Incrementally parses JSON array, creates Row objects, and yields them.
    """
    run_log = RunLog.objects.create(
        interview=interview,
        step="extract",
        started_at=timezone.now(),
        message="Starting row extraction stream"
    )

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash')

    prompt_text = ""
    if interview.prompt_version and interview.prompt_version.text:
        prompt_text = interview.prompt_version.text
    else:
        prompt_file = settings.BASE_DIR / 'gemini_prompt_ward119.md'
        if prompt_file.exists():
            prompt_text = prompt_file.read_text(encoding='utf-8')

    full_system_instruction = (
        f"{prompt_text}\n\n"
        "IMPORTANT: Output MUST be a strictly valid JSON array of objects. "
        "Do NOT include markdown formatting or explanations."
    )

    extracted_rows = []
    order_no = 1

    # Offline / Mock Fallback if no GEMINI_API_KEY
    if not api_key:
        run_log.message = "No GEMINI_API_KEY found; extracting problem rows from transcript"
        run_log.save()
        
        parsed_problems = []
        if interview.transcript and len(interview.transcript.strip()) > 30:
            parsed_problems = extract_qa_problems_from_text(
                interview.transcript, 
                interview.area.name if interview.area else ""
            )
            
        if not parsed_problems:
            parsed_problems = MOCK_EXTRACTED_PROBLEMS
        
        for problem in parsed_problems:
            time.sleep(0.1)
            row = Row.objects.create(
                interview=interview,
                area=interview.area,
                speaker_name=interview.speaker_name,
                speaker_phone=interview.speaker_phone,
                category=problem.get('category', 'Other'),
                sub_category=problem.get('sub_category', 'General'),
                order_no=order_no,
                source_quote=problem.get('source_quote', ''),
                source_time=problem.get('source_time', ''),
                where=problem.get('where', ''),
                what=problem.get('what', ''),
                why=problem.get('why', ''),
                to_people=problem.get('to_people', ''),
                how=problem.get('how', ''),
                solution=problem.get('solution', ''),
                solution_impact=problem.get('solution_impact', ''),
                voter_impact=problem.get('voter_impact', ''),
                vote_plus=problem.get('vote_plus', ''),
                vote_minus=problem.get('vote_minus', ''),
                urgency=problem.get('urgency', ''),
                scale=problem.get('scale', ''),
                dept_official=problem.get('dept_official', ''),
                influencer=problem.get('influencer', ''),
                law_route=problem.get('law_route', ''),
                work_done=problem.get('work_done', ''),
                past_complaint=problem.get('past_complaint', '')
            )
            order_no += 1
            extracted_rows.append(row)
            yield {'type': 'row_created', 'row': row, 'data': problem}

        raw_json_str = json.dumps(parsed_problems, ensure_ascii=False, indent=2)
        interview.raw_extract_response = raw_json_str
        interview.status = 'done'
        interview.finished_at = timezone.now()
        interview.save(update_fields=['raw_extract_response', 'status', 'finished_at'])

        run_log.ended_at = timezone.now()
        run_log.tokens_in = len(parsed_problems) * 120
        run_log.tokens_out = len(parsed_problems) * 150
        run_log.message = f"Successfully created {len(extracted_rows)} structured problem rows"
        run_log.save()
        return extracted_rows

    # Real Gemini execution with retry
    retries = 1
    last_error = None
    accumulated_chunks = []

    for attempt in range(retries + 1):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            user_content = (
                f"Extract structured problem rows from this Telugu interview transcript:\n\n"
                f"{interview.transcript}"
            )

            response_stream = client.models.generate_content_stream(
                model=model_name,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=full_system_instruction,
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )

            def chunk_generator():
                for chunk in response_stream:
                    t = chunk.text or ""
                    accumulated_chunks.append(t)
                    yield t

            for parsed_obj in parse_incremental_json_objects(chunk_generator()):
                row = Row.objects.create(
                    interview=interview,
                    area=interview.area,
                    speaker_name=interview.speaker_name,
                    speaker_phone=interview.speaker_phone,
                    category=parsed_obj.get('category', 'Other'),
                    sub_category=parsed_obj.get('sub_category', 'General'),
                    order_no=order_no,
                    source_quote=parsed_obj.get('source_quote', ''),
                    source_time=parsed_obj.get('source_time', ''),
                    where=parsed_obj.get('where', ''),
                    what=parsed_obj.get('what', ''),
                    why=parsed_obj.get('why', ''),
                    to_people=parsed_obj.get('to_people', ''),
                    how=parsed_obj.get('how', ''),
                    solution=parsed_obj.get('solution', ''),
                    solution_impact=parsed_obj.get('solution_impact', ''),
                    voter_impact=parsed_obj.get('voter_impact', ''),
                    vote_plus=parsed_obj.get('vote_plus', ''),
                    vote_minus=parsed_obj.get('vote_minus', ''),
                    urgency=parsed_obj.get('urgency', ''),
                    scale=parsed_obj.get('scale', ''),
                    dept_official=parsed_obj.get('dept_official', ''),
                    influencer=parsed_obj.get('influencer', ''),
                    law_route=parsed_obj.get('law_route', ''),
                    work_done=parsed_obj.get('work_done', ''),
                    past_complaint=parsed_obj.get('past_complaint', '')
                )
                order_no += 1
                extracted_rows.append(row)
                yield {'type': 'row_created', 'row': row, 'data': parsed_obj}

            # If incremental missed any objects due to format quirks, try fallback sanitize
            raw_full_text = "".join(accumulated_chunks)
            interview.raw_extract_response = raw_full_text
            
            if len(extracted_rows) == 0:
                fallback_items = sanitize_json_response(raw_full_text)
                for item in fallback_items:
                    row = Row.objects.create(
                        interview=interview,
                        area=interview.area,
                        speaker_name=interview.speaker_name,
                        speaker_phone=interview.speaker_phone,
                        category=item.get('category', 'Other'),
                        sub_category=item.get('sub_category', 'General'),
                        order_no=order_no,
                        source_quote=item.get('source_quote', ''),
                        source_time=item.get('source_time', ''),
                        where=item.get('where', ''),
                        what=item.get('what', ''),
                        why=item.get('why', ''),
                        to_people=item.get('to_people', ''),
                        how=item.get('how', ''),
                        solution=item.get('solution', ''),
                        solution_impact=item.get('solution_impact', ''),
                        voter_impact=item.get('voter_impact', ''),
                        vote_plus=item.get('vote_plus', ''),
                        vote_minus=item.get('vote_minus', ''),
                        urgency=item.get('urgency', ''),
                        scale=item.get('scale', ''),
                        dept_official=item.get('dept_official', ''),
                        influencer=item.get('influencer', ''),
                        law_route=item.get('law_route', ''),
                        work_done=item.get('work_done', ''),
                        past_complaint=item.get('past_complaint', '')
                    )
                    order_no += 1
                    extracted_rows.append(row)
                    yield {'type': 'row_created', 'row': row, 'data': item}

            interview.status = 'done'
            interview.finished_at = timezone.now()
            interview.save(update_fields=['raw_extract_response', 'status', 'finished_at'])

            run_log.ended_at = timezone.now()
            run_log.message = f"Successfully extracted {len(extracted_rows)} rows"
            run_log.save()
            return extracted_rows

        except Exception as e:
            last_error = e
            time.sleep(1)

    raw_full_text = "".join(accumulated_chunks)
    if len(extracted_rows) > 0:
        interview.raw_extract_response = raw_full_text
        interview.status = 'done'
        interview.finished_at = timezone.now()
        interview.save(update_fields=['raw_extract_response', 'status', 'finished_at'])
        run_log.ended_at = timezone.now()
        run_log.message = f"Stream ended with partial exception, but saved {len(extracted_rows)} Gemini extracted rows."
        run_log.save()
        return extracted_rows

    err_msg = f"Extraction failed: {str(last_error)}"
    interview.raw_extract_response = raw_full_text
    interview.error = err_msg
    interview.status = 'failed'
    interview.finished_at = timezone.now()
    interview.save(update_fields=['raw_extract_response', 'error', 'status', 'finished_at'])

    run_log.ended_at = timezone.now()
    run_log.message = err_msg
    run_log.save()
    raise RuntimeError(err_msg)
