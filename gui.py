from PyQt6.QtWidgets import QDialog, QLabel, QCheckBox, QGridLayout
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
import logging
from .addon_config import AddonConfig
from aqt import mw


class GUI:
    def __init__(self, logger: logging.Logger, add_on_config: AddonConfig):
        self.logger: logging.Logger = logger
        self.add_on_config: AddonConfig = add_on_config
        self.menu_button = None

    def add_menu_button(self):
        self.menu_button = QAction("Auto Button Suggestion", mw)
        self.menu_button.triggered.connect(self.create_settings_window)
        mw.form.menuTools.addAction(self.menu_button)

    def enable_checkbox_change_state(self, state, cb):
        mid = cb.property("mid")
        t_ord = cb.property("t_ord")
        if state == 0 or state == 1:
            self.add_on_config.set_template_state(mid=mid, t_ord=t_ord, key="enabled", value=False)
        if state == 2:
            self.add_on_config.set_template_state(mid=mid, t_ord=t_ord, key="enabled", value=True)

    def _get_quantile_label(self, mid: str, t_ord: str, quantile_value, color: str = "white"):
        enabled = self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="enabled")
        if not enabled:
            return QLabel("")
        text = str(round(quantile_value / 1000, 1))
        label = QLabel(text)
        label.setStyleSheet(f"color: {color};")
        return label

    def create_settings_window(self):
        dlg = QDialog()
        dlg.setWindowTitle("Auto Button Suggestion")
        grid_layout = QGridLayout()

        grid_layout.addWidget(QLabel("MODEL"), 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("TEMPLATE"), 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("ENABLED"), 0, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("HARD"), 0, 3, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("MEDIAN"), 0, 4, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("EASY"), 0, 5, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("N"), 0, 6, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("REVIEW\nMODE"), 0, 7, alignment=Qt.AlignmentFlag.AlignCenter)
        grid_layout.addWidget(QLabel("LEARN\nMODE"), 0, 8, alignment=Qt.AlignmentFlag.AlignCenter)

        i = 1
        for mid in self.add_on_config.get_models_ids():
            model_name = self.add_on_config.get_model_state(mid=mid, key="name")
            for t_ord in self.add_on_config.get_templates_ids(mid=mid):
                ###############################################################
                model_label = QLabel(model_name)
                grid_layout.addWidget(model_label, i, 0, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                template_label = QLabel(self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="name"))
                grid_layout.addWidget(template_label, i, 1, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                enabled = QCheckBox()
                enabled.setProperty("mid", mid)
                enabled.setProperty("t_ord", t_ord)
                enabled.setStyleSheet("""
                            QCheckBox::indicator {
                                width: 20px;
                                height: 20px;
                            }
                            QCheckBox::indicator:checked {
                                background-color: green;
                            }
                            QCheckBox::indicator:unchecked {
                                background-color: red;
                            }
                                    """)
                enabled.setChecked(self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="enabled"))
                enabled.stateChanged.connect(
                    lambda state, cb=enabled: self.enable_checkbox_change_state(state, cb))
                grid_layout.addWidget(enabled, i, 2, alignment=Qt.AlignmentFlag.AlignCenter)
                if not enabled.isChecked():
                    i += 1
                    continue
                ###############################################################
                quantile = self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="hard_quantile")
                quantile_label = self._get_quantile_label(mid=mid, t_ord=t_ord, quantile_value=quantile, color="red")
                grid_layout.addWidget(quantile_label, i, 3, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                quantile = self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="median_quantile")
                quantile_label = self._get_quantile_label(mid=mid, t_ord=t_ord, quantile_value=quantile, color="white")
                grid_layout.addWidget(quantile_label, i, 4, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                quantile = self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="easy_quantile")
                quantile_label = self._get_quantile_label(mid=mid, t_ord=t_ord, quantile_value=quantile, color="green")
                grid_layout.addWidget(quantile_label, i, 5, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                n_text = str(self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="n"))
                n_label = QLabel(n_text)
                grid_layout.addWidget(n_label, i, 6, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                review_mode_text = str(self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="review_mode"))
                review_mode_label = QLabel(review_mode_text)
                grid_layout.addWidget(review_mode_label, i, 7, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                learn_mode_text = str(self.add_on_config.get_template_state(mid=mid, t_ord=t_ord, key="learn_mode"))
                learn_mode_label = QLabel(learn_mode_text)
                grid_layout.addWidget(learn_mode_label, i, 8, alignment=Qt.AlignmentFlag.AlignCenter)
                ###############################################################
                i += 1
        dlg.setLayout(grid_layout)
        dlg.exec()
