import sys
from tokenize import tokenize, NAME, STRING, NEWLINE
from pprint import pprint
from io import BytesIO
from collections import namedtuple

import helpers

Token = namedtuple("Token", ["type", "str"])


class Tokenizer:
    def __init__(self, fp):
        self.__tokenizer = tokenize(fp.readline)
        self.__tokens = list()
        self.__pos = 0

        try:
            next(self.__tokenizer)  # To skip encoding
        except StopIteration:
            pass

    def get_pos(self):
        return self.__pos

    def set_pos(self, pos):
        self.__pos = pos

    def get_token(self):
        token = self.peek_token()
        if (token):
            self.__pos += 1
        return token

    def peek_token(self):
        if self.__pos < len(self.__tokens):
            return self.__tokens[self.__pos]

        try:
            token = Token(*next(self.__tokenizer)[:2])
            self.__tokens.append(token)
            return token
        except StopIteration:
            return None


class Parser:
    def __init__(self, fp):
        self.__tokenizer = Tokenizer(fp)

    def get(self):
        return self.__tokenizer.get_pos()

    def set(self, pos):
        self.__tokenizer.set_pos(pos)

    def expect(self, arg):
        token = self.__tokenizer.peek_token()
        if token.str == arg or token.type == arg:
            return self.__tokenizer.get_token()
        return None


Rule = namedtuple("Rule", ["name", "alts"])

Wildcard = namedtuple("Wildcard", ["op", "alts"])
Charset = namedtuple("Charset", ["op", "chars"])


class GrammarParser(Parser):

    def parseCharset(self):
        pos = self.get()

        if not self.expect("["):
            self.set(pos)
            return None

        chars = self.expect(STRING)
        if not chars:
            self.set(pos)
            return None

        if not self.expect("]"):
            self.set(pos)
            return None

        if self.expect("+"):
            return Charset("+", chars.str)

        if self.expect("*"):
            return Charset("*", chars.str)

        if self.expect("?"):
            return Charset("?", chars.str)

        return Charset("", chars.str)

    def parseWildcard(self):
        pos = self.get()

        if not self.expect("("):
            self.set(pos)
            return None

        alts = self.parseAlternatives()
        if not alts:
            self.set(pos)
            return None

        if not self.expect(")"):
            self.set(pos)
            return None

        if self.expect("+"):
            return Wildcard("+", alts)

        if self.expect("*"):
            return Wildcard("*", alts)

        if self.expect("?"):
            return Wildcard("?", alts)

        return Wildcard("", alts)

    def parseAlternatives(self):
        alt = self.parseAlternative()
        if not alt:
            return None

        alts = [alt]
        while True:
            if not self.expect("|"):
                return alts

            alt = self.parseAlternative()

            if not alt:
                return alts

            alts.append(alt)

    def parseAlternative(self):
        token = (self.expect(NAME) or
                 self.expect(STRING) or
                 self.parseCharset() or
                 self.parseWildcard())

        if not token:
            return None

        alt = [token]
        while True:
            token = (self.expect(NAME) or
                     self.expect(STRING) or
                     self.parseCharset() or
                     self.parseWildcard())

            if not token:
                return alt

            alt.append(token)

    def parseRule(self):
        pos = self.get()

        name = self.expect(NAME)
        if not name:
            self.set(pos)
            return None

        if not self.expect("->"):
            self.set(pos)
            return None

        alts = self.parseAlternatives()
        if not alts:
            self.set(pos)
            return None

        if not self.expect(NEWLINE):
            self.set(pos)
            return None

        return Rule(name.str, alts)

    def parseGrammar(self):
        rule = self.parseRule()
        retval = list()

        while rule:
            retval.append(rule)
            rule = self.parseRule()

        return retval


class PEGGenerator:
    def __init__(self, grammar, fp):
        self.__grammar = grammar
        self.__fp = fp
        self.depth = 0

    def part(self, part):
        if isinstance(part, Token):
            if part.type == STRING:
                expect = helpers.TMP_EXPECT.format(
                    part.str, len(part.str) - 2
                )

                self.__fp.write(expect)

            elif part.type == NAME:
                parse = helpers.TMP_PARSE.format(
                    part.str
                )

                self.__fp.write(parse)

            self.__fp.write(helpers.TMP_ESCAPE)
            self.__fp.write(helpers.TMP_PUSH_BACK)

        if isinstance(part, Wildcard):
            header = helpers.WILDCARD_HEADER.format(
                part.op, part.alts
            )
            self.__fp.write(header)

            if part.op == "":
                self.alts(part.alts)

                self.__fp.write(helpers.TMP_POP)
                self.__fp.write(helpers.TMP_ESCAPE)
                self.__fp.write(helpers.INSERT_CHILDS)

            elif part.op == "+":
                self.alts(part.alts)

                self.__fp.write(helpers.TMP_POP)
                self.__fp.write(helpers.TMP_ESCAPE)
                self.__fp.write(helpers.INSERT_CHILDS)

                self.__fp.write(helpers.ENDLESS_LOOP_HEADER)

                self.alts(part.alts)

                self.__fp.write(helpers.TMP_POP)
                self.__fp.write(helpers.INSERT_IF_TMP_ELSE_BREAK)

                self.__fp.write(helpers.ENDLESS_LOOP_FOOTER)

            elif part.op == "?":
                self.alts(part.alts)

                self.__fp.write(helpers.TMP_POP)
                self.__fp.write(helpers.INSERT_IF_TMP)

            elif part.op == "*":
                self.__fp.write(helpers.ENDLESS_LOOP_HEADER)

                self.alts(part.alts)

                self.__fp.write(helpers.TMP_POP)
                self.__fp.write(helpers.INSERT_IF_TMP_ELSE_BREAK)

                self.__fp.write(helpers.ENDLESS_LOOP_FOOTER)

            footer = helpers.WILDCARD_FOOTER.format(
                part.op, part.alts
            )
            self.__fp.write(footer)

        if isinstance(part, Charset):
            symbol = helpers.CTMP_SYMBOL.format(part.chars)
            self.__fp.write(symbol)

            if part.op == "":
                self.__fp.write(helpers.CTMP_ESCAPE)
                self.__fp.write(helpers.CREATE_CHILD)

            elif part.op == "+":
                self.__fp.write(helpers.CTMP_ESCAPE)
                self.__fp.write(helpers.CREATE_CHILD)

                add = helpers.ADD_WHILE_CTMP.format(part.chars)
                self.__fp.write(add)

            elif part.op == "?":
                self.__fp.write(helpers.CREATE_IF_CTMP)

            elif part.op == "*":
                self.__fp.write(helpers.CREATE_IF_CTMP)

                add = helpers.ADD_WHILE_CTMP.format(part.chars)
                self.__fp.write(add)

    def alt(self, alt):
        self.__fp.write(helpers.TOP_NEW_NODE)

        for part in alt:
            self.part(part)

    def alts(self, alts):
        self.depth += 1

        header = helpers.ALTS_HEADER.format(alts)
        self.__fp.write(header)

        for alt in alts:
            header = helpers.ALT_HEADER.format(alt)
            self.__fp.write(header)

            self.alt(alt)

            footer = helpers.ALT_FOOTER.format(alt)
            self.__fp.write(footer)

        footer = helpers.ALTS_FOOTER.format(alts, self.depth)
        self.__fp.write(footer)

        self.depth -= 1

    def generate(self):
        self.__fp.write(helpers.CLASS_HEADER)

        name = self.__grammar[0].name
        parse = helpers.PARSE_METHOD.format(name)
        self.__fp.write(parse)

        for rule in self.__grammar:
            header = helpers.RULE_HEADER.format(rule.name)
            self.__fp.write(header)

            self.alts(rule.alts)

            footer = helpers.RULE_FOOTER.format(rule.name)
            self.__fp.write(footer)

        self.__fp.write(helpers.CLASS_FOOTER)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} GRAMMAR_FILE HEADER_FILE")
        print("Takes BNF grammar in GRAMMAR_FILE")
        print("And generates C++ parser in HEADER_FILE")

        exit(0)

    with open(sys.argv[1], "rb") as fin:
        parser = GrammarParser(fin)
        grammar = parser.parseGrammar()

    print("Parsed grammar:")
    pprint(grammar)

    with open(sys.argv[2], "w") as fout:
        generator = PEGGenerator(grammar, fout)
        generator.generate()
