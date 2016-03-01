import random

import wheezy.captcha.image
from PIL import Image
from PIL.ImageColor import getrgb
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype


def captcha_text(fonts, font_sizes=None, drawings=None, color='#5C87B2',
                 squeeze_factor=0.8):
    fonts = tuple([truetype(name, size)
                   for name in fonts
                   for size in font_sizes or (65, 70, 75)])
    if not callable(color):
        c = getrgb(color)
        color = lambda: c

    def drawer(image, text):
        draw = Draw(image)
        char_images = []
        for c in text:
            font = random.choice(fonts)
            c_width, c_height = draw.textsize(c, font=font)
            c_height *= 2
            char_image = Image.new('RGB', (c_width, c_height), (0, 0, 0))
            char_draw = Draw(char_image)
            char_draw.text((0, 0), c, font=font, fill=color())
            char_image = char_image.crop(char_image.getbbox())
            for drawing in drawings:
                char_image = drawing(char_image)
            char_images.append(char_image)
        width, height = image.size
        offset = int((width - sum(int(i.size[0] * squeeze_factor)
                                  for i in char_images[:-1])
                      - char_images[-1].size[0]) / 2)
        for char_image in char_images:
            c_width, c_height = char_image.size
            mask = char_image.convert('L').point(lambda i: i * 1.97)
            image.paste(char_image,
                        (offset, int((height - c_height) / 2)),
                        mask)
            offset += int(c_width * squeeze_factor)
        return image
    return drawer

captcha_image = wheezy.captcha.image.captcha(drawings=[
    wheezy.captcha.image.background(),
    captcha_text(
        fonts=['fonts/Courier New Bold.ttf'],
        drawings=[wheezy.captcha.image.warp(),
                  wheezy.captcha.image.rotate(),
                  wheezy.captcha.image.offset()],
        font_sizes=(24, 26, 28), squeeze_factor=1.0),
    wheezy.captcha.image.curve(width=1),
    wheezy.captcha.image.curve(width=1),
    wheezy.captcha.image.curve(width=1),
    wheezy.captcha.image.noise(number=2),
], width=100, height=34)


captcha_clear_image = wheezy.captcha.image.captcha(drawings=[
    wheezy.captcha.image.background(),
    captcha_text(
        fonts=['fonts/Courier New Bold.ttf'],
        drawings=[wheezy.captcha.image.offset()],
        font_sizes=(24, 26, 28), squeeze_factor=1.0),
], width=100, height=34)
