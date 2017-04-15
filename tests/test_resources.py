import unittest
from majestic import load_settings
from majestic.resources import (
    copy_files, copy_resources,
    link_files, parse_copy_paths
    )

import os
from pathlib import Path
import shutil
import time


TESTS_DIR = Path(__file__).resolve().parent


class TestCopyFiles(unittest.TestCase):
    """Test the file copying/symlinking features"""
    def setUp(self):
        os.chdir(str(TESTS_DIR.joinpath('test-copy')))
        self.settings = load_settings()
        self.output_dir = Path(self.settings['paths']['output root'])

    def tearDown(self):
        try:
            shutil.rmtree(str(self.output_dir))
        except FileNotFoundError:
            pass

    def test_parse_copy_paths_simple(self):
        """parse_copy_paths produces list of src/dst pairs for simple list

        This test handles the most simple scenario: a list of paths to
        copy to the output directory with no new subdirectories or renames.
        """
        copy_paths = [
            ['404.html'],
            ['images']
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('404.html')),
            (Path('images'), self.output_dir.joinpath('images'))
            ]
        result = parse_copy_paths(path_list=copy_paths,
                                  output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_glob(self):
        """parse_copy_paths produces list of src/dst pairs for glob path

        In this test, check that a glob path produces the expected list of
        src/dst pairs — importantly that one path rule can produce several
        such pairs.
        """
        copy_paths = [
            ['images/*.jpg']
            ]
        expected = [
            (Path('images/copytest1.jpg'),
             self.output_dir.joinpath('copytest1.jpg')),
            (Path('images/copytest2.jpg'),
             self.output_dir.joinpath('copytest2.jpg'))
            ]
        result = parse_copy_paths(path_list=copy_paths,
                                  output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_subdir(self):
        """parse_copy_paths result includes specified subdir

        In this test, check that a path specifying a subdir produces a
        destination that includes the subdir.
        """
        copy_paths = [
            ['404.html', {'subdir': 'static'}],
            ['images', {'subdir': 'static'}]
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('static/404.html')),
            (Path('images'), self.output_dir.joinpath('static/images'))
            ]
        result = parse_copy_paths(path_list=copy_paths,
                                  output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_name(self):
        """parse_copy_paths result includes specified new name

        In this test, check that a path specifying a name produces a
        destination whose last component is the new name.
        """
        copy_paths = [
            ['404.html', {'name': 'error.html'}],
            ['images', {'name': 'img'}]
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('error.html')),
            (Path('images'), self.output_dir.joinpath('img'))
            ]
        result = parse_copy_paths(path_list=copy_paths,
                                  output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_parse_copy_paths_subdir_and_name(self):
        """parse_copy_paths result includes specified subdir and name

        In this test, check that a path specifying both a subdir and
        a new name produces a destination which includes both
        """
        copy_paths = [
            ['404.html', {'subdir': 'static', 'name': 'error.html'}],
            ['images', {'subdir': 'static', 'name': 'img'}]
            ]
        expected = [
            (Path('404.html'), self.output_dir.joinpath('static/error.html')),
            (Path('images'), self.output_dir.joinpath('static/img'))
            ]
        result = parse_copy_paths(path_list=copy_paths,
                                  output_root=self.output_dir)
        self.assertEqual(expected, result)

    def test_copy_files_simple(self):
        """copy_files copies sources to the specified output

        Both files and directories should be copied.

        copy_files should create enclosing folders as necessary.
        """
        paths = [
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('images'), self.output_dir.joinpath('images')]
            ]
        copy_files(paths)
        for source, dest in paths:
            self.assertTrue(dest.exists())
            self.assertEqual(source.stat().st_size, dest.stat().st_size)

    def test_copy_files_dir_updated(self):
        """copy_files copies modified files inside target directory

        This tests whether copy_files checks the files inside the
        target directory for modifications rather than just testing
        the containing directory (which may not have its mtime
        changed by a modification to a file it contains).
        """
        src = Path('images')
        dst = self.output_dir.joinpath('images')
        paths = [[src, dst]]

        test_filename = 'copytest1.jpg'
        src_file = src.joinpath(test_filename)
        dst_file = dst.joinpath(test_filename)

        self.output_dir.mkdir()
        shutil.copytree(str(src), str(dst))     # Manually copy over directory

        old_dst_mtime = dst_file.stat().st_mtime
        self.assertEqual(src_file.stat().st_mtime, old_dst_mtime)

        time.sleep(1)   # Ensure m_time will be different
        src_file.touch()
        # Check src now has a different mtime
        self.assertNotEqual(src_file.stat().st_mtime, old_dst_mtime)

        copy_files(paths)
        new_dst_mtime = dst_file.stat().st_mtime
        # Check that modified source has indeed been copied
        self.assertNotEqual(old_dst_mtime, new_dst_mtime)

    def test_copy_files_dir_exists(self):
        """When copying dirs, copy_files should remove existing dest dir

        This is to avoid shutil.copytree raising FileExistsError.

        It's necessary to sleep for a second before touching the folder to
        ensure the modification date is properly changed, and ensure that
        copy_files doesn't skip the folder (making the test useless!).
        """
        src = Path('images')
        dst = self.output_dir.joinpath('images')
        paths = [[src, dst]]

        dst.mkdir(parents=True)  # Ensure destination dir exists
        time.sleep(1)            # Modification date resolution
        src.touch()              # Ensure src is newer (so should be copied)

        try:
            copy_files(paths)
        except FileExistsError:
            self.fail('destination directory was not removed')

    def test_link_files_simple(self):
        """link_files links to sources at the specified output locations

        Both files and directories should be linked.

        link_files should create enclosing folders as necessary.
        """
        paths = [
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('404.html'), self.output_dir.joinpath('404.html')],
            [Path('images'), self.output_dir.joinpath('images')]
            ]
        link_files(paths)
        for source, dest in paths:
            self.assertTrue(dest.is_symlink())
            self.assertEqual(source.stat().st_size, dest.stat().st_size)

    def test_copy_resources(self):
        """copy_resources copies specified files"""
        expected_walk = [
            ('output', ['resources', 'static'], []),
            ('output/resources', ['img'], []),
            ('output/resources/img', [], ['copytest1.jpg', 'copytest2.jpg']),
            ('output/static', [], ['error.html']),
        ]
        copy_resources(
            resources=self.settings['resources'],
            output_root=self.settings['paths']['output root'])
        self.assertEqual(sorted(expected_walk), sorted(os.walk('output')))

    def test_copy_resources_links(self):
        """copy_resources correctly uses symlinks when use_symlinks=True"""
        locations = [
            self.output_dir.joinpath('static', 'error.html'),
            self.output_dir.joinpath('resources', 'img'),
        ]

        copy_resources(
            resources=self.settings['resources'],
            output_root=self.settings['paths']['output root'],
            use_symlinks=True)
        for loc in locations:
            self.assertTrue(loc.is_symlink())
