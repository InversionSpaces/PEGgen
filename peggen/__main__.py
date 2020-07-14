import argparse
from pprint import pprint

from peggen.__init__ import GrammarParser, PEGGenerator

if __name__ == "__main__":
    args_parser = argparse.ArgumentParser(prog="peggen", 
            description="C++ recursive descent parser generator from formal grammar")

    args_parser.add_argument("grammar", help="file with grammar", type=argparse.FileType("rb"))
    args_parser.add_argument("header", help="file for generated header", type=argparse.FileType("w"))

    args_parser.add_argument("-n", "--name", help="parser class name", default="Parser")
    args_parser.add_argument("-v", "--verbose", help="turn verbose mode on", action="store_true")

    args = args_parser.parse_args()

    parser = GrammarParser(args.grammar)
    grammar = parser.parseGrammar()

    if args.verbose:
        pprint(grammar)

    generator = PEGGenerator(args.name, grammar, args.header)
    generator.generate()
