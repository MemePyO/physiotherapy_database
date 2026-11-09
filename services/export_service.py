"""Export service: generates CSV, PDF and Word exports in background."""

import csv

import db
import utils


def export_csv(path):
    patients = db.get_all_patients()
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(
            [
                "Nr.",
                "Nume Pacient",
                "Localitate",
                "Diagnostic",
                "Obiectiv",
                "Evaluare",
                "Observatii",
            ]
        )
        for i, p in enumerate(patients, 1):
            w.writerow(
                [
                    i,
                    p.get("name", ""),
                    p.get("localitate", ""),
                    p.get("diagnostic", ""),
                    p.get("objective", ""),
                    p.get("evaluation", ""),
                    p.get("observation", ""),
                ]
            )
    return len(patients)


def export_pdf(path):
    patients = db.get_all_patients()
    lines = ["Patient Database", "=" * 60]
    for p in patients:
        lines.append("")
        lines.append("Name: " + str(p.get("name", "")))
        lines.append("Locality: " + str(p.get("localitate", "")))
        for fld in ("diagnostic", "objective", "evaluation", "observation"):
            val = (p.get(fld, "") or "").replace("\n", " | ")
            lines.append(fld.capitalize() + ": " + val)
        lines.append("-" * 60)
    text = "\n".join(lines)
    pdf = utils._make_simple_pdf(text)
    with open(path, "wb") as fh:
        fh.write(pdf)
    return len(patients)


def export_word(path):
    patients = db.get_all_patients()
    parts = [r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}}", r"\title Patient Database"]
    for p in patients:
        parts.append(r"\par \b " + utils._rtf_escape(p.get("name", "")) + r"\b0")
        parts.append(r"\par Locality: " + utils._rtf_escape(p.get("localitate", "")))
        for fld in ("diagnostic", "objective", "evaluation", "observation"):
            val = (p.get(fld, "") or "").replace("\n", "\\par ")
            parts.append(r"\par \b " + fld.capitalize() + r":\b0 " + utils._rtf_escape(val))
        parts.append(r"\par " + "-" * 40)
    parts.append("}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(parts))
    return len(patients)
