# solar_eclipse_mustard
Camera sequencer for solar eclipses

This is a thing I've made for myself and friends, so if you've arrived here,
I'd recommend that you don't expect this to work. It might! But it's risky.
No warranties, as stated in the license, and so forth.

In short, the otherwise wonderful application named Solar Eclipse Maestro does
not run on my modern Mac, and doesn't detect the cameras we need it to work
for. So, what I've put together here is a set of scripts to parse a SEM script
file, unroll its for-loops, generate a linear list of commands with times, and
run those commands at the precscribed times, to take pictures using an
interchangeable-lens camera.

You need:

## Dependencies

Solar Eclipse Maestro
(to generate scripts, not necessarily to execute)

gphoto2

python-gphoto2

I think that's probably it.
