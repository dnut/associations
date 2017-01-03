from itertools import chain
from copy import copy
import numpy as np
import matplotlib.pyplot as plt
import os
import textwrap
from .libassoc import invert, istr, iint, pretty, make_dir

class Analysis():
	""" Ideally this class would implement totally generic methods
	that can be used to analyze any Histogram() and Associations()
	objects. This class is an attempt at that but it is still
	somewhat specialized and may need adaptation for general use.
	"""
	def __init__(self, histogram, assoc, output_dir='output', plot_format='pdf'):
		self.hist = histogram
		self.assoc = assoc
		self.plot_counter = 0
		self.gen_assoc = {}
		self.output_dir = output_dir
		self.plot_dir = make_dir(output_dir, 'plots')
		self.maxes = [('', 1), ('', 1), ('', 1)]
		self.mins = [('', 1), ('', 1), ('', 1)]
		self.time = ('age', 'weekday', 'season')
		self.plot_format = plot_format

	def percent(self, count, total=65499):
		""" Basic percent calculator outputting nice string """
		return istr(100*count/total) + '%'

	def percentify(self, pairs, total=65499):
		""" Use on the list of tuples to convert ratios to percentages """
		return tuple((a, self.percent(b, total=total)) for (a, b) in pairs)

	def bin_sort(self, bins):
		""" Sort bins according to value of longest int(string[0:?]) """
		def value(s):
			i = iint(s[0]) if isinstance(s, tuple) else iint(s)
			return i if i != None else float('inf')
		return sorted(bins, key=value)

	def most_common(self, test_group, *subpop):
		""" Rank test_group by greatest occurrence within subpop. """
		fields = [self.hist.field_index[val] for val in subpop]
		hist = self.hist.simplify(test_group, *fields)
		data = [
			(test, hist.get(test, *subpop))
			for test in hist.valists[hist.fieldict[test_group]]
		]
		return self.percentify(
			sorted(data, key=lambda x: -x[1]),
			total=self.hist.get(*subpop)
		)

	def most_assoc(self, test_group, value, *subpop):
		""" Rank test_group by greatest association with value within
		subpop.
		"""
		data, a = [], self.assoc.report(test_group, value)
		for assoc in a:
			mutable = set(assoc)
			mutable.remove(value)
			data.append((''.join(mutable), a[assoc][frozenset()]))
		return sorted(data, key=lambda x: -x[1])

	def extremes(self):
		""" Find absolute most associations within all associations
		for both specific field values as well as generic field types.

		Return data in format that can be easily interpreted by
		AsciiTable().
		"""
		gens = sorted([(k, self.gen_assoc[k]) for k in self.gen_assoc],
		              key=lambda x: x[1])
		fmat = lambda x: [(', '.join(s[:30] for s in i[0]), i[1]) for i in x]
		gl, gm = fmat(gens[:3]), fmat(gens[:-4:-1])
		sl, sm = fmat(self.mins), fmat(self.maxes)
		return (('Generic Associations',
			('Most Associated', gm),
			('Least Associated', gl)),
		('Specific Associations',
			('Most Associated', sm),
			('Least Associated', sl)))

	def prep_hist(self, field, other_field, notable=1, subpop=''):
		""" Filter out irrelevant data for plotting """
		bins = self.hist.valdicts_dict[field]
		associations = self.assoc.report(field, other_field)
		keep_of = set()
		if field in self.time:
			# Keep all bins for time
			keep_of = set(self.hist.valists_dict[field])
		else:
			# For non-time, remove excess bins without notable data
			for key in associations:
				try:
					ratio = associations[key][frozenset(subpop)]
				except KeyError:
					continue
				# Only keep notable bins
				if ratio >= notable or ratio <= 1/float(notable):
					for myfield in key:
						typ = self.hist.field_index[myfield]
						if typ == field:
							keep_of.add(myfield)
		# Don't include mis-entered data (eg. ages > 200 years)
		try:
			keep_of.remove('typo')
		except KeyError:
			pass
		# Sort bins (eg. time related such as ages)
		bins = self.bin_sort([s for s in bins if s in keep_of])
		return bins, associations

	def make_hist(self, field, other_field, notable=1, subpop=''):
		""" This method creates the data structure for a histogram plot
		given the names of the fields we want to compare. This is done
		manually because we are working with already existent bins.

		This method is long, but it is primarily a single cohesive
		loop that serves a single purpose.
		
		field: x-axis
		other_field: legend
		notable: threshold for ratio of notable data (also inverse)
		"""
		keep_f, values, hists = set(), [], []
		skip, top = False, 0
		bins, associations = self.prep_hist(
			field, other_field, notable, subpop
		)
		bindex = invert(bins)
		empty_things = np.zeros(len(bins))
		# Traverse each association to find and add notable data
		for key in associations:
			# For each of the two items per association
			for myfield in key:
				if myfield == 'typo':
					# Typo ages not useful
					skip = True
				# Determine whether item is from field or other_field
				typ = self.hist.field_index[myfield]
				if typ == other_field:
					# Legend fields
					value = myfield
					# Only keep notable legend fields
					if myfield not in values:
						values.append(myfield)
						hists.append(copy(empty_things))
				elif myfield not in bins:
					# Keep out unwanted bins
					skip = True
				else: # Bin fields
					actual = myfield
			# Gather association ratio for combination
			try:
				ratio = associations[key][frozenset(subpop)]
			except KeyError:
				skip = True
			if skip == True:
				skip = False
				continue
			# Record highest value among all data
			top = max(ratio, top)
			# index i used in original histogram
			index = values.index(value)
			if ratio >= notable or ratio <= 1/float(notable):
				# Save index for this field so we keep its data in the end
				keep_f.add(index)
			try:
				# Record the ratio if we decided it is notable above
				hists[index][bindex[actual]] = ratio
			except KeyError:
				pass
		# Filter out data which is not notable
		keepers = [value for i, value in enumerate(hists) if i in keep_f]
		new_values = [value for i, value in enumerate(values) if i in keep_f]
		return bins, new_values, top, keepers

	def plot_hist(self, title, xlabel, ylabel, bins, ds_names,
		          *data_sets, log=False, legend=True):
		""" Plot pre-binned histogram. """
		ds_names = [
			name if len(name) < 60 else name[:59] + '...' for name in ds_names
		]
		colors = ('b', 'r', 'g', 'c', 'm', 'y', 'k', 'w')
		n_sets = len(data_sets)
		if n_sets == 0:
			return
		if n_sets == 1:
			colors = 'g'
		fit = 0.7 if n_sets > 1 else 1
		width = fit/n_sets
		plt.figure(self.plot_counter)
		index = np.arange(len(data_sets[0]))
		for i, data_set in enumerate(data_sets):
			plt.bar(index + i * width, data_set, width, alpha=0.4,
				    color=colors[i % 8], label=ds_names[i])
		plt.title(title); plt.xlabel(xlabel); plt.ylabel(ylabel)
		# Use log base 10 scale
		if log:
			plt.yscale('log')
		wrap_width = int(250/len(data_sets[0]))
		plt.xticks(index + fit/2, [textwrap.fill(s, wrap_width) for s in bins])
		plt.tight_layout()
		# Horizontal dotted line at 1
		plt.axes().plot([-0.05, len(data_sets[0]) - 0.25], [1, 1], "k--")
		if legend:
			plt.legend()
		#plt.plot()
		self.plot_counter += 1

	def nice_plot_assoc(self, one, two, title=False, xlabel=False,
		                bins=False, notable=1.5, subpop='', force=False):
		""" Try plot with arbitrary limitation first, change if needed. """
		while notable > 1:
			# This means floats such as 0.9999999999999997 will
			# be excluded, but we don't want < 1.1 anyway.
			bad = self.plot_assoc(
				one, two, title, xlabel, bins, notable, subpop
			)
			if bad == 'high':
				notable += 0.1
			elif bad == 'low':
				notable -= 0.1
			elif bad == None:
				break
			else:
				raise RuntimeError
		else:
			if force:
				self.plot_assoc(
					one, two, title, xlabel, bins, notable, subpop, force=True
				)

	def savefig(self, name):
		fig = plt.gcf()
		fig.set_size_inches(25, 15)
		fig.savefig(
			os.path.join(self.plot_dir, name + '.' + self.plot_format),
			bbox_inches='tight',
			dpi=100
		)

	def plot_assoc(self, one, two, title=False, xlabel=False,
		           bins=False, notable=2, subpop='', force=False):
		""" Plot associations between values one and two. Extract a
		more complete data set from the histogram and make the plot.
		"""
		One, Two = one.capitalize(), two.capitalize()
		if not xlabel:
			xlabel = one.capitalize() + 's'
		if not title:
			title = 'Associations between {} and {}'.format(One, Two)
		if not bins:
			bins = self.hist.valists_dict[one]
		ylabel = 'Association Ratio'
		bins, names, top, data = self.make_hist(
			one, two, notable, subpop=subpop
		)
		log = True if top > 10 else False
		if not force:
			if len(data) < 2 or len(data[0]) < 2:
				return 'low'
			if len(data) > 8:
				return 'high'
		self.plot_hist(title, xlabel, ylabel, bins, names, *data, log=log)
		name = one +', '+ two + (' for ' + istr(subpop) if subpop else '')
		self.savefig(name)

	def max_helper(self, one, two):
		""" Record most associated specific pairs within the generic
		one two combination and find mean for one two combo.
		"""
		c, tot, val = 0, 0, 1
		search = self.assoc.report(one, two)
		for combo in search:
			try:
				val = search[combo][frozenset()]
			except KeyError:
				continue
			# Find specific maxes
			for big_one in self.maxes:
				if val > big_one[1]:
					self.maxes.append((combo, val))
					self.maxes = sorted(self.maxes, key=lambda x: -x[1])[:3]
					break
			# Find specific mins
			for small_one in self.mins:
				if val < small_one[1]:
					self.mins.append((combo, val))
					self.mins = sorted(self.mins, key=lambda x: x[1])[:3]
					break
			# Standardize so anti-associations are equally represented
			if val < 1: val = 1/val
			# To do: Improve by weighting by occurrences.
			c += 1
			tot += val
		# Record average association for combo type
		self.gen_assoc[frozenset((one, two))] = tot/c

	def plot_all(self):
		""" Plot the associations between every possible field pair. """
		memo = set()
		h = self.hist
		for one in self.hist.fieldict:
			for two in self.hist.fieldict:
				# Plots must meet these conditions:
				# - one and two must be different.
				# - Times should be bins only unless both bin + legend are times
				# - Group of bins is larger than legend unless bins are time.
				# - If both bins and legend are times, larger set is bins.
				ugly_sizes = len(h.valists[h.fieldict[two]]) > \
				             len(h.valists[h.fieldict[one]])
				if one == two \
						or (
							one not in self.time
							and (two in self.time or ugly_sizes)
						) or (
							one in self.time
							and two in self.time
							and ugly_sizes
						):
					continue
				self.nice_plot_assoc(one, two)
				# For efficiency, use opportunity to run through nested loops
				# to determine how associated each field pair is overall.
				self.max_helper(one, two)


class AsciiTable():
	""" This grew out of a need to portray specific data that was
	found using this module. Originally, it was just one method in
	Analysis(), but that no longer seemed appropriate so it has been
	split off. It needs some work to become friendly for general use.
	"""
	def __init__(self):
		self.tables = []

	def __str__(self):
		return '\n\n'.join(self.tables)

	def add_table(self, *args):
		""" Create an ascii table out of sections from self.table_section()
		"""
		formatted = tuple(chain(*[self.table_section(*a) for a in args]))
		tuples = [(x[0], istr(x[1])) for x in formatted if isinstance(x, tuple)]
		lens = [len(max(i, key=len)) for i in tuple(zip(*tuples))]
		tlen = sum(lens)
		t, hb = [], '─'*(tlen + 3)
		t.append('┌' + hb + '┐')
		for item in formatted:
			if item == 'hb' and len(t) == 1:
				continue
			if item == 'hb':
				t.append('├' + hb + '┤')
			elif isinstance(item, tuple):
				pad = [(lens[i] - len(istr(item[i])) + 1) * ' ' for i in (0, 1)]
				t.append(('│{}{}│{}{}│').format(item[0], pad[0],
				                                pad[1], istr(item[1])))
			else:
				this_pad = (tlen+3 - len(item))
				if item[:2] == '==':
					l = ' '*int(this_pad / 2)
					r = ' '*(this_pad % 2) + l
					t.append('│' + l + item + r + '│')
				else:
					t.append('│' + item + ' '*(tlen+3 - len(item)) + '│')
		t.append('└' + hb + '┘')
		table = '\n'.join(t)
		self.tables.append(table)
		return '\n'.join(t)

	def table_section(self, title, *subsects):
		""" Create a table section from question output that can be
		properly formatted by self.table()
		
		For multiple subsects:
		subsect[0]: subsect title
		subsect[1]: subsect data
		"""
		h = 'hb'
		ret = (h, '== ' + title + ' ==', h)
		if len(subsects) == 1:
			for line in subsects[0]:
				ret += (line,)
			ret += (h,)
		else:
			for subsect in subsects:
				ret += (subsect[0], h)
				for line in subsect[1]:
					ret += (line,)
				ret += (h,)
		return ret