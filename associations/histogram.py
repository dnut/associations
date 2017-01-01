import csv
import numpy as np


class Histogram():
	def __init__(self, table_filename='', fields=[], ordered_fields=[],
		         histogram=None, valists=[], valdicts=[]):
		""" Can be given seed data (table_filename)	or complete histogram. """
		self.table_filename = table_filename
		self.fields = fields
		self.ordered_fields = ordered_fields
		self.histogram = histogram
		self.valists = valists
		self.valdicts = valdicts

	# Methods intended to be overridden by subclasses if needed.
	def fix_head(head): return head
	def fix_row(row): return row

	def count(self):
		""" Run through an entire CSV table and count the number for
		every possible combination of all self.fields, saving counts
		in a len(self.fields) dimensional numpy array.

		A numpy array is vastly superior in efficiency and available
		operations to another data structure, such as a dictionary,
		but it adds some obscurity since it is simply an array of
		integers indexed by integers. Likewise, some supporting data
		structures are necessary to prevent the entire program from
		degrading into spaghetti code that relies too heavily on the
		structure of the histogram.
		
		- self.histogram: each dimension represents a field (age, sex,
		etc.), as indexed by fields. Each entry in the dimension
		represents a possible string for that field as indexed by
		valists and valdicts. The value at each intersection of
		dimensions represents the number of occurrences for a specific
		combination.

		The following are data structures intended to be used where
		Histogram() objects are used in order to allow indexing the
		array with strings:
		- self.valists: List of list. Each sublist contains every value.
			- self.valists[0][1] = 'winter' ... ([season][winter])
		- self.valdicts: List of dicts. Lists within valists are inverted.
			- self.valdicts[0]['winter'] = 1 ... ([season][winter])

		Generic field names are indexed (season --> 0) by useful_stuff().
		The example values given here should be assumed to be inaccurate.

		We could split this into two methods because it has two jobs
		(analyze the table then count everything), but that would
		require opening the file twice, and, more importantly, the
		increased complexity of passing many variables back and forth,
		which probably isn't worth it just to decrease LOC per method.
		"""
		with open(self.table_filename) as table_file:
			table_csv = csv.reader(table_file)
			head = self.fix_head(next(table_csv))
			indices = dict(
				(name, i) for i, name in enumerate(head) if name in self.fields
			)
			loi = sorted([indices[name] for name in indices])
			self.ordered_fields = [head[i] for i in loi]
			values = [set() for i in loi]
			# Count number of possibilities for each field to shape histogram
			for row in table_csv:
				self.fix_row(row)
				for i, j in enumerate(loi):
					values[i].add(row[j])
			valcount = []
			for valset in values:
				# 15% more efficient than comprehensions
				valcount.append(len(valset))
				self.valists.append(list(valset))
				self.valdicts.append(
					dict((value, i) for i, value in enumerate(valset))
				)
			# Go back to beginning to run back through file, counting this time.
			table_file.seek(0)
			next(table_csv)
			self.histogram=np.zeros(valcount, dtype=np.int32)
			for row in table_csv:
				row = self.fix_row(row)
				combo = tuple(
					self.valdicts[i][row[j]] for i, j in enumerate(loi)
				)
				self.histogram[combo] += 1
		self.useful_stuff()

	def useful_stuff(self):
		""" Run this after the necessary values have been set. This
		provides the additional information necessary to use the
		supporting data structures for self.histogram
		"""
		# fieldict['sex'] = 4
		self.fieldict = dict(
			(field, i) for i, field in enumerate(self.ordered_fields)
		)
		# field_dict_dict['sex'] = {'Male': 0, 'Female': 1}
		self.valdicts_dict = dict(
			(field, self.valdicts[i])
			for i, field in enumerate(self.ordered_fields)
		)
		# field_list_dict['sex'] = ['Male', 'Female']
		self.valists_dict = dict(
			(field, self.valists[i])
			for i, field in enumerate(self.ordered_fields)
		)
		# self.field_index['Male'] = sex
		self.field_index = dict(
			(key, self.ordered_fields[i]) for i, dict in
			enumerate(self.valdicts) for key in dict
		)
		# self.field_index_int['Male'] = 4
		self.field_index_int = dict(
			(key, i) for i, dict in enumerate(self.valdicts) for key in dict
		)
		# Array of indices for all nonzero elements (occurred at least once)
		self.nonzero_indices = np.transpose(np.nonzero(self.histogram))

	def simplify(self, *fields):
		keep = set(self.fieldict[field] for field in fields)
		rm = tuple(i for i in range(len(self.fields)) if i not in keep)
		hist = self.histogram.sum(rm)
		return self.reduce(hist, keep, fields)

	def reduce(self, array, indices, fields):
		""" Helper function for simplify and slice. Feed it the new
		numpy array and indices for the fields being kept, return
		Histogram() object.
		"""
		ordered, valists, valdicts = [], [], []
		for i in indices:
			ordered.append(self.ordered_fields[i])
			valists.append(self.valists[i])
			valdicts.append(self.valdicts[i])
		new_hist = Histogram(None, ordered, ordered, array, valists, valdicts)
		new_hist.useful_stuff()
		return new_hist

	def slice(self, *values):
		""" Reduce number of dimensions by only looking at a specific
		situation as defined by values. Limit to only non-specified
		dimensions. Returns new Histogram() object.

		This is similar to simplify() but serves a very different
		purpose because it does not account for all occurrences.

		For example, if we have a Histogram() for (sex, weekday)
		and we want to slice it for all males, we get this transition:
		(1 male on tuesday, 2 female on tuesday) turns into:
		(1 on tuesday)
		"""
		rm, keep, pre_slice, slicer, fields = set(), [], {}, [], []
		for val in values:
			index = self.field_index_int[val]
			rm.add(index)
			pre_slice[index] = self.valdicts[index][val]
		for i in range(len(self.fields)):
			if i in rm:
				slicer.append(pre_slice[i])
			else:
				keep.append(i)
				fields.append(self.ordered_fields[i])
				slicer.append(slice(0, len(self.valists[i])))
		hist = self.histogram[slicer]
		return self.reduce(hist, keep, fields)

	def nonzeros(self, fast=False):
		""" Generator function to iterate through nonzero values.
		fast: yield only counts and no field strings
		"""
		for index in self.nonzero_indices:
			if isinstance(self.histogram, np.int64):
				yield '', self.histogram
			elif fast:
				yield self.histogram[index]
			else:
				yield (
					[alist[index[i]] for i, alist in enumerate(self.valists)],
					self.histogram[tuple(index)]
				)

	def get(self, *entries):
		""" entries: string names for field values (eg. 'Male').
		Return the counts for that particular case, merging dimensions
		if necessary.
		"""
		# Figure out fieldname (eg. age) for each entry (eg. 18-24)
		fields = [self.field_index[entry] for entry in entries]
		if set(fields) != set(self.fields):
			# Create new histogram with only those fields if needed.
			hist = self.simplify(*fields)
		else:
			# Many times faster to use the same histogram if possible.
			hist = self
		# Convert entries to list so it can be sorted
		lent = list(entries)
		# Sort according to array dimension of field
		lent.sort(key=lambda x: self.field_index_int[x])
		# Convert strings into ints to use as array indices
		lint = [hist.valdicts[i][val] for i, val in enumerate(lent)]
		return hist.histogram[tuple(lint)]