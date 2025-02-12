from pathlib import Path

import numpy as np
import yaml


# === CUSTOM YAML REPRESENTERS (ENCODING) ===
def yaml_represent_baseparams(dumper: yaml.Dumper, data: "BaseParams") -> yaml.Node:
    """Serialize BaseParams objects into YAML."""
    return dumper.represent_mapping(
        f"!{data.__class__.__name__}", {name: getattr(data, name) for name in data._get_annotations()}
    )


def yaml_represent_path(dumper: yaml.Dumper, data: Path) -> yaml.Node:
    """Serialize pathlib.Path into YAML."""
    return dumper.represent_scalar("!Path", str(data))


def yaml_represent_ndarray(dumper: yaml.Dumper, data: np.ndarray) -> yaml.Node:
    """Serialize numpy.ndarray into YAML."""
    return dumper.represent_sequence("!ndarray", data.tolist())


# === CUSTOM YAML CONSTRUCTORS (DECODING) ===
def yaml_construct_baseparams(loader: yaml.Loader, node: yaml.Node) -> "BaseParams":
    """Deserialize BaseParams objects from YAML."""
    data = loader.construct_mapping(node)
    return BaseParams(**data)

    return obj


def yaml_construct_path(loader: yaml.Loader, node: yaml.Node) -> Path:
    """Deserialize pathlib.Path from YAML."""
    return Path(loader.construct_scalar(node))


def yaml_construct_ndarray(loader: yaml.Loader, node: yaml.Node) -> np.ndarray:
    """Deserialize numpy.ndarray from YAML."""
    return np.array(loader.construct_sequence(node))


# === REGISTER CUSTOM YAML TYPES ===
yaml.add_representer(BaseParams, yaml_represent_baseparams)
yaml.add_representer(Path, yaml_represent_path)
yaml.add_representer(np.ndarray, yaml_represent_ndarray)

yaml.add_constructor("!BaseParams", yaml_construct_baseparams, Loader=yaml.SafeLoader)
yaml.add_constructor("!Path", yaml_construct_path, Loader=yaml.SafeLoader)
yaml.add_constructor("!ndarray", yaml_construct_ndarray, Loader=yaml.SafeLoader)


class CustomYAMLLoader(yaml.SafeLoader):
    """Custom YAML Loader to handle special types."""

    pass


# Register constructors in the custom loader
CustomYAMLLoader.add_constructor("!BaseParams", yaml_construct_baseparams)
CustomYAMLLoader.add_constructor("!Path", yaml_construct_path)
CustomYAMLLoader.add_constructor("!ndarray", yaml_construct_ndarray)
