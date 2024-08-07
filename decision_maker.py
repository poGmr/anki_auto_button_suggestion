import logging
from .addon_config import AddonConfig


class DecisionMaker:
    def __init__(self, logger: logging.Logger, add_on_config: AddonConfig, mid: str, t_ord: str):
        self.logger: logging.Logger = logger
        self.add_on_config: AddonConfig = add_on_config
        self.mid: str = mid
        self.mid_name: str = self.add_on_config.get_model_state(mid=self.mid, key="name")
        self.t_ord: str = t_ord
        self.t_ord_name: str = self.add_on_config.get_template_state(mid=self.mid, t_ord=self.t_ord, key="name")

    def get_decision(self, c_time_taken: int, c_type: int, c_queue: int):
        easy_quantile = self.add_on_config.get_template_state(mid=self.mid, t_ord=self.t_ord, key="easy_quantile")
        hard_quantile = self.add_on_config.get_template_state(mid=self.mid, t_ord=self.t_ord, key="hard_quantile")
        decision: int = 0
        if c_type in (0, 2) and c_queue in (0, 2, 4):
            if c_time_taken > hard_quantile:
                decision = 2
            if easy_quantile <= c_time_taken <= hard_quantile:
                decision = 3
            if c_time_taken < easy_quantile:
                decision = 4

        if c_type in (1, 3) and c_queue in (1, 3):
            if c_time_taken > hard_quantile:
                decision = 1
            if c_time_taken <= hard_quantile:
                decision = 3

        debug_output = f"[{self.mid_name}][{self.t_ord_name}] Card time taken: {c_time_taken},"
        debug_output += f" card type: {c_type}, card queue: {c_queue}, decision: {decision}"
        self.logger.debug(debug_output)
        return decision
