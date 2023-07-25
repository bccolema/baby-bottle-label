from __future__ import annotations

from PIL import ImageFont, ImageDraw, Image
from pathlib import Path
import contextlib
import ast
import re
import string
from typing import Tuple, List, Optional, Union, Literal, Type
import math
import dataclasses
import argparse
import collections
import enum

_IMAGE_MODE = "L"
_IMAGE_BG = 255
_TEXT_FG = 0
_MONO_FONT_NAME: Optional[str] = None
_MONO_FONT_FONT_NAMES = (
    "FreeMono",  # linux
    "DejaVuSansMono",  # linux
    "LiberationMono",  # linux
    "NotoSansMono-Regular",  # linux
    "NotoSansMono",  # linux
    "DejaVuSans",  # linux
    "NotoSans",  # linux
    "consola",  # Win: Consolas
    "cour",  # Win: Courier New
    "lucon",  # Win: Lucida Console
    "arial",  # Win
)
_TALLEST_LETTER: Optional[str] = None


def load_mono_font(size: int = 12) -> ImageFont:
    global _MONO_FONT_NAME
    if _MONO_FONT_NAME is None:
        for font_name in _MONO_FONT_FONT_NAMES:
            try:
                _ = ImageFont.truetype(font_name)
                _MONO_FONT_NAME = font_name
                break
            except OSError:
                continue
        if _MONO_FONT_NAME is None:
            raise TypeError("Could not find default font")
    return ImageFont.truetype(_MONO_FONT_NAME, size=size)


def tallest_letter() -> str:
    global _TALLEST_LETTER
    if _TALLEST_LETTER is None:
        font: ImageFont = load_mono_font(size=16)
        tallest_char = "|"
        # (left, top, right, bottom)
        _, _, _, height = font.getbbox(tallest_char)
        for c in string.printable:
            _, _, _, char_height = font.getsize(c)
            if char_height[0] >= height[0]:
                tallest_char = c
                height = char_height
        _TALLEST_LETTER = tallest_char
    return _TALLEST_LETTER


@dataclasses.dataclass
class PxSize:
    x: int
    y: int


@dataclasses.dataclass
class EmSize:
    x: float
    y: float


def parse_size(text: str) -> Union[PxSize, EmSize]:
    text = text.strip()
    try:
        if m := re.fullmatch(r"(\d+(?:\.\d+)?) *(px|em)?", text, flags=re.I):
            # 7 px
            is_em = m[2].lower() == "em"
            val = float(m[1]) if is_em else int(m[1])
            klass = EmSize if is_em else PxSize
            return klass(val, val)
        if m := re.fullmatch(
            r"(\d+(?:\.\d+)?) *(px|em)?(?: +| *x *)?(\d+(?:\.\d+)?) *(px|em)?",
            text,
            flags=re.I,
        ):
            # 7 14 px
            # 300x400
            # 3px 4px
            is_em = m[4].lower() == "em"
            conv = float if is_em else int
            klass = EmSize if is_em else PxSize
            if m[2] and m[4] != m[2]:
                raise ValueError("Mismatched px/em")
            return klass(conv(m[1]), conv(m[3]))
        if m := re.fullmatch(r"\d+", text):
            val = int(m[0])
            return PxSize(val, val)
        if m := re.fullmatch(r"\d+\.\d+", text):
            val = float(m[0])
            return EmSize(val, val)
    except ValueError as e:
        raise ValueError("Failed to parse size") from e
    raise ValueError("Failed to parse size")


@dataclasses.dataclass
class SizedLine:
    text: str
    size: int = 0
    frozen: bool = False
    _init_size: int = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self._init_size = self.size

    def increment(self) -> None:
        if not self.frozen:
            self.size += 1

    def decrement(self) -> None:
        if not self.frozen and self.size > self._init_size:
            self.size -= 1


@dataclasses.dataclass
class SizedImage:
    width: int
    height: int
    dpi: int
    padding: PxSize | EmSize
    line_padding: PxSize | EmSize
    lines: List[SizedLine]

    def increment(self) -> None:
        for line in self.lines:
            line.increment()

    def decrement(self) -> None:
        for line in self.lines:
            line.decrement()

    def smallest_line(self) -> int:
        # Line with the smallest font size
        return sorted(l.size for l in self.lines)[0]

    def all_frozen(self) -> bool:
        return all(l.frozen for l in self.lines)


def padding_to_px(padding: PxSize | EmSize, font_size: int) -> Tuple[int, int]:
    if isinstance(padding, EmSize):
        small_font = load_mono_font(size=font_size)
        # (left, top, right, bottom)
        _, _, _, height = small_font.bbox(tallest_letter())
        padding_x = int(round((height // 2) * padding.x))
        padding_y = int(round((height // 2) * padding.y))
    else:
        padding_x = padding.x
        padding_y = padding.y

    return padding_x, padding_y


def calc_padding(padding: str, font_size: int) -> int:
    # if isinstance(line_padding, EmSize):
    #     height += height * spec.line_padding.x
    # else:
    #     height += spec.line_padding.x
    pass


def calc_image_overflow_lines(spec: SizedImage) -> Tuple[List[bool], int]:
    overflow = [False for _ in spec.lines]
    # Convert padding to pixel
    padding_x, padding_y = padding_to_px(spec.padding, spec.smallest_line())
    # figure how large each line can be
    per_line_width = spec.width - (padding_x * 2)
    per_line_height = (spec.height - (padding_y * 2)) // len(spec.lines)

    """
    There will be some issues with the last line having extra line-height
    padding for no good reason 
    """

    bbox_total_height = 0
    for i, line in enumerate(spec.lines):
        font = load_mono_font(size=line.size)
        _, _, width, height = font.getbbox(line.text)
        if isinstance(spec.line_padding, EmSize):
            height += height * spec.line_padding.y
        else:
            height += spec.line_padding.y
        bbox_total_height += height
        if width > per_line_width or height > per_line_height:
            overflow[i] = True
    return overflow, bbox_total_height


def draw_image(spec: SizedImage) -> Image:
    im = Image.new(_IMAGE_MODE, (spec.width, spec.height), color=_IMAGE_BG)
    try:
        d = ImageDraw.Draw(im)
        _, padding_y = padding_to_px(spec.padding, spec.smallest_line())
        _, bbox_height = calc_image_overflow_lines(spec)

        # Center vertically
        line_y_start = padding_y + max(0, int((spec.height - bbox_height) // 2))
        print(f"line_y_start {line_y_start}")
        # No need to worry about padding because calc_image_overflow_lines did
        # when it calculated the font. So pin center and use anchor="mt" to align.
        line_x_start = spec.width // 2
        for line in spec.lines:
            font = load_mono_font(line.size)
            d.text(
                (line_x_start, line_y_start),
                line.text,
                fill=_TEXT_FG,
                anchor="mt",
                font=font,
            )
            _, _, _, height = font.getbbox(line.text)
            if isinstance(spec.line_padding, EmSize):
                height += height * spec.line_padding.y
            else:
                height += spec.line_padding.y
            line_y_start += height

        im.show()
    except:
        im.close()
        raise
    return im


def generate_image(
    text: str,
    image_size: PxSize,
    dpi: int,
    padding: PxSize | EmSize,
    line_padding: PxSize | EmSize,
) -> Image:
    spec = SizedImage(
        width=image_size.x,
        height=image_size.y,
        padding=padding,
        dpi=dpi,  # TODO: Not using this are we? Maybe size needs to be 1in 2in 300dpi
        line_padding=line_padding,
        lines=[SizedLine(text=line, size=1) for line in text.split("\n")],
    )
    for outer in range(100):
        if outer != 0:
            spec.increment()
        for i, is_over in enumerate(calc_image_overflow_lines(spec)[0]):
            if is_over:
                spec.lines[i].decrement()
                spec.lines[i].frozen = True
        if spec.all_frozen():
            break

    return draw_image(spec)


@contextlib.contextmanager
def wrap_error(
    msg: str,
    /,
    *error_types: Type[Exception],
    wrapper: Optional[Type[Exception]] = None,
) -> None:
    if 0 == len(error_types):
        error_types = (ValueError,)
    if wrapper is None:
        wrapper = ValueError
    try:
        yield
    except Exception as e:
        if isinstance(e, error_types):
            raise wrapper(msg) from e
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument(
        "--padding",
        "-p",
        default="10px",
        help="Padding around label. (Default: %(default))",
    )
    parser.add_argument(
        "--line-padding",
        "-l",
        default="1em",
        help="Height of each line. (Default %(default))",
    )
    parser.add_argument("--dpi", "-d", default=300, type=int)
    parser.add_argument("--image-size", "-i", default="150x300px")

    args = parser.parse_args()
    with wrap_error("Failed to parse padding"):
        padding = parse_size(args.padding)
    with wrap_error("Failed to parse line padding"):
        line_padding = parse_size(args.line_padding)
    with wrap_error("Failed to parse image size"):
        image_size = parse_size(args.image_size)
    if not isinstance(image_size, PxSize):
        raise TypeError("Image size must be specified in pixels not em")

    im = generate_image(
        # unescape string https://stackoverflow.com/a/57192592
        text=args.text.encode("latin-1", "backslashreplace").decode("unicode-escape"),
        image_size=image_size,
        dpi=args.dpi,
        padding=padding,
        line_padding=line_padding,
    )
    im.close()


#
# image = Image.open("hsvwheel.png")
# draw = ImageDraw.Draw(image)
# txt = "Hello World"
# fontsize = 1  # starting font size
#
# # portion of image width you want text width to be
# img_fraction = 0.50
#
# font = ImageFont.truetype("arial.ttf", fontsize)
# while font.getsize(txt)[0] < img_fraction * image.size[0]:
#     # iterate until the text size is just larger than the criteria
#     fontsize += 1
#     font = ImageFont.truetype("arial.ttf", fontsize)
#
# # optionally de-increment to be sure it is less than criteria
# fontsize -= 1
# font = ImageFont.truetype("arial.ttf", fontsize)
#
# print("final font size", fontsize)
# draw.text((10, 25), txt, font=font)  # put the text on the image
# image.save("hsvwheel_txt.png")  # save it
