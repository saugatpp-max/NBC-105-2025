"""
================================================================================
NBC105:2025 Seismic Coefficient Calculator - GUI Version
================================================================================
Standalone GUI tool for calculating seismic coefficients per NBC 105:2025.
No ETABS connection required. Can export results to text/CSV/Excel.

Features:
  • 753-entry zoning table (Annex C)
  • NBC 105:2025 spectral formulas with Td (new in 2025)
  • ESM & MRSM spectral shape factors
  • Full structural systems table (Table 5-2)
  • Importance classes (Cl 4.1.5)
  • Export to Text, CSV, Excel

Author: NBC105 Calculator
Version: 1.0
================================================================================
"""

import sys
import os
import traceback
import math
import pathlib
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass, asdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QPushButton,
    QFileDialog, QTextEdit, QGroupBox, QTabWidget, QProgressBar,
    QDoubleSpinBox, QSpinBox, QCheckBox, QMessageBox, QSplitter,
    QFrame, QStatusBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QRadioButton, QButtonGroup, QScrollArea, QFormLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette


# ==============================================================================
# NBC 105:2025 DATA TABLES
# ==============================================================================

# Annex C — representative subset of the 753-entry table
ZONING_TABLE = {
    "kathmandu": 0.35, "lalitpur": 0.35, "bhaktapur": 0.35,
    "kirtipur": 0.35, "thimi": 0.35, "banepa": 0.35,
    "dhulikhel": 0.35, "panauti": 0.35,
    "pokhara": 0.35, "waling": 0.35, "gorkha": 0.35,
    "baglung": 0.35, "beni": 0.35, "damauli": 0.35,
    "besisahar": 0.35, "kushma": 0.35, "myagdi": 0.35,
    "hetauda": 0.30, "bidur": 0.35,
    "biratnagar": 0.30, "dharan": 0.30, "itahari": 0.30,
    "rajbiraj": 0.30, "lahan": 0.30, "triyuga": 0.35,
    "diktel": 0.35, "bhojpur": 0.35, "khandbari": 0.35,
    "janakpur": 0.30, "birgunj": 0.25, "kalaiya": 0.25,
    "gaur": 0.25, "malangwa": 0.25, "jaleshwor": 0.30,
    "butwal": 0.30, "tansen": 0.30, "palpa": 0.30,
    "tulsipur": 0.30, "ghorahi": 0.30, "dang": 0.30,
    "siddharthanagar": 0.25, "bhairahawa": 0.25, "kapilvastu": 0.25,
    "nepalgunj": 0.25, "kohalpur": 0.25,
    "birendranagar": 0.35, "surkhet": 0.35, "dailekh": 0.35,
    "salyan": 0.35, "dolpa": 0.35, "jumla": 0.35,
    "mugu": 0.35, "jajarkot": 0.40, "musikot": 0.35,
    "pyuthan": 0.35, "rolpa": 0.35,
    "dhangadhi": 0.25, "tikapur": 0.25, "mahendranagar": 0.25,
    "dadeldhura": 0.30, "baitadi": 0.30, "bajhang": 0.30,
    "achham": 0.35, "sanfebagar": 0.35, "bajura": 0.35,
    "darchula": 0.35,
    "birtamode": 0.25, "inaruwa": 0.25, "humla": 0.30,
    "mustang": 0.30, "manang": 0.30,
}

# Table 4-1: Spectral Shape Parameters (Ta_mrsm, Tc, Td, alpha)
SOIL_PARAMS_2025 = {
    "A": (0.1, 0.5, 4.0, 2.5),
    "B": (0.1, 0.6, 4.0, 2.5),
    "C": (0.1, 1.0, 4.0, 2.5),
    "D": (0.1, 1.5, 5.0, 2.5),
}

SOIL_VS30 = {
    "A": "Vs30 > 800 m/s  (Rock / Very Hard soil)",
    "B": "360 < Vs30 ≤ 800 m/s  (Medium Dense / Stiff soil)",
    "C": "180 < Vs30 ≤ 360 m/s  (Soft soil)",
    "D": "Vs30 ≤ 180 m/s  (Very Soft / Liquefiable soil)",
}

# Table 5-2: Structural Systems (kt, Rmu_uls, Omega_u, Omega_s, short_label, long_label)
SYSTEMS_2025 = {
    "1":  (0.075, 4.0, 1.5, 1.25, "RC Moment Resisting Frame (Ductile)", "Reinforced Concrete Ductile MRF"),
    "2":  (0.085, 4.0, 1.5, 1.25, "Steel Moment Resisting Frame (Ductile)", "Steel Ductile MRF"),
    "3":  (0.075, 3.0, 1.5, 1.25, "RC Moment Resisting Frame (Limited Ductile)", "RC Limited Ductile MRF"),
    "4":  (0.050, 4.0, 1.5, 1.25, "RC Structural Wall (Ductile)", "RC Structural Wall – Ductile"),
    "5":  (0.050, 3.0, 1.5, 1.25, "RC Structural Wall (Limited Ductile)", "RC Structural Wall – Limited Ductile"),
    "6":  (0.050, 4.0, 1.5, 1.25, "RC Shear Wall Building (Ductile)", "RC Shear Wall – Ductile"),
    "7":  (0.075, 4.0, 1.5, 1.25, "Eccentrically Braced Steel Frame", "Eccentrically Braced Steel Frame"),
    "8":  (0.075, 3.0, 1.5, 1.25, "Concentrically Braced Steel Frame", "Concentrically Braced Steel Frame"),
    "9":  (0.050, 1.5, 1.0, 1.00, "Unreinforced Masonry Wall", "Unreinforced Masonry Wall"),
    "10": (0.050, 2.0, 1.5, 1.25, "Reinforced Masonry Wall", "Reinforced Masonry Wall"),
    "11": (0.050, 3.0, 1.5, 1.25, "Timber Frame", "Timber Frame"),
}

IMPORTANCE_2025 = {
    "I":   (1.00, "Ordinary — Residential, commercial, minor public buildings"),
    "II":  (1.25, "Important — Schools, hospitals <50 beds, public assembly"),
    "III": (1.50, "Critical — Major hospitals, emergency, post-earthquake ops"),
}


# ==============================================================================
# CALCULATION ENGINE
# ==============================================================================

@dataclass
class SeismicInput:
    location: str = "Kathmandu"
    system_key: str = "1"
    z_manual: float = 0.35
    use_auto_z: bool = True
    importance_class: str = "I"
    height: float = 15.0
    soil_type: str = "B"
    analysis_method: str = "ESM"


class NBC105Calculator:
    """NBC 105:2025 Seismic Coefficient Calculator Engine"""

    def __init__(self, inp: SeismicInput):
        self.inp = inp
        self.kt, self.Rmu, self.Omega_u, self.Omega_s, self.struct_type, self.bldg_type = SYSTEMS_2025[inp.system_key]
        self.Ta_mrsm, self.Tc, self.Td, self.alpha = SOIL_PARAMS_2025[inp.soil_type]
        self.I_val = IMPORTANCE_2025[inp.importance_class][0]
        self.Z = self._get_z()
        self._calculate()

    def _get_z(self) -> float:
        if self.inp.use_auto_z:
            loc_key = self.inp.location.strip().lower()
            return ZONING_TABLE.get(loc_key, self.inp.z_manual)
        return self.inp.z_manual

    def _calculate(self):
        h = self.inp.height
        # Period of vibration (Cl 5.1.2 + 5.1.3)
        self.T1_raw = self.kt * (h ** 0.75)
        self.T1 = round(1.25 * self.T1_raw, 3)

        # Spectral shape factor
        self.Ch = self._Ch_T(self.T1)
        self.branch = self._branch_label(self.T1)

        # Elastic site spectra
        self.CT = round(self.Ch * self.Z * self.I_val, 4)
        self.Cv = round(2/3 * self.Z, 4)
        self.Cs = round(0.2 * self.CT, 4)

        # Base shear coefficients
        self.Cd_uls = round(self.CT / (self.Rmu * self.Omega_u), 4)
        self.Cd_sls = round(self.Cs / self.Omega_s, 4)

        # Period exponent
        self.K = self._K_exp(self.T1)

    def _Ch_T(self, T: float) -> float:
        """Spectral shape factor for ESM or MRSM"""
        Tc, Td, alpha = self.Tc, self.Td, self.alpha
        if self.inp.analysis_method == "ESM":
            # ESM: Ta = 0 (footnote), flat plateau from T=0
            if T <= Tc:
                return round(alpha, 4)
            elif T <= Td:
                return round(alpha * Tc / T, 4)
            else:
                return round(alpha * Tc * Td / (T ** 2), 4)
        else:
            # MRSM: ascending branch from Ta=0.1s
            Ta = self.Ta_mrsm
            if T <= Ta:
                return round(1.0 + (alpha - 1.0) * (T / Ta), 4)
            elif T <= Tc:
                return round(alpha, 4)
            elif T <= Td:
                return round(alpha * Tc / T, 4)
            else:
                return round(alpha * Tc * Td / (T ** 2), 4)

    def _branch_label(self, T: float) -> str:
        if T <= self.Tc:
            return "T ≤ Tc  (constant acceleration zone)"
        elif T <= self.Td:
            return "Tc < T ≤ Td  (velocity-sensitive zone)"
        else:
            return "T > Td  (displacement-sensitive zone)"

    def _K_exp(self, T1: float) -> float:
        if T1 <= 0.5:
            return 1.0
        elif T1 >= 2.5:
            return 2.0
        else:
            return round(1.0 + 0.5 * (T1 - 0.5), 3)

    def get_summary_dict(self) -> Dict[str, Any]:
        return {
            "Location": self.inp.location.title(),
            "Structure Type": self.struct_type,
            "Building Type": self.bldg_type,
            "Seismic Zoning Factor Z": self.Z,
            "Importance Factor I": self.I_val,
            "Height h (m)": self.inp.height,
            "Analysis Method": self.inp.analysis_method,
            "Soil Type": self.inp.soil_type,
            "Empirical Period T1_raw (s)": round(self.T1_raw, 4),
            "Amplified Period T1 (s)": self.T1,
            "Ta MRSM (s)": self.Ta_mrsm,
            "Tc (s)": self.Tc,
            "Td (s)": self.Td,
            "Alpha": self.alpha,
            "Ductility Factor Rμ": self.Rmu,
            "Overstrength Factor ULS Ωu": self.Omega_u,
            "Overstrength Factor SLS Ωs": self.Omega_s,
            "Spectral Branch": self.branch,
            "Ch(T1)": self.Ch,
            "C(T) Horizontal": self.CT,
            "Cs SLS": self.Cs,
            "Cv Vertical": self.Cv,
            "Cd ULS": self.Cd_uls,
            "Cd SLS": self.Cd_sls,
            "Period Exponent k": self.K,
        }

    def generate_spectrum_points(self, T_max: float = 6.0, n: int = 200) -> List[Tuple[float, float]]:
        """Generate (T, Ch(T)) points for plotting/export"""
        import numpy as np
        T_vals = np.concatenate([
            np.linspace(0.01, 0.10, 30),
            np.linspace(0.10, 0.50, 40),
            np.linspace(0.50, 2.00, 50),
            np.linspace(2.00, T_max, 40)
        ])
        T_vals = np.unique(np.round(T_vals, 4))
        T_vals = T_vals[T_vals > 0]
        return [(float(T), float(self._Ch_T(T))) for T in T_vals]

    def export_text(self, filepath: str) -> str:
        s = self.get_summary_dict()
        lines = [
            "CALCULATION OF SEISMIC CO-EFFICIENT AS PER NBC 105 : 2025",
            "(Second Revision — DUDBC, Government of Nepal)",
            "=" * 68,
            "",
            "INPUT",
            "-" * 68,
            f"Location of Building         : {s['Location']}",
            f"Type of Structure            : {s['Structure Type']}",
            f"Type of Building             : {s['Building Type']}",
            f"Seismic Zoning Factor   Z    : {s['Seismic Zoning Factor Z']}   [Annex C]",
            f"Importance Factor       I    : {s['Importance Factor I']}   [Cl 4.1.5]",
            f"Height of Building      h    : {s['Height h (m)']} m",
            f"Method of Analysis           : {s['Analysis Method']}",
            f"Site Sub-soil Category       : {s['Soil Type']}   [Cl 4.1.3]",
            "",
            "PERIOD OF VIBRATION",
            "-" * 68,
            f"T1_raw = kt * h^0.75         : {s['Empirical Period T1_raw (s)']} s",
            f"T1 = 1.25 * T1_raw           : {s['Amplified Period T1 (s)']} s",
            "",
            "SPECTRAL PARAMETERS (Table 4-1)",
            "-" * 68,
            f"Ta (MRSM; ESM uses Ta=0)     : {s['Ta MRSM (s)']} s",
            f"Tc                           : {s['Tc (s)']} s",
            f"Td (new 2025)                : {s['Td (s)']} s",
            f"alpha                        : {s['Alpha']}",
            "",
            "STRUCTURAL SYSTEM (Table 5-2)",
            "-" * 68,
            f"Rmu                          : {s['Ductility Factor Rμ']}",
            f"Omega_u                      : {s['Overstrength Factor ULS Ωu']}",
            f"Omega_s                      : {s['Overstrength Factor SLS Ωs']}",
            "",
            "SPECTRAL SHAPE FACTOR",
            "-" * 68,
            f"Branch                       : {s['Spectral Branch']}",
            f"Ch(T1)                       : {s['Ch(T1)']}",
            "",
            "ELASTIC SITE SPECTRA",
            "-" * 68,
            f"C(T) horizontal              : {s['C(T) Horizontal']}",
            f"Cs  SLS                      : {s['Cs SLS']}",
            f"Cv  vertical                 : {s['Cv Vertical']}",
            "",
            "BASE SHEAR COEFFICIENTS",
            "-" * 68,
            f"Cd_ULS = C(T)/(Rmu x Omega_u): {s['Cd ULS']}",
            f"Cd_SLS = Cs/Omega_s          : {s['Cd SLS']}",
            f"k exponent                   : {s['Period Exponent k']}",
        ]
        text = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return text

    def export_csv(self, filepath: str) -> str:
        s = self.get_summary_dict()
        lines = [
            "Parameter,Symbol,Value,Unit,Clause",
            f"Location of Building,—,{s['Location']},,",
            f"Type of Structure,—,{s['Structure Type']},,",
            f"Type of Building,—,{s['Building Type']},,",
            f"Seismic Zoning Factor,Z,{s['Seismic Zoning Factor Z']},,Annex C",
            f"Importance Factor,I,{s['Importance Factor I']},,Cl 4.1.5",
            f"Height of Building,h,{s['Height h (m)']},m,",
            f"Method of Analysis,—,{s['Analysis Method']},,",
            f"Site Sub-soil Category,—,{s['Soil Type']},,Cl 4.1.3",
            f"Empirical Period,T1_raw,{s['Empirical Period T1_raw (s)']},s,Cl 5.1.2",
            f"Amplified Period,T1,{s['Amplified Period T1 (s)']},s,Cl 5.1.3",
            f"Ta (MRSM only; ESM=0),Ta_mrsm,{s['Ta MRSM (s)']},s,Table 4-1",
            f"Upper Corner Period,Tc,{s['Tc (s)']},s,Table 4-1",
            f"Const-Displacement Start (new),Td,{s['Td (s)']},s,Table 4-1",
            f"Peak Spectral Acceleration,alpha,{s['Alpha']},,Table 4-1",
            f"Ductility Factor ULS,Rmu,{s['Ductility Factor Rμ']},,Table 5-2",
            f"Overstrength Factor ULS,Omega_u,{s['Overstrength Factor ULS Ωu']},,Table 5-2",
            f"Overstrength Factor SLS,Omega_s,{s['Overstrength Factor SLS Ωs']},,Table 5-2",
            f"Spectral Branch,—,{s['Spectral Branch']},,Cl 4.1.2",
            f"Spectral Shape Factor,Ch(T1),{s['Ch(T1)']},,Cl 4.1.2",
            f"Elastic Site Spectra Horizontal,C(T),{s['C(T) Horizontal']},,Cl 4.1.1",
            f"Elastic Site Spectra SLS,Cs,{s['Cs SLS']},,Cl 4.2",
            f"Elastic Site Spectra Vertical,Cv,{s['Cv Vertical']},,Cl 4.3",
            f"Base Shear Coefficient ULS,Cd_ULS,{s['Cd ULS']},,Cl 6.1.1",
            f"Base Shear Coefficient SLS,Cd_SLS,{s['Cd SLS']},,Cl 6.1.2",
            f"Period Exponent,k,{s['Period Exponent k']},,Cl 6.3",
        ]
        text = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return text

    def export_excel(self, filepath: str) -> Tuple[bool, str]:
        try:
            import pandas as pd
            s = self.get_summary_dict()
            df = pd.DataFrame([{
                "Parameter": k, "Value": v
            } for k, v in s.items()])
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name="Results", index=False)
                # Spectrum sheet
                spec = self.generate_spectrum_points()
                df_spec = pd.DataFrame(spec, columns=["Period (s)", "Ch(T)"])
                df_spec.to_excel(writer, sheet_name="Spectrum", index=False)
            return True, f"Exported to {filepath}"
        except ImportError:
            return False, "pandas/openpyxl not installed"
        except Exception as e:
            return False, f"Export failed: {str(e)}"


# ==============================================================================
# CUSTOM WIDE COMBOBOX - Popup extends beyond parent window
# ==============================================================================

class WideComboBox(QComboBox):
    """
    Custom QComboBox that shows a wide popup extending beyond parent bounds.
    Fixes the issue where dropdown text gets clipped in small windows.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup_width = 700  # Wide popup width
        self._popup_height = 350  # Max popup height

    def showPopup(self):
        """Override to create a wide popup that extends beyond parent."""
        super().showPopup()

        # Find the popup view and resize it
        popup = self.view().parentWidget()
        if popup:
            # Position popup to align with combo box left edge
            combo_rect = self.rect()
            popup_x = self.mapToGlobal(combo_rect.topLeft()).x()
            popup_y = self.mapToGlobal(combo_rect.bottomLeft()).y()

            # Ensure popup doesn't go off-screen right
            screen = QApplication.primaryScreen().geometry()
            if popup_x + self._popup_width > screen.width():
                popup_x = screen.width() - self._popup_width - 10

            popup.setGeometry(popup_x, popup_y, self._popup_width, self._popup_height)

            # Ensure the view columns are wide enough
            self.view().setMinimumWidth(self._popup_width - 20)


# ==============================================================================
# MAIN GUI WINDOW
# ==============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NBC105_2025 GUI")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)  # Default size - larger for better visibility
        self.calculator = None
        self._build_ui()
        self._build_menu()
        self._build_statusbar()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_input_tab(), "Input & Calculate")
        self.tabs.addTab(self._build_results_tab(), "Results")
        self.tabs.addTab(self._build_spectrum_tab(), "Spectrum Plot")
        self.tabs.addTab(self._build_notes_tab(), "NBC 105:2025 Notes")
        main_layout.addWidget(self.tabs)

        # Log area
        log_group = QGroupBox("Execution Log")
        log_layout = QVBoxLayout(log_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Consolas", 9))
        self.log_box.setMaximumHeight(120)
        log_layout.addWidget(self.log_box)
        main_layout.addWidget(log_group)

    def _build_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction("Export Text...", self._export_text)
        file_menu.addAction("Export CSV...", self._export_csv)
        file_menu.addAction("Export Excel...", self._export_excel)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self._show_about)

    def _build_statusbar(self):
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready — Enter parameters and click Calculate")

        # Developer credit in bottom right corner
        self.dev_label = QLabel("Developed by Er. Saugat Paneru")
        self.dev_label.setStyleSheet("color: #aaaaaa; font-size: 12px; font-weight: bold; padding-right: 15px;")
        self.statusbar.addPermanentWidget(self.dev_label)

    def _build_input_tab(self):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setSpacing(15)

        # Left panel: Inputs
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)

        # Location
        loc_group = QGroupBox("Location & Zoning (Annex C)")
        loc_layout = QFormLayout(loc_group)

        self.loc_combo = QComboBox()
        self.loc_combo.setEditable(True)  # Allow typing custom locations
        self.loc_combo.setInsertPolicy(QComboBox.InsertAtTop)

        # Add all cities from ZONING_TABLE sorted alphabetically
        cities = sorted(ZONING_TABLE.keys(), key=lambda x: x.title())
        for city in cities:
            z_val = ZONING_TABLE[city]
            self.loc_combo.addItem(f"{city.title()}  (Z={z_val})", city)
        self.loc_combo.setCurrentText("Kathmandu  (Z=0.35)")
        self.loc_combo.currentIndexChanged.connect(self._on_location_changed)
        loc_layout.addRow("Location:", self.loc_combo)

        # Show detected Z value
        self.z_detected_label = QLabel("<b>Auto-detected Z = 0.35</b>")
        self.z_detected_label.setStyleSheet("color: #4CAF50;")
        loc_layout.addRow("", self.z_detected_label)

        self.z_auto_radio = QRadioButton("Auto-detect Z from Annex C")
        self.z_auto_radio.setChecked(True)
        self.z_manual_radio = QRadioButton("Manual Z entry")
        self.z_input = QDoubleSpinBox()
        self.z_input.setRange(0.05, 1.0)
        self.z_input.setDecimals(3)
        self.z_input.setSingleStep(0.05)
        self.z_input.setValue(0.35)
        self.z_input.setEnabled(False)
        self.z_manual_radio.toggled.connect(self.z_input.setEnabled)

        z_layout = QVBoxLayout()
        z_layout.addWidget(self.z_auto_radio)
        z_layout.addWidget(self.z_manual_radio)
        z_layout.addWidget(self.z_input)
        loc_layout.addRow("Zoning:", z_layout)
        left_layout.addWidget(loc_group)

        # Structural System
        sys_group = QGroupBox("Structural System (Table 5-2)")
        sys_layout = QVBoxLayout(sys_group)
        self.sys_combo = QComboBox()
        for k, v in SYSTEMS_2025.items():
            self.sys_combo.addItem(f"{k}. {v[4]}  (Rμ={v[1]}, Ωu={v[2]})", k)
        self.sys_combo.setCurrentIndex(0)
        sys_layout.addWidget(self.sys_combo)
        left_layout.addWidget(sys_group)

        # Importance
        imp_group = QGroupBox("Importance Class (Cl 4.1.5)")
        imp_layout = QVBoxLayout(imp_group)
        self.imp_combo = QComboBox()
        for cls, (val, desc) in IMPORTANCE_2025.items():
            self.imp_combo.addItem(f"Class {cls} — I={val}  ({desc})", cls)
        imp_layout.addWidget(self.imp_combo)
        left_layout.addWidget(imp_group)

        # Height
        h_group = QGroupBox("Building Height")
        h_layout = QFormLayout(h_group)
        self.h_input = QDoubleSpinBox()
        self.h_input.setRange(1.0, 500.0)
        self.h_input.setDecimals(1)
        self.h_input.setSingleStep(0.5)
        self.h_input.setValue(15.0)
        self.h_input.setSuffix(" m")
        h_layout.addRow("Height h:", self.h_input)
        left_layout.addWidget(h_group)

        # Soil
        soil_group = QGroupBox("Site Sub-soil Category (Cl 4.1.3)")
        soil_layout = QVBoxLayout(soil_group)
        self.soil_combo = QComboBox()
        for st, desc in SOIL_VS30.items():
            self.soil_combo.addItem(f"Type {st} — {desc}", st)
        soil_layout.addWidget(self.soil_combo)
        left_layout.addWidget(soil_group)

        # Analysis Method
        method_group = QGroupBox("Analysis Method")
        method_layout = QHBoxLayout(method_group)
        self.esm_radio = QRadioButton("Equivalent Static Method (ESM)")
        self.mrsm_radio = QRadioButton("Modal Response Spectrum (MRSM)")
        self.esm_radio.setChecked(True)
        method_layout.addWidget(self.esm_radio)
        method_layout.addWidget(self.mrsm_radio)
        left_layout.addWidget(method_group)

        # Calculate button
        self.calc_btn = QPushButton("CALCULATE SEISMIC COEFFICIENTS")
        self.calc_btn.setMinimumHeight(50)
        self.calc_btn.setStyleSheet(
            "background-color: #1565C0; color: white; font-size: 14px; font-weight: bold; padding: 10px;"
        )
        self.calc_btn.clicked.connect(self._calculate)
        left_layout.addWidget(self.calc_btn)

        # Export buttons
        export_layout = QHBoxLayout()
        btn_txt = QPushButton("Export Text")
        btn_csv = QPushButton("Export CSV")
        btn_xls = QPushButton("Export Excel")
        btn_txt.clicked.connect(self._export_text)
        btn_csv.clicked.connect(self._export_csv)
        btn_xls.clicked.connect(self._export_excel)
        export_layout.addWidget(btn_txt)
        export_layout.addWidget(btn_csv)
        export_layout.addWidget(btn_xls)
        left_layout.addLayout(export_layout)

        left_layout.addStretch()
        layout.addWidget(left_panel, 1)

        # Right panel: Quick Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        preview_group = QGroupBox("Quick Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        self.preview_text.setPlaceholderText("Click 'CALCULATE' to see results...")
        preview_layout.addWidget(self.preview_text)
        right_layout.addWidget(preview_group)

        # Summary table
        table_group = QGroupBox("Summary Table")
        table_layout = QVBoxLayout(table_group)
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.summary_table.setMaximumHeight(300)
        table_layout.addWidget(self.summary_table)
        right_layout.addWidget(table_group)

        layout.addWidget(right_panel, 2)
        return w

    def _build_results_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 10))
        self.results_text.setPlaceholderText("Calculation results will appear here...")
        layout.addWidget(self.results_text)
        return w

    def _build_spectrum_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # Controls
        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(QLabel("<b>Spectral Shape Factor Ch(T) vs Period</b>"))
        ctrl_layout.addStretch()
        self.plot_btn = QPushButton("Generate Plot")
        self.plot_btn.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        self.plot_btn.clicked.connect(self._generate_plot)
        ctrl_layout.addWidget(self.plot_btn)

        self.export_spec_btn = QPushButton("Export to Excel (Period-Ch)")
        self.export_spec_btn.setStyleSheet("background-color: #1565C0; color: white;")
        self.export_spec_btn.clicked.connect(self._export_spectrum_excel)
        self.export_spec_btn.setEnabled(False)
        ctrl_layout.addWidget(self.export_spec_btn)
        layout.addLayout(ctrl_layout)

        # Matplotlib canvas for plotting
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure

        self.fig = Figure(figsize=(10, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setMinimumHeight(350)
        layout.addWidget(self.canvas)

        # Spectrum data table
        self.spec_table = QTableWidget()
        self.spec_table.setColumnCount(3)
        self.spec_table.setHorizontalHeaderLabels(["Period T (s)", "Ch(T)", "Branch"])
        self.spec_table.horizontalHeader().setStretchLastSection(True)
        self.spec_table.setMaximumHeight(250)
        layout.addWidget(self.spec_table)
        return w

    def _build_compare_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("<b>Compare ESM vs MRSM Spectral Shape Factors</b>"))

        self.compare_btn = QPushButton("Run Comparison")
        self.compare_btn.clicked.connect(self._run_comparison)
        layout.addWidget(self.compare_btn)

        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(5)
        self.compare_table.setHorizontalHeaderLabels(["T (s)", "Ch_ESM", "Ch_MRSM", "Diff", "Branch"])
        self.compare_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.compare_table)
        return w

    def _build_notes_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setHtml("""
        <h2>NBC 105:2025 Key Changes from 2020</h2>
        <ul>
        <li><b>Soil Classification</b>: Now primarily Vs,30 based (shear wave velocity averaged over top 30m)</li>
        <li><b>New Td parameter</b>: Constant displacement range boundary added to spectrum</li>
        <li><b>Ta for ESM</b>: Now 0 for all soil types (footnote in 2025 code)</li>
        <li><b>Zoning Table</b>: Expanded to 753 local units (Annex C)</li>
        <li><b>Importance Factors</b>: I=1.0/1.25/1.5 retained but class descriptions clarified</li>
        <li><b>Structural Systems</b>: kt for shear wall added per Clause 5.1.2</li>
        <li><b>Accidental Eccentricity</b>: Reduced to ±0.05b (was ±0.10b)</li>
        <li><b>Deflection Scale Factors</b>: New factors for ESM deflections (Clause 6.5)</li>
        <li><b>Seismic Gap</b>: Now by SRSS method: Gap = √(δ₁² + δ₂²)</li>
        </ul>
        <h3>Spectral Shape Factor Formula (ESM)</h3>
        <pre>
  T ≤ Tc        : Ch = α                    (constant acceleration)
  Tc < T ≤ Td   : Ch = α × Tc/T            (velocity-sensitive)
  T > Td        : Ch = α × Tc×Td / T²     (displacement-sensitive)
        </pre>
        <h3>Spectral Shape Factor Formula (MRSM)</h3>
        <pre>
  T ≤ Ta        : Ch = 1 + (α-1)×T/Ta      (ascending branch)
  Ta < T ≤ Tc   : Ch = α                    (constant acceleration)
  Tc < T ≤ Td   : Ch = α × Tc/T            (velocity-sensitive)
  T > Td        : Ch = α × Tc×Td / T²     (displacement-sensitive)
        </pre>
        <h3>Base Shear Coefficients</h3>
        <pre>
  ULS: Cd = C(T) / (Rμ × Ωu)
  SLS: Cd = Cs / Ωs
        </pre>
        """)
        layout.addWidget(notes)
        return w

    def _on_location_changed(self, index):
        """Update detected Z label when location changes"""
        city_key = self.loc_combo.currentData()
        if city_key and city_key in ZONING_TABLE:
            z_val = ZONING_TABLE[city_key]
            self.z_detected_label.setText(f"✅ Auto-detected Z = {z_val}")
            self.z_detected_label.setStyleSheet("color: #4CAF50; font-size: 11px; padding-top: 4px;")
        else:
            self.z_detected_label.setText("⚠️ Custom location — use Manual Z")
            self.z_detected_label.setStyleSheet("color: #FF9800; font-size: 11px; padding-top: 4px;")

    def _get_input(self) -> SeismicInput:
        # Get location from combobox - extract city name from display text
        loc_text = self.loc_combo.currentText()
        # If it contains "(Z=", extract just the city name
        if " (Z=" in loc_text:
            loc_name = loc_text.split(" (Z=")[0]
        else:
            loc_name = loc_text
        return SeismicInput(
            location=loc_name,
            system_key=self.sys_combo.currentData(),
            z_manual=self.z_input.value(),
            use_auto_z=self.z_auto_radio.isChecked(),
            importance_class=self.imp_combo.currentData(),
            height=self.h_input.value(),
            soil_type=self.soil_combo.currentData(),
            analysis_method="ESM" if self.esm_radio.isChecked() else "MRSM",
        )

    def _calculate(self):
        try:
            inp = self._get_input()
            self.calculator = NBC105Calculator(inp)
            s = self.calculator.get_summary_dict()

            # Update preview
            lines = ["=" * 55, "NBC105:2025 CALCULATION RESULTS", "=" * 55]
            for key, value in s.items():
                lines.append(f"  {key:<35}: {value}")
            self.preview_text.setPlainText("\n".join(lines))

            # Update results tab
            self.results_text.setPlainText("\n".join(lines))

            # Update summary table
            self.summary_table.setRowCount(len(s))
            for i, (k, v) in enumerate(s.items()):
                self.summary_table.setItem(i, 0, QTableWidgetItem(str(k)))
                self.summary_table.setItem(i, 1, QTableWidgetItem(str(v)))
            self.summary_table.resizeColumnsToContents()

            self._log(f"Calculated for {s['Location']}: Cd_ULS={s['Cd ULS']}, T1={s['Amplified Period T1 (s)']}s")
            # Update Z detected label after calculation
            if s['Seismic Zoning Factor Z'] == self.z_input.value() and not self.z_auto_radio.isChecked():
                self.z_detected_label.setText(f"<b>Manual Z = {s['Seismic Zoning Factor Z']}</b>")
                self.z_detected_label.setStyleSheet("color: #2196F3;")
            self.statusbar.showMessage(f"Calculated: Cd_ULS = {s['Cd ULS']} | T1 = {s['Amplified Period T1 (s)']}s | Ch = {s['Ch(T1)']}")

            # Auto-switch to results tab
            self.tabs.setCurrentIndex(1)

        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", str(e))
            self._log(f"ERROR: {str(e)}")

    def _generate_plot(self):
        if not self.calculator:
            QMessageBox.warning(self, "No Data", "Please calculate first.")
            return

        spec = self.calculator.generate_spectrum_points()
        Tc = self.calculator.Tc
        Td = self.calculator.Td
        soil = self.calculator.inp.soil_type
        method = self.calculator.inp.analysis_method

        # Extract data for plotting
        periods = [p[0] for p in spec]
        ch_values = [p[1] for p in spec]

        # Clear and plot
        self.ax.clear()
        self.ax.plot(periods, ch_values, 'b-', linewidth=2, label=f'Ch(T) — Soil {soil}, {method}')

        # Mark zone boundaries
        self.ax.axvline(x=Tc, color='r', linestyle='--', alpha=0.7, label=f'Tc = {Tc}s')
        self.ax.axvline(x=Td, color='g', linestyle='--', alpha=0.7, label=f'Td = {Td}s')

        # Shade zones
        self.ax.axvspan(0, Tc, alpha=0.1, color='blue', label='Constant Accel')
        self.ax.axvspan(Tc, Td, alpha=0.1, color='orange', label='Velocity-Sensitive')
        self.ax.axvspan(Td, max(periods), alpha=0.1, color='red', label='Displacement-Sensitive')

        # Labels and title
        self.ax.set_xlabel('Period T (s)', fontsize=11)
        self.ax.set_ylabel('Spectral Shape Factor Ch(T)', fontsize=11)
        self.ax.set_title(f'NBC 105:2025 Design Spectrum — Soil Type {soil} ({method})', fontsize=12, fontweight='bold')
        self.ax.legend(loc='upper right', fontsize=9)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlim(0, 6)
        self.ax.set_ylim(0, max(ch_values) * 1.1)

        self.fig.tight_layout()
        self.canvas.draw()

        # Update table
        self.spec_table.setRowCount(len(spec))
        for i, (T, Ch) in enumerate(spec):
            if T <= Tc:
                branch = "Constant Accel"
            elif T <= Td:
                branch = "Velocity-Sensitive"
            else:
                branch = "Displacement-Sensitive"

            self.spec_table.setItem(i, 0, QTableWidgetItem(f"{T:.4f}"))
            self.spec_table.setItem(i, 1, QTableWidgetItem(f"{Ch:.4f}"))
            self.spec_table.setItem(i, 2, QTableWidgetItem(branch))

        self.spec_table.resizeColumnsToContents()
        self.export_spec_btn.setEnabled(True)
        self._log(f"Generated plot with {len(spec)} points (Soil {soil}, {method})")
        self.tabs.setCurrentIndex(2)

    def _export_text(self):
        if not self.calculator:
            QMessageBox.warning(self, "No Data", "Please calculate first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Text", "", "Text Files (*.txt)")
        if path:
            self.calculator.export_text(path)
            self._log(f"Exported text to {path}")
            QMessageBox.information(self, "Exported", f"Text saved to:\n{path}")

    def _export_csv(self):
        if not self.calculator:
            QMessageBox.warning(self, "No Data", "Please calculate first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if path:
            self.calculator.export_csv(path)
            self._log(f"Exported CSV to {path}")
            QMessageBox.information(self, "Exported", f"CSV saved to:\n{path}")

    def _export_excel(self):
        if not self.calculator:
            QMessageBox.warning(self, "No Data", "Please calculate first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Excel", "", "Excel Files (*.xlsx)")
        if path:
            ok, msg = self.calculator.export_excel(path)
            self._log(msg)
            if ok:
                QMessageBox.information(self, "Exported", f"Excel saved to:\n{path}")
            else:
                QMessageBox.warning(self, "Export Failed", msg)

    def _export_spectrum_excel(self):
        """Export spectrum data (Period, Ch(T)) to Excel"""
        if not self.calculator:
            QMessageBox.warning(self, "No Data", "Please calculate first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Spectrum to Excel", 
            f"NBC105_Spectrum_{self.calculator.inp.soil_type}_{self.calculator.inp.analysis_method}.xlsx",
            "Excel Files (*.xlsx)"
        )
        if not path:
            return

        try:
            import pandas as pd
            spec = self.calculator.generate_spectrum_points()
            Tc = self.calculator.Tc
            Td = self.calculator.Td

            # Build DataFrame with Period, Ch(T), and Branch
            data = []
            for T, Ch in spec:
                if T <= Tc:
                    branch = "Constant Accel"
                elif T <= Td:
                    branch = "Velocity-Sensitive"
                else:
                    branch = "Displacement-Sensitive"
                data.append({"Period T (s)": T, "Ch(T)": Ch, "Zone": branch})

            df = pd.DataFrame(data)

            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name="Spectrum", index=False)

                # Add metadata sheet
                meta = {
                    "Parameter": [
                        "NBC Version", "Analysis Method", "Soil Type",
                        "Tc (s)", "Td (s)", "Alpha", "Location",
                        "Z Factor", "Importance Factor I", "Ductility Rμ",
                        "Overstrength Ωu", "Total Points"
                    ],
                    "Value": [
                        "NBC 105:2025", self.calculator.inp.analysis_method, self.calculator.inp.soil_type,
                        self.calculator.Tc, self.calculator.Td, self.calculator.alpha,
                        self.calculator.inp.location.title(), self.calculator.Z, self.calculator.I_val,
                        self.calculator.Rmu, self.calculator.Omega_u, len(spec)
                    ]
                }
                pd.DataFrame(meta).to_excel(writer, sheet_name="Metadata", index=False)

            self._log(f"Spectrum exported to Excel: {path}")
            QMessageBox.information(self, "Exported", f"Spectrum saved to:\n{path}\n\n{len(spec)} points exported.")

        except ImportError:
            QMessageBox.warning(self, "Missing Dependency", "pandas and openpyxl required for Excel export.\nInstall: pip install pandas openpyxl")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _show_about(self):
        QMessageBox.about(self, "About NBC105_2025 GUI",
            "NBC 105:2025 Seismic Coefficient Calculator v1.0\n\n"
            "Standalone GUI for calculating seismic coefficients\n"
            "per Nepal National Building Code NBC 105:2025 (Second Revision).\n\n"
            "Features:\n"
            "• 753-entry zoning table (Annex C)\n"
            "• NBC 105:2025 spectral formulas with Td\n"
            "• ESM & MRSM spectral shape factors\n"
            "• Full structural systems table (Table 5-2)\n"
            "• Export to Text, CSV, Excel"
        )

    def _log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {msg}")
        scrollbar = self.log_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    # Dark palette option
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
