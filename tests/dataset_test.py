import os
import unittest
from faceReidDatasets import datasets


class DatasetBaseBasic(unittest.TestCase):
    def setUp(self):
        self.data = [
            ("A", 1),
            ("B", 2),
            ("C", 3),
            ("D", 1),
            ("E", 2),
        ]

    def test_init(self):
        dataset = datasets.DatasetBase(self.data)
        self.assertIsNotNone(dataset)
        sorted_dataset = [("A", 1),
                          ("D", 1),
                          ("B", 2),
                          ("E", 2),
                          ("C", 3)]
        self.assertListEqual(dataset.dataset, sorted_dataset)

    def test_iterator(self):
        dataset = datasets.DatasetBase(self.data)
        sorted_dataset = [("A", 1),
                          ("D", 1),
                          ("B", 2),
                          ("E", 2),
                          ("C", 3)]
        self.assertListEqual(list(dataset), sorted_dataset)

    def test_as_target_to_source_list(self):
        dataset = datasets.DatasetBase(self.data).as_target_to_source_list()
        correct = {1: ["A", "D"],
                   2: ["B", "E"],
                   3: ["C"]}
        self.assertDictEqual(dataset, correct)


class MultiLevelDatasetBaseBasic(unittest.TestCase):
    def setUp(self):
        self.data = {
            "train": [("A", 1),
                      ("B", 2),
                      ("C", 3),
                      ("D", 1),
                      ("E", 2)],
            "test":  [("F", 10),
                      ("G", 11),
                      ("H", 10)]
        }

    def test_init(self):
        dataset = datasets.MutiLevelDatasetBase(self.data)
        self.assertIsNotNone(dataset)
        sorted_dataset = {
            "train": [("A", 1),
                      ("D", 1),
                      ("B", 2),
                      ("E", 2),
                      ("C", 3)],
            "test":  [("F", 10),
                      ("H", 10),
                      ("G", 11)]}
        self.assertListEqual(dataset.dataset["train"].dataset,
                             sorted_dataset["train"])
        self.assertListEqual(dataset.dataset["test"].dataset,
                             sorted_dataset["test"])

    def test_iterator(self):
        dataset = datasets.MutiLevelDatasetBase(self.data)
        self.assertListEqual(sorted(list(dataset)), sorted(["train", "test"]))

    def test_as_target_to_source_list(self):
        dataset = datasets.MutiLevelDatasetBase(self.data)
        dataset = dataset.as_target_to_source_list()
        correct = {
            "train": {1: ["A", "D"],
                      2: ["B", "E"],
                      3: ["C"]},

            "test":  {10: ["F", "H"],
                      11: ["G"]}
        }
        self.assertDictEqual(dataset, correct)


class VGGFace2Tests(unittest.TestCase):
    def setUp(self):
        self.dataset_directory = os.path.join(
            "~",
            "datasets",
            "vggface2"
        )

    def test_init(self):
        dataset = datasets.VGGFace2(self.dataset_directory)
        self.assertIsNotNone(dataset)

        # Test for two subsets.
        self.assertSetEqual(set(dataset), set(["train", "test"]))

        # Check classes are in correct sub directory.
        self.assertTrue("n000002" in (x[1] for x in dataset["train"]))
        self.assertTrue("n000001" in (x[1] for x in dataset["test"]))

    def test_v2s_dataset(self):
        dataset = datasets.VGGFace2(self.dataset_directory).get_v2s()

        # Test for two subsets.
        self.assertSetEqual(set(dataset), set(["train", "test"]))

        # Test for galleries and probes.
        self.assertSetEqual(set(dataset["train"]), set(["gallery", "probe"]))
        self.assertSetEqual(set(dataset["test"]), set(["gallery", "probe"]))

        # Test length of galleries.
        self.assertEqual(len(dataset["train"]["gallery"]), 8631)
        self.assertEqual(len(dataset["test"]["gallery"]), 500)