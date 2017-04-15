from glob import iglob as glob
import os
from pathlib import Path
import shutil


def parse_copy_paths(path_list, output_root):
    """Parse a list of resource copy instructions

    Returns (Path(source), Path(destination)) for each entry in path_list

    path_list is a list of lists containing a path (as a string)
    and optionally a dictionary which can contain the keys
    'subdir' and 'name'.

    output_root is a pathlib.Path object to a directory which serves
    as the root directory for any copied resources.

    Given an example entry in path_list:

        [source, {'subdir': subdir, 'name': name}]

    source is a (str) path to a file or directory. It can be a glob pattern.
    For example:
        [
            ['../error.html'],
            ['~/Pictures/*.jpg']
        ]

    subdir specifies a subdirectory of the output directory in which to
    place the source. If not given, the destination directory will be
    the root of the output directory. For example:
        [
            ['../error.html'],
            # -> output_root/error.html

            ['~/Pictures/*.jpg', {'subdir': 'images'}]
            # -> output_root/images/*.jpg
        ]

    name allows the source to be renamed. If not given, the filename
    of the source will be used. For example:
        [
            ['../error.html', {'name': '404.html'}]
            # -> output_root/404.html
        ]

    If source is a glob pattern, name should not be specified as each
    source path will be copied to the same output path. For example:
        [
            ['~/Pictures/*.jpg', {'name': 'image.jpg'}]
            # Supposing 1.jpg, 2.jpg
            # ~/Pictures/1.jpg -> output_root/image.jpg
            # ~/Pictures/2.jpg -> output_root/image.jpg
        ]
    """
    # Add empty dict to path_list entries if they only contain the source path
    # Allows for simpler code below
    entries = (e if len(e) == 2 else e + [dict()] for e in path_list)
    src_dst_pairs = []

    for source_pattern, options_dict in entries:
        output_subdir = options_dict.get('subdir', '')
        for source in glob(os.path.expanduser(source_pattern)):
            source = Path(source)
            output_name = options_dict.get('name', source.name)
            pair = (source, Path(output_root, output_subdir, output_name))
            src_dst_pairs.append(pair)

    return src_dst_pairs


def copy_files(path_pairs):
    """Copy files and directories to specified new locations

    path_pairs should be a list of [Path(src), Path(dst)]
    """
    def is_older(path_1, path_2):
        return path_1.stat().st_mtime < path_2.stat().st_mtime

    def copy_directory_tree(source, dest):
        """Walk source directory, copying files into dest if new or newer

        source and dest should both be pathlib.Path objects
        """
        if not dest.exists():
            # Ensure destination dir exists
            dest.mkdir(parents=True, exist_ok=True)

        # Store strings for source and destination roots for path 'rebasing'
        # later on. Both paths are resolved so that the wrong part of the
        # path isn't swapped in the str.replace operation.
        # Not resolving could lead to problems with duplicate path segments.
        source_root = str(source.resolve())
        dest_root = str(dest.resolve())

        for dirpath, dirnames, filenames in os.walk(source_root,
                                                    followlinks=True):
            # Swap source_root for dest_root.
            # Manipulating strings as pathlib doesn't have an alternative
            new_dest = Path(dirpath.replace(source_root, dest_root, 1))

            for file in filenames:
                src_file = source.joinpath(file)
                dst_file = new_dest.joinpath(file)
                if not dst_file.exists() or is_older(dst_file, src_file):
                    shutil.copy(str(src_file), str(dst_file))

            for dirname in dirnames:
                # Make subdirectories ready for copying files
                new_dest.joinpath(dirname).mkdir(exist_ok=True)

    for source, dest in path_pairs:
        if source.is_dir():
            copy_directory_tree(source, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or is_older(dest, source):
                shutil.copy2(str(source), str(dest))


def link_files(path_pairs):
    """Create symlinks to files and directories at specified new locations

    path_pairs should be a list of [Path(src), Path(dst)]
    """
    for source, dest in path_pairs:
        source = source.resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.symlink_to(source, source.is_dir())
        except FileExistsError:
            if dest.resolve() == source:    # symlink points to source
                pass
            else:                           # remove dest and try again
                if dest.is_dir():
                    shutil.rmtree(str(dest))
                else:
                    dest.unlink()
                dest.symlink_to(source, source.is_dir())


def copy_resources(resources, output_root, use_symlinks=False):
    """Place resource files in the output directory.

    If use_symlinks is True, files/directories will be linked, not copied.
    """
    src_dst_pairs = parse_copy_paths(path_list=resources,
                                     output_root=output_root)
    copy_func = copy_files if not use_symlinks else link_files
    copy_func(src_dst_pairs)
