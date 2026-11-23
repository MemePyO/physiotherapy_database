from ui import recolor

from .common import LANG_LABELS, ctk, dialog_scale, fit_to_content, lang, logger, theme

MIN_WIDTH = 420
MIN_HEIGHT = 460


def _option_button(parent, text, active, command, width=90):
    """Button that shows whether its option is currently active."""
    return ctk.CTkButton(
        parent,
        text=text,
        width=width,
        fg_color=theme.ACCENT if active else theme.MUTED_BTN,
        hover_color=theme.ACCENT_DARK if active else theme.MUTED_BTN_HOVER,
        text_color=theme.ON_ACCENT,
        command=command,
    )


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self._master = master
        self.title(lang.t("ui_settings"))
        self.geometry("%dx%d" % (MIN_WIDTH, MIN_HEIGHT))
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self._register_with_app()
        self._build_ui()

    # -- lifecycle -----------------------------------------------------------

    def _register_with_app(self):
        """Track this window so the app can refresh it after language changes."""
        try:
            dialogs = getattr(self._master, "_settings_dialogs", None)
            if dialogs is None:
                dialogs = []
                self._master._settings_dialogs = dialogs
            if self not in dialogs:
                dialogs.append(self)
            self.bind("<Destroy>", self._on_destroy, add="+")
        except Exception:
            logger.debug("could not register settings dialog", exc_info=True)

    def _on_destroy(self, event=None):
        if event is not None and getattr(event, "widget", None) is not self:
            return
        try:
            dialogs = getattr(self._master, "_settings_dialogs", None)
            if dialogs is not None and self in dialogs:
                dialogs.remove(self)
        except Exception:
            logger.debug("could not unregister settings dialog", exc_info=True)

    def refresh_language(self):
        """Re-render the labels after the application language changed."""
        try:
            self.after_idle(self._rebuild_safely)
        except Exception:
            logger.debug("could not schedule settings refresh", exc_info=True)

    def _rebuild_safely(self):
        try:
            if not self.winfo_exists():
                return
            self._build_ui()
            fit_to_content(self, MIN_WIDTH, MIN_HEIGHT)
            self._refresh_highlights()
        except Exception:
            logger.debug("could not rebuild settings dialog", exc_info=True)

    # -- layout --------------------------------------------------------------

    def _build_ui(self):
        for child in self.winfo_children():
            try:
                child.destroy()
            except Exception:
                logger.debug("could not clear settings dialog", exc_info=True)
        self.title(lang.t("ui_settings"))
        self.grid_columnconfigure(0, weight=1)
        self.scale_buttons = {}
        self.theme_buttons = {}
        self.appearance_buttons = {}

        ctk.CTkLabel(
            self, text=lang.t("ui_settings"), font=theme.FONT_TITLE, text_color=theme.TEXT
        ).grid(row=0, column=0, sticky="w", padx=theme.PADDING, pady=(theme.PADDING, 8))

        # Language
        ctk.CTkLabel(
            self, text=lang.t("ui_language"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=1, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        self.lang_menu = ctk.CTkOptionMenu(
            self,
            values=list(LANG_LABELS.values()),
            width=200,
            command=self._choose_language,
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
            active = self._scale_active(pct)
            btn = _option_button(
                scale_frame,
                str(pct) + "%",
                active,
                lambda p=pct: self._choose_scale(p),
                width=70,
            )
            btn.pack(side="left", padx=2)
            self.scale_buttons[pct] = (btn, active)

        # Interface theme
        ctk.CTkLabel(
            self, text=lang.t("ui_interface_theme"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=5, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        itf_frame = ctk.CTkFrame(self, fg_color="transparent")
        itf_frame.grid(row=6, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        base = theme.base()
        classic_btn = _option_button(
            itf_frame,
            lang.t("ui_theme_classic"),
            base == "classic",
            lambda: self._choose_theme("classic"),
        )
        classic_btn.pack(side="left", padx=2)
        medidash_btn = _option_button(
            itf_frame,
            lang.t("ui_theme_medidash"),
            base == "medidash",
            lambda: self._choose_theme("medidash"),
            width=120,
        )
        medidash_btn.pack(side="left", padx=2)
        self.theme_buttons = {
            "classic": (classic_btn, base == "classic"),
            "medidash": (medidash_btn, base == "medidash"),
        }

        # Theme
        ctk.CTkLabel(
            self, text=lang.t("ui_theme_label"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=7, column=0, sticky="w", padx=theme.PADDING, pady=(4, 2))
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.grid(row=8, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        for mode, label in (("Light", lang.t("ui_light")), ("Dark", lang.t("ui_dark"))):
            active = (theme.appearance() == "Dark") == (mode == "Dark")
            btn = _option_button(
                theme_frame,
                label,
                active,
                lambda m=mode: self._choose_appearance(m),
            )
            btn.pack(side="left", padx=2)
            self.appearance_buttons[mode] = (btn, active)

        # Backup / Restore / Import
        ctk.CTkLabel(
            self, text=lang.t("ui_data"), font=theme.FONT_BOLD, text_color=theme.TEXT
        ).grid(row=9, column=0, sticky="w", padx=theme.PADDING, pady=(8, 2))
        data_frame = ctk.CTkFrame(self, fg_color="transparent")
        data_frame.grid(row=10, column=0, sticky="w", padx=theme.PADDING, pady=(0, 8))
        ctk.CTkButton(
            data_frame, text=lang.t("ui_backup_now"), width=110, command=self._master._backup_now
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            data_frame,
            text=lang.t("ui_restore_backup"),
            width=110,
            command=self._master._restore_backup,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            data_frame, text=lang.t("ui_import"), width=110, command=self._master._import_data
        ).pack(side="left", padx=2)

        # Trash
        ctk.CTkButton(
            self, text=lang.t("ui_open_trash"), width=220, command=self._master._show_trash
        ).grid(row=11, column=0, sticky="w", padx=theme.PADDING, pady=(8, 8))

        ctk.CTkButton(self, text=lang.t("ui_close"), width=90, command=self.destroy).grid(
            row=12, column=0, sticky="e", padx=theme.PADDING, pady=(8, theme.PADDING)
        )

        try:
            self.after_idle(lambda: fit_to_content(self, MIN_WIDTH, MIN_HEIGHT))
        except Exception:
            logger.debug("could not schedule settings fit", exc_info=True)

    # -- live option handling ------------------------------------------------

    def _current_scale(self):
        try:
            return float(self._master.current_ui_scale())
        except Exception:
            return dialog_scale(self._master)

    def _scale_active(self, pct):
        return abs(self._current_scale() - pct / 100.0) < 0.01

    @staticmethod
    def _paint(button, active):
        try:
            button.configure(
                fg_color=theme.ACCENT if active else theme.MUTED_BTN,
                hover_color=theme.ACCENT_DARK if active else theme.MUTED_BTN_HOVER,
                text_color=theme.ON_ACCENT,
            )
        except Exception:
            logger.debug("could not refresh settings button", exc_info=True)

    def _refresh_highlights(self):
        """Re-read the live app state and repaint the active option buttons."""
        try:
            for pct, (button, _active) in list(self.scale_buttons.items()):
                active = self._scale_active(pct)
                self.scale_buttons[pct] = (button, active)
                self._paint(button, active)
            for name, (button, _active) in list(self.theme_buttons.items()):
                active = theme.base() == name
                self.theme_buttons[name] = (button, active)
                self._paint(button, active)
            for mode, (button, _active) in list(self.appearance_buttons.items()):
                active = (theme.appearance() == "Dark") == (mode == "Dark")
                self.appearance_buttons[mode] = (button, active)
                self._paint(button, active)
        except Exception:
            logger.debug("could not refresh settings dialog", exc_info=True)

    def _choose_language(self, choice):
        try:
            self._master._on_language_change(choice)
        except Exception:
            logger.debug("could not change language", exc_info=True)

    def _choose_scale(self, pct):
        try:
            self._master._set_ui_scale(pct / 100.0)
        except Exception:
            logger.debug("could not change ui scale", exc_info=True)
        self._refresh_highlights()

    def _choose_theme(self, name):
        old_palette = recolor.snapshot()
        try:
            self._master._apply_ui_theme(name)
        except Exception:
            logger.debug("could not change interface theme", exc_info=True)
        # A layout change rebuilds the app, not this dialog: recolour it here.
        recolor.apply(self, old_palette)
        self._refresh_highlights()

    def _choose_appearance(self, mode):
        try:
            self._master._apply_appearance(mode)
        except Exception:
            logger.debug("could not change appearance", exc_info=True)
        self._refresh_highlights()
