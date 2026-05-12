import os
import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.5-flash"

CSV_PATH = Path("tasting_log.csv")


# ---------- Language detection ----------
def detect_language(text: str) -> str:
    """한글 비율이 충분히 높으면 'ko', 아니면 'en'."""
    korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters == 0:
        return "en"
    return "ko" if korean_chars / total_letters > 0.2 else "en"


# ---------- Polishing prompt ----------
POLISH_SYSTEM = """**CRITICAL OUTPUT LANGUAGE RULE / 중요 출력 언어 규칙**

If the body text is primarily in Korean → respond ENTIRELY in Korean.
If the body text is primarily in English → respond ENTIRELY in English.
The language hint in the user message tells you which one. Obey it strictly.
NEVER translate. NEVER switch languages.

본문이 한국어이면 반드시 한국어로 출력하세요. 영어이면 영어로.
헤더가 다른 언어여도 본문(body)의 주된 언어를 따르세요.
절대 번역하거나 언어를 바꾸지 마세요.

---

You are a light-touch editor for Gangmuk's coffee tasting essays.

He dictates drafts using voice-to-text in EITHER English OR Korean.

Common issues:

ENGLISH:
- Disfluencies: "um", "uh", "like", "you know"
- Homophones: their/there, bean/been
- Missing punctuation, run-on sentences

KOREAN (한국어):
- 음성인식 오류: 비슷한 발음 단어 잘못 인식
- 조사 누락 또는 잘못된 조사
- 띄어쓰기 오류, 문장부호 누락
- 구어체 추임새: "어", "음", "그", "막", "약간", "뭔가" (필러로 쓰일 때만)
- 영어 단어 한글 표기 오류 (V60 등 영문 그대로 둘 것)
- 명백한 오타: "낫다" → "났다", "설익은ㅇ" → "설익은", "나두었다" → "놔두었다"

WHAT TO FIX (양쪽 언어 공통):
1. 음성인식/입력 오류 (homophones, 잘못 인식된 단어, 명백한 오타)
2. 문장부호, 문단 나누기 추가
3. 순수 필러만 제거
4. 중복 반복
5. 명백히 비논리적인 단어
6. 의미를 바꾸는 문법 오류
7. 띄어쓰기 오류 (예: "맛도굉장히" → "맛도 굉장히")

WHAT NOT TO TOUCH:
- 문장 구조, 어색해도 — 그게 그 사람 목소리
- 단어 선택, 캐주얼한 표현, 슬랭
- 자연스럽게 흐르는 긴 문장
- 개인적 관용 표현, 특이한 맛 묘사
- 한 문장 안의 한국어/영어 혼용 — 그대로 두기
- 반말/존댓말 — 원문 그대로
- "근데", "그래서", "And", "But"로 문장 시작 OK
- 대괄호 섹션 헤더 [...] 형식 유지
- 형식적 메타데이터 라인 (브루 파라미터 등) 그대로 유지

CRITICAL: 확신 없으면 건드리지 마세요. 거친 게 평평한 것보다 낫습니다.

Output ONLY the cleaned text. No preamble, no explanation."""


METADATA_REFORMAT_BASE = """You are reformatting brew-parameter lines in a coffee tasting essay.

The input is a polished coffee tasting essay. Some lines are bare comma-separated brew
parameters, typically appearing right under a [bracketed section header]. Example of such
a line:

  96°C, Kirkland purified water, plastic V60, K-Ultra, 5.5 tick, Origami cone filter, 15g coffee, 220g water

YOUR TASK: Replace ONLY those metadata lines with a structured block (format below).
LEAVE EVERYTHING ELSE EXACTLY AS-IS. Do not touch prose, do not touch [section] headers,
do not translate anything, do not rewrap or reflow paragraphs.

Categorize each token in the metadata line into one of these fields:
- Water:   temperature (°C / celcius / 도) AND water source/brand (e.g. "Kirkland purified").
           Join with ", " if both present.
- Brewer:  dripper (V60, Origami, Kalita, Chemex, Aeropress, etc.) AND filter paper
           (cone filter, abaca, Sibarist, tabbed, etc.). Join with " + ".
           Include material qualifier (plastic / ceramic / 세라믹 / 플라스틱) with the dripper.
- Grinder: grinder model (K-Ultra, Comandante, EK43, etc.) AND grind setting
           (tick, click, number). Join with " @ ".
- Dose:    coffee weight AND water weight. Join with " → ". If BOTH are numeric,
           append the ratio at the end like "(1:14.7)" — compute as water_g / coffee_g,
           one decimal place.

Field-label language must match the surrounding essay language:
- Korean essay → 물 / 브루어 / 그라인더 / 투입량
- English essay → Water / Brewer / Grinder / Dose

Rules:
- If a category has no values for a given metadata line, OMIT that row/bullet entirely.
  Never emit empty rows.
- If a [section header] has no metadata line beneath it (only prose), do nothing for
  that section — leave it untouched.
- Do not invent values. Do not translate brand/model names. Do not translate values
  inside the block.
- Preserve the order of sections and prose. The reformatted block goes in the same
  position as the original metadata line.

{format_spec}

Output the FULL essay with the metadata blocks reformatted. No preamble, no explanation.
"""

METADATA_FORMAT_BULLETS = """OUTPUT FORMAT — markdown bullet list:

- **Water:** 96°C, Kirkland purified
- **Brewer:** Plastic V60 + Origami cone filter
- **Grinder:** K-Ultra @ 5.5 tick
- **Dose:** 15g coffee → 220g water (1:14.7)

(Korean equivalent uses 물 / 브루어 / 그라인더 / 투입량 as the bold labels.)"""

METADATA_FORMAT_TABLE = """OUTPUT FORMAT — markdown table:

| Field   | Value                             |
|---------|-----------------------------------|
| Water   | 96°C, Kirkland purified           |
| Brewer  | Plastic V60 + Origami cone filter |
| Grinder | K-Ultra @ 5.5 tick                |
| Dose    | 15g coffee → 220g water (1:14.7)  |

(Korean equivalent uses 물 / 브루어 / 그라인더 / 투입량 in the Field column;
keep the header row in the same language as the labels.)"""

METADATA_FORMATS = {
    "bullets": METADATA_REFORMAT_BASE.format(format_spec=METADATA_FORMAT_BULLETS),
    "table": METADATA_REFORMAT_BASE.format(format_spec=METADATA_FORMAT_TABLE),
}


TRANSLATE_SYSTEM = """You are translating Gangmuk's coffee tasting essays
between Korean and English. The input is ALREADY POLISHED text (clean grammar,
clear punctuation). Your job is translation only.

**CRITICAL: Preserve voice, not just meaning.**

Gangmuk writes coffee notes in a personal, observational style — not reviews,
not marketing copy. He uses unconventional flavor descriptions, memories,
casual phrasing, and code-switches between languages. The translation must
sound like HE wrote it in the target language, not like a translator's output.

RULES:
1. Translate every sentence. Do not skip, do not summarize.
2. Preserve the bracketed section headers [...] — translate the content inside,
   keep the bracket structure.
3. Keep specialty coffee terminology in its conventional form in the target
   language (e.g. "워시드" ↔ "washed", "내추럴" ↔ "natural", "펑키함" ↔ "funkiness",
   "잡맛" ↔ "off-flavors", "산미" ↔ "acidity", "단맛" ↔ "sweetness").
4. Brand/model names stay as-is in both languages (V60, Origami, Kalita,
   K-Ultra, SEY, Cafec, Hario, Sibarist).
5. Numbers, weights, temperatures, tick settings — keep exactly as written.
6. Mixed-language phrases ("funky함", "consistent하기") — render the meaning
   naturally in the target language without losing the casual feel.
7. Keep the tone register:
   - Korean 반말 (해라/한다 style) → English first-person casual essay voice
   - English casual → Korean 반말 (다나까 X, 했다/이다 O)
8. Unconventional flavor descriptions: translate the IMAGE, not word-for-word.
   "셔! 라고 말이 튀어나오고 눈이 살짝 윙크가 될 정도의 신맛" →
   "sour enough that I blurted 'sour!' out loud and my eye twitched a little"
   NOT "a sour taste that makes you say 'sour' and wink slightly your eye"
9. Preserve any English words/phrases that appear in Korean source (and vice
   versa) — they're stylistic choices, not errors.

WHAT NOT TO DO:
- Do not "improve" the prose. Translate at the same level of polish as input.
- Do not add explanatory phrases or context the source didn't have.
- Do not formalize the tone. Casual stays casual.
- Do not translate proper nouns or brand names.

Output ONLY the translated text. No preamble, no notes."""

# ---------- Extraction schema ----------
POUR_SCHEMA = {
    "type": "object",
    "properties": {
        "pour_label": {
            "type": "string",
            "description": "Label in same language as draft. EN: 'bloom', 'second'. KO: '뜸들이기', '2차'."
        },
        "water_g_cumulative": {"type": "number"},
        "time_sec": {"type": "number"},
    },
}

BREW_SCHEMA = {
    "type": "object",
    "properties": {
        "roastery": {
            "type": "string",
            "description": "Roaster name. Proper noun as written (SEY, 프릳츠, Onyx)."
        },
        "coffee_name": {
            "type": "string",
            "description": "Coffee name/lot only (e.g. 'Armando Hurtado Los PINOS SL9'). "
                           "Do NOT include the country here — that goes in the country field."
        },
        "country": {
            "type": "string",
            "description": "Country of origin. SAME LANGUAGE as draft. "
                           "Korean draft → 에티오피아, 페루, 콜롬비아. "
                           "English draft → Ethiopia, Peru, Colombia. "
                           "If only a region (Yirgacheffe/예가체프), infer the country."
        },
        "processing_method": {
            "type": "string",
            "description": "Same language as draft. "
                           "EN: washed, natural, honey, anaerobic. "
                           "KO: 워시드, 내추럴, 허니, 무산소."
        },
        "roasting_date": {"type": "string", "description": "YYYY-MM-DD if mentioned."},
        "roast_level": {
            "type": "string",
            "description": "Same language as draft. "
                           "EN: light, medium-light, medium, medium-dark, dark. "
                           "KO: 라이트, 미디엄 라이트, 미디엄, 미디엄 다크, 다크. "
                           "If not explicitly stated, leave empty."
        },
        "dripper": {
            "type": "string",
            "description": "Brewing device ONLY. e.g. V60, Origami, Kalita Wave, Aeropress, Chemex. "
                           "Brand/model names stay as-is regardless of draft language. "
                           "NOT the filter paper. If multiple drippers were used across sessions, "
                           "list them all separated by commas (e.g. 'V60, Origami, Kalita')."
        },
        "filter": {
            "type": "string",
            "description": "Filter paper ONLY. e.g. Hario tabbed, Cafec abaca, Kalita 185, Sibarist, "
                           "오리가미 콘 필터. NOT the dripper itself."
        },
        "coffee_g": {"type": "number"},
        "water_g_total": {"type": "number"},
        "water_temp_c": {"type": "number"},
        "pour_recipe": {"type": "array", "items": POUR_SCHEMA},
        "total_brew_time_sec": {"type": "number"},
        "tasting_notes_short": {
            "type": "string",
            "description": "One-line summary under 100 chars for table scanning. "
                           "SAME LANGUAGE as draft. Korean draft → Korean summary."
        },
        "tasting_notes_full": {
            "type": "string",
            "description": (
                "Every sentence describing taste, smell, mouthfeel, or evocation, "
                "verbatim from the draft, in the SAME LANGUAGE as the draft. "
                "Gangmuk uses unconventional, evocative, personal language — "
                "memories, places, textures, scenes, metaphors. "
                "Preserve ALL of it: surrounding phrasing, personal context, qualifiers. "
                "Use the original wording. Do NOT condense to keywords. "
                "Do NOT translate. If a sentence mixes tasting with personal memory, keep all of it. "
                "Concatenate all tasting-related sentences across the whole draft."
            ),
        },
    },
}

EXTRACT_SYSTEM = """Extract coffee brewing details from the draft.
The user dictated this casually, so info may be scattered or partial.

Rules:
- If a field is not mentioned, leave it null/empty. Do NOT guess.
- Times in seconds. Weights in grams. Temperature in Celsius.
- For roast_level: only fill if explicitly stated. Otherwise leave empty.
- For country: extract even if it's in the title/header line.
- Distinguish dripper (V60, Origami, Kalita) from filter (paper type).
- If the draft covers multiple sessions, aggregate: list all drippers used in
  the dripper field; for parameters, use the primary/most-mentioned setup;
  for tasting_notes_full, include all sessions."""


# ---------- CSV ----------
CSV_COLUMNS = [
    "date", "roastery", "coffee_name", "country", "processing_method",
    "roasting_date", "roast_level", "dripper", "filter",
    "coffee_g", "water_g_total", "water_temp_c",
    "pour_recipe", "total_brew_time_sec",
    "tasting_notes_short", "tasting_notes_full",
    "source_file",
]


# ---------- File I/O ----------
def read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if ext == ".rtf":
        from striprtf.striprtf import rtf_to_text
        return rtf_to_text(path.read_text(encoding="utf-8", errors="ignore"))
    if ext == ".docx":
        import docx
        doc = docx.Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    sys.exit(f"Unsupported file type: {ext}")


def build_output_path(source_path: Path, language: str, output_dir, fmt_suffix: str = ""):
    """{original_name}-polished-{language}[-{fmt}].{ext}"""
    base = source_path.stem
    ext = source_path.suffix
    if ext.lower() in {".rtf", ".docx"}:
        ext = ".md"
    suffix = f"-{fmt_suffix}" if fmt_suffix else ""
    new_name = f"{base}-polished-{language}{suffix}{ext}"
    target_dir = output_dir if output_dir else source_path.parent
    return target_dir / new_name


# ---------- LLM calls ----------
def polish(draft: str, language: str) -> str:
    lang_label = "KOREAN (한국어)" if language == "ko" else "ENGLISH"
    user_msg = f"[DRAFT LANGUAGE: {lang_label}. Respond entirely in {lang_label}.]\n\n{draft}"
    resp = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=POLISH_SYSTEM,
            temperature=0.2,
        ),
        contents=user_msg,
    )
    return resp.text

def translate(polished_text: str, source_lang: str) -> str:
    target_lang = "en" if source_lang == "ko" else "ko"
    target_label = "ENGLISH" if target_lang == "en" else "KOREAN (한국어)"
    user_msg = f"[Translate the following from {source_lang.upper()} to {target_label}.]\n\n{polished_text}"
    resp = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=TRANSLATE_SYSTEM,
            temperature=0.3,  # 약간 여유 — 자연스러운 번역 위해
        ),
        contents=user_msg,
    )
    return resp.text

def reformat_metadata(text: str, fmt: str) -> str:
    """Reformat comma-separated brew-param lines into a structured block."""
    system = METADATA_FORMATS[fmt]
    resp = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.0,
        ),
        contents=text,
    )
    return resp.text


def extract_brew(draft: str) -> dict:
    resp = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=EXTRACT_SYSTEM,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=BREW_SCHEMA,
        ),
        contents=draft,
    )
    return json.loads(resp.text)


def format_pour_recipe(pours):
    if not pours:
        return ""
    parts = []
    for p in pours:
        label = p.get("pour_label", "")
        water = p.get("water_g_cumulative", "")
        t = p.get("time_sec", "")
        parts.append(f"{label}:{water}g@{t}s")
    return " | ".join(parts)


def append_to_csv(brew: dict, source_file: str) -> dict:
    is_new = not CSV_PATH.exists()
    row = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "roastery": brew.get("roastery") or "",
        "coffee_name": brew.get("coffee_name") or "",
        "country": brew.get("country") or "",
        "processing_method": brew.get("processing_method") or "",
        "roasting_date": brew.get("roasting_date") or "",
        "roast_level": brew.get("roast_level") or "",
        "dripper": brew.get("dripper") or "",
        "filter": brew.get("filter") or "",
        "coffee_g": brew.get("coffee_g") or "",
        "water_g_total": brew.get("water_g_total") or "",
        "water_temp_c": brew.get("water_temp_c") or "",
        "pour_recipe": format_pour_recipe(brew.get("pour_recipe", [])),
        "total_brew_time_sec": brew.get("total_brew_time_sec") or "",
        "tasting_notes_short": brew.get("tasting_notes_short") or "",
        "tasting_notes_full": brew.get("tasting_notes_full") or "",
        "source_file": source_file,
    }
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
    return row


# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Polish coffee essay draft and log brew specs to CSV.")
    parser.add_argument("file", help=".txt/.md/.rtf/.docx draft")
    parser.add_argument("--output-dir", help="Output directory (default: same as input)")
    parser.add_argument("--no-log", action="store_true", help="Skip CSV logging")
    parser.add_argument("--no-polish", action="store_true", help="Skip polishing")
    parser.add_argument("--no-translate", action="store_true", help="Skip translation to the other language")
    parser.add_argument("--lang", choices=["ko", "en"], help="Force language (overrides auto-detect)")
    parser.add_argument(
        "--format",
        choices=["bullets", "table", "both", "none"],
        default="table",
        help="Reformat brew-param metadata lines. 'both' writes two output files per language.",
    )
    args = parser.parse_args()

    if args.format == "both":
        formats = ["bullets", "table"]
    elif args.format == "none":
        formats = []
    else:
        formats = [args.format]

    src_path = Path(args.file).expanduser().resolve()
    if not src_path.exists():
        sys.exit(f"Not found: {src_path}")

    draft = read_file(src_path)
    if not draft.strip():
        sys.exit("Empty draft.")

    language = args.lang or detect_language(draft)
    print(f"[detected language: {language}]")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None

    def write_variants(text: str, lang: str, label: str):
        """Write `text` once per requested format (or once unformatted if formats=[]).

        When only one format is requested, write to the canonical (unsuffixed) path
        so the Jekyll pipeline picks it up. With --format both, suffix each file.
        """
        targets = formats if formats else [""]
        suffix_files = len(targets) > 1
        for fmt in targets:
            if fmt:
                print(f"[reformatting metadata as {fmt} ({lang})...]")
                final = reformat_metadata(text, fmt)
            else:
                final = text
            path_suffix = fmt if (fmt and suffix_files) else ""
            out_path = build_output_path(src_path, lang, output_dir, fmt_suffix=path_suffix)
            if out_path.resolve() == src_path.resolve():
                sys.exit(f"Refusing to overwrite source file: {src_path}")
            out_path.write_text(final, encoding="utf-8")
            print("=" * 60)
            print(final)
            print("=" * 60)
            tag = f"{lang}, {fmt}" if fmt else lang
            print(f"{label} ({tag}): {out_path}\n")

    # 1. Polish in original language
    if not args.no_polish:
        print(f"[polishing {len(draft)} chars in {language}...]")
        polished = polish(draft, language)

        print(f"\nSource (untouched): {src_path}")
        write_variants(polished, language, "Polished")

        # 2. Translate to the other language
        if not args.no_translate:
            other_lang = "en" if language == "ko" else "ko"
            print(f"[translating to {other_lang}...]")
            translated = translate(polished, language)
            write_variants(translated, other_lang, "Translated")

    # 2. Extract + log
    if not args.no_log:
        print("\n[extracting brew specs...]")
        try:
            brew = extract_brew(draft)
            row = append_to_csv(brew, src_path.stem)
            print(f"Logged to {CSV_PATH}:")
            for k, v in row.items():
                if v:
                    display = v if len(str(v)) < 100 else str(v)[:100] + "..."
                    print(f"  {k}: {display}")
        except Exception as e:
            print(f"[extract error] {e}")


if __name__ == "__main__":
    main()