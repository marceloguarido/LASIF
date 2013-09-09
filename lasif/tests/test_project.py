#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test cases for the project class.

:copyright:
    Lion Krischer (krischer@geophysik.uni-muenchen.de), 2013
:license:
    GNU General Public License, Version 3
    (http://www.gnu.org/copyleft/gpl.html)
"""
import copy
import inspect
import matplotlib.pylab as plt
import obspy
import os
import pytest
import shutil
import time

from lasif.project import Project, LASIFException


# Folder where all the images for comparison are stored.
IMAGES = os.path.join(os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe()))), "baseline_images")
DATA = os.path.join(os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe()))), "data")


@pytest.fixture
def project(tmpdir):
    """
    Fixture returning the initialized example project. It will be a fresh copy
    every time that will be deleted after the test has finished so every test
    can mess with the contents of the folder.
    """
    example_project = os.path.join(DATA, "ExampleProject")
    project_path = os.path.join(str(tmpdir), "ExampleProject")
    shutil.copytree(example_project, project_path)
    return Project(project_path)


def images_are_identical(expected, actual):
    """
    Partially copied from ObsPy
    """
    from matplotlib.testing.compare import compare_images as mpl_compare_images
    from matplotlib.pyplot import rcdefaults
    # set matplotlib builtin default settings for testing
    rcdefaults()
    import locale
    locale.setlocale(locale.LC_ALL, str('en_US.UTF-8'))
    if mpl_compare_images(expected, actual, 0.001) is None:
        return True
    else:
        return False


def test_initalizing_project_in_wrong_path():
    """
    A useful error message should be returned when a project initialized with
    the wrong path.
    """
    with pytest.raises(LASIFException) as excinfo:
        Project("/some/random/path")
    assert "wrong project path" in excinfo.value.message.lower()


def test_project_creation(tmpdir):
    """
    Tests the project creation.
    """
    tmpdir = str(tmpdir)

    pr = Project(tmpdir, init_project="TestProject")

    # Make sure the root path is correct.
    assert pr.paths["root"] == tmpdir

    # Check that all folders did get created.
    foldernames = [
        "EVENTS",
        "DATA",
        "CACHE",
        "LOGS",
        "MODELS",
        "ITERATIONS",
        "SYNTHETICS",
        "KERNELS",
        "STATIONS",
        "OUTPUT",
        os.path.join("ADJOINT_SOURCES_AND_WINDOWS", "WINDOWS"),
        os.path.join("ADJOINT_SOURCES_AND_WINDOWS", "ADJOINT_SOURCES"),
        os.path.join("STATIONS", "SEED"),
        os.path.join("STATIONS", "StationXML"),
        os.path.join("STATIONS", "RESP")]
    for foldername in foldernames:
        assert os.path.isdir(os.path.join(tmpdir, foldername))

    # Make some more tests that the paths are set correctly.
    assert pr.paths["events"] == os.path.join(tmpdir, "EVENTS")
    assert pr.paths["kernels"] == os.path.join(tmpdir, "KERNELS")

    # Assert that the config file has been created.
    assert os.path.exists(os.path.join(pr.paths["root"], "config.xml"))


def test_config_file_creation_and_parsing(tmpdir):
    """
    Tests the creation of a default config file and the reading of the file.
    """
    # Create a new project.
    pr = Project(str(tmpdir), init_project="TestProject")
    del pr

    # Init it once again.
    pr = Project(str(tmpdir))

    # Assert the config file will test the creation of the default file and the
    # reading.
    assert pr.config["name"] == "TestProject"
    assert pr.config["description"] == ""
    assert pr.config["download_settings"]["arclink_username"] is None
    assert pr.config["download_settings"]["seconds_before_event"] == 300
    assert pr.config["download_settings"]["seconds_after_event"] == 3600
    assert pr.domain["bounds"]["minimum_longitude"] == -20
    assert pr.domain["bounds"]["maximum_longitude"] == 20
    assert pr.domain["bounds"]["minimum_latitude"] == -20
    assert pr.domain["bounds"]["maximum_latitude"] == 20
    assert pr.domain["bounds"]["minimum_depth_in_km"] == 0.0
    assert pr.domain["bounds"]["maximum_depth_in_km"] == 200.0
    assert pr.domain["bounds"]["boundary_width_in_degree"] == 3.0
    assert pr.domain["rotation_axis"] == [1.0, 1.0, 1.0]
    assert pr.domain["rotation_angle"] == -45.0


def test_config_file_caching(tmpdir):
    """
    The config file is cached to read if faster as it is read is every single
    time a LASIF command is executed.
    """
    # Create a new project.
    pr = Project(str(tmpdir), init_project="TestProject")
    config = copy.deepcopy(pr.config)
    domain = copy.deepcopy(pr.domain)
    del pr

    # Check that the config file cache has been created.
    cache = os.path.join(str(tmpdir), "CACHE", "config.xml_cache.pickle")
    assert os.path.exists(cache)

    # Delete it.
    os.remove(cache)
    assert not os.path.exists(cache)

    a = time.time()
    pr = Project(str(tmpdir), init_project="TestProject")
    b = time.time()
    time_for_non_cached_read = b - a

    # Assert that everything is still the same.
    assert config == pr.config
    assert domain == pr.domain
    del pr

    # This should have created the cached file.
    assert os.path.exists(cache)

    a = time.time()
    pr = Project(str(tmpdir), init_project="TestProject")
    b = time.time()
    time_for_cached_read = b - a

    # A cached read should always be faster.
    assert time_for_cached_read < time_for_non_cached_read

    # Assert that nothing changed.
    assert config == pr.config
    assert domain == pr.domain


def test_domain_plotting(tmpdir):
    """
    Very simple domain plotting test.
    """
    pr = Project(str(tmpdir), init_project="TestProject")
    pr.plot_domain(show_plot=False)

    baseline_image = os.path.join(IMAGES, "simple_test_domain.png")
    this_image = os.path.join(str(tmpdir), "simple_test_domain.png")

    plt.savefig(this_image)

    assert images_are_identical(baseline_image, this_image)


def test_event_handling(project):
    """
    Tests the event handling.
    """
    # Get the event dictionary. This is a simple mapping between internal event
    # name and QuakeML filename.
    event_dict = project.get_event_dict()
    assert len(event_dict) == 2
    assert "GCMT_event_TURKEY_Mag_5.9_2011-5-19-20-15" in event_dict
    assert event_dict["GCMT_event_TURKEY_Mag_5.9_2011-5-19-20-15"].endswith(
        "GCMT_event_TURKEY_Mag_5.9_2011-5-19-20-15.xml")
    assert event_dict["GCMT_event_TURKEY_Mag_5.1_2010-3-24-14-11"].endswith(
        "GCMT_event_TURKEY_Mag_5.1_2010-3-24-14-11.xml")

    # Test single and multiple event retrieval.
    event_1 = project.get_event("GCMT_event_TURKEY_Mag_5.9_2011-5-19-20-15")
    event_2 = project.get_event("GCMT_event_TURKEY_Mag_5.1_2010-3-24-14-11")
    assert isinstance(event_1, obspy.core.event.Event)
    assert isinstance(event_2, obspy.core.event.Event)
    events = sorted([event_1, event_2])
    assert events == sorted(project.get_all_events())
