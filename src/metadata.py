from PIL import Image


def strip_metadata(image: Image.Image) -> Image.Image:
    clean = Image.new(image.mode, image.size)
    clean.putdata(list(image.getdata()))
    # P-mode pixel values are palette indices, not colors. Copy the palette
    # independently so stripping metadata does not turn indexed images black
    # or let later edits mutate the input image's colors.
    if image.palette is not None:
        clean.putpalette(image.getpalette(image.palette.mode), rawmode=image.palette.mode)
    clean.info = {}
    # PNG/GIF transparency is needed to interpret pixels, unlike descriptive
    # EXIF/text metadata. Preserve both palette alpha and RGB color keys.
    if "transparency" in image.info:
        clean.info["transparency"] = image.info["transparency"]
    return clean
