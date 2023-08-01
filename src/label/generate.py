from __future__ import annotations

import argparse
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

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


def font_size_for_line(
    text: str, width: int, height: int, line_height_em: float = 1.2
) -> int:
    for i in range(1, 100):
        font = load_mono_font(size=i)
        _, _, line_w, line_h = font.getbbox(text)
        line_h *= line_height_em
        if line_w >= width or line_h >= height:
            return max(1, (i - 1))
    return 100


def generate_image(
    text: List[str],
    image_size: List[int],
    padding: List[int],
    debug: str = "",
) -> Image:
    orig_width, orig_height = image_size

    pad_top, pad_left = padding
    height = orig_height - (pad_top * 2)
    width = orig_width - (pad_left * 2)

    line_height_em = 1.2
    line_count = len(text)
    per_line_height = height // line_count

    im = Image.new(_IMAGE_MODE, (orig_width, orig_height), color=_IMAGE_BG)
    d = ImageDraw.Draw(im)

    if debug and "padding" in debug:
        # Draw padding lines
        d.line(((pad_left, 0), (pad_left, orig_height)))
        d.line(((0, pad_top), (orig_width, pad_top)))

    for i, line in enumerate(text):
        font_size = font_size_for_line(
            line, width=width, height=per_line_height, line_height_em=line_height_em
        )
        font = load_mono_font(size=font_size)

        # Calc top left of text box
        text_x = pad_left + (width // 2)
        text_y = pad_top + (per_line_height * i) + (per_line_height // 2)

        if debug:
            if "box" in debug:
                # line box
                tt = pad_top + (per_line_height * i)
                d.rectangle(
                    ((pad_left, tt), (orig_width - pad_left, tt + per_line_height))
                )
            if "center" in debug:
                # Center
                yy = pad_top + (per_line_height * i) + (per_line_height // 2)
                d.line(((0, yy), (orig_width, yy)))

            zz = pad_top + (per_line_height * i) + (per_line_height // 2)
            d.line(((0, zz), (orig_width, zz)), fill=127)

        d.text(
            (
                text_x,
                text_y,
            ),
            line,
            fill=_TEXT_FG,
            font=font,
            align="center",
            anchor="mm",
        )
    return im


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("output")
    parser.add_argument(
        "--padding",
        "-p",
        default=[10, 10],
        nargs=2,
        type=int,
        help="Padding around label in pixels (Default: %(default)s)",
    )
    parser.add_argument(
        "--image-size",
        "-i",
        nargs=2,
        default=[300, 150],
        type=int,
        help="Size in pixels. (Default %(default)s)",
    )
    parser.add_argument("--show", action="store_true")

    args = parser.parse_args()
    if 2 != len(args.padding):
        raise ValueError("padding takes 2 args")
    if 2 != len(args.image_size):
        raise ValueError("image-size takes 2 args")

    im = generate_image(
        # unescape string https://stackoverflow.com/a/57192592
        text=(
            args.text.encode("latin-1", "backslashreplace")
            .decode("unicode-escape")
            .split("\n")
        ),
        image_size=args.image_size,
        padding=args.padding,
    )
    im.save(args.output)
    if args.show:
        im.show()


if __name__ == "__main__":
    main()
