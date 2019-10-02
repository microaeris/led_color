#!usr/bin/python
'''
Goal of this script is to convert colors from a commonly used color space
(sRBG) to one that can be used with additive color mixing.

Note to self, to test, use FFFFF as the input hex color.
Expected XYZ: D65 White Point (x,y): 0.3128, 0.3292
Expected color mixing ratio: 0.7348:1.53696:0.265
And use these primaries:
    PRIMARY_RED_X = 0.67
    PRIMARY_RED_Y = 0.33
    PRIMARY_GREEN_X = 0.21
    PRIMARY_GREEN_Y = 0.71
    PRIMARY_BLUE_X = 0.14
    PRIMARY_BLUE_Y = 0.08
'''

import numpy
import argparse
import binascii
import struct

# Converted the dominant wavelengths of my RGB LEDs, given in datasheet, into
# CIE chromaticity coordinates using an online converter.
# https://www.ledtuning.nl/en/cie-convertor
#
# Typical dominant wavelengths
#   * Red: 625 nm
#   * Green: 530 nm
#   * Blue: 475 nm
PRIMARY_RED_X = 0.700606061
PRIMARY_RED_Y = 0.299300699
PRIMARY_GREEN_X = 0.154722061
PRIMARY_GREEN_Y = 0.805863545
PRIMARY_BLUE_X = 0.109594324
PRIMARY_BLUE_Y = 0.08684251

# Typical luminous intensity, from LED datasheet. In candela.
RED_LUMINOUS_INTENSITY = 0.105
GREEN_LUMINOUS_INTENSITY = 0.330
BLUE_LUMINOUS_INTENSITY = 0.200

MAX_8_BIT = 0xFF

# Inverse Companding Constants
COMPAND_V_MIN = 0.04045
COMPAND_A = 12.92
COMPAND_B = 0.055
COMPAND_C = 1.055
COMPAND_POW = 2.4
COMPAND_MAGIC_NUM = 100

# This transformation matrix is calculated from the sRGB reference primaries.
# Source: http://www.brucelindbloom.com/index.html?Math.html
RGB_TO_XYZ = numpy.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041]
])


def inverse_companding(v):
    '''Inverse companding of a single color channel.
    Literally no idea how this works. Copied and pasted from the net...
    '''
    if v <= COMPAND_V_MIN:
        v = v / COMPAND_A
    else:
        v = pow(((v + COMPAND_B) / COMPAND_C), COMPAND_POW)
    return v


def rgb_to_xyz(red, green, blue):
    '''Convert sRGB to CIE 1931 XYZ color space.

    Source
        * https://www.easyrgb.com/en/math.php
        * http://www.brucelindbloom.com/index.html?Math.html

    :param red: Value for red, 0-255
    :type red: int
    :param green: Value for green, 0-255
    :type green: int
    :param blue: Value for blue, 0-255
    :type blue: int
    :return: 3x1 matrix representing the color in XYZ
    :type: numpy array
    '''

    rgb_arr = numpy.array([[red], [green], [blue]])
    rgb_arr = rgb_arr.astype(float)

    # Normalize RGB values
    rgb_arr = numpy.divide(rgb_arr, MAX_8_BIT)

    # Inverse sRGB Companding
    for i, v in enumerate(rgb_arr):
        rgb_arr[i] = inverse_companding(v) * COMPAND_MAGIC_NUM

    # Convert to CIE 1931 XYZ color space
    return numpy.dot(RGB_TO_XYZ, rgb_arr)


def xyz_to_xyy(xyz):
    '''Convert CIE 1931 XYZ to CIE 1931 xyY, a much more sane color space.
    xyY is the color space with the 2D chromaticity diagram you see everywhere.

    Conversion:
        x = X / (X+Y+Z)
        y = Y / (X+Y+Z)
        Y = Y
    '''
    x = xyz[0] / numpy.sum(xyz)
    y = xyz[1] / numpy.sum(xyz)
    luminance = xyz[1]
    return numpy.array([x, y, luminance])


def calc_ratio_of_mixtures(y1, y2, y3):
    '''Returns ratio of y1 to y2 at y3.
    y1 and y2 are the extremes. Y3 is the midpoint between the two.

    Ratio of mixtures formula
        R = -(y2/y1) * (y1-y3) / (y2-y3).
    '''
    return (((-1 * (y2 / y1)) * (y1 - y3)) / (y2 - y3))


def xyy_to_rgb_mixing_ratio(cie_xyy):
    '''Calculate RGB color mixing values using the center of gravity method

    :param cie_xyy: xyY color coordinate to describe the target color.
                    (x, y, Y).
    '''
    # Line between red and blue in the 2D CIE 1931 xyY color space
    slope_rb = (PRIMARY_RED_Y - PRIMARY_BLUE_Y) / \
        (PRIMARY_RED_X - PRIMARY_BLUE_X)
    const_rb = PRIMARY_BLUE_Y - (slope_rb * PRIMARY_BLUE_X)

    # Line between green and target color (D)
    slope_gd = (PRIMARY_GREEN_Y - cie_xyy.item(1)) / \
        (PRIMARY_GREEN_X - cie_xyy.item(0))
    # There was a typo in the article
    # const_gd = PRIMARY_GREEN_Y - (slope_gd * cie_xyy[0])
    const_gd = PRIMARY_GREEN_Y - (slope_gd * PRIMARY_GREEN_X)

    # Find interception point between the two lines
    purple_x = (const_rb - const_gd) / (slope_gd - slope_rb)
    purple_y = (slope_rb * purple_x) + const_rb

    # Calculate color ratio
    # Blue to red ratio to create purple
    ratio_br = calc_ratio_of_mixtures(PRIMARY_BLUE_Y, PRIMARY_RED_Y, purple_y)
    # Purple to green ratio to create the target color
    ratio_pg = calc_ratio_of_mixtures(purple_y, PRIMARY_GREEN_Y,
                                      cie_xyy.item(1))

    # Fraction of the red ratio required to produce the purple color
    red_fraction = (ratio_br / (ratio_br + 1.0))
    # Fraction of the blue ratio required to produce the purple color
    blue_fraction = (1.0 / (ratio_br + 1.0))

    # Normalize on blue
    red_ratio = red_fraction / blue_fraction
    green_ratio = ratio_pg / blue_fraction
    blue_ratio = blue_fraction / blue_fraction

    return (red_ratio, green_ratio, blue_ratio)


def print_result(color_mixing_ratio, rgb_percentages, rgb_intensities):
    # Calculate relative luminous intensities
    red_intensity_percent = (rgb_intensities[0] / RED_LUMINOUS_INTENSITY) * 100
    green_intensity_percent = (rgb_intensities[1] / GREEN_LUMINOUS_INTENSITY) \
        * 100
    blue_intensity_percent = (rgb_intensities[2] / BLUE_LUMINOUS_INTENSITY) \
        * 100

    print '\t\t\tRed \t\tGreen \t\tBlue'
    print 'Mix Ratio: \t\t%.3f \t\t%.3f \t\t%.3f' % (color_mixing_ratio[0],
                                                     color_mixing_ratio[1],
                                                     color_mixing_ratio[2])
    print 'Mix Ratio %%: \t\t%d%% \t\t%d%% \t\t%d%%' % (
        rgb_percentages[0] * 100,
        rgb_percentages[1] * 100,
        rgb_percentages[2] * 100
    )
    print 'Intensity (cd): \t%.2f \t\t%.2f \t\t%.2f' % (
        round(rgb_intensities[0], 2),
        round(rgb_intensities[1], 2),
        round(rgb_intensities[2], 2)
    )
    print 'Relative Intensity %%: \t%d%% \t\t%d%% \t\t%d%%' % (
        red_intensity_percent,
        green_intensity_percent,
        blue_intensity_percent
    )

    # Now map the Relative Intensity % to the the `Relative Intensity vs.
    # Current` graph in the datasheet.


def choose_luminous_intensities(color_mixing_ratio):
    '''Find the luminous intensities that can create the target color

    Given the color mixing ratio to produce the target color, find the
    candela for each color to satisfy the ratio.
    '''
    red_percentage = (color_mixing_ratio[0] / sum(color_mixing_ratio))
    green_percentage = (color_mixing_ratio[1] / sum(color_mixing_ratio))
    blue_percentage = (color_mixing_ratio[2] / sum(color_mixing_ratio))

    # Use the red to define the bounding candela.
    red_intensity = RED_LUMINOUS_INTENSITY
    green_intensity = (red_intensity / red_percentage) * green_percentage
    blue_intensity = (red_intensity / red_percentage) * blue_percentage

    rgb_percentages = (red_percentage, green_percentage, blue_percentage)
    rgb_intensities = (red_intensity, green_intensity, blue_intensity)

    print_result(color_mixing_ratio, rgb_percentages, rgb_intensities)


def main():
    parser = argparse.ArgumentParser(description='LED color converter')

    parser.add_argument('--rgb-color', action='store', dest='color_hex_str',
                        type=str, required=True, help='RGB color to convert. \
                        Expected format in 8-bit per channel hex string. Color\
                        is assumed to be chosen from the sRBG color space.')
    args = parser.parse_args()

    color_bytes = binascii.unhexlify(args.color_hex_str)
    red, green, blue = struct.unpack('>BBB', color_bytes)

    cie_xyz = rgb_to_xyz(red, green, blue)
    cie_xyy = xyz_to_xyy(cie_xyz)
    color_mixing_ratio = xyy_to_rgb_mixing_ratio(cie_xyy)

    if any(map(lambda x: x < 0, color_mixing_ratio)):
        # Your target color can't be created through additive mixing of the
        # primary colors.
        print('Ratio: %f %f %f' % color_mixing_ratio)
        raise Exception('You\'ve chosen an imaginary color given your \
primaries!')

    choose_luminous_intensities(color_mixing_ratio)


if __name__ == '__main__':
    main()
