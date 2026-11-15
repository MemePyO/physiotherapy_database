"""Attachments tab for the patient file panel."""

from __future__ import annotations

import os
from tkinter import filedialog, ttk
from typing import Any

import customtkinter as ctk

import lang
import log
import theme
from error_ui import report_error
from services.attachment_service import get_attachment_service

from .base import TabSection

logger = log.get_logger(__name__)

_COLUMNS = (("filename", "File", 200), ("size", "Size", 70), ("added_at", "Added", 120))


class AttachmentsSection(TabSection):
    """Builds the attachments tab and manages attachment files."""

    def build(self, tabview: ctk.CTkTabview) -> None:
        panel = self.panel
        att_tab = tabview.add("Attachments")
        att_tab.grid_columnconfigure(0, weight=1)
        att_tab.grid_rowconfigure(0, weight=1)
        panel.attach_tree = ttk.Treeview(
            att_tab,
            columns=[c for c, _, _ in _COLUMNS],
            show="headings",
            selectmode="browse",
        )
        for c, title, width in _COLUMNS:
            panel.attach_tree.heading(c, text=title)
            panel.attach_tree.column(c, width=width)
        panel.attach_tree.grid(row=0, column=0, sticky="nsew", pady=(4, 4))
        ab = ctk.CTkFrame(att_tab, fg_color="transparent")
        ab.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        ctk.CTkButton(
            ab,
            text=lang.t("ui_attach_file"),
            width=100,
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_DARK,
            command=self.attach_file,
        ).pack(side="left", padx=2)
        ctk.CTkButton(ab, text="Preview", width=80, command=self.preview).pack(side="left", padx=2)
        ctk.CTkButton(ab, text=lang.t("ui_open"), width=80, command=self.open_attachment).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            ab,
            text=lang.t("ui_delete"),
            width=80,
            fg_color="#c0392b",
            command=self.delete,
        ).pack(side="left", padx=2)
        ctk.CTkButton(ab, text=lang.t("ui_refresh"), width=80, command=self.load).pack(
            side="left", padx=2
        )

    def load(self) -> None:
        panel = self.panel
        tree = getattr(panel, "attach_tree", None)
        if tree is None:
            return
        try:
            for r in tree.get_children():
                tree.delete(r)
        except Exception:
            log.debug_exc(logger)
        try:
            for a in get_attachment_service().list(panel.patient_id):
                size = a.get("size", 0)
                size_str = (
                    (str(round(size / 1024, 1)) + " KB") if size >= 1024 else (str(size) + " B")
                )
                tree.insert(
                    "",
                    "end",
                    iid=str(a["id"]),
                    values=(a.get("filename", ""), size_str, a.get("added_at", "")),
                )
        except Exception:
            log.debug_exc(logger)

    def attach_file(self) -> None:
        panel = self.panel
        path = filedialog.askopenfilename(title="Attach file", filetypes=[("All files", "*.*")])
        if not path:
            return
        try:
            get_attachment_service().add(panel.patient_id, path)
            self.load()
            self.info(lang.t("ui_file_attached"))
        except Exception as e:
            report_error(str(e))

    def _selected_path(self) -> str | None:
        panel = self.panel
        sel = panel.attach_tree.selection()
        if not sel:
            self.info(lang.t("ui_select_attachment"))
            return None
        att = get_attachment_service().get(int(sel[0]))
        if not att:
            return None
        path = att.get("stored_path", "")
        if not path or not os.path.exists(path):
            report_error(lang.t("ui_file_not_found"))
            return None
        return str(path)

    def open_attachment(self) -> None:
        path = self._selected_path()
        if not path:
            return
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess

                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            report_error(str(e))

    def preview(self) -> None:
        path = self._selected_path()
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
        try:
            if ext in image_exts:
                from PIL import Image

                img = Image.open(path)
                # scale to fit
                max_w, max_h = 900, 700
                img.thumbnail((max_w, max_h))
                self.show_preview_image(img, title=os.path.basename(path))
            elif ext == ".pdf":
                import fitz

                doc = fitz.open(path)
                if doc.page_count == 0:
                    self.info(lang.t("ui_empty_pdf"))
                    return
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                from PIL import Image

                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img.thumbnail((900, 700))
                self.show_preview_image(
                    img, title=os.path.basename(path) + " (page 1/%d)" % doc.page_count
                )
                doc.close()
            else:
                # fallback to OS viewer
                self.open_attachment()
        except Exception as e:
            report_error(str(e))

    def show_preview_image(self, img: Any, title: str = "Preview") -> None:
        from PIL import ImageTk

        win = ctk.CTkToplevel(self.panel)
        win.title(title)
        win.geometry("920x740")
        lbl = ctk.CTkLabel(win, text="")
        lbl.pack(expand=True, fill="both", padx=10, pady=10)
        tk_img = ImageTk.PhotoImage(img)
        lbl.configure(image=tk_img)
        lbl.image = tk_img  # keep ref
        ctk.CTkButton(win, text="Close", command=win.destroy).pack(pady=8)

    def delete(self) -> None:
        panel = self.panel
        sel = panel.attach_tree.selection()
        if not sel:
            self.info(lang.t("ui_select_attachment"))
            return
        if not self.confirm("Delete this attachment?"):
            return
        try:
            get_attachment_service().delete(int(sel[0]))
            self.load()
        except Exception as e:
            report_error(str(e))


__all__ = ["AttachmentsSection"]
