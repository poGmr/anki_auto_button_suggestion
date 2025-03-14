import logging
from logging.handlers import RotatingFileHandler
import os
from .addon_config import AddonConfig
from .gui import GUI
from anki.cards import Card
from typing import Literal
from aqt.reviewer import Reviewer
from .time_statistics import TimeStatistic
from .decision_maker import DecisionMaker
from PyQt6.QtGui import QAction
from aqt import mw
from aqt.gui_hooks import profile_did_open
from aqt.gui_hooks import profile_will_close
from aqt.gui_hooks import reviewer_will_init_answer_buttons
from aqt.gui_hooks import reviewer_did_answer_card
from aqt.gui_hooks import current_note_type_did_change
from enum import Enum, unique


def initialize_logger():
    result = logging.getLogger(__name__)
    if not result.handlers:
        log_file_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "auto_button_suggestion.log"
        )
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=3 * 1024 * 1024, backupCount=3
        )
        log_format = "%(asctime)s [%(levelname)s]: %(message)s"
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        result.addHandler(file_handler)
        result.setLevel(logging.INFO)
    return result


def _default_ease_1() -> int:
    return 1


def _default_ease_2() -> int:
    return 2


def _default_ease_3() -> int:
    return 3


def _default_ease_4() -> int:
    return 4


@unique
class CT(Enum):
    LEARN = 0  # Typ: Ucz się
    REVIEW = 1  # Typ: Powtórka
    RELEARN = 2  # Typ: Ponowne uczenie
    FILTERED = 3  # Typ: Filtrowane
    MANUAL = 4  # Typ: Ręczne


@unique
class CQ(Enum):
    NEW = 0  # Kolejka: Nowe
    LEARNING = 1  # Kolejka: Nauka
    REVIEW = 2  # Kolejka: Powtórka
    IN_LEARNING = 3  # Kolejka: W nauce, ale następny przegląd za co najmniej dzień
    PREVIEW = 4  # Kolejka: Podgląd (Preview)


# CARD_TYPE_MAP 0=learn, 1=review, 2=relearn, 3=filtered, 4=manual
# CARD_QUEUE_MAP
#       -- 0=new, 1=learning, 2=review (as for type)
#       -- 3=in learning, next rev in at least a day after the previous review
#       -- 4=preview


def update_template(mid: str, t_ord: str) -> None:
    global logger
    global addon_config
    statistics = TimeStatistic(
        logger=logger, add_on_config=addon_config, mid=mid, t_ord=t_ord
    )
    statistics.update_template_stats()


@profile_did_open.append
def gui_hook_profile_did_open():
    global logger
    global addon_config
    global gui_menu
    global menu_button
    logger.info("#")
    addon_config = AddonConfig(logger=logger)
    for mid in addon_config.get_models_ids():
        for t_ord in addon_config.get_templates_ids(mid):
            if addon_config.get_template_state(mid=mid, t_ord=t_ord, key="enabled"):
                update_template(mid=mid, t_ord=t_ord)

    gui_menu = GUI(logger=logger, add_on_config=addon_config)
    menu_button = QAction("Auto Button Suggestion", mw)
    menu_button.triggered.connect(gui_menu.create_settings_window)
    mw.form.menuTools.addAction(menu_button)


@profile_will_close.append
def profile_will_close():
    global logger
    global addon_config
    global gui_menu
    global menu_button
    mw.form.menuTools.removeAction(menu_button)
    menu_button.triggered.disconnect(gui_menu.create_settings_window)
    del menu_button
    del gui_menu
    addon_config.__exit__()
    del addon_config


@reviewer_will_init_answer_buttons.append
def gui_hook_reviewer_will_init_answer_buttons(
    buttons_tuple: tuple[bool, Literal[1, 2, 3, 4]], reviewer: Reviewer, card: Card
):
    global logger
    global addon_config
    logger.debug("#")
    note = card.note()
    mid = str(note.note_type()["id"])  # Words, Grammar, Spelling, etc.
    mid_name: str = addon_config.get_model_state(mid=mid, key="name")
    t_ord = str(card.ord)  # 0,1,2 Type of cards, EN->PL, PL->EN, EN->Write, etc,
    t_ord_name: str = addon_config.get_template_state(mid=mid, t_ord=t_ord, key="name")
    c_time_taken = int(card.time_taken())
    c_type = card.type
    c_queue = card.queue
    ####################################################################################################
    if not addon_config.get_template_state(mid=mid, t_ord=t_ord, key="enabled"):
        logger.debug(f"[{mid_name}][{t_ord_name}] is disabled.")
        reviewer._defaultEase = _default_ease_3
        return buttons_tuple
    ####################################################################################################
    update_template(mid=mid, t_ord=t_ord)
    if addon_config.get_template_state(mid=mid, t_ord=t_ord, key="n") < 20:
        logger.debug(f"[{mid_name}][{t_ord_name}] too few elements.")
        reviewer._defaultEase = _default_ease_3
        return buttons_tuple
    ####################################################################################################
    dec_maker = DecisionMaker(
        logger=logger, add_on_config=addon_config, mid=mid, t_ord=t_ord
    )
    decision: int = 3
    key = "none"
    mode = "none"
    if c_queue in (CQ.LEARNING.value, CQ.IN_LEARNING.value):
        key = "learn_mode"
        mode = addon_config.get_template_state(mid=mid, t_ord=t_ord, key=key)
        if mode == "3311":
            decision = dec_maker.get_decision_3311(c_time_taken)
        if mode == "3331":
            decision = dec_maker.get_decision_3331(c_time_taken)
    elif c_queue == CQ.REVIEW.value:
        key = "review_mode"
        mode = addon_config.get_template_state(mid=mid, t_ord=t_ord, key=key)
        if mode == "4332":
            decision = dec_maker.get_decision_4332(c_time_taken)
        if mode == "4333":
            decision = dec_maker.get_decision_4333(c_time_taken)
    debug_output = (
        f"[{mid_name}][{t_ord_name}] Mode: {mode}, Card time taken: {c_time_taken},"
    )
    debug_output += f" {CT(c_type)}, {CQ(c_queue)} -> {key}, decision: {decision}"
    logger.debug(debug_output)

    ####################################################################################################
    b1 = (1, "Again")
    b2 = (2, "Hard")
    b3 = (3, "Good")
    b4 = (4, "Easy")
    if decision == 1:
        b1 = (1, "<b><u>AGAIN</u></b>")
        reviewer._defaultEase = _default_ease_1
    if decision == 2:
        b2 = (2, "<b><u>HARD</u></b>")
        reviewer._defaultEase = _default_ease_2
    if decision == 3:
        b3 = (3, "<b><u>GOOD</u></b>")
        reviewer._defaultEase = _default_ease_3
    if decision == 4:
        b4 = (4, "<b><u>EASY</u></b>")
        reviewer._defaultEase = _default_ease_4
    return b1, b2, b3, b4


@reviewer_did_answer_card.append
def gui_hook_reviewer_did_answer_card(
    reviewer: Reviewer, card: Card, ease: Literal[1, 2, 3, 4]
):
    global logger
    global addon_config
    logger.debug("#")
    note = card.note()
    mid = str(note.note_type()["id"])  # Words, Grammar, Spelling, etc.
    mid_name: str = addon_config.get_model_state(mid=mid, key="name")
    t_ord = str(card.ord)  # 0,1,2 Type of cards, EN->PL, PL->EN, EN->Write, etc,
    t_ord_name: str = addon_config.get_template_state(mid=mid, t_ord=t_ord, key="name")
    c_type = card.type
    c_queue = card.queue
    # logger_output = f"[{mid_name}][{t_ord_name}] User pressed button: {ease}"
    # logger_output += f" Auto button was: {reviewer._defaultEase()} -> [{CQ(c_queue)}]"
    logger_output = (
        f"[{mid_name}][{t_ord_name}] Auto button was: {reviewer._defaultEase()} -> "
    )
    logger_output += f"User pressed button: {ease} -> "
    logger_output += f"Card went to: {CQ(c_queue)}"
    logger.info(logger_output)


@current_note_type_did_change.append
def current_note_type_did_change():
    global logger
    logger.error("current_note_type_did_change")


####################################################################################################
logger: logging.Logger = initialize_logger()
addon_config: AddonConfig
gui_menu: GUI
menu_button: QAction
