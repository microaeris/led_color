# sRGB to Color Mixing Ratio

Goal of this script is to convert colors from a commonly used color space
(sRBG) to one that can be used with additive color mixing.

## How to Use

Given your 8-bit hex RGB color, the script will tell you what candela you need your LED to output to create the target color. You will need to configure the script to your specific LED; there are a few constants in the script you need to manually edit (they can all be found at the top of the file).

### Example

```
$ python ./led_color.py --rgb-color E0A3B5
        Mix Ratio %      Candela Intensity  Relative Intensity %
Red:    38%          0.10           100%
Green:  49%          0.13           40%
Blue:   11%          0.03           15%

```

## About LED Color Mixing

This script implements the calculations laid out in LEDs Magazine's article on
LED color mixing, plus a little extra. [Source](https://www.ledsmagazine.com/smart-lighting-iot/color-tuning/article/16695054/understand-rgb-led-mixing-ratios-to-realize-optimal-color-in-signs-and-displays-magazine)

To explain the article's contents in plain English:

There exists a color standard called CIE 1931 XYZ. This standard captures all colors visible to the average human eye. It's also great for calculating additive colors. 

Let's say we have an RGB LED and an RGB color we want to create. There a great number of conversions we need to go through to get from A to B.

When I first got started with this endeavor, I thought I could simply light the RGB LEDs at the same relative intensities as their hex values. That is, I naively hoped that I could take the RGB colors, find their percentage to their primaries, light the LEDs at that intensity. There a few problems with this line of thinking. First, the human eye doesn't perceive all color wavelengths equally. We are much more sensitive to greens due to nature being mostly green. That means a light source needs to emit a bunch more green to create white (an equal weighting of red, green, and blue). Next, I tried hand tuning the current to drive my LEDs by looking at the LEDs and then matching it to some target color. Well, my eye and brain are the least precise sensors ever, and the LED datasheet explicitly warns the user to not stare at the LEDs for more than a few seconds if they don't want to blind themselves. Uhh, I read that line in the datasheet a little too late. But either way, this first attempt was a failure.

So step one of the article is to convert your target color to a color system that takes into account the particular sensitivities of the human eye and one that can be used for additive color mixing. That's where the CIE 1931 XYZ color space comes in. This color space was defined as a result of a number of measurements taken on some humans in Great Britain in the 1900's. Average enough. Anyways, so there's some math to do that. Thanks Internet. XYZ is actually a 3D color space that is hard to envision, so most of the article was actually working in CIE 1931's xyY color space. It's much nicer, trust me. `(x,y)` captures the color (chromaticity, as the jargon goes) and `Y` represents the objective brightness (luminance). So we have to convert to xyY. 

We also need to measure the color of the light from our LED. Since we're adding colors here, we need to know the primitive colors that we're going to add together to create the newer, and prettier colors. To get this information, go to your datasheet, scratch your head a little, and resort to using an online converter to convert the given typical dominant wavelength to xyY. [Link to converter](https://www.ledtuning.nl/en/cie-convertor).

At this point, we have our target colors and source colors all in xyY. Next, we're going to find the ratio of red to green to blue that is needed to form your target color. Do some basic algebra with a fancy name like 'center-of-gravity method', and voila, you have your color mixing ratio. That's the critical piece of information we're after. 

Now, depending on the requirements of your application, you have to use this color mixing to determine the intensities of your individual R, G, B LEDs. I chose values that would make the brightest versions of my target color. I did some sketchy math here, and finally, you will have to refer to your datasheet again to convert intensity to forward current. 

And with that, you can finally light your LEDs at the precise shade you wanted. I hope it was worth it. Except, I've implemented this all for you. Good luck! Feel free to ask my any questions if you run into issues.
