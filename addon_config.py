from aqt import mw
import logging
from typing import Dict, Any
import os
import json


# TODO: add modi and remove
class AddonConfig:
    def __init__(self, logger: logging.Logger):
        self.logger: logging.Logger = logger
        self.logger.debug("__init__")
        self.raw: Dict[str, Any] = self._load()
        self._init_decks_update()

    def __exit__(self):
        self.logger.debug("__exit__")
        self._save()

    def _load(self):
        self.logger.debug("_load")
        profile_folder = mw.pm.profileFolder()
        config_path = os.path.join(profile_folder, "auto_button_suggestion_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = {}
        return config

    def _save(self):
        self.logger.debug("_save")
        profile_folder = mw.pm.profileFolder()
        config_path = os.path.join(profile_folder, "auto_button_suggestion_config.json")

        with open(config_path, "w") as f:
            json.dump(self.raw, f, indent=4)

    def _init_decks_update(self):
        self.logger.debug("_init_decks_update")
        self._add_new_models()
        # self._save()

    def _add_new_models(self):
        self.logger.debug(f"_add_new_models")
        if "models" not in self.raw:
            self.raw["models"] = {}

        models = mw.col.models.all_names_and_ids()
        for model in models:
            mid = str(model.id)
            if mid not in self.raw["models"] and len(mw.col.find_cards(query=f"mid:{mid}")) > 0:
                self.raw["models"][mid] = {
                    "name": model.name
                }
                self._add_new_templates(mid=mid)

    def _add_new_templates(self, mid: str):
        self.logger.debug(f"_add_new_templates {mid}")
        if "templates" not in self.raw["models"][mid]:
            self.raw["models"][mid]["templates"] = {}
        templates: dict = mw.col.models.get(id=mid)["tmpls"]
        for template in templates:
            t_ord = str(template["ord"])
            if t_ord not in self.raw["models"][mid]["templates"]:
                self.raw["models"][mid]["templates"][t_ord] = {
                    "name": template["name"],
                    "enabled": False,
                    "hard_quantile": 0,
                    "easy_quantile": 0,
                    "median_quantile": 0,
                    "n": 0,
                    "review_mode": "4333",
                    "learn_mode": "3311"
                }

    def get_model_state(self, mid: str, key: str):

        if mid in self.raw["models"] and key in self.raw["models"][mid]:
            value = self.raw["models"][mid][key]
            mid_name = self.raw["models"][mid]["name"]
            self.logger.debug(f"[{mid_name}] get_model_state key {key} value {value}")
            return value
        else:
            self.logger.error(f"[{mid}] get_model_state key {key}")
            return None

    def get_template_state(self, mid: str, t_ord: str, key: str):
        if mid in self.raw["models"] and t_ord in self.raw["models"][mid]["templates"] and key in \
                self.raw["models"][mid]["templates"][t_ord]:
            value = self.raw["models"][mid]["templates"][t_ord][key]
            mid_name = self.raw["models"][mid]["name"]
            t_ord_name = self.raw["models"][mid]["templates"][t_ord]["name"]
            self.logger.debug(f"[{mid_name}][{t_ord_name}] get_template_state key {key} value {value}")
            return value
        else:
            self.logger.error(f"[{mid}][{t_ord}] get_template_state key {key}")
            return None

    def set_template_state(self, mid: str, t_ord: str, key: str, value):
        if mid in self.raw["models"] and t_ord in self.raw["models"][mid]["templates"]:
            self.raw["models"][mid]["templates"][t_ord][key] = value
            # self._save()
            mid_name = self.raw["models"][mid]["name"]
            t_ord_name = self.raw["models"][mid]["templates"][t_ord]["name"]
            self.logger.debug(f"[{mid_name}][{t_ord_name}] set_template_state key {key} value {value}")
        else:
            self.logger.error(f"[{mid}][{t_ord}] set_template_state key {key} value {value}")

    def get_models_ids(self):
        return sorted(list(self.raw["models"].keys()))

    def get_templates_ids(self, mid: str):
        return sorted(list(self.raw["models"][mid]["templates"].keys()))
