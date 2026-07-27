"""
File: app/application/services/report_service.py
Folder: backend/app/application/services
Purpose: Aggregates persisted control results into the assessment report and
         dashboard figures. Pure aggregation over data already stored by the
         Maturity Assessment Engine — it never calls the LLM, so a report can
         be regenerated any number of times and always yields the same
         numbers (the reproducibility guarantee).

         Aggregation mirrors the official VDA ISA "Results" sheet:
           control -> subchapter (1.1) -> chapter (1) -> domain (IS/PP/DP)
                   -> overall, each an average of assessed controls with
           skipped/na excluded from both numerator and denominator, and every
           level capped at the declared target ("cutback").

         On top of the standard it adds the figures a modern compliance
         dashboard shows: compliance %, gap counts, evidence coverage,
         confidence mix, assessment completeness.
"""

import json
from collections import defaultdict

from app.domain.maturity import apply_cutback, average_excluding_na


def _subchapter_of(control_number: str) -> str:
    # "1.6.2" -> "1.6"
    parts = control_number.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else control_number


def _chapter_of(control_number: str) -> str:
    # "1.6.2" -> "1"
    return control_number.split(".")[0]


class ReportService:
    def __init__(self, target: int = 3) -> None:
        self._target = target

    def build_control_rows(self, controls: list) -> list[dict]:
        """One row per control, in order — the detail table of the report."""
        rows = []
        for c in controls:
            skipped = c.state == "skipped"
            ml = None if skipped else c.maturity_score
            cutback = apply_cutback(ml, self._target) if ml is not None else None
            gap = None
            if cutback is not None:
                gap = max(0.0, float(self._target) - cutback)
            rows.append({
                "control_number": c.control_number,
                "domain": c.domain,
                "title": c.title,
                "state": c.state,
                "maturity_level": ml,
                "cutback_level": cutback,
                "target_level": None if skipped else self._target,
                "gap": gap,
                "confidence": c.confidence,
                "assessment_mode": c.assessment_mode,
                "evidence_status": c.evidence_status,
                "finding": c.finding,
                "recommendation": c.recommendation,
                "missing_for_next_level": c.missing_for_next_level,
            })
        return rows

    def _aggregate(self, rows: list[dict], key_fn) -> list[dict]:
        buckets: dict[str, list] = defaultdict(list)
        for r in rows:
            if r["state"] == "skipped" or r["cutback_level"] is None:
                continue
            buckets[key_fn(r["control_number"])].append(r["cutback_level"])
        out = []
        for key in sorted(buckets, key=lambda k: [int(p) for p in k.split(".")]):
            avg = average_excluding_na(buckets[key])
            out.append({
                "key": key,
                "average_maturity": avg,
                "target": self._target,
                "gap": None if avg is None else max(0.0, float(self._target) - avg),
                "assessed_controls": len(buckets[key]),
            })
        return out

    def build_report(self, assessment, controls: list) -> dict:
        rows = self.build_control_rows(controls)

        # cutback values of assessed (non-skipped) controls
        assessed = [r["cutback_level"] for r in rows if r["cutback_level"] is not None]
        overall = average_excluding_na(assessed)

        total = len(rows)
        skipped = sum(1 for r in rows if r["state"] == "skipped")
        assessed_count = len(assessed)

        # Compliance distribution (by cutback level vs target)
        at_or_above = sum(1 for v in assessed if v >= self._target)
        below = assessed_count - at_or_above

        # Maturity distribution buckets for the donut
        distribution = {"ml0": 0, "ml1": 0, "ml2": 0, "ml3": 0, "ml4": 0, "ml5": 0, "na": skipped}
        for r in rows:
            if r["state"] == "skipped" or r["maturity_level"] is None:
                continue
            distribution[f"ml{int(r['maturity_level'])}"] += 1

        # Confidence mix
        conf = {"high": 0, "medium": 0, "low": 0}
        for r in rows:
            if r["confidence"] in conf:
                conf[r["confidence"]] += 1

        # Evidence view
        ev = defaultdict(int)
        for r in rows:
            if r["evidence_status"]:
                ev[r["evidence_status"]] += 1

        # Assessment completeness: how much of the selected scope is assessed
        completeness = round((assessed_count / total) * 100, 1) if total else 0.0
        verified = sum(1 for r in rows if r["assessment_mode"] == "verified")
        declared = sum(1 for r in rows if r["assessment_mode"] == "declared")
        verified_pct = round((verified / assessed_count) * 100, 1) if assessed_count else 0.0
        declared_pct = round((declared / assessed_count) * 100, 1) if assessed_count else 0.0

        # Compliance percentage: overall cutback as a fraction of target
        compliance_pct = round((overall / self._target) * 100, 1) if overall is not None else 0.0

        return {
            "assessment_id": str(assessment.id),
            "name": assessment.name,
            "assessment_level": assessment.assessment_level,
            "target_maturity_level": self._target,
            "status": assessment.status,
            "summary": {
                "overall_maturity": overall,
                "compliance_percent": compliance_pct,
                "total_controls": total,
                "assessed_controls": assessed_count,
                "skipped_controls": skipped,
                "controls_at_target": at_or_above,
                "controls_below_target": below,
                "assessment_completeness": completeness,
                "verified_controls": verified,
                "declared_controls": declared,
                "verified_percent": verified_pct,
                "declared_percent": declared_pct,
            },
            "maturity_distribution": distribution,
            "confidence_distribution": conf,
            "evidence_distribution": dict(ev),
            "by_domain": self._aggregate(rows, _chapter_of),  # chapter-level under each domain
            "by_subchapter": self._aggregate(rows, _subchapter_of),
            "controls": rows,
        }