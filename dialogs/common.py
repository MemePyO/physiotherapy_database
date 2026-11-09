"""Shared helpers for dialog modules."""

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

import db
import lang
import log
import theme
import utils
from utils import _validate_dob

LANG_LABELS = {"en": "English", "ro": "Rom\u00e2n\u0103"}
logger = log.get_logger(__name__)

__all__ = [
    "tk",
    "messagebox",
    "ttk",
    "ctk",
    "db",
    "lang",
    "log",
    "theme",
    "utils",
    "_validate_dob",
    "LANG_LABELS",
    "logger",
]
