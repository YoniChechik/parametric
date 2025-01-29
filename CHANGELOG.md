## [0.12.0] - 2025-01-29

- faster serialization

## [0.11.1] - 2025-01-19

- don't copy np array if you don't have to

## [0.11.0] - 2024-12-31

- load_from cls functionality for msgpack and yaml + more test coverage (#89)

## [0.10.0] - 2024-12-29

- numpy + pydantic (#87)
- better errors
- Add tests for handling frozen numpy arrays in BaseParams

## [0.9.0] - 2024-12-03

- Use 'uv run' to execute the release update script
- Numpy + uv (#85)

## [0.8.0] - 2024-12-01

- Works on python 3.10 (#83)
- make-instance-frozen-by-default (#82)

## [0.7.2] - 2024-10-15

- bugfix coerced non defaults

## [0.7.1] - 2024-10-15

- bugfix reading yaml file: None returns if file is empty
- spelling
- update readme (#79)

## [0.7.0] - 2024-10-14

- model_dump_non_defaults (#77)

## [0.6.0] - 2024-10-14

- Enums support (#75)

## [0.5.0] - 2024-10-12

- works with pydantic as base (#73)

## [0.4.2] - 2024-09-09

- manual release bugfix
- add conversion from python object, dumpable or str, and fix more bugs along the way (#71)
- upgrade tests and fix a bunch of bugs (#67)

## [0.4.1] - 2024-08-31

- fix changelog built only on releases and other action fixes
- ___parametric_empty_field (#64)
- `get_defaults_dict` and `get_overrides_dict` and freeze not mandatory on `to_dict` (#63)
- add pycov for coverage (#62)

## [0.4.0] - 2024-08-27

- Return overrides dict (#60)
- support tuple[x] means any amount of var of type x (#59)
- Strict and relaxed type conversion (#58)

## [0.3.0] - 2024-08-20

- Type node (#52)

## [0.2.4] - 2024-08-15

- Automated Changelog + new version release notes (#49)
- Base params as input field (#41)
- Path to str yaml (#40)
- Yaml write tuple as string (#38)
- style: add missing trailing commas (#37)
- style: remove redundant open modes (#36)
- perf: reduce calls for override_from_dict in override_from_cli (#32)
  
## [0.2.3] - 2024-08-08

- add changelog to release (#22)
- add pytest to release action (#14)
- run tests action only on PR (#12)
- manual release PR update (#11)
