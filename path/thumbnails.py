import os

from imagekit import ImageSpec, register
from imagekit.processors import (
    MakeOpaque,
    ResizeToCover,
    Thumbnail,
    TrimBorderColor,
)
from imagekit.utils import get_field_info

from django.conf import settings

# JPEG options
# ------------
#
# Recommendations
# https://developers.google.com/speed/docs/insights/OptimizeImages
#
# Options
# http://pillow.rtfd.org/en/latest/handbook/image-file-formats.html#jpeg
#
# RGB
# Images are converted to RGB by MakeOpaque
#
# EXIF data
# Should be removed by saving the resized image TODO test
# See https://stackoverflow.com/a/19786636
#
# Retina
# 2 x or 3 x of standard pixels
#
# Set DPI or not?
# "If you import it into Microsoft Word for example,
# it will scale the image to be the size implied by the DPI
# when measured on the printed page."
# Source: https://graphicdesign.stackexchange.com/a/29768
#
# Standard DPI
# https://en.wikipedia.org/wiki/Dots_per_inch#Proposed_metrication
#
# Different versions in HTML
# <img src="low-res.jpg" srcset="medium-res.jpg 1.5x, high-res.jpg 2x">
# Source: https://stackoverflow.com/a/43823483
# https://html.com/attributes/img-srcset/
#
# High Resolution
# https://developer.apple.com/high-resolution/

USER_AVATAR = {
    'processors': [
        TrimBorderColor(),
        ResizeToCover(width=600, height=600, upscale=False),
        MakeOpaque((255, 255, 255)),
    ],
    'options': {
        'quality': 85,  # default is 75
        'dpi': (72, 72),
        'optimize': True,
        'subsampling': 2,  # equivalent to 4:2:0
    },
}


class UserThumbnail(ImageSpec):
    """
    Create thumbnail based on the size or model fields.
    """

    format = 'JPEG'
    options = {
        # 'quality': 85,
        'dpi': (72, 72),
        'optimize': True,
        # Assumes the original image has the correct subsampling
    }

    @property
    def processors(self):
        model, field_name = get_field_info(self.source)
        # if model.avatar_crop:
        #     # TODO Resize and corp accordingly
        #     raise NotImplementedError()
        # else:
        return [Thumbnail(width=self.size, height=self.size)]


#    # https://github.com/matthewwithanm/django-imagekit/issues/256
#    # #issuecomment-25442264
#    @property
#    def cachefile_name(self):
#        """
#        Create path in the from <source_path>/<img_name>/<width>x<hight>.jpg.
#        """
#        if not self.source.name:
#            # No source image
#            return
#        path = os.path.normpath(os.path.join(
#            settings.IMAGEKIT_CACHEFILE_DIR,
#            os.path.splitext(self.source.name)[0],
#            '{size}x{size}.jpg'.format(size=self.size),
#        ))
#        return path


# Using curry doesn't work
class UserThumbnail60(UserThumbnail):
    size = 60


class UserThumbnail120(UserThumbnail):
    size = 120


class UserThumbnail300(UserThumbnail):
    size = 300


register.generator('path:thumbnails:user_thumbnail_60', UserThumbnail60)
register.generator('path:thumbnails:user_thumbnail_120', UserThumbnail120)
register.generator('path:thumbnails:user_thumbnail_300', UserThumbnail300)


def source_name_as_path_with_sizes(generator):
    """
    A namer that uses the source path, width and hight to build the path.

    path/to/img_erwe34k.jpg
    will generate
    path/to/chached/images/path/to/img_erwe34k/<width>x<height>.jpg
    """
    path = os.path.join(
        settings.IMAGEKIT_CACHEFILE_DIR,
        os.path.splitext(generator.source.name)[0],
        '{size}x{size}.jpg'.format(size=generator.size),
    )
    return os.path.normpath(path)
