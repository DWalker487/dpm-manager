from __future__ import print_function
import argparse as ap
import os
import multiprocessing

def get_args():
    parser = ap.ArgumentParser(
        description="General manager for durham grid storage")
    parser.add_argument(
        "directories",
        help="gfal directories to look in",
        nargs="*")
    parser.add_argument(
        "--search",
        "-s",
        help="search strings for file name",
        nargs="+")
    parser.add_argument(
        "--reject",
        "-r",
        help="reject strings for file name",
        nargs="+")
    parser.add_argument(
        "--copy",
        "-cp",
        help="Copy to current working directory",
        action="store_true",
        default=False)
    parser.add_argument(
        "--move",
        "-mv",
        help="Move file around on grid",
        action="store_true",
        default=False)
    parser.add_argument(
        "--recursive",
        "-rc",
        help="recursive search",
        action = "store_true")
    parser.add_argument(
        "--exclude",
        "--exclude-dirs",
        "-e",
        help="exclude directories matching the string from recursion. Works with wildcard flag if enabled",
        nargs="+", default=None)
    parser.add_argument(
        "--delete", 
        "-d", 
        "-rm", 
        help="Delete selected files",
        action="store_true", default=False)
    parser.add_argument(
        "--long", 
        "-l", 
        help="long mode because Marian is too lazy to type -vp",
        action="store_true", default=False)
    parser.add_argument(
        "--bare", 
        "-b", 
        help="bare output, when you want full filepath info",
        action="store_true", default=False)
    parser.add_argument(
        "--case_insensitive",
        "-i",
        help="case insensitive search",
        action="store_true",
        default=False)
    parser.add_argument(
        "--wildcards",
        "--regexp",
        "-w",
        "-regexp",
        help="Allow wildcards in search",
        action="store_true",
        default=False)
    parser.add_argument(
        "--time",
        "-t",
        help="time output",
        action="store_true",
        default=False)
    parser.add_argument(
        "--output_directory",
        "-o",
        help="output directory for copy")
    thread_count = multiprocessing.cpu_count()
    parser.add_argument(
        "--no_threads",
        "-j",
        help="no. threads to run in parallel for copying from grid/deletions. Default={0}".format(thread_count),
        action="store",
        nargs="?",
        default= thread_count,
        type=int)
    parser.add_argument(
        "--unique_runcards",
        "-u",
        help="""only display unique runcards [WIP].
                Doesn't work if numbers are in file name!""",
        action="store_true")
    parser.add_argument(
        "--permissions",
        "-p",
        help="display permissions for files",
        action="store_true")
    parser.add_argument(
        "--verbose",
        "-v",
        help="Gives extra output for lfc-ls calls",
        action="store_true")
    parser.add_argument(
        "--sort",
        "-st",
        help="Sort output",
        action="store_true")
    parser.add_argument(
        "--sortkey",
        "-sk",
        help="key to sort with",
        type=str)
    parser.add_argument(
        "--reverse",
        "-rev",
        help="Reverse sort",
        action="store_true",
        default=False)
    parser.add_argument(
        "--copy_to_grid",
        "-cpg",
        nargs="+",
        help="""copy files specified to grid directory specified
                with -o flag""")
    parser.add_argument(
        "--user",
        help="user to view filesystem as. Defaults to the one set in .bashrc")

    args = parser.parse_args()
    if args.long:
        args.verbose=True
        args.permissions = True

    if args.output_directory is not None:
        args.output_directory = os.path.expanduser(args.output_directory)
        if not os.path.isdir(args.output_directory):
            os.makedirs(args.output_directory)

    if args.user is not None:
        os.environ["LFC_HOME"]="/grid/pheno/{0}/".format(args.user)

    return args
