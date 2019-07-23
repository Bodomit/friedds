import os
import re
import abc
import random
import itertools
import sacred
import pickle
import collections
import csv

from typing import List, Set, Tuple

ingrediant = sacred.Ingredient("dataset")


class DatasetBase(collections.abc.Sequence):
    """
    #TODO
    """

    def __init__(self, dataset: List[Tuple[str, str]]):
        self._dataset = sorted(dataset, key=lambda x: (x[1], x[0]))

    @property
    def dataset(self):
        return self._dataset

    def __getitem__(self, key):
        return self.dataset.__getitem__(key)

    def __len__(self):
        return self.dataset.__len__()

    def as_target_to_source_list(self):
        target_to_source_list = {}
        for k, g in itertools.groupby(self._dataset, lambda x: x[1]):
            target_to_source_list[k] = [i[0] for i in g]
        return target_to_source_list

    def as_column_lists(self):
        return list(zip(*self.dataset))


class MutiLevelDatasetBase(abc.ABC):
    """
    #TODO
    """

    def __init__(self, dataset: dict):
        self._dataset = self._populate_dataset(dataset)

    def _traverse(self, node, f):
        if isinstance(node, list) or isinstance(node, DatasetBase):
            return f(node)
        elif isinstance(node, dict):
            return {k: self._traverse(v, f) for k, v in node.items()}
        else:
            raise ValueError("Node must be a list of tuples.")

    def _populate_dataset(self, dataset):
        return self._traverse(dataset, lambda d: DatasetBase(d))

    @property
    def dataset(self):
        return self._dataset

    def __iter__(self):
        return self.dataset.__iter__()

    def __getitem__(self, key):
        return self.dataset[key]

    def as_target_to_source_list(self):
        return self._traverse(self.dataset,
                              lambda d: d.as_target_to_source_list())

    @staticmethod
    def _read_train_test_dataset(dataset_directory, image_ext):
        if not os.path.isdir(dataset_directory):
            raise NotADirectoryError()

        dataset = {
            "train": [],
            "test": []
        }

        for root, dirs, files in os.walk(dataset_directory, topdown=True):
            assert not (dirs and files)

            for file in files:
                if os.path.splitext(file)[1] == image_ext:
                    path = os.path.join(root, file)
                    path = os.path.expanduser(path)
                    path = os.path.abspath(path)
                    label = os.path.basename(os.path.dirname(path))
                    subset = os.path.basename(os.path.dirname(root))
                    dataset[subset].append((path, label))

        return dataset


class ReadableMultiLevelDatasetBase(MutiLevelDatasetBase, abc.ABC):
    """
    #TODO
    """
    def __init__(self, dataset_directory, cache_file_name, **kwargs):
        dataset_directory = os.path.expanduser(dataset_directory)
        dataset_directory = os.path.abspath(dataset_directory)
        self.dataset_directory = dataset_directory
        self.cache_file_name = cache_file_name
        super().__init__(
            self._read_dataset_via_cache(dataset_directory, **kwargs)
        )

    def _read_dataset_via_cache(self,
                                dataset_directory,
                                cache_directory=None):
        if cache_directory is None:
            return self._read_dataset()

        # Read / Store in the cache.
        try:
            cache_directory = os.path.expanduser(cache_directory)
            cache_directory = os.path.abspath(cache_directory)
            cache_path = os.path.join(cache_directory,
                                      self.cache_file_name + ".pickle")
            with open(cache_path, "rb") as f:
                # Prefix dataset directory.
                scrubbed_dataset = pickle.load(f)
                return self._prefix_dataset_directory(scrubbed_dataset)

        except FileNotFoundError:
            dataset = self._read_dataset()
            try:
                # Scrub dataset of dataset_directory.
                scrubbed_dataset = self._scrub_dataset_directory(dataset)
                with open(cache_path, 'wb') as f:
                    pickle.dump(scrubbed_dataset, f)
            finally:
                return dataset

    @abc.abstractmethod
    def _read_dataset(self):
        pass

    def _scrub_dataset_directory(self, dataset):

        def scrub(dataset):
            scrubbed_samples = []
            for sample in dataset:
                scrubbed_samples.append(
                    (sample[0].replace(self.dataset_directory + "/", ""),
                     sample[1]))
            return scrubbed_samples

        return self._traverse(dataset, scrub)

    def _prefix_dataset_directory(self, dataset):

        def prefix(dataset):
            prefixed_samples = []
            for sample in dataset:
                prefixed_samples.append(
                    (
                        os.path.join(self.dataset_directory, sample[0]),
                        sample[1]
                    )
                )
            return prefixed_samples

        return self._traverse(dataset, prefix)


class VGGFace2(ReadableMultiLevelDatasetBase):
    """
    #TODO
    """

    def __init__(self, dataset_directory, **kwargs):
        super().__init__(dataset_directory, "vggface2", **kwargs)

    def _read_dataset(self):
        return self._read_train_test_dataset(self.dataset_directory, ".jpg")

    def get_v2s(self, seed=42):
        random.seed(seed)
        return {
            "train": self._v2s_subset(self.dataset["train"]),
            "test": self._v2s_subset(self.dataset["test"])
        }

    def _v2s_subset(self, subset):
        gallery = []
        probe = []
        for label, paths in subset.as_target_to_source_list().items():
            gallery_candidate = paths.pop(random.randrange(0, len(paths)))
            gallery.append((gallery_candidate, label))
            probe.extend((p, label) for p in paths)
        return {"gallery": DatasetBase(gallery), "probe": DatasetBase(probe)}


class Synthetic(ReadableMultiLevelDatasetBase):
    """
    #TODO
    """

    def __init__(self, dataset_directory, **kwargs):
        super().__init__(dataset_directory, "synth", **kwargs)

    def _read_dataset(self):
        return self._read_train_test_dataset(self.dataset_directory, ".png")

    def get_v2s(self, seed=42):
        random.seed(seed)
        return {
            "train": self._v2s_subset(self.dataset["train"]),
            "test": self._v2s_subset(self.dataset["test"])
        }

    def _v2s_subset(self, subset):
        gallery = []
        probe = []

        regex = "{0}_{1}_{2}_{3}_{4}.png".format(r"\d{5}",  # Model
                                                 r"A",      # Lighting
                                                 r"270",    # Azimuth
                                                 r"90",     # Zenith
                                                 r"256")    # Resolution
        hq_regex = re.compile(regex)

        for label, paths in subset.as_target_to_source_list().items():
            gallery_candidate = [i for i in paths
                                 if hq_regex.match(os.path.basename(i))][0]
            paths.remove(gallery_candidate)
            gallery.append((gallery_candidate, label))
            probe.extend((p, label) for p in paths)
        return {"gallery": DatasetBase(gallery), "probe": DatasetBase(probe)}


class COXFaceDB(ReadableMultiLevelDatasetBase):
    """
    #TODO
    """

    SUBDATASETS = {
        "FACE_32_40": os.path.join("data1", "face_32_40"),
        "FACE_48_60": os.path.join("data1", "face_48_60"),
        "ORIGINAL": os.path.join("data2", "original_still_video")
    }

    def __init__(self, dataset_directory, subdataset="FACE_48_60", **kwargs):
        subdataset_directory = os.path.join(dataset_directory,
                                            self.SUBDATASETS[subdataset])
        super().__init__(subdataset_directory, "coxfacedb", **kwargs)

    def _read_dataset(self):

        if not os.path.isdir(self.dataset_directory):
            raise NotADirectoryError()

        dataset = {
            "still": [],
            "cam1": [],
            "cam2": [],
            "cam3": []
        }

        # Get stills.
        stills_directory = os.path.join(self.dataset_directory, "still")
        for root, _, files in os.walk(stills_directory, topdown=True):
            for file in files:
                if os.path.splitext(file)[1] == ".bmp":
                    path = os.path.join(root, file)
                    path = os.path.expanduser(path)
                    path = os.path.abspath(path)
                    label = file.split("_")[0]
                    dataset["still"].append((path, label))
            break

        # Get videos.
        video_directory = os.path.join(self.dataset_directory, "video")
        for root, dirs, files in os.walk(video_directory, topdown=True):
            assert not (dirs and files)

            for file in files:
                if os.path.splitext(file)[1] == ".bmp":
                    path = os.path.join(root, file)
                    path = os.path.expanduser(path)
                    path = os.path.abspath(path)
                    label = os.path.basename(os.path.dirname(path))
                    subset = os.path.basename(os.path.dirname(root))
                    dataset[subset].append((path, label))

        return dataset

    def get_v2s(self, gallery_and_probe=True, seed=42):
        random.seed(seed)
        return {
            "train": self._v2s_subset("train", gallery_and_probe),
            "test": self._v2s_subset("test", gallery_and_probe)
        }

    def _v2s_subset(self, subset, gallery_and_probe):
        ids = self._get_ids_per_scenario(subset, "v2s")
        return [self._v2s_subset_round(r, gallery_and_probe) for r in ids]

    def _v2s_subset_round(self, ids, gallery_and_probe):
        v2s_subset_round = {
            "still": self._get_v2s_round_camera(ids, "still"),
            "cam1": self._get_v2s_round_camera(ids, "cam1"),
            "cam2": self._get_v2s_round_camera(ids, "cam2"),
            "cam3": self._get_v2s_round_camera(ids, "cam3")
        }

        if gallery_and_probe:
            probe = DatasetBase(
                itertools.chain.from_iterable(
                    v2s_subset_round[c] for c in ["cam1", "cam2", "cam3"]))
            return {
                "gallery": v2s_subset_round["still"],
                "probe": probe
            }
        else:
            return v2s_subset_round

    def _get_id_map_for_scenario(self, scenario):
        filename = "{}_sub_id_list.csv".format(scenario)
        dir_path = os.path.dirname(__file__)
        path = os.path.join(dir_path, "resources", "coxfacedb", filename)
        path = os.path.abspath(path)
        with open(path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            return {k: i.strip() for (k, i) in reader}

    def _get_ids_per_scenario(self, subset, scenario):
        assert scenario in ["v2s", "s2v", "v2v"]
        # Map index in list to actual id.
        id_map = self._get_id_map_for_scenario(scenario)

        # Get ids for each round in each scenario.
        filename = "{}_{}_sub_list.csv".format(scenario, subset)
        dir_path = os.path.dirname(__file__)
        path = os.path.join(dir_path, "resources", "coxfacedb", filename)
        path = os.path.abspath(path)

        rounds = []
        with open(path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            for row in reader:
                rounds.append([id_map[i] for i in row])

        return rounds

    def _get_v2s_round_camera(self, ids, camera):
        return DatasetBase([s for s in self[camera] if s[1] in ids])


class MMF(ReadableMultiLevelDatasetBase):
    """
    #TODO
    """

    def __init__(self, dataset_directory, **kwargs):
        super().__init__(dataset_directory, "mmf", **kwargs)

    def _read_dataset(self):

        if not os.path.isdir(self.dataset_directory):
            raise NotADirectoryError()

        def get_images(subset):
            paths_with_labels = []
            subset_directory = os.path.join(self.dataset_directory, subset)
            for root, dirs, files in os.walk(subset_directory, topdown=True):
                assert not (dirs and files)
                for file in files:
                    if os.path.splitext(file)[1] == ".png":
                        path = os.path.join(root, file)
                        path = os.path.expanduser(path)
                        path = os.path.abspath(path)
                        label = os.path.basename(os.path.dirname(path))
                        paths_with_labels.append((path, label))
            return paths_with_labels

        dataset = {
            "A": get_images("A"),
            "B": get_images("B")
        }

        return dataset
