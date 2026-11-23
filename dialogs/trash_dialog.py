from error_ui import report_error
from services.patient_service import get_patient_service
from ui import ttk_style

from .common import ctk, dialog_scale, fit_to_content, lang, messagebox, theme, ttk


class TrashDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        ttk_style.apply(self, scale=dialog_scale(master))
        self.title(lang.t("dlg_trash_title"))
        self.geometry("520x360")
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        cols = ("name", "localitate", "deleted_at")
        tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        tree.heading("name", text=lang.t("ui_name"))
        tree.heading("localitate", text=lang.t("ui_locality"))
        tree.heading("deleted_at", text=lang.t("ui_deleted_at"))
        tree.column("name", width=200)
        tree.column("localitate", width=120)
        tree.column("deleted_at", width=160)
        tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        rows = get_patient_service().list_deleted()
        for r in rows:
            tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(r.get("name", ""), r.get("localitate", ""), r.get("deleted_at", "")),
            )
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="e", padx=10, pady=10)

        def _restore():
            sel = tree.selection()
            if not sel:
                return
            try:
                get_patient_service().restore_patient(int(sel[0]))
                tree.delete(sel[0])
            except Exception as e:
                report_error(str(e))

        def _purge():
            sel = tree.selection()
            if not sel:
                return
            if not messagebox.askyesno(lang.t("app_name"), lang.t("confirm_purge")):
                return
            get_patient_service().purge_deleted([int(sel[0])])
            tree.delete(sel[0])

        def _restore_all():
            for iid in list(tree.get_children()):
                try:
                    get_patient_service().restore_patient(int(iid))
                    tree.delete(iid)
                except Exception as e:
                    report_error(str(e))

        def _empty_trash():
            if not messagebox.askyesno(lang.t("app_name"), lang.t("confirm_purge_all")):
                return
            get_patient_service().empty_deleted()
            for iid in list(tree.get_children()):
                tree.delete(iid)

        ctk.CTkButton(btns, text=lang.t("ui_restore"), width=80, command=_restore).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btns, text=lang.t("ui_restore_all"), width=90, command=_restore_all).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            btns,
            text=lang.t("ui_purge"),
            width=70,
            fg_color=theme.DANGER,
            command=_purge,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btns,
            text=lang.t("ui_empty_trash"),
            width=90,
            fg_color=theme.DANGER,
            command=_empty_trash,
        ).pack(side="left", padx=2)
        ctk.CTkButton(btns, text=lang.t("ui_close"), width=70, command=self.destroy).pack(
            side="left", padx=2
        )
        try:
            self.after_idle(lambda: fit_to_content(self, 520, 360))
        except Exception:
            pass
