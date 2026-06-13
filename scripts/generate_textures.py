from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
TEXTURES = ROOT / "assets" / "textures"


class Mulberry32:
    def __init__(self, seed):
        self.seed = seed & 0xFFFFFFFF

    def __call__(self):
        self.seed = (self.seed + 0x6D2B79F5) & 0xFFFFFFFF
        value = self.seed
        value = ((value ^ (value >> 15)) * (1 | value)) & 0xFFFFFFFF
        value = (
            value
            + (((value ^ (value >> 7)) * (61 | value)) & 0xFFFFFFFF)
        ) & 0xFFFFFFFF
        value ^= value >> 14
        return (value & 0xFFFFFFFF) / 4294967296


def rgba_draw(image):
    return ImageDraw.Draw(image, "RGBA")


def ellipse_box(x, y, rx, ry):
    return (x - rx, y - ry, x + rx, y + ry)


def save(image, group, name):
    directory = TEXTURES / group
    directory.mkdir(parents=True, exist_ok=True)
    image.save(directory / name, optimize=True)


def draw_polyline(draw, points, fill, width):
    draw.line(points, fill=fill, width=max(1, round(width)), joint="curve")


def quadratic_points(p0, p1, p2, count=16):
    points = []
    for index in range(count + 1):
        t = index / count
        inv = 1 - t
        points.append(
            (
                inv * inv * p0[0] + 2 * inv * t * p1[0] + t * t * p2[0],
                inv * inv * p0[1] + 2 * inv * t * p1[1] + t * t * p2[1],
            )
        )
    return points


def generate_ground():
    size = 512
    color = Image.new("RGB", (size, size), "#24180d")
    bump = Image.new("RGB", (size, size), "#777777")
    rough = Image.new("RGB", (size, size), "#eeeeee")
    color_draw = rgba_draw(color)
    bump_draw = rgba_draw(bump)
    rough_draw = rgba_draw(rough)
    rng = Mulberry32(101)

    for _ in range(190):
        x, y = rng() * size, rng() * size
        radius = 10 + rng() * 44
        light = 18 + rng() * 24
        fill = (
            int(light + 18),
            int(light + 7),
            int(light * 0.45),
            int((0.04 + rng() * 0.08) * 255),
        )
        color_draw.ellipse(ellipse_box(x, y, radius, radius), fill=fill)

    for _ in range(5200):
        x, y = rng() * size, rng() * size
        grain_size = 0.45 + rng() * rng() * 3.2
        light = rng()
        alpha = int((0.28 + rng() * 0.48) * 255)
        box = (x, y, x + grain_size * 1.5, y + grain_size)
        color_draw.rectangle(
            box,
            fill=(
                int(35 + light * 58),
                int(24 + light * 40),
                int(13 + light * 25),
                alpha,
            ),
        )
        height = int(90 + light * 110)
        bump_draw.rectangle(
            (x, y, x + grain_size * 1.6, y + grain_size),
            fill=(height, height, height, 255),
        )
        roughness = int(205 + rng() * 50)
        rough_draw.rectangle(
            (x, y, x + grain_size * 1.6, y + grain_size),
            fill=(roughness, roughness, roughness, 255),
        )

    for _ in range(120):
        x, y = rng() * size, rng() * size
        rx, ry = 1.5 + rng() * 4.5, 0.8 + rng() * 2.2
        color_draw.ellipse(
            ellipse_box(x, y, rx, ry),
            fill=(
                int(70 + rng() * 45),
                int(57 + rng() * 32),
                int(40 + rng() * 22),
                184,
            ),
        )
        bump_draw.ellipse(ellipse_box(x, y, rx, ry), fill=(210, 210, 210, 255))

    save(color, "ground", "albedo.png")
    save(bump, "ground", "bump.png")
    save(rough, "ground", "roughness.png")


def generate_rock():
    size = 256
    color = Image.new("RGB", (size, size), "#c2bbb0")
    bump = Image.new("RGB", (size, size), "#888888")
    rough = Image.new("RGB", (size, size), "#f2f2f2")
    color_draw = rgba_draw(color)
    bump_draw = rgba_draw(bump)
    rng = Mulberry32(303)

    for _ in range(680):
        x, y = rng() * size, rng() * size
        radius = 0.8 + rng() * rng() * 8
        value = int(125 + rng() * 95)
        color_draw.ellipse(
            ellipse_box(x, y, radius, radius),
            fill=(
                value,
                value - 5,
                value - 12,
                int((0.08 + rng() * 0.28) * 255),
            ),
        )
        height = int(78 + rng() * 120)
        bump_draw.ellipse(
            ellipse_box(x, y, radius * 0.8, radius * 0.8),
            fill=(
                height,
                height,
                height,
                int((0.25 + rng() * 0.5) * 255),
            ),
        )

    for _ in range(16):
        x, y = rng() * size, rng() * size
        color_points = [(x, y)]
        bump_points = [(x, y)]
        color_alpha = int((0.12 + rng() * 0.18) * 255)
        bump_alpha = int((0.2 + rng() * 0.25) * 255)
        width = 0.7 + rng() * 1.6
        for _ in range(5):
            x += (rng() - 0.5) * 34
            y += 7 + rng() * 22
            color_points.append((x, y))
            bump_points.append((x, y))
        draw_polyline(
            color_draw, color_points, (220, 214, 202, color_alpha), width
        )
        draw_polyline(
            bump_draw, bump_points, (205, 205, 205, bump_alpha), width
        )

    save(color, "rock", "albedo.png")
    save(bump, "rock", "bump.png")
    save(rough, "rock", "roughness.png")


def generate_bark():
    width, height = 256, 512
    color = Image.new("RGB", (width, height), "#412615")
    bump = Image.new("RGB", (width, height), "#858585")
    rough = Image.new("RGB", (width, height), "#ededed")
    color_draw = rgba_draw(color)
    bump_draw = rgba_draw(bump)
    rough_draw = rgba_draw(rough)
    rng = Mulberry32(707)

    x0 = -4.0
    while x0 < width + 8:
        shade = int(28 + rng() * 35)
        line_width = 1.2 + rng() * 3.2
        color_alpha = int((0.45 + rng() * 0.35) * 255)
        bump_alpha = int((0.35 + rng() * 0.45) * 255)
        rough_alpha = int((0.25 + rng() * 0.4) * 255)
        x = x0
        points = [(x0, -8)]
        y = 0
        while y <= height + 12:
            x += (rng() - 0.5) * 4.5
            points.append((x, y))
            y += 18
        draw_polyline(
            color_draw,
            points,
            (shade + 20, shade + 7, shade, color_alpha),
            line_width,
        )
        draw_polyline(
            bump_draw, points, (35, 35, 35, bump_alpha), line_width * 0.75
        )
        draw_polyline(
            rough_draw, points, (255, 255, 255, rough_alpha), line_width
        )
        x0 += 6 + rng() * 6

    for _ in range(110):
        x, y = rng() * width, rng() * height
        length = 3 + rng() * 17
        color_alpha = int((0.28 + rng() * 0.45) * 255)
        bump_alpha = int((0.25 + rng() * 0.5) * 255)
        line_width = 0.6 + rng() * 1.4
        control_y = y + (rng() - 0.5) * 5
        end_y = y + (rng() - 0.5) * 3
        points = quadratic_points(
            (x - length / 2, y), (x, control_y), (x + length / 2, end_y)
        )
        draw_polyline(
            color_draw, points, (18, 8, 3, color_alpha), line_width
        )
        draw_polyline(
            bump_draw, points, (30, 30, 30, bump_alpha), line_width
        )

    for _ in range(70):
        x = rng() * width
        y = rng() * height
        color_alpha = int((0.12 + rng() * 0.18) * 255)
        bump_alpha = int((0.18 + rng() * 0.24) * 255)
        line_width = 0.5 + rng() * 1.1
        points = [(x, y)]
        for _ in range(4):
            y += 12 + rng() * 30
            dx = (rng() - 0.5) * 5
            points.append((x + dx, y))
        draw_polyline(
            color_draw,
            points,
            (
                int(105 + rng() * 35),
                int(58 + rng() * 24),
                int(27 + rng() * 15),
                color_alpha,
            ),
            line_width,
        )
        draw_polyline(
            bump_draw, points, (210, 210, 210, bump_alpha), line_width
        )

    for _ in range(10):
        x, y = rng() * width, rng() * height
        rx, ry = 5 + rng() * 11, 2 + rng() * 5
        color_draw.ellipse(
            ellipse_box(x, y, rx, ry),
            outline=(20, 8, 3, 184),
            width=max(1, round(2 + rng() * 2)),
        )
        bump_draw.ellipse(
            ellipse_box(x, y, rx * 0.72, ry * 0.72),
            fill=(74, 74, 74, 255),
        )

    save(color, "bark", "albedo.png")
    save(bump, "bark", "bump.png")
    save(rough, "bark", "roughness.png")


def generate_char():
    width, height = 256, 512
    color = Image.new("RGB", (width, height), "#100b09")
    bump = Image.new("RGB", (width, height), "#777777")
    emissive = Image.new("RGB", (width, height), "#000000")
    color_draw = rgba_draw(color)
    bump_draw = rgba_draw(bump)
    emissive_draw = rgba_draw(emissive)
    rng = Mulberry32(909)

    for _ in range(950):
        value = int(12 + rng() * 42)
        x, y = rng() * width, rng() * height
        size = 0.5 + rng() * 2.4
        color_draw.rectangle(
            (x, y, x + size, y + size),
            fill=(
                value + 8,
                value,
                value - 2,
                int((0.18 + rng() * 0.42) * 255),
            ),
        )

    for _ in range(38):
        x, y = rng() * width, rng() * height
        line_width = 0.7 + rng() * 1.4
        color_alpha = int((0.35 + rng() * 0.45) * 255)
        emissive_alpha = int((0.45 + rng() * 0.5) * 255)
        emissive_green = int(105 + rng() * 95)
        points = [(x, y)]
        steps = 3 + rng() * 5
        index = 0
        while index < steps:
            x += (rng() - 0.5) * 18
            y += 7 + rng() * 20
            points.append((x, y))
            index += 1
        draw_polyline(
            color_draw, points, (78, 27, 8, color_alpha), line_width
        )
        draw_polyline(
            bump_draw, points, (25, 25, 25, 191), line_width
        )
        draw_polyline(
            emissive_draw,
            points,
            (255, emissive_green, 40, emissive_alpha),
            line_width,
        )

    save(color, "char", "albedo.png")
    save(bump, "char", "bump.png")
    save(emissive, "char", "emissive.png")


def main():
    generate_ground()
    generate_rock()
    generate_bark()
    generate_char()
    print(f"Generated textures in {TEXTURES}")


if __name__ == "__main__":
    main()
