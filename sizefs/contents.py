import random

class Filler(object):

    def __init__(self, regenerate=False, pattern=None, max_random=128):
        self.regenerate = regenerate
        self.pattern = pattern
        self.max_random = max_random


    def fill(self, size):
        content = ContentGen(pattern=self.pattern, regenerate=self.regenerate, max_random=self.max_random)
        content_string = content.generate_content()
        result = ""

        while size > len(result):
            result += content_string.next()

        return result[:size]



class ContentGen(object):

    def __init__(self, pattern=None, regenerate=False, max_random=128):
        self.pattern = pattern
        self.regenerate = regenerate
        self.max_random = max_random

    # BNF for acceptable patterns:
    #   <Pattern> ::= <Expression> | <Expression> <Pattern>
    #   <Expression> ::= <Char> | <Char> <Multiplier> | "(" <Expression> ")" <Multiplier> | "[" <Range> "]"
    #   <Multiplier> ::= "*" | "+" | '{' <Num> '}'
    #   <Range> ::= <Char> | <Char> "-" <Char> | <Range> "," <Range>
    #
    # The grammar above can probably be improved, but we'll look into that later
    # For now we have no escapes, so *,+,{,},[,],(,) are reserved
    def _build_result(self, working):
        result = ""
        current_expression = ""
        options = []

        while len(working) > 0:
            top = working.pop(0)
            if top == '(':
                # Start processing a new expression
                result += current_expression
                result += options.pop(0)
                current_expression = ""
                options = []
                expression = self._build_result(working)
                result += expression
            elif top == ')':
                current_expression += options.pop(0)
                options = []
                options.insert(0,current_expression)
                result += self._process_multiplier(working, options)
                return result
            elif top == '*':
                result += current_expression
                current_expression = ""
                working.insert(0,'*')
                result += self._process_multiplier(working, options)
                options = []
            elif top == '+':
                result += current_expression
                current_expression = ""
                working.insert(0,'*')
                result += self._process_multiplier(working, options)
                options = []
            elif top == '{':
                result += current_expression
                current_expression = ""
                working.insert(0,'{')
                result += self._process_multiplier(working, options)
                options = []
            elif top == '[':
                result += current_expression
                if len(options) > 0:
                    result += self._return_random_element(options)
                current_expression = ""
                options = self._process_range_options(working)
            else:
                if len(options) > 0:
                    current_expression += self._return_random_element(options)
                options = [top]

        result += current_expression
        if len(options) > 0:
            result += self._return_random_element(options)
        return result


    def _process_range_options(self, working):
        select_list = []
        ch1 = ''
        ch2 = ''

        if len(working) == 0:
            raise PatternError("Selection pattern incomplete")

        while len(working) > 0:
            top = working.pop(0)
            if top == ']':
                if not ch1 == '':
                    select_list.insert(0, ch1)
                    ch1 = ''
                return select_list
            elif top == ',':
                if not ch1 == '':
                    select_list.insert(0, ch1)
                    ch1 = ''
            elif top == '-':
                if ch1 == '':
                    raise PatternError("Invalid range pattern")
                elif len(working) == 0:
                    raise PatternError("Range pattern incomplete")
                else:
                    ch2 = working.pop(0)
                    range_gen = self._char_range(ch1, ch2)
                    for c in range_gen:
                        select_list.insert(0, c)
                    ch1 = ''
                    ch2 = ''
            else:
                ch1 = top

        # The range was incomplete because we never reached the closing brace
        raise PatternError("Selection pattern incomplete")


    def _process_multiplier(self, working, options):
        result = ""
        multiplier_expression = ""
        multiplier = 0

        if len(working) == 0:
            current_expression = self._return_random_element(options)
            return current_expression

        top = working.pop(0)
        if top == '*':
            multiplier = random.randint(0,self.max_random)
        elif top == '+':
            multiplier = random.randint(1,self.max_random)
        elif top == '{':
            try:
                top = working.pop(0)
            except Exception:
                raise PatternError("Multiplier expression incomplete")

            while top != '}':
                if len(working) == 0:
                    raise PatternError("Multiplier expression error")
                else:
                    multiplier_expression += top
                    top = working.pop(0)

            multiplier = self._string_to_int(multiplier_expression)
        else:
            working.insert(0, top)
            return self._return_random_element(options)

        while multiplier > 0:
            multiplier -= 1
            result += self._return_random_element(options)

        return result


    def _string_to_int(self,s):
        try:
            return int(s)
        except ValueError:
            raise PatternError("The provided multiplier wasn't an integer")


    def _char_range(self, a, b):
        for c in xrange(ord(a), ord(b) + 1):
            yield chr(c)


    def _return_random_element(self, ls):
        if len(ls) > 1:
            return ls[random.randint(0,len(ls)-1)]
        else:
            return ls[0]


    def generate_content(self):
        result_string = ""
        if not self.regenerate:
            working = list(self.pattern)
            result_string = self._build_result(working)

        while True:
            if self.regenerate:
                working = list(self.pattern)
                yield self._build_result(working)
            else:
                yield result_string



class PatternError(Exception):

    def __init__(self, value):
        self.value = value


    def __str__(self):
        return repr(self.value)