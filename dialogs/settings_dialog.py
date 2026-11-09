from .common import LANG_LABELS, ctk, lang, theme


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Settings")
        self.geometry("420x460")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=lang.t("ui_settings"), font=theme.FONT_TITLE, text_color=theme.TEXT
        ).grid(row=0, column=0, sticky="w", padx=theme.PADDING, pady=(theme.PADDING, 8))

        # Language
        ctk.CTkLabel(
            self, text=lang.t("ui_language"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=1, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        self.lang_menu = ctk.CTkOptionMenu(
            self, values=list(LANG_LABELS.values()), width=200, command=master._on_language_change
        )
        self.lang_menu.set(LANG_LABELS.get(lang.get_language(), "English"))
        self.lang_menu.grid(row=2, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))

        # UI scale
        ctk.CTkLabel(
            self, text=lang.t("ui_ui_scale"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=3, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        scale_frame = ctk.CTkFrame(self, fg_color="transparent")
        scale_frame.grid(row=4, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        for pct in (100, 125, 150):
            ctk.CTkButton(
                scale_frame,
                text=str(pct) + "%",
                width=70,
                command=lambda p=pct: master._set_ui_scale(p / 100.0),
            ).pack(side="left", padx=2)

        # Interface theme
        ctk.CTkLabel(
            self, text=lang.t("ui_interface_theme"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=5, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        itf_frame = ctk.CTkFrame(self, fg_color="transparent")
        itf_frame.grid(row=6, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        ctk.CTkButton(
            itf_frame,
            text=lang.t("ui_theme_classic"),
            width=90,
            command=lambda: (master._apply_ui_theme("classic"), self.destroy()),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            itf_frame,
            text=lang.t("ui_theme_medidash"),
            width=120,
            command=lambda: (master._apply_ui_theme("medidash"), self.destroy()),
        ).pack(side="left", padx=2)

        # Theme
        ctk.CTkLabel(
            self, text=lang.t("ui_theme_label"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=7, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.grid(row=8, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        ctk.CTkButton(
            theme_frame,
            text=lang.t("ui_light"),
            width=90,
            command=lambda: master._apply_appearance("Light"),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            theme_frame,
            text=lang.t("ui_dark"),
            width=90,
            command=lambda: master._apply_appearance("Dark"),
        ).pack(side="left", padx=2)

        # Backup / Restore / Import
        ctk.CTkLabel(
            self, text=lang.t("ui_data"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=9, column=0, sticky="w", padx=theme.PADDING, pady=(8, 2))
        data_frame = ctk.CTkFrame(self, fg_color="transparent")
        data_frame.grid(row=10, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        ctk.CTkButton(
            data_frame, text=lang.t("ui_backup_now"), width=110, command=master._backup_now
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            data_frame, text=lang.t("ui_restore_backup"), width=110, command=master._restore_backup
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            data_frame, text=lang.t("ui_import"), width=110, command=master._import_data
        ).pack(side="left", padx=2)

        # Trash
        ctk.CTkButton(
            self, text=lang.t("ui_open_trash"), width=220, command=master._show_trash
        ).grid(row=11, column=0, sticky="w", padx=theme.PADDING, pady=(8, 8))

        ctk.CTkButton(self, text=lang.t("ui_close"), width=90, command=self.destroy).grid(
            row=12, column=0, sticky="e", padx=theme.PADDING, pady=(8, theme.PADDING)
        )
