"""
File: app/infrastructure/knowledge_base/excel_isa_parser.py
Folder: backend/app/infrastructure/knowledge_base
Purpose: Faithful port of the hierarchical chunking logic from the original
         Colab pipeline (rag_script_and_result.txt). Given a VDA ISA
         questionnaire Excel file, produces the same chunk shape as the
         default corpus (all_corpus_final__7_.json): one "control_parent"
         chunk per control + up to 7 thematic sub-chunks (objective / must /
         should / additional / references / examples / audit).

         Only the Excel side of the original script is ported — PDF parsing
         is out of scope for the upload feature (Phase 2 only needs Excel
         upload, per the roadmap).

         Output shape: list[dict], identical field names to the JSON corpus,
         so both flows (default corpus + uploaded Excel) converge through
         the same metadata_builder.chunks_to_knowledge_chunks() step.
"""

import re
from io import BytesIO
from typing import Any, Optional

import pandas as pd

from app.core.exceptions import ValidationError

# ── Config (mirrors CFG in the original script) ─────────────────────────
MAX_ISA_CHARS = 2000
MIN_ISA_CHARS = 50
MIN_CONTENT_CHARS = 60
MIN_EMB_CHARS = 40

# ── Excel column maps (confirmed by analysis of the VDA ISA workbook) ───
ISA_COL = {
    "row_format": 0, "is_title": 1, "ctrl_num": 2, "maturity": 3,
    "impl_desc": 4, "ref_doc": 5, "ctrl_q": 7, "objective": 8,
    "must": 9, "should": 10, "high": 11, "vhigh": 12, "sga": 13,
    "responsible": 14, "ref_std": 15, "impl_guide": 16, "measures": 17,
    "ex_normal": 23, "ex_high": 24, "ex_vhigh": 25, "questions": 26, "evidence": 27,
}

ISA_COL_PP = {
    **ISA_COL,
    "high": 11, "responsible": 12, "ref_std": 13, "measures": 14,
    "vhigh": None, "sga": None, "impl_guide": None,
    "ex_normal": None, "ex_high": None, "ex_vhigh": None,
    "questions": None, "evidence": None,
}

ISA_COL_DP = {
    **ISA_COL,
    "must": 9, "should": None, "high": None, "vhigh": None, "sga": None,
    "responsible": 10, "ref_std": 11, "impl_guide": None, "measures": None,
    "ex_normal": None, "ex_high": None, "ex_vhigh": None,
    "questions": None, "evidence": None,
}

SHEET_COLS = {
    "Information Security": ISA_COL,
    "Prototype Protection": ISA_COL_PP,
    "Data Protection": ISA_COL_DP,
}

ISA_QUESTIONNAIRE_SHEETS = set(SHEET_COLS.keys())
ISA_SKIP_SHEETS = {"Cover", "Results"}
INVISIBLE_RE = re.compile(r"This is intentional invisible text.*?(?=$|\n)", re.IGNORECASE)


# ── Utilities ─────────────────────────────────────────────────────────

def _cv(val: Any) -> str:
    """Clean a raw Excel cell value."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    text = INVISIBLE_RE.sub("", str(val).strip())
    text = re.sub(r"\\n", "\n", text)
    text = re.sub(r"\r\n|\r", "\n", text)
    lines = [re.sub(r" {2,}", " ", l).strip() for l in text.split("\n")]
    return "\n".join(l for l in lines if l).strip()


def _gcol(row: Any, col_idx: Optional[int]) -> str:
    if col_idx is None:
        return ""
    try:
        if col_idx >= len(row):
            return ""
        return _cv(row.iloc[col_idx])
    except Exception:
        return ""


def _is_none_val(s: str) -> bool:
    return s.lower() in ("none", "nan", "", "null")


def smart_split(text: str, max_c: int = MAX_ISA_CHARS, min_c: int = 80) -> list[str]:
    """Split text without breaking mid-sentence/word. Priority: paragraph
    break > sentence end > punctuation > whitespace fallback."""
    text = text.strip()
    if len(text) <= max_c:
        return [text] if text else []
    chunks, rem = [], text
    while len(rem) > max_c:
        win = rem[:max_c]
        cut = -1
        for m in re.finditer(r"\n\n", win):
            cut = m.end()
        if cut == -1:
            for m in re.finditer(r'[.!?]\s+(?=[A-Z0-9"(])', win):
                cut = m.end()
        if cut == -1:
            for m in re.finditer(r"[.!?]\s+", win):
                cut = m.end()
        if cut == -1:
            for m in re.finditer(r"[,;:]\s+", win):
                cut = m.end()
        if cut == -1:
            ls = win.rfind(" ")
            cut = ls + 1 if ls > max_c // 2 else max_c
        part = rem[:cut].strip()
        if part and len(part) >= min_c:
            chunks.append(part)
        rem = rem[cut:].strip()
    if rem:
        if len(rem) >= min_c:
            chunks.append(rem)
        elif chunks:
            chunks[-1] += " " + rem
    return [c for c in chunks if len(c.strip()) >= min_c]


def _build_ctx_header(sheet: str, section_l1: str, section_l2: str, ctrl_num: str, ctrl_q: str) -> str:
    parts = [f"[Sheet: {sheet}]"]
    if section_l1:
        parts.append(f"[Section: {section_l1}]")
    if section_l2 and section_l2 != section_l1:
        parts.append(f"[Sub-section: {section_l2}]")
    parts.append(f"[Control: {ctrl_num}]")
    parts.append(f"[Question: {ctrl_q}]")
    return "\n".join(parts)


def _make_subchunk(
    ctrl_num: str, ctrl_q: str, sheet: str, section_l1: str, section_l2: str,
    subtype: str, label: str, content: str, ctx_header: str,
) -> dict:
    emb = f"{ctx_header}\n\n[{label}]\n{content}"
    return {
        "sheet": sheet, "sheet_type": subtype, "control_number": ctrl_num,
        "control_question": ctrl_q, "section_l1": section_l1, "section_l2": section_l2,
        "title": f"{ctrl_num} — {label}", "content": content, "content_length": len(content),
        "is_container": False, "is_subchunk": True, "embedding_text": emb,
        "sub_label": label, "source": "",
    }


def _make_control_parent(
    ctrl_num: str, ctrl_q: str, sheet: str, section_l1: str, section_l2: str,
    maturity_target: str, n_subchunks: int,
) -> dict:
    emb = (
        f"[Sheet: {sheet}]\n[Section: {section_l1}]\n[Sub-section: {section_l2}]\n"
        f"[Control: {ctrl_num}]\n\n[Question: {ctrl_q}]"
    )
    return {
        "sheet": sheet, "sheet_type": "control_parent", "control_number": ctrl_num,
        "control_question": ctrl_q, "section_l1": section_l1, "section_l2": section_l2,
        "title": f"{ctrl_num} — {ctrl_q[:80]}", "content": ctrl_q, "content_length": len(ctrl_q),
        "is_container": True, "is_subchunk": False, "n_subchunks": n_subchunks,
        "maturity_target": maturity_target, "embedding_text": emb, "sub_label": "parent",
        "source": "",
    }


def parse_questionnaire_hierarchical(df: pd.DataFrame, sheet_name: str) -> list[dict]:
    """One control -> 1 parent chunk + up to 7 thematic sub-chunks."""
    cols = SHEET_COLS.get(sheet_name, ISA_COL)
    chunks: list[dict] = []

    hr = 1
    for i in range(min(5, len(df))):
        vals = [str(v) for v in df.iloc[i].tolist() if pd.notna(v)]
        if any("Control number" in v or "Control question" in v for v in vals):
            hr = i
            break

    section_l1 = section_l2 = ctrl_l1 = ctrl_l2 = ""

    for _, row in df.iloc[hr + 1:].reset_index(drop=True).iterrows():
        rf = _gcol(row, cols["row_format"]).lower()
        it = _gcol(row, cols["is_title"])
        cn = _gcol(row, cols["ctrl_num"])

        if not cn or _is_none_val(cn):
            continue

        if rf == "header" and it == "1":
            section_l1 = _gcol(row, cols["ctrl_q"])
            ctrl_l1 = cn
            section_l2 = ctrl_l2 = ""
            continue
        if rf == "header" and it == "2":
            section_l2 = _gcol(row, cols["ctrl_q"])
            ctrl_l2 = cn
            continue

        ctrl_q = _gcol(row, cols["ctrl_q"])
        if not ctrl_q or _is_none_val(ctrl_q):
            continue

        maturity_target = _gcol(row, cols.get("maturity", 3))
        sec_l1 = f"{ctrl_l1} {section_l1}".strip() if section_l1 else ""
        sec_l2 = f"{ctrl_l2} {section_l2}".strip() if section_l2 else ""
        ctx = _build_ctx_header(sheet_name, sec_l1, sec_l2, cn, ctrl_q)

        objective = _gcol(row, cols["objective"])
        must = _gcol(row, cols["must"])
        should = _gcol(row, cols.get("should"))
        high = _gcol(row, cols.get("high"))
        vhigh = _gcol(row, cols.get("vhigh"))
        sga = _gcol(row, cols.get("sga"))
        ref_std = _gcol(row, cols.get("ref_std"))
        impl_guide = _gcol(row, cols.get("impl_guide"))
        measures = _gcol(row, cols.get("measures"))
        ex_n = _gcol(row, cols.get("ex_normal"))
        ex_h = _gcol(row, cols.get("ex_high"))
        ex_vh = _gcol(row, cols.get("ex_vhigh"))
        questions = _gcol(row, cols.get("questions"))
        evidence = _gcol(row, cols.get("evidence"))

        sub_chunks: list[dict] = []

        def _add_split(text: str, subtype: str, label_base: str) -> None:
            parts = smart_split(text, MAX_ISA_CHARS)
            for k, sub in enumerate(parts):
                label = label_base + (f" §{k + 1}" if len(parts) > 1 else "")
                sub_chunks.append(_make_subchunk(cn, ctrl_q, sheet_name, sec_l1, sec_l2, subtype, label, sub, ctx))

        if objective and not _is_none_val(objective):
            _add_split(objective, "objective", "Objective")
        if must and not _is_none_val(must):
            _add_split(must, "must", "Requirements (must)")
        if should and not _is_none_val(should):
            _add_split(should, "should", "Requirements (should)")

        add_parts = []
        if high and not _is_none_val(high):
            add_parts.append(f"High protection:\n{high}")
        if vhigh and not _is_none_val(vhigh):
            add_parts.append(f"Very high protection:\n{vhigh}")
        if sga and not _is_none_val(sga):
            add_parts.append(f"SGA:\n{sga}")
        if measures and not _is_none_val(measures):
            add_parts.append(f"Measures:\n{measures}")
        if add_parts:
            _add_split("\n\n".join(add_parts), "additional", "Additional requirements")

        ref_parts = []
        if ref_std and not _is_none_val(ref_std):
            ref_parts.append(f"Reference standards:\n{ref_std}")
        if impl_guide and not _is_none_val(impl_guide):
            ref_parts.append(f"Implementation guidance:\n{impl_guide}")
        if ref_parts:
            _add_split("\n\n".join(ref_parts), "references", "References")

        ex_parts = []
        if ex_n and not _is_none_val(ex_n):
            ex_parts.append(f"Example (normal):\n{ex_n}")
        if ex_h and not _is_none_val(ex_h):
            ex_parts.append(f"Example (high):\n{ex_h}")
        if ex_vh and not _is_none_val(ex_vh):
            ex_parts.append(f"Example (very high):\n{ex_vh}")
        if ex_parts:
            _add_split("\n\n".join(ex_parts), "examples", "Examples")

        audit_parts = []
        if questions and not _is_none_val(questions):
            audit_parts.append(f"Possible questions:\n{questions}")
        if evidence and not _is_none_val(evidence):
            audit_parts.append(f"Possible evidence:\n{evidence}")
        if audit_parts:
            _add_split("\n\n".join(audit_parts), "audit", "Audit questions & evidence")

        if not sub_chunks:
            continue

        chunks.append(_make_control_parent(cn, ctrl_q, sheet_name, sec_l1, sec_l2, maturity_target, len(sub_chunks)))
        for sc in sub_chunks:
            sc["parent_control"] = cn
            chunks.append(sc)

    return chunks


def parse_maturity_levels(df: pd.DataFrame) -> list[dict]:
    chunks: list[dict] = []
    intro = _cv(df.iloc[0, 1]) if df.shape[1] > 1 else ""
    if intro:
        chunks.append({
            "sheet": "Maturity levels", "sheet_type": "maturity", "control_number": None,
            "title": "Maturity levels — Introduction", "section_l1": "Maturity levels", "section_l2": "",
            "control_question": None, "content": intro, "content_length": len(intro),
            "is_container": False, "is_subchunk": False, "sub_label": "",
            "embedding_text": f"[Sheet: Maturity levels]\n\n{intro}", "source": "",
        })
    row_labels = {2: "Name", 3: "Principle", 4: "Definition", 5: "Possible evidence (GWP)", 6: "Example"}
    for col in range(2, min(8, df.shape[1])):
        level_label = _cv(df.iloc[1, col]) if df.shape[0] > 1 else f"Level {col - 2}"
        if not level_label or "Maturity" not in level_label:
            continue
        parts = []
        for row_idx, label in row_labels.items():
            if row_idx < df.shape[0]:
                val = _cv(df.iloc[row_idx, col])
                if val:
                    parts.append(f"{label}:\n{val}")
        if not parts:
            continue
        content = "\n\n".join(parts)
        splits = smart_split(content, MAX_ISA_CHARS)
        for k, sub in enumerate(splits):
            title = f"Maturity levels — {level_label}" + (f" §{k + 1}/{len(splits)}" if len(splits) > 1 else "")
            chunks.append({
                "sheet": "Maturity levels", "sheet_type": "maturity", "control_number": None, "title": title,
                "section_l1": "Maturity levels", "section_l2": level_label, "control_question": None,
                "content": sub, "content_length": len(sub), "is_container": False, "is_subchunk": False,
                "sub_label": "", "embedding_text": f"[Sheet: Maturity levels]\n[Level: {level_label}]\n\n{sub}",
                "source": "",
            })
    return chunks


def parse_definitions(df: pd.DataFrame) -> list[dict]:
    chunks: list[dict] = []
    buf_term, buf_def = "", []

    def flush() -> None:
        nonlocal buf_term, buf_def
        if not buf_term or not buf_def:
            return
        content = f"Term: {buf_term}\n\nDefinition: {chr(10).join(buf_def)}"
        for sub in smart_split(content, MAX_ISA_CHARS):
            chunks.append({
                "sheet": "Definitions", "sheet_type": "definitions", "control_number": None,
                "title": f"Definition: {buf_term}", "section_l1": "Definitions", "section_l2": "",
                "control_question": None, "content": sub, "content_length": len(sub),
                "is_container": False, "is_subchunk": False, "sub_label": "",
                "embedding_text": f"[Sheet: Definitions]\n[Definition: {buf_term}]\n\n{sub}", "source": "",
            })
        buf_term, buf_def = "", []

    for i in range(len(df)):
        cells = [_cv(v) for v in df.iloc[i] if _cv(v)]
        if not cells:
            continue
        for cell in cells:
            is_term = len(cell) < 60 and "\n" not in cell and not cell.endswith(".") and len(cell) > 2
            is_def = len(cell) >= 40
            if is_term and not is_def:
                flush()
                buf_term = cell
                buf_def = []
            else:
                if buf_term:
                    buf_def.append(cell)
    flush()
    return chunks


def parse_kpi(df: pd.DataFrame) -> list[dict]:
    chunks: list[dict] = []
    ctrl_row = 2
    for i in range(min(5, df.shape[0])):
        vals = [str(v) for v in df.iloc[i].tolist() if pd.notna(v) and str(v).strip()]
        if any("Control ISA" in v or "Control number" in v for v in vals):
            ctrl_row = i
            break
    scope_row, id_row, desc_row, obj_row, recip_row = ctrl_row + 1, ctrl_row + 2, ctrl_row + 3, ctrl_row + 4, ctrl_row + 5
    ctrl_by_col: dict[int, str] = {}
    cur_ctrl = ""
    for col in range(df.shape[1]):
        val = _cv(df.iloc[ctrl_row, col])
        if val and "Control ISA" not in val and "Scope" not in val:
            cur_ctrl = val
        ctrl_by_col[col] = cur_ctrl
    for col in range(1, df.shape[1]):
        kpi_id = _cv(df.iloc[id_row, col]) if id_row < df.shape[0] else ""
        scope = _cv(df.iloc[scope_row, col]) if scope_row < df.shape[0] else ""
        desc = _cv(df.iloc[desc_row, col]) if desc_row < df.shape[0] else ""
        obj = _cv(df.iloc[obj_row, col]) if obj_row < df.shape[0] else ""
        recip = _cv(df.iloc[recip_row, col]) if recip_row < df.shape[0] else ""
        ctrl = ctrl_by_col.get(col, "")
        if not kpi_id or len(kpi_id) < 3:
            continue
        parts = []
        if ctrl:
            parts.append(f"ISA Control: {ctrl}")
        if scope:
            parts.append(f"KPI Type: {scope}")
        if desc:
            parts.append(f"Description:\n{desc}")
        if obj:
            parts.append(f"Objective:\n{obj}")
        if recip:
            parts.append(f"Recipients: {recip}")
        if not parts:
            continue
        content = "\n\n".join(parts)
        for sub in smart_split(content, MAX_ISA_CHARS):
            chunks.append({
                "sheet": "Examples KPI", "sheet_type": "kpi", "control_number": None, "title": f"KPI: {kpi_id}",
                "section_l1": "Examples KPI", "section_l2": ctrl[:60] if ctrl else "", "control_question": ctrl,
                "content": sub, "content_length": len(sub), "is_container": False, "is_subchunk": False,
                "sub_label": "", "embedding_text": f"[Sheet: Examples KPI]\n[Control: {ctrl}]\n[KPI: {kpi_id}]\n\n{sub}",
                "source": "",
            })
    return chunks


def parse_text_sheet(df: pd.DataFrame, sheet_name: str) -> list[dict]:
    chunks: list[dict] = []
    parts: list[str] = []
    for i in range(len(df)):
        for val in df.iloc[i]:
            text = _cv(val)
            if text and len(text) >= MIN_ISA_CHARS and (not parts or parts[-1] != text):
                parts.append(text)
    if not parts:
        return chunks

    def _flush(buf: str) -> None:
        for sub in smart_split(buf, MAX_ISA_CHARS):
            chunks.append({
                "sheet": sheet_name, "sheet_type": "text", "control_number": None, "title": sheet_name,
                "section_l1": sheet_name, "section_l2": "", "control_question": None, "content": sub,
                "content_length": len(sub), "is_container": False, "is_subchunk": False, "sub_label": "",
                "embedding_text": f"[Sheet: {sheet_name}]\n\n{sub}", "source": "",
            })

    buf, buf_len = "", 0
    for part in parts:
        if buf_len + len(part) > MAX_ISA_CHARS and buf:
            _flush(buf)
            buf, buf_len = "", 0
        buf += ("\n\n" if buf else "") + part
        buf_len += len(part)
    if buf:
        _flush(buf)
    return chunks


def _clean_chunks(chunks: list[dict]) -> list[dict]:
    """Lightweight version of clean_corpus() from the original script — drops
    chunks that are too short or have degenerate embedding text. URL/table
    cleanup is skipped here since Excel cells rarely contain PDF artifacts."""
    kept = []
    for c in chunks:
        content = c.get("content", "")
        if content and len(content) < MIN_CONTENT_CHARS and not c.get("is_container"):
            continue
        if len((c.get("embedding_text") or "").strip()) < MIN_EMB_CHARS:
            continue
        kept.append(c)
    return kept


def process_excel(file_bytes: bytes, filename: str) -> list[dict]:
    """Entry point: parse an uploaded VDA ISA Excel workbook into the same
    chunk shape as the default corpus JSON."""
    try:
        xl = pd.ExcelFile(BytesIO(file_bytes))
    except Exception as exc:
        raise ValidationError(f"Could not read '{filename}' as an Excel file.") from exc

    if not xl.sheet_names:
        raise ValidationError(f"'{filename}' has no sheets.")

    all_chunks: list[dict] = []
    for sheet_name in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
        if sheet_name in ISA_SKIP_SHEETS:
            continue
        if sheet_name in ISA_QUESTIONNAIRE_SHEETS:
            new = parse_questionnaire_hierarchical(df, sheet_name)
        elif sheet_name == "Maturity levels":
            new = parse_maturity_levels(df)
        elif sheet_name == "Definitions":
            new = parse_definitions(df)
        elif sheet_name == "Examples KPI":
            new = parse_kpi(df)
        else:
            new = parse_text_sheet(df, sheet_name)
        all_chunks.extend(new)

    all_chunks = _clean_chunks(all_chunks)

    if not all_chunks:
        raise ValidationError(
            f"'{filename}' produced no usable chunks — check it matches the VDA ISA questionnaire format."
        )

    for idx, c in enumerate(all_chunks):
        c["corpus_id"] = idx

    return all_chunks
