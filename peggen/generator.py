from tokenize import NAME, STRING, NEWLINE

from peggen.parser import Token, Wildcard, Charset
import peggen.helpers as helpers

class PEGGenerator:
    def __init__(self, name, grammar, fp):
        self.__name = name
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
        header = helpers.CLASS_HEADER.format(self.__name)
        self.__fp.write(header)

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
