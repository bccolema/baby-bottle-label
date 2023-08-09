from __future__ import annotations

import configparser
import dataclasses
from typing import List, TypeVar, Type, Any

T = TypeVar("T")


@dataclasses.dataclass
class Config:
    host: str
    port: int
    debug: bool
    baby_name: str
    baby_name_twice: bool
    alexa_app_id: List[str]
    label_size: List[float]  # Inches
    padding: List[int]  # Pixels
    printer_name: str

    def __post_init__(self) -> None:
        # Ensure debug is bool
        if not isinstance(self.debug, bool):
            if isinstance(self.debug, str):
                self.debug = self.debug.lower() in ("1", "true", "yes")
            else:
                self.debug = False

        self.alexa_app_id = self._flat_str_list(self.alexa_app_id)
        self.label_size = self._to_list(self.label_size, float)
        assert len(self.label_size) == 2
        self.padding = self._to_list(self.padding, int)
        assert len(self.padding) == 4
        self.port = int(self.port)

    @classmethod
    def _to_list(cls, value: Any, class_: Type[T]) -> List[T]:
        if value is None:
            return []
        elif isinstance(value, str):
            value = [class_(i) for vs in value.split() for i in vs.split(",")]
        elif isinstance(value, class_):
            value = [value]
        if not isinstance(value, list):
            raise TypeError("Unexpected type")
        return [class_(v) for v in value]

    @classmethod
    def _flat_str_list(cls, seq) -> List[str]:
        if isinstance(seq, str):
            return [seq]
        if not isinstance(seq, list):
            return []
        new_list = []
        for item in seq:
            new_list.extend(cls._flat_str_list(item))
        return new_list

    @classmethod
    def read_ini(cls, ini: str) -> dict:
        parser = configparser.ConfigParser()
        try:
            parser.read(ini)
        except configparser.MissingSectionHeaderError:
            # Add a section for the ini file without a section
            with open(ini, "r") as f:
                ini_contents = "[whatever]\n" + f.read()
            parser = configparser.ConfigParser()
            parser.read_string(ini_contents, source=str(ini))
        config = dict()
        for name in parser.sections():
            config.update(parser[name])
        if not config:
            config.update(parser.defaults())
        return config


DEFAULT = Config(
    host="0.0.0.0",
    port=7788,
    debug=False,
    baby_name="",
    baby_name_twice=True,
    alexa_app_id=[],
    # label_size=[2, 0.75],
    # padding=[10, 10, 10, 10],
    # Seems the printer driver picks a known size close enough when a custom
    # size is specified. In order to print a 1x2in label we print a 2x2in with
    # 300px (for 300dpi) bottom padding to offset this.
    label_size=[2, 2],
    padding=[10, 10, 300, 100],
    printer_name="dymo450",
)
