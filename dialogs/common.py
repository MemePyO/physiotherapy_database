"""Shared helpers for dialog modules."""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

import db
import lang
import log
import theme
import utils

LANG_LABELS = {"en": "English", "ro": "Română"}
logger = log.get_logger(__name__)
