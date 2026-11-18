"""Compression des photos à l'upload (M5).

Spec : « Photos : redimensionnées côté serveur (~1600 px, JPEG
qualité correcte) pour contenir le poids du stockage et des
sauvegardes. » Pillow fait le travail, l'orientation EXIF des
photos de téléphone est appliquée, l'original n'est pas conservé.
"""
from io import BytesIO

from PIL import Image, ImageOps
from django.core.files.base import ContentFile

#: Côté maximal (pixels) de la plus grande dimension.
COTE_MAX = 1600
#: Qualité JPEG au réenregistrement.
QUALITE_JPEG = 85


def compresser_photo(fichier):
    """Redimensionne (côté max 1600 px, jamais agrandie), aplatit sur
    fond blanc et recompresse en JPEG qualité 85 (spec). Renvoie un
    ContentFile prêt pour un ImageField ; un fichier illisible passe
    tel quel, c'est le champ ImageField du formulaire qui jugera."""
    try:
        image = Image.open(fichier)
        image.load()
    except Exception:
        fichier.seek(0)
        return fichier

    image = ImageOps.exif_transpose(image) or image
    if image.mode != "RGB":
        calque = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode in ("RGBA", "LA"):
            calque.paste(image, mask=image.getchannel("A"))
        else:
            calque.paste(image.convert("RGB"))
        image = calque

    if max(image.size) > COTE_MAX:
        rapport = COTE_MAX / max(image.size)
        image = image.resize(
            (
                max(1, round(image.width * rapport)),
                max(1, round(image.height * rapport)),
            ),
            Image.Resampling.LANCZOS,
        )

    tampon = BytesIO()
    image.save(tampon, format="JPEG", quality=QUALITE_JPEG, optimize=True)
    return ContentFile(tampon.getvalue(), name="photo.jpg")
