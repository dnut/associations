import numpy as np
import os
import re


def make_dir(*folders):
	""" Check for folder's existence. Makes if nonexistent. Raise
	OSerror if collision with file. Compatible with nested folders.
	If you want to make path/to/folder, use like this:
	make_dir(path, to, folder)

	This expands on os.makedir() by not worrying about directory
	collisions and having better cross-platform compatibility.
	"""
	path = os.path.join(*folders)
	if not os.path.isdir(path):
		os.makedirs(path)
	return path

def pretty(obj):
	""" Useful for testing.	Courtesy of Edward Betts:
	https://gist.github.com/EdwardBetts/0814484fdf7bbf808f6f
	"""
	from pygments import highlight
	from pygments.lexers import PythonLexer
	from pygments.formatters import Terminal256Formatter
	from pprint import pformat
	print(
		highlight(pformat(obj, width=160),
		PythonLexer(),
		Terminal256Formatter())
	)

def istr(obj):
	""" intelligent str(): Convert strings, floats, tuples, and lists
	to easily read strings. All else converted normally with str().
	- Floats are converted to three sig figs.
	- Lists and tuples are represented without (['']).
	- Strings have some special characters removed to improve filename
	compatibility.
	Lists and tuples may become unclear	if they contain strings	with
	commas in them. This is OK because the intention of istr() is
	very different from pretty(). It is not meant to reveal the
	internal data structure; rather, it	prioritizes brevity.
	"""
	if isinstance(obj, (float, np.float64, np.float32)):
		if obj >= 100:
			return str(int(obj + 0.5))
		return '{:.3g}'.format(obj)
	if isinstance(obj, list):
		return ', '.join([istr(element) for element in obj])
	if isinstance(obj, str):
		return re.sub(r'/|\n|\t', '-', obj)
	return str(obj)

def iint(string):
	""" Extract integer value of longest possible integer starting at
	beginning of string. eg. iint("18 - 24") = 18
	"""
	seasons = {'winter': 0, 'spring': 1, 'summer': 2, 'fall': 3}
	weekdays = {
		'Sun': 0, 'Mon': 1, 'Tue': 2, 'Wed': 3,
		'Thu': 4, 'Fri': 5, 'Sat': 6
	}
	try:
		return seasons[string] if string in seasons else weekdays[string]
	except KeyError:
		try:
			return int(string)
		except ValueError:
			return iint(string[:-1]) if string != '' else None

def invert(sequence):
	""" Inverts list to dict. Use when you would otherwise have many
	list.index() operations.
	eg. invert(['a', 'b', 'c']) = {'a': 0, 'b': 1, 'c': 2}
	"""
	ret = {}
	for i, val in enumerate(sequence):
		ret[val] = i
	return ret