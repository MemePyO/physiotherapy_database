from .common import ctk, db, lang, messagebox, ttk


class TrashDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Deleted patients (trash)")
        self.geometry("520x360")
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        cols = ("name", "localitate", "deleted_at")
        tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        tree.heading("name", text="Name")
        tree.heading("localitate", text="Locality")
        tree.heading("deleted_at", text="Deleted at")
        tree.column("name", width=200)
        tree.column("localitate", width=120)
        tree.column("deleted_at", width=160)
        tree.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        rows = db.list_deleted()
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
                db.restore_deleted(int(sel[0]))
                tree.delete(sel[0])
            except Exception as e:
                messagebox.showerror(lang.t("app_name"), str(e))

        def _purge():
            sel = tree.selection()
            if not sel:
                return
            if not messagebox.askyesno(lang.t("app_name"), "Permanently delete?"):
                return
            conn = db._get_conn()
            conn.execute("DELETE FROM deleted_patients WHERE id = ?", (int(sel[0]),))
            conn.commit()
            conn.close()
            tree.delete(sel[0])

        def _restore_all():
            for iid in list(tree.get_children()):
                try:
                    db.restore_deleted(int(iid))
                    tree.delete(iid)
                except Exception as e:
                    messagebox.showerror(lang.t("app_name"), str(e))

        def _empty_trash():
            if not messagebox.askyesno(
                lang.t("app_name"), "Permanently delete ALL deleted patients?"
            ):
                return
            conn = db._get_conn()
            conn.execute("DELETE FROM deleted_patients")
            conn.commit()
            conn.close()
            for iid in list(tree.get_children()):
                tree.delete(iid)

        ctk.CTkButton(btns, text="Restore", width=80, command=_restore).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Restore all", width=90, command=_restore_all).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btns, text="Purge", width=70, fg_color="#c0392b", command=_purge).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            btns, text="Empty trash", width=90, fg_color="#c0392b", command=_empty_trash
        ).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="Close", width=70, command=self.destroy).pack(side="left", padx=2)
