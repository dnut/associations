#!/bin/bash
# This file only exists so that the github repo can be used to install
# the package without modification. If preparing an AUR package, you
# should also prepare your own src directory. prepare() and this file
# likewise should be unnecessary (but won't break anything if both are
# kept).

if [ ! -d 'associations' ]; then
	mv ../../associations .
fi
if [ ! -f 'setup.py' ]; then
	mv ../../setup.py .
fi