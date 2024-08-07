from statistics import quantiles, mean, mode, median
import logging
from .addon_config import AddonConfig
from aqt import mw


class TimeStatistic:
    def __init__(self, logger: logging.Logger, add_on_config: AddonConfig, mid: str, t_ord: str):
        self.logger: logging.Logger = logger
        self.add_on_config: AddonConfig = add_on_config
        self.mid: str = mid
        self.mid_name: str = self.add_on_config.get_model_state(mid=self.mid, key="name")
        self.t_ord: str = t_ord
        self.t_ord_name: str = self.add_on_config.get_template_state(mid=self.mid, t_ord=self.t_ord, key="name")
        self.raw_times: list[int] = self._get_template_times()
        self.raw_times_n: int = len(self.raw_times)
        self._debug_before_clean_up()
        self.clean_times: list[int] = self._create_clean_up_times()
        self.clean_times_n: int = len(self.clean_times)
        self.add_on_config.set_template_state(mid=self.mid, t_ord=self.t_ord, key="n", value=self.clean_times_n)
        self._debug_after_clean_up()
        self.hard_quantile, self.median_quantile, self.easy_quantile = self._get_quantiles()

    def _get_template_times(self) -> list[int]:
        query: str = f"""
                SELECT revlog.time
                FROM revlog
                JOIN cards ON revlog.cid=cards.id
                JOIN notes ON cards.nid=notes.id
                WHERE notes.mid='{self.mid}' AND
                cards.ord='{self.t_ord}' AND
                revlog.ease>'0' AND
                revlog.type='1'
                """
        result = sorted(mw.col.db.list(query))
        if result is None:
            return []
        return result

    def _debug_before_clean_up(self):
        if self.raw_times_n < 1:
            self.logger.debug(f"[{self.mid_name}][{self.t_ord_name}] _debug_before_clean_up - empty list.")
            return
        debug_output = f"[{self.mid_name}][{self.t_ord_name}] Before clean up: "
        debug_output += f"n {self.raw_times_n} "
        debug_output += f"min {min(self.raw_times)} "
        debug_output += f"mean {round(mean(self.raw_times))} "
        debug_output += f"mode {mode(self.raw_times)} "
        debug_output += f"median {round(median(self.raw_times))} "
        debug_output += f"max {max(self.raw_times)}"
        self.logger.debug(debug_output)

    def _debug_after_clean_up(self):
        if self.raw_times_n < 1:
            self.logger.debug(f"[{self.mid_name}][{self.t_ord_name}] _debug_after_clean_up - empty list.")
            return
        debug_output = f"[{self.mid_name}][{self.t_ord_name}] After clean up: "
        debug_output += f"n {self.clean_times_n} "
        debug_output += f"min {min(self.clean_times)} "
        debug_output += f"mean {round(mean(self.clean_times))} "
        debug_output += f"mode {mode(self.clean_times)} "
        debug_output += f"median {round(median(self.clean_times))} "
        debug_output += f"max {max(self.clean_times)}"
        self.logger.debug(debug_output)

    def _create_clean_up_times(self) -> list[int]:
        if self.raw_times_n < 1:
            self.logger.debug(f"[{self.mid_name}][{self.t_ord_name}] _clean_up_times - empty list.")
            return []
        first_5_per = int(0.05 * self.raw_times_n)
        last_5_per = int(0.95 * self.raw_times_n)
        return self.raw_times[first_5_per:last_5_per]

    def _get_quantiles(self) -> tuple[int, int, int]:
        if self.clean_times_n < 1:
            self.logger.debug(f"[{self.mid_name}][{self.t_ord_name}] _get_quantiles - empty list.")
            return 0, 0, 0
        quantiles_times = [round(q) for q in quantiles(self.clean_times, n=4)]
        hard_quantile = quantiles_times[2]
        median_quantile = quantiles_times[1]
        easy_quantile = quantiles_times[0]
        self.logger.debug(f"[{self.mid_name}][{self.t_ord_name}] quantiles_times: {quantiles_times}")
        return hard_quantile, median_quantile, easy_quantile

    def update_template_stats(self):
        self.add_on_config.set_template_state(mid=self.mid, t_ord=self.t_ord, key="hard_quantile",
                                              value=self.hard_quantile)
        self.add_on_config.set_template_state(mid=self.mid, t_ord=self.t_ord, key="median_quantile",
                                              value=self.median_quantile)
        self.add_on_config.set_template_state(mid=self.mid, t_ord=self.t_ord, key="easy_quantile",
                                              value=self.easy_quantile)
