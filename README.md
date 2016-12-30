# Associations
Associations is a Python 3 module used to identify and analyze associations in any data set. It was originally created to aid in solving a specific set of problems. I have not included that original implementation code to respect the employer's wishes.

As you examine this module, you will see there are some aspects of it that could be made more encapsulated, efficient, concise, or generalized. Once I start working on a reference implementation, I will begin to resolve these issues. I urge you to make pull requests if you see anything that could be improved.

## Installation
- **Dependencies**: NumPy, matplotlib, multiprocessing
- **Build Dependencies**: git (only for Arch Linux python-associations-git package)

This is ***not*** compatible with Python 2.
### Universal
Run this if you would like to install associations directly into Python without the use of a package manager. This should be compatible with any system.
```
$ python setup.py sdist
# python setup.py
```

### Arch Linux
For Arch Linux users, I recommend installing the python-associations-git package because you can keep reusing the same PKGBUILD. It will automatically download the latest source code and update the version number based on the revision number. Simply download the PKGBUILD from my PKGBUILDs repository and use that to install python-associations-git.

To install python-associations-git, run this in an empty directory:
```
$ wget https://raw.githubusercontent.com/dnut/PKGBUILDs/master/assocations/python-associations-git/PKGBUILD
$ makepkg -si
```

You can also download the source code here and install using the included PKGBUILD in python-associations. However, the version number will not always keep up with changes. Additionally, you would have to manually clone this repo or download the zip from github.com every time. I only recommend this PKGBUILD for testing (eg. if you are contributing to development) or if you are forking your own local version of the package.

To install python-associations, cd into the python-associations directory and run this command:
```
makepkg -si
```

# Overview
We can count occurrences with a histogram, find associations between different fields, and are provided tools that aid in the analysis of the resultant data.

## libassoc.py
This file contains the most generic procedures that do not belong in any created classes. They are convenient procedures for Python's fundamental data structures.

## histogram.py - Histogram()
The primary job of a ```Histogram()``` object is to traverse a CSV file and create a NumPy array with as many dimensions as fields we wish to record and to fill that array with the count for every possible occurrence. This is accomplished with the ```count()``` method. Access to the internal data structure is provided via the ```get()``` method.

| Attribute            | Description |
| -------------------- | ----------- |
| ```fields```         | Table fields that we want to measure.|
| ```histogram```      | NumPy array containing counts.|
| ```valists```        | List of lists containing strings of each field's values.|
| ```valdicts```       | List of dicts, inverted valists (key = string, val = int)|
| ```valists_dict```   | Dict of valists keyed by field names.|
| ```valdicts_dict```  | Dict of valdicts keyed by field names.|
| ```field_index```    | Keys field values to field names.|
| ```field_index_int```| Keys field values to valists/valdicts index (int).|

| Method               | Description |
| -------------------- | ----------- |
| ```count()```        | Count all occurrences for every possible situation| 
| ```useful_stuff()``` | Expose the string values for quantitative internal data structure.|
| ```simplify()```     | Return new ```Histogram()``` with fewer dimensions by summing undesired dimensions.|
| ```get()```          | Retrieve count for any field value combination.| 


## associations.py
Contains two classes that serve to identify associations in a ```Histogram()```. ```Associator()``` finds associations for a specific field combination and ```Associations()``` uses ```Associator()``` objects to find all associations.

### Associator()
The associator object identifies associations between different field values (eg. fatalities and amputations) by comparing one group to a larger group that encompasses it. 

Knowing that white males are injured on Tuesday more frequently than black males is not very useful information because it is likely caused by there being more white males than black. Furthermore, knowing that while males are more injured on Tuesday than other days doesn't tell us whether or not white males and Tuesday are associated because it may be that Tuesdays have more injuries overall. Therefore, we must establish a standardized numerical value that represents the actual association between two fields by taking into consideration the overall populations we are sampling from.

As another example, if we want to find the association between amputations and fatalities (diagnosis and disposition), we need to take the same approach. While the likelihood that an amputation is fatal is valuable information, we are more interested in the relative fatality of different diagnoses. Amputations may have a very low likelihood of fatality, but we must compare it to the likelihood that any other diagnosis leads to fatality before we discover whether amputations are relatively likely to be fatal. Therefore, we must take into consideration the extreme infrequency of fatalities in general to get a standardized numerical representation of how associated each field is.

There are two approaches to resolve our dilemma that are mathematically equivalent. One approach is to divide the number of fatal amputations by the number of amputations with any disposition, which yields the likelihood that an amputation is fatal. Then we divide that by the likelihood that any diagnosis is fatal (total fatalities / total of everything) and that yields the association ratio between amputation and fatality.

Identical results would be reached by first dividing fatal amputations by all fatalities (likelihood that a fatality is caused by amputation) and then dividing that by the average likelihood that an amputation is the cause of any disposition (total amputations / total of everything). This results in the exact same association ratio as the first approach.

Both approaches are the same algorithm run in opposite directions. They are also mathematically equivalent since they both result in the same calculation:
```
association between amputations and fatalities = (fatal amputations)*(total of everything) / (fatalities)*(amputations)
```
Since we must also be able to examine the associations within complex subgroups/subpopulations, we approach the problem by looking at a field name combination (diag, disposition, sex, weekday) and finding the associations for any two values for any two of the fields. We start out with a general combination that we know exists (amputation, fatality, male, Tuesday) and work with every association pair and subgroup within that combination. We could do it in reverse, by looking first at every (diag, disposition) association within every (sex, weekday) population, and that would allow us to use the general formula with minimal histogram reshaping, but it would force us to test many orders of magnitude more combinations than actually exist in the data set.

For efficiency, we are forced to limit ourselves to actual combinations that do exist and cycling through different associations within that combination. Likewise, if we wanted to use the general formula, we would have to either reshape our histogram four times for every association ratio or keep several histograms cached at all times (as many as several dozen). Instead, by using an adapted version of the two step algorithm described above, we can calculate broad ratios for many types of subgroups at once and reuse them several times. This increases code complexity, but brings execution time down from minutes or hours to seconds or minutes.

I have a rough idea of a way to optimize the efficiency of an algorithm using the general formula to reduce code complexity without hurting overall efficiency, but the inclusion of subgroups would make it a time intensive process with a lot of testing and benchmarking, and I simply have not yet found the time to work on this.

| Attribute        | Description |
| ---------------- | ----------- |
| ```notable```    | Minimum association ratio (or inverse) to be included.|
| ```significant```| Minimum number of occurrences (statistical significance).|
| ```assoc```      | Associations organized by association then subgroup.|
| ```subgroups```  | Associations organized by subgroup then association.|
| ```memo```       | Record examined situations to avoid redundancy.|
| ```hist```       | ```Histogram()``` object to extract data from.|
| ```relevant```   | All instances of combination that exist.|

| Method                | Description |
| --------------------- | ----------- |
| ```overall_ratios()```| Find general likelihoods (eg. fatality for any diagnosis, not just amputation) |
| ```test()```          | Find association ratio given overall_ratios and histogram.|
| ```add()```           | Save association ratio.|
| ```find()```          | Find the association ratio for every field value combination among a specific field name combination.|

### Associations()
Attributes: self.pairs and self.subgroups contain all association ratios.
```python
>>> self.pairs
{
	pair_type: {
		frozenset(association_pair): {
			frozenset(subgroup/subpopulation): association_ratio
		}
	}
}
```
```python
>>> self.subgroups
{
	subgroup_type: {
		frozenset(subgroup/subpopulation): {
			frozenset(association_pair): association_ratio
		}
	}
}
```

| Method                 | Description |
| ---------------------- | ----------- |
| ```find_all()```       | Use multiprocessing pool to test every field name combination using ```Associator().find()```.|
| ```helper()```         | Runs ```Associator().find()```. Needed for multiprocessing.|
| ```add()```            | Add entire ```Associator()```'s data structures to ```Associations()``` object using ```merge()```.|
| ```merge()```          | Lower level dictionary processor than ```add()```.|
| ```report()```         | Report associations between two fields.|
| ```subgroup_report()```| Report associations for any pairs within a subgroup/subpopulation.|

## analysis.py - Analysis()
Analyze data from ```Histogram()``` and ```Associations()```.

| Attribute                  | Description |
| -------------------------- | ----------- |
| ```hist```                 | ```Histogram()```|
| ```assoc```                | ```Associations()```|
| ```gen_assoc```            | Average association ratios for combo types.|
| ```maxes``` and ```mins``` | Max and min association ratios for combo types.|

| Method                  | Description |
| ----------------------- | ----------- |
| ```make_hist()```       | Create data structure for a histogram plot.|
| ```prep_hist()```       | Used by ```make_hist()``` to include only notable data.|
| ```plot_hist()```       | Use data from ```make_hist()``` to create an actual plot.|
| ```plot_assoc()```      | Use ```make_hist()``` and ```plot_hist()``` for specific purpose of plotting association ratios between two field names.|
| ```nice_plot_assoc()``` | Try ```plot_assoc()``` with various ```notable``` values to create a legible plot containing meaningful data.|
| ```plot_all()```        | Run ```nice_plot_assoc()``` for every field combination.|
| ```table()```           | Draw ascii table.|
| ```table_section()```   | Format data into a section to be interpreted by ```table()```.|
| ```max_helper()```      | Find ```mins``` and ```maxes``` while making hists.|
