# Antigravity prompt: Ward 119 interview -> live sheet (Django + PostgreSQL)

Build a Django 5 + PostgreSQL web app. Purpose: TESTING. One user (me) uploads a Telugu interview audio, watches it being transcribed and turned into sheet rows LIVE, and then marks exactly where the AI went wrong. Keep it simple, readable and easy to debug.

## STACK
- Django 5, Python 3.12, PostgreSQL (Neon or Supabase, via DATABASE_URL), HTML/CSS/JS (no React).
- Gemini through the `google-genai` SDK. Env vars: GEMINI_API_KEY, GEMINI_MODEL (default a current Gemini Flash model, keep it configurable), DATABASE_URL, SECRET_KEY.
- Live updates with Server-Sent Events (StreamingHttpResponse). No Channels or Redis. Deploy target: Render.
- Auth: one shared password (env APP_PASSWORD) with a simple login page. No user accounts.

## PAGES
1. **Upload** (`/`): upload audio (mp3, wav, m4a), choose area (dropdown of the 10 areas), enter **speaker name** and **speaker phone** (these are saved on every row made from this interview), choose prompt version. Button "Start".
2. **Live run** (`/run/<id>/`): split screen.
   - Left: audio player and the Telugu transcript appearing live as Gemini streams it.
   - Right: the sheet. Rows appear one by one as Gemini finishes each problem, and each cell types out live (typewriter effect) like it is being written in front of me. Columns are filled in order.
3. **Sheet** (`/sheet/`): the full table of all rows from all interviews, grouped by Category > Sub-category (same layout as my Google-sheet style table). Every cell is editable inline and saves automatically after 500 ms. Filter by area, speaker, interview.
4. **Review** (`/review/<id>/`): for one interview show side by side: transcript, `source_quote` for each row, the row cells, and the raw Gemini response. Next to every cell: a tick and a cross. A cross opens a reason: wrong_transcription, wrong_category, wrong_split, invented_fact, missing_info, wrong_vote, wrong_level, wrong_cause, other, plus a free note. Show a summary: how many cells ticked or crossed, and which reason is most common.
5. **Prompts** (`/prompts/`): list, edit and create prompt versions (the Gemini system prompt text is stored in the database). Each run records which version it used. Seed version 1 from the file `gemini_prompt_ward119.md` (copy its text into a fixtures file).

## DATA MODEL (PostgreSQL)
- Area(name)
- PromptVersion(name, text, created_at)
- Interview(area, speaker_name, speaker_phone, audio_file, transcript, prompt_version, model_name, status [uploaded, transcribing, extracting, done, failed], raw_transcript_response, raw_extract_response, error, created_at, finished_at)
- Row(interview, area, speaker_name, speaker_phone, category, sub_category, order_no, source_quote, and these cell fields, all text, blank allowed: where, what, why, to_people, how, solution, solution_impact, voter_impact, vote_plus, vote_minus, urgency, scale, dept_official, influencer, law_route, work_done, past_complaint)
- CellReview(row, field_name, is_correct, reason, note, created_at)
- RunLog(interview, step, started_at, ended_at, tokens_in, tokens_out, message)

Every Row copies speaker_name and speaker_phone from its Interview, so I can see WHO said each point.

## THE AI PIPELINE (two Gemini calls, both streamed)
1. **Transcribe**: upload the audio with the Gemini File API. Ask for a faithful Telugu transcript, keeping names, numbers and phone numbers as spoken, marking unclear words as [అస్పష్టం]. Stream chunks to the page and save the full text in `Interview.transcript`.
2. **Extract**: send the transcript with the saved prompt version as the system instruction. Request JSON only: an array of objects, one per problem, with keys: category, sub_category, where, what, why, to_people, how, solution, solution_impact, voter_impact, vote_plus, vote_minus, urgency, scale, dept_official, influencer, law_route, work_done, past_complaint, source_quote (the exact Telugu sentence from the transcript that this row comes from). Parse the streamed JSON incrementally; as soon as one object is complete, save a Row and push it to the page.
Rules for the code: never crash on bad JSON (save the raw response, set status failed, show the error), retry once, and always keep raw responses so I can inspect them.

## LIVE BEHAVIOUR (SSE events)
`transcript_chunk`, `row_created`, `cell_filled` (row id, field, text), `status`, `done`, `error`. The page reconnects automatically if the stream drops. If I refresh during a run, show what is already saved and continue streaming.

## SHEET LAYOUT AND COLUMNS (headings in English, cell text in Telugu)
Categories and sub-categories (store as constants):
1. Water Supply: Water for drinking; Water for washing / daily use
2. Drainage & Flooding: Drainage overflow; Rainwater entering houses; Open nala hazard
3. Sanitation & Cleanliness: Cleaning of roads & silt removal; Garbage & dump yards; Mosquitoes & fogging; Public toilets
4. Roads & Electricity: Roads & potholes; Streetlights; Electric poles & hanging wires; Speed breakers & traffic
5. Health & Community: Parks & playgrounds; Hospital & medicines; Stray dogs
6. Safety & Law/Order: Drugs & ganja nuisance; Police patrolling & night safety; Bribery & worker extortion
7. Welfare & Schemes: Pensions (Widow / Old Age / Disability); Ration cards; Double bedroom houses (2BHK)
8. Local Leaders & Cadre: Leader behaviour with public (rude behaviour, not visiting, opposition leaders gaining ground, election-time money / liquor talk)
Columns: 1.where, 2.what is happening, 3.why (root cause), 4.what is happening to people, 5.how (steps), 6.solution, 7.solution impact (leader level), voter impact, + done, - not done, urgency, scale, responsible dept and official, local influencer, law/authority route, work done?, past complaint given?, plus speaker name and phone.
Rows can be more than 2 per sub-category; show as many rows as exist, grouped.

## ERROR-FINDING FEATURES (the main point of this app)
- Show under every row its `source_quote` and a button "play this part" if a timestamp is available (ask Gemini for an approximate start time in seconds as `source_time`).
- Highlight a cell in yellow if it is empty but the transcript seems to contain that information, and in red if the cell text has words that do not appear in the transcript (possible invention). Do a simple check in Python, no AI.
- A "Compare runs" page: pick two runs of the same audio (different prompt versions) and show the rows side by side.
- Export: CSV of the sheet (UTF-8 with BOM so Telugu opens correctly in Excel) and a JSON export of one interview.

## QUALITY BAR
- Telugu text must display correctly (UTF-8 everywhere, a Telugu-capable font such as Noto Sans Telugu via Google Fonts with a system fallback).
- Mobile-friendly upload page; sheet scrolls horizontally with sticky headers and sticky first columns.
- Keep code in small modules: `pipeline/transcribe.py`, `pipeline/extract.py`, `pipeline/sse.py`, `models.py`, `views.py`.
- Write tests for the JSON parser (partial objects, bad JSON) and for the invented-fact check.
- README with: how to run locally, env vars, how to deploy on Render, how to add a prompt version.

## FIRST MILESTONE (do this first, then stop and show me)
Upload -> transcribe live -> extract rows live -> sheet page with inline editing -> Review page with tick and cross. Everything else after I confirm.
