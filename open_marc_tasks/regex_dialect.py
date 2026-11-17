import re


class RegexDialectError(ValueError):
    """Raised when a regex is outside the task format dialect."""


_LITERAL_ESCAPES = frozenset(".?$/\\()[]+*{}|^-")
_SPECIAL_REPLACEMENTS = frozenset("$+&{`'_")


class _Parser:
    def __init__(self, pattern):
        self.pattern = pattern
        self.index = 0

    def _error(self, message):
        raise RegexDialectError(message)

    def _alternation(self, grouped=False):
        branches = []
        while True:
            translated, nullable = self._sequence()
            branches.append((translated, nullable))
            if self.index >= len(self.pattern) or self.pattern[self.index] != "|":
                break
            self.index += 1

        if grouped:
            if self.index >= len(self.pattern) or self.pattern[self.index] != ")":
                self._error("unclosed group")
            self.index += 1

        return "|".join(item[0] for item in branches), any(
            item[1] for item in branches
        )

    def _sequence(self):
        parts = []
        nullable = True
        while self.index < len(self.pattern) and self.pattern[self.index] not in ")|":
            translated, atom_nullable, can_repeat = self._atom()
            quantifier = self._quantifier(atom_nullable)
            if quantifier[0]:
                if not can_repeat:
                    self._error("quantifier cannot follow an anchor")
                translated += quantifier[0]
                atom_nullable = quantifier[1]
                if self.index < len(self.pattern) and self.pattern[self.index] in "+?":
                    self._error("lazy and possessive quantifiers are not supported")
            parts.append(translated)
            nullable = nullable and atom_nullable
        return "".join(parts), nullable

    def _atom(self):
        char = self.pattern[self.index]
        self.index += 1

        if char == "\\":
            if self.index >= len(self.pattern):
                self._error("trailing backslash")
            escaped = self.pattern[self.index]
            self.index += 1
            if escaped in "dws":
                return "\\" + escaped, False, True
            if escaped in _LITERAL_ESCAPES:
                return "\\" + escaped, False, True
            self._error("unsupported escape \\" + escaped)
        if char == "[":
            return self._character_class(), False, True
        if char == "(":
            if self.index < len(self.pattern) and self.pattern[self.index] == "?":
                self._error("special groups are not supported")
            contents, nullable = self._alternation(grouped=True)
            return "(" + contents + ")", nullable, True
        if char == ".":
            return ".", False, True
        if char == "^":
            return "^", True, False
        if char == "$":
            return r"\Z", True, False
        if char in "*+?{":
            self._error("quantifier has no preceding atom")
        if char in ")]|":
            self._error("unexpected closing delimiter")
        if char == "}":
            self._error("unmatched closing brace")
        return re.escape(char), False, True

    def _quantifier(self, atom_nullable):
        if self.index >= len(self.pattern):
            return "", False
        char = self.pattern[self.index]
        if char == "*":
            self.index += 1
            return "*", True
        if char == "+":
            self.index += 1
            return "+", atom_nullable
        if char == "?":
            self.index += 1
            return "?", True
        if char != "{":
            return "", False

        start = self.index
        self.index += 1
        minimum = self._digits()
        if minimum is None:
            self._error("invalid repetition count")
        maximum = minimum
        if self.index < len(self.pattern) and self.pattern[self.index] == ",":
            self.index += 1
            maximum = self._digits()
        if self.index >= len(self.pattern) or self.pattern[self.index] != "}":
            self._error("unclosed repetition count")
        self.index += 1
        if maximum is not None and minimum > maximum:
            self._error("repetition minimum exceeds maximum")
        quantifier = self.pattern[start : self.index]
        return quantifier, minimum == 0 or atom_nullable

    def _digits(self):
        start = self.index
        while self.index < len(self.pattern) and self.pattern[self.index] in "0123456789":
            self.index += 1
        if start == self.index:
            return None
        return int(self.pattern[start : self.index])

    def _character_class(self):
        translated = ["["]
        if self.index < len(self.pattern) and self.pattern[self.index] == "^":
            translated.append("^")
            self.index += 1
        has_character = False
        while self.index < len(self.pattern):
            char = self.pattern[self.index]
            if char == "]":
                if not has_character:
                    self._error("empty character class")
                self.index += 1
                translated.append("]")
                return "".join(translated)
            if char == "[":
                self._error("nested character classes are not supported")
            if self.pattern.startswith("&&", self.index):
                self._error("character class intersection is not supported")
            if char == "-" and self.index + 1 < len(self.pattern) and self.pattern[self.index + 1] == "[":
                self._error("character class subtraction is not supported")
            if char == "\\":
                if self.index + 1 >= len(self.pattern):
                    self._error("trailing backslash in character class")
                escaped = self.pattern[self.index + 1]
                if escaped not in "dws" and escaped not in _LITERAL_ESCAPES:
                    self._error("unsupported escape in character class: \\" + escaped)
                translated.append("\\" + escaped)
                self.index += 2
                has_character = True
                continue
            translated.append(char)
            self.index += 1
            has_character = True
        self._error("unclosed character class")

    def parse(self):
        translated, nullable = self._alternation()
        if self.index != len(self.pattern):
            self._error("unexpected closing delimiter")
        if nullable:
            self._error("pattern can match empty text")
        try:
            return re.compile(translated, re.ASCII)
        except re.error as error:
            raise RegexDialectError("invalid regex pattern: {}".format(error)) from error


def compile_pattern(pattern):
    return _Parser(pattern).parse()


def validate_replacement(replacement):
    index = 0
    while index < len(replacement):
        if replacement[index] != "$" or index + 1 >= len(replacement):
            index += 1
            continue
        following = replacement[index + 1]
        if following in "0123456789":
            if following == "0" or (
                index + 2 < len(replacement)
                and replacement[index + 2] in "0123456789"
            ):
                raise RegexDialectError("ambiguous replacement group reference")
            index += 2
            continue
        if following in _SPECIAL_REPLACEMENTS:
            raise RegexDialectError("unsupported .NET replacement syntax")
        index += 1


def expand_replacement(match, replacement):
    result = []
    index = 0
    while index < len(replacement):
        if (
            replacement[index] == "$"
            and index + 1 < len(replacement)
            and replacement[index + 1] in "123456789"
        ):
            group_number = int(replacement[index + 1])
            if group_number <= match.re.groups:
                result.append(match.group(group_number) or "")
            else:
                result.append(replacement[index : index + 2])
            index += 2
        else:
            result.append(replacement[index])
            index += 1
    return "".join(result)
