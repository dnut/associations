# 0.0 Alpha & Beta releases
Alpha and Beta releases do not precisely follow semantic version numbering. Backwards incompatible changes occur at secondary numeral changes (eg. 0.1 to 0.2) instead of primary numeral changes (eg. 1.0 to 2.0). Secondary numeral changes may also simply represent new features while maintaining backwards compatibility.

## 0.1.0 - Initial Release (2016-12-30)
First adaptation from specific solution to module.

## 0.2.0 - Not Released (2017-01-01)
This version saw major improvements but was not released because there were some issues.
### Improvements
Use general formula for association ratio. The internals of Associator().find() are completely new.

The following are deprecated by this change:
- Associator().overall_ratios()
- Associator().test()
- Associator().relevant
- Associator().memo

### New Features
Further encapsulate Histogram() object by providing the following:
- Histogram().reduce() (this method is also used to shorten Histogram.simplify())
- Histogram().slice()
- Histogram().nonzeros()
- Histogram().nonzero_indices

## 0.2.1 - Initial Beta Release (Release 2) (2017-01-01)
### Bug Fixes
Reintroduce support for Associator().notable and Associator().significant.
### Improvements
Clean up excess code, removed old methods, renamed new methods to take their place.

## ???
### New Features
make_dir()
### Improvements
- Table methods have been split off from Analysis() into its own class, AsciiTable().
- Use make_dir() and os.path.join() for better compatibility with a broader range of uses.