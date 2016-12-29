from time import time

class Stopwatch():
	""" A Stopwatch object keeps track of multiple concurrent timers.
	For robustness, unfamiliar coders should explicitly set every option.
	"""
	def __init__(self, *args):
		""" If you want to start timing at instantiation, you need to give
		at least one name.
		"""
		self.times = {}    # Dict so times can overlap
		self.names = []    # Keep track of order
		self.generic_counter = 0
		for name in args:
			self.start(name)

	def __str__(self):
		""" eg. Procedure #3: 1.2 s """
		sl = self.str_list()
		return '\n'.join([t[0] + ': ' + t[1] for t in sl])

	def str_list(self):
		""" Simplified list of durations instead of start and end times. """
		return [
			(self.names[i], '{:.2g} s'.format(self.measure(name)))
			for i, name in enumerate(self.names)
		]

	def generic(self, start=True):
		""" Produces next consecutive generic name starting at 0. """
		return 'Procedure #{}'.format(self.generic_counter)
		self.generic_counter += 1

	def start(self, name=None):
		""" Starts a new timer. Time is measured as late as possible
		to prevent overhead from being included.
		"""
		if not name: name = self.generic()
		self.names.append(name)
		self.times[name] = [time()]

	def stop(self, name=None, quiet=False):
		""" Stops a timer and records the finishing time. If no name
		is given, the most recently started timer is stopped. Time is
		measured first to prevent overhead from being included.
		"""
		now = time()
		if not name: name = self.names[-1]
		self.times[name].append(now)
		segment = self.measure(name)
		if not quiet:
			print('{}: {:.2g} s'.format(name, segment))

	def lap(self, new_name=None, former_name=None, quiet=False):
		""" End one timer and start another. If you give only a
		single argument, that is the name for the NEW timer,
		and the most recently started timer is stopped.
		"""
		self.stop(former_name, quiet)
		self.start(new_name)

	def measure(self, name):
		""" Calculates duration in seconds. """
		return self.times[name][1] - self.times[name][0]

	def end(self, quiet=False):
		""" Stops all timers. Prints all times. """
		now = time()
		print('\nDone.\n')
		for pair in self.times:
			if len(self.times[pair]) == 1:
				self.times[pair].append(now)
		if not quiet:
			print('== Times ==\n' + self)