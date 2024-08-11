import logging
from logging.handlers import RotatingFileHandler
import os
from .addon_config import AddonConfig
from aqt import gui_hooks
from .gui import GUI
from anki.cards import Card
from typing import Literal
from aqt.reviewer import Reviewer
from .time_statistics import TimeStatistic
from .decision_maker import DecisionMaker


def initialize_logger():
    result = logging.getLogger(__name__)
    if not result.handlers:
        log_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "auto_button_suggestion.log")
        file_handler = RotatingFileHandler(log_file_path, maxBytes=3 * 1024 * 1024, backupCount=3)
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


CARD_TYPE_MAP = {
    0: "new",
    1: "learning",
    2: "review",
    3: "relearning"
}
CARD_QUEUE_MAP = {
    -3: "suspended",
    -2: "buried",
    -1: "user buried",
    0: "new",
    1: "learning",
    2: "review",
    3: "day learning"
}
REVLOG_TYPE_MAP = {
    0: "learn",
    1: "review",
    2: "relearn",
    3: "filtered",
    4: "manual"
}


def gui_hook_profile_did_open():
    global logger
    global addon_config
    global menu_button_added
    logger.info("#")
    logger.info("################################### ADD-ON STARTED #################################################")
    logger.info("#")
    addon_config = AddonConfig(logger=logger)
    for mid in addon_config.get_models_ids():
        for t_ord in addon_config.get_templates_ids(mid):
            if addon_config.get_template_state(mid=mid, t_ord=t_ord, key="enabled"):
                statistics = TimeStatistic(logger=logger, add_on_config=addon_config, mid=mid, t_ord=t_ord)
                statistics.update_template_stats()
    if not menu_button_added:
        try:
            addon_gui = GUI(logger=logger, add_on_config=addon_config)
            gui_hooks.profile_did_open.append(addon_gui.add_menu_button)
            menu_button_added = True
            logger.debug("Menu button added successfully.")
        except Exception as e:
            logger.error(f"Failed to add menu button: {e}")
    else:
        logger.debug("Menu button was already added, skipping.")


def profile_will_close():
    global addon_config
    global menu_button_added
    addon_config.__exit__()
    menu_button_added = False


def gui_hook_reviewer_will_init_answer_buttons(buttons_tuple: tuple[bool, Literal[1, 2, 3, 4]], reviewer: Reviewer,
                                               card: Card):
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
    statistics = TimeStatistic(logger=logger, add_on_config=addon_config, mid=mid, t_ord=t_ord)
    statistics.update_template_stats()
    if addon_config.get_template_state(mid=mid, t_ord=t_ord, key="n") < 20:
        logger.debug(f"[{mid_name}][{t_ord_name}] too few elements.")
        reviewer._defaultEase = _default_ease_3
        return buttons_tuple
    ####################################################################################################
    dec_maker = DecisionMaker(logger=logger, add_on_config=addon_config, mid=mid, t_ord=t_ord)
    decision: int = 3
    debug_output = ""
    if c_type in (1, 3) and c_queue in (1, 3):
        learn_mode = addon_config.get_template_state(mid=mid, t_ord=t_ord, key="learn_mode")
        if learn_mode == "3311":
            decision = dec_maker.get_decision_3311(c_time_taken)
        if learn_mode == "3331":
            decision = dec_maker.get_decision_3331(c_time_taken)
        debug_output = f"[{mid_name}][{t_ord_name}] Mode: {learn_mode}, Card time taken: {c_time_taken},"
    if c_type in (0, 2) and c_queue in (0, 2, 4):
        review_mode = addon_config.get_template_state(mid=mid, t_ord=t_ord, key="review_mode")
        if review_mode == "4332":
            decision = dec_maker.get_decision_4332(c_time_taken)
        if review_mode == "4333":
            decision = dec_maker.get_decision_4333(c_time_taken)
        debug_output = f"[{mid_name}][{t_ord_name}] Mode: {review_mode}, Card time taken: {c_time_taken},"
    debug_output += f" card type: {c_type}, card queue: {c_queue}, decision: {decision}"
    logger.debug(debug_output)

    ####################################################################################################
    b1 = (1, 'Again')
    b2 = (2, 'Hard')
    b3 = (3, 'Good')
    b4 = (4, 'Easy')
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


def gui_hook_reviewer_did_answer_card(reviewer: Reviewer, card: Card, ease: Literal[1, 2, 3, 4]):
    logger.debug("#")
    note = card.note()
    mid = str(note.note_type()["id"])  # Words, Grammar, Spelling, etc.
    mid_name: str = addon_config.get_model_state(mid=mid, key="name")
    t_ord = str(card.ord)  # 0,1,2 Type of cards, EN->PL, PL->EN, EN->Write, etc,
    t_ord_name: str = addon_config.get_template_state(mid=mid, t_ord=t_ord, key="name")
    c_type = card.type
    c_queue = card.queue
    if c_type in (1, 3) and c_queue in (1, 3):
        logger_output = f"[LEARN][{mid_name}][{t_ord_name}] User pressed button: {ease}."
    elif c_type in (0, 2) and c_queue in (0, 2, 4):
        logger_output = f"[REVIEW][{mid_name}][{t_ord_name}] User pressed button: {ease}."
    else:
        logger_output = f"Error of type / queue."
    logger_output += f" Auto button was: {reviewer._defaultEase()}"
    logger.info(logger_output)


logger: logging.Logger = initialize_logger()
addon_config: AddonConfig
menu_button_added: bool = False

gui_hooks.profile_did_open.append(gui_hook_profile_did_open)
gui_hooks.reviewer_will_init_answer_buttons.append(gui_hook_reviewer_will_init_answer_buttons)
gui_hooks.reviewer_did_answer_card.append(gui_hook_reviewer_did_answer_card)
gui_hooks.profile_will_close.append(profile_will_close)
