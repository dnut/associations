from copy import copy, deepcopy
from itertools import combinations, repeat
from collections import defaultdict
import multiprocessing
import numpy as np
from .libassoc import pretty


class Associator():
	""" Find all associations within the most specific subpopulations
	possible. Feed it a simpler histogram to test broader
	subpopulations.
	"""
	def __init__(self, histogram, desired, notable=1, significant=3):
		# Ratio with average (or inverse) to be included.
		self.notable = notable
		# Number of items to be statistically significant.
		self.significant = significant
		self.pairs, self.subpops = defaultdict(dict), defaultdict(dict)
		self.hist = histogram.simplify(*desired)

	def convert(self, combo):
		""" Convert list of indices to strings. Useful for testing. """
		def get(i, j):
			try:
				return self.hist.valists[i][j]
			except TypeError:
				return None
		return [get(i, j) for i, j in enumerate(tuple(combo))]

	def add(self, pair_type, pair, subpop, ratio):
		""" Add new association ratio results into both data
		structures as long as the ratio meets notability requirement.
		"""
		if (ratio > 1 and ratio < self.notable) \
		  or (ratio < 1 and 1/ratio < self.notable):
			return
		subpop = frozenset(subpop)
		assoc = frozenset(pair)
		assoc_type = frozenset(pair_type)
		subpop_type = frozenset(self.hist.field_index[spec] for spec in subpop)
		self.pairs[assoc_type].setdefault(assoc, {})[subpop] = ratio
		self.subpops[subpop_type].setdefault(subpop, {})[assoc] = ratio

	def find(self):
		""" Find the association ratio for every possible combination
		of field values for a given set of field names. 

		The algorithm is explained here (not the theory). See README.md
		for more information about the theory/math behind this method.

		eg. self.hist.fields = ['diag', 'disposition', 'race', 'sex']

		{ Main for loop:
		Iterate through all the pair_types of fields
			- (diag, disposition), (diag, sex), etc.
		1. Identify subpop_type.
			- if pair_type is (diag, disp) then subpop_type is (race, sex)
		2. simple_subpops_hist = Simplify n-dimensional histogram to
			(n - 2)-dimensional histogram, all pairs are combined so
			we have the totals for every type of subpopulation.
			- histogram fields are now only (race, sex), representing all
				(diag, disp) combined.
		{ First nested for loop:
		Iterate through every existent subpopulation, as determined
			by self.hist.nonzeros().
			- eg. (white, male)
		subtotal = comes from nonzeros(): total within subpop
			- eg. total number of white males
		1. subpop_hist = Slice (not simplify) 2D histogram out of
			main histogram to include only occurrences for this
			subpopulation. It has one dimension for each field in pair.
			- eg. 2D hist with fields (diag, disp)
			- eg. only (white, male) occurrences represented
		2. mini_hists = Create list with 1D hist for each field in
			pair_type.
			- eg. 1D diag histogram for every diag within subpop,
			and 1D disp histogram for every disp within subpop
		{ Second nested for loop:
		Iterate through every possible pair values for pair_type
			- eg. (amputation, fatality) for (diag, disp)
		1. totals = Get the total number within this subpopulation for
			each pair item from mini_hists
			- eg. total number of amputations and total number of
			fatalities among (white, male)
		2. Use general formula to calculate association ratio.
			                (fatal amputations in w,m) * (all w,m)
			- eg. ratio = ------------------------------------------
			              (fatalities in w,m) * (amputations in w,m)
		3. Record value with self.add_new.
		} } }
		Return all associations with both data structures: pairs and subpops
		"""
		for pair_type in combinations(self.hist.fields, 2):
			subpop_type = [f for f in self.hist.fields if f not in pair_type]
			simple_subpops_hist = self.hist.simplify(*subpop_type)
			for subpop, subtotal in simple_subpops_hist.nonzeros():
				if subtotal < self.significant:
					continue
				subpop_hist = self.hist.slice(*subpop)
				mini_hists = [
					subpop_hist.simplify(field_type) for field_type in pair_type
				]
				for pair, pair_total in subpop_hist.nonzeros():
					if pair_total < self.significant:
						continue
					totals = [mini_hists[i].get(f) for i, f in enumerate(pair)]
					assoc_ratio = pair_total * subtotal / (totals[0] * totals[1])
					self.add(pair_type, pair, subpop, assoc_ratio)
		return self.pairs, self.subpops


class Associations():
	""" This class contains all results from all searches. It exists
	separately from Associator() so we can pass Associator() objects
	into a multiprocessing pool and capture their results with
	callback routines.
	"""
	def __init__(self, hist):
		#{pair_type:
		#	{frozenset(assoc_pair): {frozenset(subpop/population): factor}}}
		self.pairs = dict(dict(dict()))
		#{subpop_type:
		#	{frozenset(subpop/population): {frozenset(assoc_pair): factor)}}
		self.subpops = dict(dict(dict()))
		self.hist = hist
	
	def add(self, data, single=False):
		""" Add resultant data from Associator.find() to all associations.
		Intended to be used as a callback routine for a multiprocessing pool.
		"""
		if single:
			self.merge(self.pairs, data[0])
			self.merge(self.subpops, data[1])
			return
		for datum in data:
			self.merge(self.pairs, datum[0])
			self.merge(self.subpops, datum[1])

	def merge(self, big, small):
		""" Directly merges dictionary data structures as lower level
		component of add().
		"""
		if isinstance(small, dict):    # Works for defaultdict
			for key in small:
				if key in big:
					self.merge(big[key], small[key])
				else:
					big[key] = small[key]

	def find_all(self, specificity=(0, 1), notable=1):
		""" Find all associations for all possible field combinations.
		Pool worker processes to handle every possible field combination.
		specificity: how specific of subpops to use
			- (0, 1) means subpop is set to (), so entire population
			- (0, 2) extends to subpops with a single field (diag)
			- (2, 3) only look at 2-field subpops, eg. (diag, disposition)
		"""
		self.field_index = self.hist.field_index
		if isinstance(specificity, int):
			spec = range(0, specificity)
		else:
			spec = [
				np.clip(i, 0, len(self.hist.fields)-1) + 2 for i in specificity
			]
		for i in range(*spec):
			pool = multiprocessing.Pool()
			pool.starmap_async(
				self.helper,
				zip(combinations(self.hist.fields, i), repeat(notable)),
				callback=self.add, error_callback=print)
			pool.close()
			pool.join()

	def helper(self, combo, notable):
		""" This function exists instead of lambda in map_async() due
		to pickling requirement.
		"""
		return Associator(self.hist, combo, notable=notable).find()

	def report(self, one, two, specificity=0):
		""" Report any Associations between fields one and two. They
		can be generic (eg 'age' and 'season'), specific (eg. ages
		'20 - 24' and 'summer'), or a mix of generic and specific.

		specificity: How specific of subpops to report. Do we want
		the association between white and summer for all male 20-24
		year olds that got head injuries (specificity = 3), or just
		the general association between 20-24 year olds and summer
		(specificity = 0).
		"""
		def search(gen, spec):
			""" For generic plus specific (eg. diag, male) """
			broad = deepcopy(self.pairs[frozenset({gen, sfi[spec]})])
			keep = set(key for key in broad if spec in key)
			for key in self.pairs[frozenset({gen, sfi[spec]})]:
				if key not in keep:
					del broad[key]
			return broad
		sfi = self.field_index
		if one in sfi and two in sfi:
			# Typical use case. Both specific, eg. summer male
			return self.pairs \
				[frozenset({sfi[one], sfi[two]})] \
				[frozenset({one, two})]
		elif one in sfi:
			return search(two, one)
		elif two in sfi:
			return search(one, two)
		else: return self.pairs[frozenset({one, two})]

	def subpop_report(self, *args):
		""" Provide a subpop (eg. white males age 20-24) and report
		all Associations discovered for that group. Must be either
		entirely specific (male, summer) or entirely generic (sex, season)
		"""
		gen, spec, specs = False, False, set()
		sfi = self.field_index
		for arg in args:
			if arg in sfi:
				spec = True
				specs.add(sfi[arg])
			else:
				gen = True
		if gen and spec:
			raise ValueError('Must be either fully generic or fully specific.')
		elif gen:
			return self.subpops[frozenset(args)]
		elif spec:
			return self.subpops[frozenset(specs)][frozenset(args)]