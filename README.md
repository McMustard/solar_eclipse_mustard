# Solar Eclipse Mustard
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

## Testing Camera Support

First, you might want to test your camera, to see if this is worth it.
When developing this, I tested on a Nikon D3300 and a Fujifilm X-H2.

1. Connect your camera to the computer where you'll run these utilities. Make
sure it is set up for tethering and such.

2. Run:
```
python cam.py capture --list-cameras
```

If your camera is listed, go ahead and run:
```
python cam.py capture -F APERTURE -S SHUTTERSPEED -I ISO
```

substituting in an aperture, shutter speed, and ISO. Aperture can be `8` for
f/8. Shutter speed can be `1/2` or `0.5` for 1/2 second. ISO is just the
number, e.g. `100` for 100.

Try various settings and if it's not working for you, you probably need to
edit the code.

## Instructions for use

These instructions assume Solar Eclipse Maestro is set up as needed, such as
with your target location and so forth.

1. Use Solar Eclipse Maestro to generate a script using the Configuration
Wizard, or use any other method to write one. These instructions will assume
you've named it "script.txt", but you can of course choose another name.

2. In Solar Eclipse Maestro, on the Observer menu, choose Detailed Local
Circumstances Table.

3. In the Detailed Local Circumstances window, right-click and select Save
Content to Text File.

4. Choose a save location and file name, and click Save. These instructions
will assume you've named it "circumstances.txt"

5. Copy the file you just saved to the system that will run these utilities.

6. Run:
```
python sem.py -t circumstances.txt script.txt -o script.csv
```

7. The file "script.csv" contains a list of timestamps and commands, similar
to what is seen in Solar Eclipse Maestro. It would not be a bad idea to
compare the timestamps in "script.csv" to the list to what Solar Eclipse
Maestro shows.

8. To do a dry run, connect your camera and run:
```
python sequncer.py -t DATETIME script.csv
```

where DATETIME is the time you want the sequencer to think it is, and it
should look like `2024/04/08 12:15:00.0` and be in your local time, not UTC
like the timestamps in script.csv are.

You can set a time to somewhere in the middle of the script, such as right
before totality, to make sure your camera can handle all the commands it'll be
given.

## Prime Time

When it's time to do this for real:

1. Make sure your system time is up to date.

2. Redo "Instructions for use" if your location will have changed and you
need to regenerate a script from Solar Eclipse Maestro.

3. Run:

```
python sequencer.py script.csv
```

(You DO NOT want to use the -t option here, which sets a SIMULATED time!)



