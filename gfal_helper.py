#!/usr/bin/env python3
from __future__ import print_function
import config
import datetime
import fnmatch
import itertools
import lscp_args
import multiprocessing as mp
import os
import re
import sre_constants
import string
import subprocess as sp
import sys


default_user = config.default_user
file_count_reprint_no = config.file_count_reprint_no
pcol_def = config.protocol_default
pcol_ls = config.protocol_list
pcol_rm = config.protocol_delete
pcol_down = config.protocol_download
pcol_up = config.protocol_upload
pcol_mv = config.protocol_move
DPM = pcol_def+config.DPM
dir_colour = config.dir_colour
exe_colour = config.exe_colour
use_fnmatch = config.use_fnmatch


def _wrap_str(string, colour):
    return "\033[{1}m{0}\033[0m".format(string, colour)


class DPMFile():
    def __init__(self, line, directory):
        self.directory = directory
        self.fname = line.strip()
        self.__split = [x.strip() for x in line.split()]
        self.fname = self.__split[-1]
        if self.directory == self.fname:
            self.fname = os.path.basename(self.fname)
            self.directory = os.path.dirname(self.directory)
        self.fname_print = self.fname

        self.time = self.__split[-2]
        self.month = self.__split[-4]
        self.day = self.__split[-3]
        self.permissions = self.__split[0]
        if self.permissions[0]=="d":
            self.is_dir = True
        else:
            self.is_dir = False

    def full_name(self):
        return os.path.join(self.directory, self.fname)


    def return_line_as_str(self, args):
        ln = self.__split

        if not args.bare:
            if self.permissions[0]=="d":
                self.fname_print = _wrap_str(self.fname, dir_colour)
            elif "x" in self.permissions:
                self.fname_print = _wrap_str(self.fname, exe_colour)


        retstr = ""

        if args.verbose:
            retstr += "{0} {1} {2:15}".format(self.month, self.day,
                                           self.time)
        if args.permissions:
            retstr += " {0:10} ".format(self.permissions)

        retstr += "{0:50}".format(self.fname_print)

        if args.bare:
            retstr = " ".join(retstr.split())
        return retstr

    def __repr__(self):
        ln = self.__split
        return "{6:4e5} {0} {1} {4} {5:17} No. files: {2:7}  {3}".format(self.time, ln[1], ln[0],*ln[-4:])


def bash_call(*args, **kwargs):
    child = sp.Popen(args, stdout=sp.PIPE, stderr=sp.PIPE,
                     **kwargs)
    streamdata = child.communicate()[0].split(b"\n")

    if child.returncode != 0:
        print("ERROR: call {0} failed with non-zero error code {1}".format(" ".join(args), child.returncode), file=sys.stderr)
    return [f.decode('utf-8') for f in streamdata
            if f != b""]


def get_usable_threads(no_threads, no_files):
    return max(min(no_threads, no_files), 1)


def copy_file_to_grid(infile, griddir, file_no, no_files):
    infile_loc, infile_name = os.path.split(infile)
    infile = os.path.join(os.getcwd(), infile)
    lcgname = os.path.join(DPM.replace(pcol_def, pcol_up, 1), griddir, infile_name)
    filename = "file://{0}".format(infile)
    print("Copying {1} to {0} [{2}/{3}]".format(filename, lcgname,
                                                file_no+1, no_files))
    bash_call("gfal-copy", filename, lcgname)


def delete_file_from_grid(xfile, file_no, no_files):
    lcgname = xfile.full_name().replace(pcol_def, pcol_rm, 1)
    print("Deleting {0} [{1}/{2}]".format(lcgname, file_no+1, no_files))

    if xfile.is_dir:
        retval = bash_call("gfal-rm", lcgname, "-r")
    else:
        retval = bash_call("gfal-rm", lcgname)


def copy_DPM_file_to_local(DPMfile, localfile):
    bash_call("gfal-copy", DPMfile, localfile)


def copy_to_dir(infile, args, file_no, no_files):
    lcgname = infile.full_name().replace(pcol_def, pcol_down, 1)
    if args.output_directory is not None:
        xfile = os.path.join(args.output_directory, infile.fname)
    else:
        xfile = os.path.join(os.getcwd(), infile.fname)
    print("Copying {0} to {1} [{2}/{3}]".format(lcgname, xfile,
                                                file_no+1, no_files))
    copy_DPM_file_to_local(lcgname, xfile)


def move_to_dir(infile, args, file_no, no_files):
    _from, _to = args.directories
    oldlcgname = "{0}{1}/{2}".format(DPM.replace(pcol_def, pcol_mv, 1), _from, infile.fname)
    newlcgname = "{0}{1}/{2}".format(DPM.replace(pcol_def, pcol_mv, 1), _to, infile.fname)

    infile_dir = os.path.join(_from, infile.fname)
    outfile_dir = os.path.join(_to, infile.fname)
    print("Moving {0} from {1} to {2} [{3}/{4}]".format(infile.fname, _from, _to,
                                                file_no+1, no_files))

    bash_call("gfal-rename", oldlcgname, newlcgname)


def create_dir(directory):
    bash_call("gfal-mkdir", "-p", "{0}{1}".format( DPM, directory ))


def _search_match(search_str, fileobj, args):
    if args.wildcards:
        if use_fnmatch:
            return fnmatch.fnmatch(search_str, fileobj.fname)
        try:
            if re.search(search_str, fileobj.fname) is not None:
                return True
            else:
                return False
        except sre_constants.error:
            print(_wrap_str("Invalid regexp entered. Don't be silly.", 31))
            sys.exit(-1)
    else:
        if args.case_insensitive:
            return search_str.upper() in fileobj.fname.upper()
        else:
            return search_str in fileobj.fname


def is_excluded(fobj, args):
    if args.exclude is None:
        return False
    else:
        for search_str in args.exclude:
            matched =  _search_match(search_str, fobj, args)
            if matched:
                return True
    return False


def do_search(files, args):
    for search_str in args.search:
        files = [x for x in files if _search_match(search_str, x, args)]
    return files


def do_reject(files, args):
    for rej_str in args.reject:
        files = [x for x in files if not _search_match(rej_str, x, args)]
    return files


def do_copy(DPMdirectory, args, files):
    no_files = len(files)
    print("> Copying {0} file{1}...".format(no_files,
                                            ("" if no_files == 1 else "s")))
    pool = mp.Pool(processes=get_usable_threads(args.no_threads, no_files))
    pool.starmap(copy_to_dir, zip(files, itertools.repeat(args),
                                  range(len(files)),
                                  itertools.repeat(no_files)), chunksize=1)


def do_move(DPMdirectory, args, files):
    try:
        assert len(args.directories) == 2
    except AssertionError as e:
        print("Cannot perform move of files between directories. {0} specified".format(len(args.directories)))
        return
    no_files = len(files)
    print("> Moving {0} file{1}...".format(no_files,
                                            ("" if no_files == 1 else "s")))
    create_dir(args.directories[1])
    pool = mp.Pool(processes=get_usable_threads(args.no_threads, no_files))
    pool.starmap(move_to_dir, zip(files, itertools.repeat(args),
                                  range(len(files)),
                                  itertools.repeat(no_files)), chunksize=1)


def do_delete(DPMdirectory, files, args):
    no_files = len(files)
    query_str = "Do you really want to delete {1} {0} file{2} [y/n]?\n".format(
        no_files,
        ("this" if no_files == 1 else "these"),
        ("" if no_files == 1 else "s"))
    deletion_confirmed = get_yes_no(input(query_str))
    if deletion_confirmed:
        print("> Deleting files...")
        pool = mp.Pool(processes=get_usable_threads(args.no_threads, no_files))
        pool.starmap(delete_file_from_grid, zip(files,
                                                range(len(files)),
                                                itertools.repeat(no_files)),
                     chunksize=1)


def get_yes_no(string):
    if string.lower().startswith("y"):
        return True
    return False


def get_unique_runcards(files):
    remove_digits = str.maketrans('', '', string.digits)
    return list(set(f.fname.translate(remove_digits).replace("-.", "-SEED.")
                    for f in files if not f.is_dir))


def lfc_ls_obj_wrapper(*args):
    if len(args) == 0:
        args = [""]
    ret_files = []
    for folder in args:
        cmd_args = ["{0}{1}".format(DPM.replace(pcol_def, pcol_ls, 1), folder)]
        cmd_args += ["-l", "-H"]
        files = bash_call("gfal-ls", *cmd_args)
        ret_files += [
            DPMFile( x.replace(pcol_ls, pcol_def, 1), cmd_args[0].replace(pcol_ls, pcol_def, 1))
            for x in files ]
    return ret_files


def print_files(files, args):
    print("\n".join(i.return_line_as_str(args) for i in files))


def print_bare_files(files, args, dir):
    # TODO make this more elegant
    printstr = []
    for i in files:
        if not i.is_dir:
            ret = i.return_line_as_str(args).split()
            printstr.append(" ".join(ret[:-1]+[os.path.join(dir, ret[-1])]))
    print("\n".join(printstr))


def sort_files(files, args):
    if not args.sort:
        return files
    else:
        if args.sortkey is not None:
            sortattr = args.sortkey
        else:
            sortattr = "fname"
        files.sort(key=lambda f : getattr(f,sortattr), reverse = args.reverse)
        return files


def parse_directory(DPMdirectory, recursive=False, bare=False, exclude_dirs=None):
    files = lfc_ls_obj_wrapper(DPMdirectory)

    if recursive:
        for f in files:
            if f.is_dir:
                if not is_excluded(f, args):
                    parse_directory(os.path.join(DPMdirectory, f.fname), recursive=recursive,
                                    bare=bare, exclude_dirs=exclude_dirs)

    files = sort_files(files, args)
    if args.search is not None:
        files = do_search(files, args)
    if args.reject is not None:
        files = do_reject(files, args)
    no_files = len([f for f in files if not f.is_dir])
    no_dirs = len([f for f in files if f.is_dir])
    something_found = no_files+no_dirs > 0

    punctuation = ":" if no_files>0 else "."
    if not bare:
        if no_files >0:
            print(_wrap_str("> {0} matching files found in {1}{2} ".format(no_files,
                                                                           DPMdirectory,
                                                                           punctuation),32))
        if no_dirs>0:
            print(_wrap_str("> {0} matching directories found in {1}{2} ".format(no_dirs,
                                                                           DPMdirectory,
                                                                           punctuation),32))

    if something_found:
        if bare:
            print_bare_files(files, args, DPMdirectory)
        elif not args.unique_runcards:
            print_files(files, args)
        else:
            unique_runcards = get_unique_runcards(files)
            print("\n".join(i for i in unique_runcards))
            print(_wrap_str("> {0} unique runcards".format(len(unique_runcards)), 34))
        if no_files+no_dirs > file_count_reprint_no and not bare:
            if no_files >0:
                print(_wrap_str("> {0} files matched".format(no_files), 32))
            if no_dirs >0:
                print(_wrap_str("> {0} directories matched".format(no_dirs), 32))
    else:
        return

    if args.copy:
        do_copy(DPMdirectory, args, files)
    if args.move:
        do_move(DPMdirectory, args, files)
    if args.delete:
        do_delete(DPMdirectory, files, args)


def do_copy_to_grid(args):
    if args.output_directory is not None:
        output = args.output_directory
    else:
        print("Please specify an output directory with -o.")
        return
    no_files = len(args.copy_to_grid)
    for file_no, xfile in enumerate(args.copy_to_grid):
        copy_file_to_grid(xfile, output, file_no, no_files)


if __name__ == "__main__":
    args = lscp_args.get_args()
    if args.user:
        DPM = DPM.format(args.user)
    else:
        DPM = DPM.format(default_user)

    if args.time:
        start_time = datetime.datetime.now()

    if args.copy_to_grid is not None:
        do_copy_to_grid(args)

    elif args.directories == []:
        parse_directory("", recursive = args.recursive, bare=args.bare,
                        exclude_dirs = args.exclude)
    else:
        if not args.move:
            for DPMdirectory in args.directories:
                parse_directory(DPMdirectory, recursive = args.recursive,
                                bare=args.bare, exclude_dirs=args.exclude)
        else:
            for DPMdirectory in args.directories[:1]:
                parse_directory(DPMdirectory, bare=args.bare)

    if args.time:
        end_time = datetime.datetime.now()
        total_time = (end_time-start_time).__str__().split(".")[0]
        print("> Time taken {0}".format(total_time))
