from copy import copy, deepcopy
from itertools import combinations, repeat
from collections import defaultdict
import multiprocessing
import numpy as np
from .libassoc import pretty


class Associator():
	""" This class uses some lower level numpy operations rather than
	the Histogram() interface in order to optimize efficiency.
	"""
	def __init__(self, histogram, desired, notable=1, significant=3):
		# Ratio with average (or inverse) to be included.
		self.notable = notable
		# Number of items to be statistically significant.
		self.significant = significant
		self.assoc, self.subgroups = defaultdict(dict), defaultdict(dict)
		self.memo = set()
		self.hist = histogram.simplify(*desired)
		# Reduce to existent combinations, represent as array of index lists.
		self.relevant = np.transpose(np.nonzero(self.hist.histogram))

	def convert(self, combo):
		""" Convert list of indices to strings. Useful for testing. """
		def get(i, j):
			try:
				return self.hist.valists[i][j]
			except TypeError:
				return None
		return [get(i, j) for i, j in enumerate(tuple(combo))]
		
	def overall_ratios(self, i, sit):
		""" Calculate overall ratios that we can later compare to specific
		situations' ratios. See docstring for find() for context.
		
		First we isolate only one element of a combination, element i.
		We look at the total number of counts for this specific combination
		for every possible i, and add them together into specific_total.
		
		Then, we iterate through all the other fields. For each field, we
		sum the total number of counts for all possible values of both that
		field and i (larger than specific_total). We then divide specific_total
		by that value, creating a ratio for every field (except i) in a list.
		"""
		sit_index = copy(sit)
		# specific value for every field except i, which covers all possible i
		sit_index[i] = slice(0, len(self.hist.valists[i]))
		specific_total = np.sum(self.hist.histogram[sit_index])
		overall_ratios = []
		for other_field in range(len(sit)):
			if i == other_field:
				overall_ratios.append(None)
			else:
				broad_index = copy(sit_index)
				broad_index[other_field] = slice(
					0, len(self.hist.valists[other_field])
				)
				# specific_total / (total for all i and all other_field)
				overall_ratios.append(
					specific_total / np.sum(self.hist.histogram[broad_index])
				)
		return overall_ratios

	def test(self, sit, other_field, overall_ratios):
		""" Calculate association ratio between other_field and 
		main_field (relevant info for main_field is provided by
		overall_ratios).

		sit: specific situation (eg. amputation, fatality, white, male)
		other_field: field we isolate here (eg. fatality)
		overall_ratios: ratios calculated for chosen main_field
			(eg. diag - amputation)
		
		1. Find our_total = total number of (amputation, white, male)
		2. Find ratio = likelihood of (amputation, fatality, white, male)
			within broad group of (amputation, white, male)
		3. Find factor = above likelihood divided by more general likelihood.
			More general likelihood comes from overall_ratios, defined as:
			(fatality, white, male) / (white, male)
		
		factor: Association ratio between amputation and fatality.
		"""
		# Add slices to index for 1D self.hist.histogram instead of single value
		sit_index = copy(sit)
		# Total occurrences for specific i but all other_field
		sit_index[other_field] = slice(0, len(self.hist.valists[other_field]))
		our_total = np.sum(self.hist.histogram[sit_index])
		# (# of (specific i, all other_field)) / (# of (all i, all other field))
		ratio = float(self.hist.histogram[tuple(sit)]) / our_total
		factor = ratio / overall_ratios[other_field]
		return factor, factor > self.notable or factor < 1/float(self.notable)

	def add(self, sit, one, two, factor):
		""" Add identified association. """
		assoc = frozenset((
			self.hist.valists[one][sit[one]],
			self.hist.valists[two][sit[two]]
		))
		assoc_type = frozenset((
			self.hist.ordered_fields[one],
			self.hist.ordered_fields[two]
		))
		subgroup = frozenset([
			self.hist.valists[m][n] for m, n in 
			enumerate(sit) if m != one and m != two
		])
		subgroup_type = frozenset([
			self.hist.ordered_fields[m] for m, n in
			enumerate(sit) if m != one and m != two
		])
		# We can't use defaultdict for this because of multiprocessing.
		self.assoc[assoc_type].setdefault(assoc, {})[subgroup] = factor
		self.subgroups[subgroup_type].setdefault(subgroup, {})[assoc] = factor

	def find(self):
		""" Find the association ratio for every possible combination
		of field values for a given set of field names. See README.md
		for more information about the theory behind this method.

		self.relevant: every existent combination for general field
			names (eg. diag, disposition, race, sex)
		combo: specific combination of field values (eg. amputation,
			fatality, white, male)
		main_field: First field being isolated, we'll swap every value
			here (eg. try all diagnoses, not just amputation).
		other_field: other field tested for association with main_field
			using the specific value for other_field found in combo
			(eg. fatality)
		situation: Excluding main field (eg. None, fatality, white,
			male)
		sit: Version of situation being tested (eg. abrasion,
			fatality, white, male)
		overall_ratios: Broad likelihoods for each other_field for all
			possible main_field values combined.
			- (fatality, white, male) / (fatality, white)
			- (fatality, white, male) / (fatality, male)
			- (fatality, white, male) / (white, male)

		1. Select combo (eg. amputation fatal white male)
		2. Select main field (eg. diag (from amputation)).
		3. Calculate overall_ratios for all possible main_fields (diags).
		4. Loop through every possible main_field.
		5. Select other_field (eg. fatality).
		6. Run test() to find association ratio.
		7. Add result if notable.

		See docstring for test() for more information.
		"""
		c, memo = 0, set()
		for combo in self.relevant:
			# Isolate each main_field to test all of its possible values.
			for main_field in range(len(combo)):
				# Label situation with a tuple setting main_field to None since
				# we will compare every possible value for the main_field.
				situation = tuple(combo)[:main_field] + (None,) \
				            + tuple(combo)[main_field+1:]
				# Label exists so we can memoize to avoid redundancy.
				if situation in memo: continue
				memo.add(situation)
				# Initialize with the first possible value for main_field.
				sit = list(situation)
				sit[main_field] = 0
				overall_ratios = self.overall_ratios(main_field, sit)
				# Try every possible value for main_field in the situation sit
				for _ in self.hist.valists[main_field]:
					# Test chosen value for main_field against each other_field
					for other_field in range(len(sit)):
						# Require some degree of statistical significance.
						if main_field == other_field \
								or self.hist.histogram[tuple(sit)] \
								< self.significant:
							continue
						# Skip statistically equivalent duplicates.
						spec_sit = tuple(sit)[:other_field] \
						           + (None,) \
						           + tuple(sit)[other_field+1:]
						if spec_sit in memo: 
							continue
						# Determine relative frequency
						factor, hit = self.test(
							sit, other_field, overall_ratios
						)
						if hit:
							self.add(sit, main_field, other_field, factor)
							c += 1
					sit[main_field] += 1
		return self.assoc, self.subgroups


class Associations():
	""" This class contains all results from all searches. """
	def __init__(self, hist):
		#{pair_type:
		#	{frozenset(assoc_pair): {frozenset(subgroup/population): factor}}}
		self.pairs = dict(dict(dict()))
		#{subgroup_type:
		#	{frozenset(subgroup/population): {frozenset(assoc_pair): factor)}}
		self.subgroups = dict(dict(dict()))
		self.hist = hist
	
	def add(self, data, single=False):
		""" Add resultant data from Associator.find() to all associations.
		Intended to be used as a callback routine for a multiprocessing pool.
		"""
		if single:
			self.merge(self.pairs, data[0])
			self.merge(self.subgroups, data[1])
			return
		for datum in data:
			self.merge(self.pairs, datum[0])
			self.merge(self.subgroups, datum[1])

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
		specificity: how specific of subgroups to use
			- (0, 1) means subgroup is set to (), so entire population
			- (0, 2) extends to subgroups with a single field (diag)
			- (2, 3) only look at 2-field subgroups, eg. (diag, disposition)
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

		specificity: How specific of subgroups to report. Do we want
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

	def subgroup_report(self, *args):
		""" Provide a subgroup (eg. white males age 20-24) and report
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
			return self.subgroups[frozenset(args)]
		elif spec:
			return self.subgroups[frozenset(specs)][frozenset(args)]