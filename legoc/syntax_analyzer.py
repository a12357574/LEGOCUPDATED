class SyntaxAnalyzer:
    def __init__(self, tokens, lines):
        self.tokens = [token for token in tokens if token.strip() not in ["Space", ""]]  # Filter spaces and empty tokens
        print("Initialized tokens:", self.tokens)
        print("Token count:", len(self.tokens))
        self.lines = lines
        self.current_index = 0
        self.current_line = 1
        self.output = []

    def analyze(self):
        print("Analyze: tokens =", self.tokens)
        print("Analyze: current_index =", self.current_index)
        self.has_ambiguities = False
        self.output = []
        try:
            self.program()
            if not self.has_ambiguities and self.current_index >= len(self.tokens):
                self.output.append("No Syntax Error")
            else:
                raise SyntaxError(f"Line {self.current_line}: Extra tokens after 'Destroy'")
        except SyntaxError as e:
            self.output.append(f"Syntax Error: {e}")
        return "\n".join(self.output)

    # CFG Rule 1: <program> → Build <global_dec> <subs_function> Link Pane (<parameter>) { <body> <void> } Destroy
    def program(self):
        print("Starting program(), current_index:", self.current_index)
        print("First token:", self.get_current_token())
        # Expect "Build" to start the program
        self.match_and_advance(["Build"], "program start")
        self.global_declaration()
        self.subs_functions()
        # Main function starts with "Link Pane"
        self.match_and_advance(["Link"], "main function start")
        self.match_and_advance(["Pane"], "main function name")
        self.match_and_advance(["("], "main function parameters open")
        self.parameter()
        self.match_and_advance([")"], "main function parameters close")
        self.match_and_advance(["{"], "main function body open")
        self.body(is_main_function=True)
        self.void()
        self.match_and_advance(["}"], "main function body close")
        self.match_and_advance(["Destroy"], "main function program end")

    # CFG Rules 2-3: <global_dec> → <declarations> <global_dec> | λ
    def global_declaration(self):
        print(f"global_declaration: Starting at index {self.current_index}")
        while self.current_index < len(self.tokens):
            next_token = self.peek_next_token()
            print(f"global_declaration: next={next_token}, next_next={self.next_next_token()}")
            if next_token in [None, "Destroy"]:
                break  # End of input or program end
            if next_token == "Subs" or (next_token == "Link" and self.next_next_token() == "Pane"):
                print(f"Exiting global_declaration: Found {'Subs' if next_token == 'Subs' else 'Link Pane'}")
                return  # Main function starts, λ production
            elif next_token in ["Link", "Bubble", "Piece", "Flip", "Const", "Set"]:
                self.declarations()  # Parse a declaration
            else:
                # Error if token isn’t valid for declarations or main function
                expected = ["Link", "Bubble", "Piece", "Flip", "Const", "Set", "Subs", "Destroy"]
                raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{next_token}' in global declarations")
        if not self.current_index < len(self.tokens):  # If we hit end of input prematurely
            raise SyntaxError(f"Line {self.current_line}: Expected 'Link Pane' for main function or a declaration, found end of input")

    # CFG Rules 4-7: <declarations> → <var_dec> | <const_dec> | <array_dec> | <struct_dec>
    def declarations(self):
        token = self.peek_next_token()
        print(f"declarations: token={token}")
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            if self.peek_two_tokens_ahead() == "[":
                self.array_declaration()
            else:
                self.variable_declaration()
        elif token == "Const":
            self.const_declaration()
        elif token == "Set":
            self.struct_declaration()
        else:
            expected = ["Link", "Bubble", "Piece", "Flip", "Const", "Set"]
            raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{token}' in declarations")

    # CFG Rules 8-11: <var_dec> → Link id <Link_tail> ; | Bubble id <Bubble_tail> ; | Piece id <Piece_tail> ; | Flip id <Flip_tail> ;
    def variable_declaration(self):
        data_type = self.peek_next_token()
        print(f"variable_declaration: data_type={data_type}")
        self.data_type()  # Matches "Link", "Bubble", etc.
        next_token = self.peek_next_token()
        if data_type == "Link" and next_token not in ["Identifier", "Pane"]:
            raise SyntaxError(f"Line {self.current_line}: Expected 'Identifier' or 'Pane' after 'Link', found '{next_token}' in variable declarations")
        elif next_token != "Identifier":
            raise SyntaxError(f"Line {self.current_line}: Expected 'Identifier' after '{data_type}', found '{next_token}'")
        self.match_and_advance(["Identifier"], "variable declaration")
        if data_type == "Link":
            self.Link_tail()
        elif data_type == "Bubble":
            self.Bubble_tail()
        elif data_type == "Piece":
            self.Piece_tail()
        elif data_type == "Flip":
            self.Flip_tail()
        self.match_and_advance([";"], "variable declaration end")

    # CFG Rules 24-25: <subs_function> → Subs id (<parameter>) { <body> } <subs_function> | λ
    def subs_functions(self):
        print(f"subs_functions: Starting at index {self.current_index}")
        while self.peek_next_token() == "Subs":
            self.subfunction_declaration()
        # λ implicit, no error needed unless next token is checked later

    # CFG Rule 24: <subs_function> → Subs id (<parameter>) { <body> }
    def subfunction_declaration(self):
        self.match_and_advance(["Subs"], "subfunction start")
        self.match_and_advance(["Identifier"], "subfunction name")
        self.match_and_advance(["("], "parameter list open")
        self.parameter()
        self.match_and_advance([")"], "parameter list close")
        self.match_and_advance(["{"], "subfunction body open")
        self.body(is_main_function=False)
        self.match_and_advance(["}"], "subfunction body close")

    # CFG Rules 26-31: <parameter> → Link id <add> <pmeter_tail> | Bubble id <add> <pmeter_tail> | Piece id <add> <pmeter_tail> | Flip id <add> <pmeter_tail> | λ
    def parameter(self):
        token = self.peek_next_token()
        print(f"parameter: token={token}")
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            self.data_type()
            self.match_and_advance(["Identifier"], "parameter name")
            if token != "Flip":  # Rule 29 omits <add>
                self.add()
            self.pmeter_tail()
        elif token == ")":
            return  # λ production
        else:
            expected = ["Link", "Bubble", "Piece", "Flip", ")"]
            raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{token}' in parameter list")
        # Rule 31: λ implicit

    # CFG Rules 30-31: <pmeter_tail> → , <parameter> | λ
    def pmeter_tail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "parameter separator")
            self.parameter()  # Rule 30
        # Rule 31: λ implicit

    # CFG Rules 32-36: <add> → [<in>] <add2> | λ
    def add(self):
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "array param open")
            self.in_param()
            self.match_and_advance(["]"], "array param close")
            self.add2()  # Rule 32
        # Rule 33: λ implicit

    # CFG Rule 34: <add2> → [<in>] | λ
    def add2(self):
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "2d array param open")
            self.in_param()
            self.match_and_advance(["]"], "2d array param close")
        # λ implicit

    # CFG Rules 35-36: <in> → Identifier | λ
    def in_param(self):
        if self.peek_next_token() == "Identifier":
            self.match_and_advance(["Identifier"], "array index param")  # Rule 35
        # Rule 36: λ implicit

    # CFG Rules (implicit): <data_type> → Link | Bubble | Piece | Flip
    def data_type(self):
        expected = ["Link", "Bubble", "Piece", "Flip"]
        self.match_and_advance(expected, "data type")

    # CFG Rules 37-47: <Link_tail> → , id <Link_init> <Link_tail> | = <Link_dec> <Link_express> <Link_add> | λ
    def Link_tail(self):
        next_token = self.peek_next_token()
        if next_token == ",":
            self.match_and_advance([","], "variable separator")
            self.match_and_advance(["Identifier"], "variable name")
            self.Link_init()
            self.Link_tail()
        elif next_token == "=":
            self.match_and_advance(["="], "assignment")
            self.Link_dec()
            self.Link_express()
            self.Link_add()
        elif next_token == ";":
            return  # λ production
        else:
            expected = [",", "=", ";"]
            raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{next_token}' in Link variable tail")
        # Rule 39: λ implicit

    # CFG Rules 40-41: <Link_dec> → Identifier | Linklit
    def Link_dec(self):
        token = self.peek_next_token()
        if token in ["Identifier", "Linklit"]:
            self.match_and_advance(token, "Link value")  # Rules 40-41
        else:
            raise SyntaxError(f"Line {self.current_line}: Expected Identifier or Linklit, found '{token}'")

    # CFG Rules 42-43: <Link_express> → <arith_op> <value> <Link_express> | λ
    def Link_express(self):
        if self.peek_next_token() in ["+", "-", "*", "/", "%"]:
            self.arith_op()  # Rule 42
            self.value()
            self.Link_express()
        # Rule 43: λ implicit

    # CFG Rules 44-45: <Link_init> → = <value> <arith_op> <value> <Link_express> | λ
    def Link_init(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")  # Rule 44
            self.value()
            self.arith_op()
            self.value()
            self.Link_express()
        # Rule 45: λ implicit

    # CFG Rules 46-47: <Link_add> → , id = <Link_dec> <Link_express> <Link_add> | λ
    def Link_add(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")  # Rule 46
            self.match_and_advance(["Identifier"], "variable name")
            self.match_and_advance(["="], "assignment")
            self.Link_dec()
            self.Link_express()
            self.Link_add()
        # Rule 47: λ implicit

    # CFG Rules 48-54: <Bubble_tail> → , id <Link_init> <Bubble_tail> | = <Bubble_dec> <Link_express> <Bubble_add> | λ
    def Bubble_tail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")  # Rule 48
            self.match_and_advance(["Identifier"], "variable name")
            self.Link_init()
            self.Bubble_tail()
        elif self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")  # Rule 49
            self.Bubble_dec()
            self.Link_express()
            self.Bubble_add()
        # Rule 50: λ implicit

    # CFG Rules 51-52: <Bubble_dec> → Identifier | Bubblelit
    def Bubble_dec(self):
        token = self.peek_next_token()
        if token in ["Identifier", "Bubblelit"]:
            self.match_and_advance(token, "Bubble value")  # Rules 51-52
        else:
            raise SyntaxError(f"Line {self.current_line}: Expected Identifier or Bubblelit, found '{token}'")

    # CFG Rules 53-54: <Bubble_add> → , id = <Bubble_dec> <Link_express> <Bubble_add> | λ
    def Bubble_add(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")  # Rule 53
            self.match_and_advance(["Identifier"], "variable name")
            self.match_and_advance(["="], "assignment")
            self.Bubble_dec()
            self.Link_express()
            self.Bubble_add()
        # Rule 54: λ implicit

    # CFG Rules 55-59: <Piece_tail> → , id <Piece_tail> | = "Piecelit" <Piece_init> | λ
    def Piece_tail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")  # Rule 55
            self.match_and_advance(["Identifier"], "variable name")
            self.Piece_tail()
        elif self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")  # Rule 57
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.Piece_init()
        # Rule 56: λ implicit

    # CFG Rules 58-59: <Piece_init> → , id = "Piecelit" <Piece_init> | λ
    def Piece_init(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")  # Rule 58
            self.match_and_advance(["Identifier"], "variable name")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.Piece_init()
        # Rule 59: λ implicit

    # CFG Rules 60-64: <Flip_tail> → , id <Flip_tail> | = Fliplit <Flip_init> | λ
    def Flip_tail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")  # Rule 60
            self.match_and_advance(["Identifier"], "variable name")
            self.Flip_tail()
        elif self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")  # Rule 62
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.Flip_init()
        # Rule 61: λ implicit

    # CFG Rules 63-64: <Flip_init> → , id = Fliplit <Flip_init> | λ
    def Flip_init(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")  # Rule 63
            self.match_and_advance(["Identifier"], "variable name")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.Flip_init()
        # Rule 64: λ implicit

    # CFG Rules 12-16: <const_dec> → Const <const_elem> ;
    def const_declaration(self):
        self.match_and_advance(["Const"], "constant declaration")  # Rule 12
        self.const_elem()
        self.match_and_advance([";"], "constant declaration end")

    # CFG Rules 13-16: <const_elem> → Link id = Linklit <Link_constail> | Bubble id = Bubblelit <Bubble_constail> | ...
    def const_elem(self):
        data_type = self.peek_next_token()
        self.data_type()
        self.match_and_advance(["Identifier"], "constant name")
        self.match_and_advance(["="], "constant assignment")
        if data_type == "Link":
            self.match_and_advance(["Linklit"], "Link literal")  # Rule 13
            self.Link_constail()
        elif data_type == "Bubble":
            self.match_and_advance(["Bubblelit"], "Bubble literal")  # Rule 14
            self.Bubble_constail()
        elif data_type == "Piece":
            self.match_and_advance(["Piecelit"], "Piece literal")  # Rule 15
            self.Piece_constail()
        elif data_type == "Flip":
            self.match_and_advance("Fliplit", "Flip literal")  # Rule 16
            self.Flip_constail()

    # CFG Rules 65-66: <Link_constail> → , id = Linklit <Link_constail> | λ
    def Link_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")  # Rule 65
            self.match_and_advance(["Identifier"], "constant name")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Linklit"], "Link literal")
            self.Link_constail()
        # Rule 66: λ implicit

    # CFG Rules 67-68: <Bubble_constail> → , id = Bubblelit <Bubble_constail> | λ
    def Bubble_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")  # Rule 67
            self.match_and_advance(["Identifier"], "constant name")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Bubblelit"], "Bubble literal")
            self.Bubble_constail()
        # Rule 68: λ implicit

    # CFG Rules 69-70: <Piece_constail> → , id = "Piecelit" <Piece_constail> | λ
    def Piece_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")  # Rule 69
            self.match_and_advance(["Identifier"], "constant name")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.Piece_constail()
        # Rule 70: λ implicit

    # CFG Rules 71-72: <Flip_constail> → , id = Fliplit <Flip_constail> | λ
    def Flip_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")  # Rule 71
            self.match_and_advance(["Identifier"], "constant name")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.Flip_constail()
        # Rule 72: λ implicit

    # CFG Rule 17: <struct_dec> → Set id { <more_dec> }
    def struct_declaration(self):
        self.match_and_advance(["Set"], "struct declaration")  # Rule 17
        self.match_and_advance(["Identifier"], "struct name")
        self.match_and_advance(["{"], "struct body open")
        while self.peek_next_token() in ["Link", "Bubble", "Piece", "Flip"]:
            self.variable_declaration()  # <more_dec> assumed as <var_dec>
        self.match_and_advance("}", "struct body close")

    # CFG Rules 18-23: <array_dec> → Link id [Linklit] <2d> = <Link_arrayA> ; | ...
    def array_declaration(self):
        data_type = self.peek_next_token()
        print(f"array_declaration: data_type={data_type}")
        self.data_type()
        self.match_and_advance(["Identifier"], "array name")
        self.match_and_advance(["["], "array size open")
        self.match_and_advance(["Linklit"], "array size")
        self.match_and_advance(["]"], "array size close")
        self.two_d()
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "array initialization")
            if data_type == "Link":
                self.Link_arrayA()  # Rule 18
            elif data_type == "Bubble":
                self.Bubble_arrayA()  # Rule 19
            elif data_type == "Piece":
                self.Piece_arrayA()  # Rule 20
            elif data_type == "Flip":
                self.Flip_arrayA()  # Rule 21
        self.match_and_advance([";"], "array declaration end")

    # CFG Rules 22-23: <2d> → [Linklit] | λ
    def two_d(self):
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "2d array open")  # Rule 22
            self.match_and_advance(["Linklit"], "2d array size")
            self.match_and_advance(["]"], "2d array close")
        # Rule 23: λ implicit

    # CFG Rules 73-79: <Link_arrayA> → { <Link_arrayB> } <Link_arrayD>
    def Link_arrayA(self):
        self.match_and_advance(["{"], "array values open")  # Rule 73
        self.Link_arrayB()
        self.match_and_advance(["}"], "array values close")
        self.Link_arrayD()

    # CFG Rules 74-77: <Link_arrayB> → Linklit <Link_arrayC> | λ
    def Link_arrayB(self):
        if self.peek_next_token() == "Linklit":
            self.match_and_advance(["Linklit"], "Link literal")  # Rule 74
            self.Link_arrayC()
        # Rule 75: λ implicit

    # CFG Rules 76-77: <Link_arrayC> → , Linklit <Link_arrayC> | λ
    def Link_arrayC(self):
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")  # Rule 76
            self.match_and_advance(["Linklit"], "Link literal")
            self.Link_arrayC()
        # Rule 77: λ implicit

    # CFG Rules 78-79: <Link_arrayD> → { <Link_arrayB> } | λ
    def Link_arrayD(self):
        if self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")  # Rule 78
            self.Link_arrayB()
            self.match_and_advance(["}"], "nested array close")
        # Rule 79: λ implicit

    # CFG Rules 80-86: <Bubble_arrayA> → { <Bubble_arrayB> } <Bubble_arrayD>
    def Bubble_arrayA(self):
        self.match_and_advance(["{"], "array values open")  # Rule 80
        self.Bubble_arrayB()
        self.match_and_advance(["}"], "array values close")
        self.Bubble_arrayD()

    # CFG Rules 81-84: <Bubble_arrayB> → Bubblelit <Bubble_arrayC> | λ
    def Bubble_arrayB(self):
        if self.peek_next_token() == "Bubblelit":
            self.match_and_advance(["Bubblelit"], "Bubble literal")  # Rule 81
            self.Bubble_arrayC()
        # Rule 82: λ implicit

    # CFG Rules 83-84: <Bubble_arrayC> → , Bubblelit <Bubble_arrayC> | λ
    def Bubble_arrayC(self):
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")  # Rule 83
            self.match_and_advance(["Bubblelit"], "Bubble literal")
            self.Bubble_arrayC()
        # Rule 84: λ implicit

    # CFG Rules 85-86: <Bubble_arrayD> → { <Bubble_arrayB> } | λ
    def Bubble_arrayD(self):
        if self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")  # Rule 85
            self.Bubble_arrayB()
            self.match_and_advance(["}"], "nested array close")
        # Rule 86: λ implicit

    # CFG Rules 87-93: <Piece_arrayA> → { <Piece_arrayB> } <Piece_arrayD>
    def Piece_arrayA(self):
        self.match_and_advance(["{"], "array values open")  # Rule 87
        self.Piece_arrayB()
        self.match_and_advance(["}"], "array values close")
        self.Piece_arrayD()

    # CFG Rules 88-91: <Piece_arrayB> → Piecelit <Piece_arrayC> | λ
    def Piece_arrayB(self):
        if self.peek_next_token() == "Piecelit":
            self.match_and_advance(["Piecelit"], "Piece literal")  # Rule 88
            self.Piece_arrayC()
        # Rule 89: λ implicit

    # CFG Rules 90-91: <Piece_arrayC> → , Piecelit <Piece_arrayC> | λ
    def Piece_arrayC(self):
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")  # Rule 90
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.Piece_arrayC()
        # Rule 91: λ implicit

    # CFG Rules 92-93: <Piece_arrayD> → { <Piece_arrayB> } | λ
    def Piece_arrayD(self):
        if self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")  # Rule 92
            self.Piece_arrayB()
            self.match_and_advance(["}"], "nested array close")
        # Rule 93: λ implicit

    # CFG Rules 94-100: <Flip_arrayA> → { <Flip_arrayB> } <Flip_arrayD>
    def Flip_arrayA(self):
        self.match_and_advance(["{"], "array values open")  # Rule 94
        self.Flip_arrayB()
        self.match_and_advance(["}"], "array values close")
        self.Flip_arrayD()

    # CFG Rules 95-98: <Flip_arrayB> → Fliplit <Flip_arrayC> | λ
    def Flip_arrayB(self):
        if self.peek_next_token() == "Fliplit":
            self.match_and_advance(["Fliplit"], "Flip literal")  # Rule 95
            self.Flip_arrayC()
        # Rule 96: λ implicit

    # CFG Rules 97-98: <Flip_arrayC> → , Fliplit <Flip_arrayC> | λ
    def Flip_arrayC(self):
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")  # Rule 97
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.Flip_arrayC()
        # Rule 98: λ implicit

    # CFG Rules 99-100: <Flip_arrayD> → { <Flip_arrayB> } | λ
    def Flip_arrayD(self):
        if self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")  # Rule 99
            self.Flip_arrayB()
            self.match_and_advance(["}"], "nested array close")
        # Rule 100: λ implicit

    # CFG Rules 101-102: <body> → <statements> <slist> <void> | λ
    def body(self, is_main_function=False):
        print(f"body: Starting at index {self.current_index}, is_main_function={is_main_function}")
        while self.peek_next_token() and self.peek_next_token() not in ["}", None]:
            token = self.peek_next_token()
            print(f"body: token={token}")
            if token in ["Link", "Bubble", "Piece", "Flip"]:
                self.statements()
                self.slist()
            elif token in ["Ifsnap", "Change", "Do", "Put", "Display", "Create", "Identifier"]:
                self.slist()
            elif token in ["Revoid", "Rebrick"]:
                self.void()
                break  # Defer to <void>
            else:
                expected = ["Link", "Bubble", "Piece", "Flip"]
                raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{token}' in body")
        if is_main_function:
            self.void()

    # CFG Rules 103-104: <statements> → <states> <slist> | λ
    def statements(self):
        token = self.peek_next_token()
        print(f"statements: token={token}")
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            self.states()  # Rule 103
            self.slist()
        # Rule 104: λ implicit

    # CFG Rules 105-106: <states> → <add_dec> | <add_array>
    def states(self):
        if self.peek_two_tokens_ahead() == "[":
            self.add_array()  # Rule 106
        else:
            self.add_dec()  # Rule 105

    # CFG Rules 107-108: <slist> → <stateset> <slist> | λ
    def slist(self):
        token = self.peek_next_token()
        print(f"slist: token={token}")
        if token in ["Ifsnap", "Change", "Do", "Put", "Display", "Create", "Identifier"]:
            self.stateset()  # Rule 107
            self.slist()
        # Rule 108: λ implicit

    # CFG Rules 109-110: <add_dec> → <var_dec> <add_dec> | λ
    def add_dec(self):
        self.variable_declaration()  # Rule 109
        if self.peek_next_token() in ["Link", "Bubble", "Piece", "Flip"]:
            self.add_dec()
        # Rule 110: λ implicit

    # CFG Rules 111-112: <add_array> → <array_dec> <add_array> | λ
    def add_array(self):
        self.array_declaration()  # Rule 111
        if self.peek_next_token() in ["Link", "Bubble", "Piece", "Flip"]:
            self.add_array()
        # Rule 112: λ implicit

    # CFG Rules 113-114, 145, 115-116, 169: <stateset> → <condi_stat> | <var_assign> | <function_call> | <create> | <display> | <loop_stat>
    def stateset(self):
        token = self.peek_next_token()
        print(f"stateset: token={token}")
        if token in ["Ifsnap", "Change"]:
            self.condi_stat()
        elif token == "Identifier" and self.peek_two_tokens_ahead() == "(":
            self.function_call()
        elif token == "Identifier":
            self.var_assign()
        elif token == "Create":
            self.create()
        elif token == "Display":
            self.display()
        elif token in ["Do", "Put"]:
            self.loop_stat()
        else:
            expected = ["Ifsnap", "Change", "Identifier", "Create", "Display", "Do", "Put"]
            raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{token}' in statement")

    # CFG Rule 115: <create> → Create ( Identifier ) ; # added [] for user inputting in arrays
    def create(self):
        self.match_and_advance(["Create"], "input statement")
        self.match_and_advance(["("], "input open")
        self.match_and_advance(["Identifier"], "input variable")
        if self.peek_next_token() == "[": #optional array in Create
            self.match_and_advance(["["], "array open")
            self.expression() # array index parsing
            self.match_and_advance(["]"], "array close")
        self.match_and_advance([")"], "input close")
        self.match_and_advance([";"], "input statement end")

    # CFG Rule 116: <display> → Display <out_print> ;
    def display(self):
        self.match_and_advance(["Display"], "display statement")
        self.out_print()
        self.match_and_advance([";"], "display statement end")

    # CFG Rules 117-129: <out_print> → "Piecelit" <out_show> | Identifier <out_display> | λ
    def out_print(self):
        token = self.peek_next_token()
        if token == '"':
            self.match_and_advance(["Piecelit"], "string literal content")
            self.out_show()
        elif token == "Identifier":
            self.match_and_advance(["Identifier"], "variable")
            self.out_display()
        # Rule 120: λ implicit

    # CFG Rules 122-126: <out_show> → , Identifier <out_dis> | λ
    def out_show(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "output separator")
            self.match_and_advance(["Identifier"], "variable")
            self.out_dis()
        # Rule 123: λ implicit

    # CFG Rules 124-126: <out_dis> → , "Piecelit" <out_show> | <arith_op> <value> <out_dis> | λ
    def out_dis(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "output separator")
            self.match_and_advance(["Piecelit"], "string literal content")
            self.out_show()
        elif self.peek_next_token() in ["+", "-", "*", "/", "%"]:
            self.arith_op()
            self.value()
            self.out_dis()
        # Rule 126: λ implicit

    # CFG Rules 127-129: <out_display> → [Linklit] <2d> <out_display> | , Identifier <out_display> | λ
    def out_display(self):
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "array index open")
            self.match_and_advance(["Linklit"], "array index")
            self.match_and_advance(["]"], "array index close")
            self.two_d()
            self.out_display()
        elif self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            self.match_and_advance(["Identifier"], "variable")
            self.out_display()
        # Rule 129: λ implicit

    # CFG Rules 130-132: <value> → Identifier | Linklit | Bubblelit
    def value(self):
        token = self.peek_next_token()
        if token in ["Identifier", "Linklit", "Bubblelit"]:
            self.match_and_advance(token, "value")  # Rules 130-132
        else:
            raise SyntaxError(f"Line {self.current_line}: Expected value, found '{token}'")

    # CFG Rules 137-138: <condi_stat> → Ifsnap ( <condition> ) { <body> } <snapif> <snap> | Change ( Identifier ) { <base> <def> }
    def condi_stat(self):
        token = self.peek_next_token()
        if token == "Ifsnap":
            self.if_statement()  # Rule 137
        elif token == "Change":
            self.switch_statement()  # Rule 138

    # CFG Rule 137: <condi_stat> → Ifsnap ( <condition> ) { <body> } <snapif> <snap>
    def if_statement(self):
        self.match_and_advance(["Ifsnap"], "if statement")
        self.match_and_advance(["("], "condition open")
        self.condition()
        self.match_and_advance([")"], "condition close")
        self.match_and_advance(["{"], "if body open")
        self.body(is_main_function=False)
        self.match_and_advance(["}"], "if body close")
        self.snapif()
        self.snap()

    # CFG Rule 139: <snapif> → Snapif ( <condition> ) { <body> } <snapif> | λ
    def snapif(self):
        while self.peek_next_token() == "Snapif":
            self.match_and_advance(["Snapif"], "elseif statement")
            self.match_and_advance(["("], "condition open")
            self.condition()
            self.match_and_advance([")"], "condition close")
            self.match_and_advance(["{"], "elseif body open")
            self.body(is_main_function=False)
            self.match_and_advance(["}"], "elseif body close")

    # CFG Rules 140-141: <snap> → Snap { <body> } | λ
    def snap(self):
        if self.peek_next_token() == "Snap":
            self.match_and_advance(["Snap"], "else statement")
            self.match_and_advance(["{"], "else body open")
            self.body(is_main_function=False)
            self.match_and_advance(["}"], "else body close")
        # Rule 141: λ implicit

    # CFG Rule 138: <condi_stat> → Change ( Identifier ) { <base> <def> }
    def switch_statement(self):
        self.match_and_advance(["Change"], "switch statement")
        self.match_and_advance(["("], "switch expression open")
        self.match_and_advance(["Identifier"], "switch variable")
        self.match_and_advance([")"], "switch expression close")
        self.match_and_advance(["{"], "switch body open")
        self.base()
        self.define()
        self.match_and_advance(["}"], "switch body close")

    # CFG Rules 145-147: <base> → Base <value> ; <broke> <bases> | λ
    def base(self):
        while self.peek_next_token() == "Base":
            self.match_and_advance(["Base"], "case start")
            self.value()
            self.match_and_advance([";"], "case separator")
            # Allow statements inside case
            while self.peek_next_token() and self.peek_next_token() not in ["Base", "Def", "}"]:
                if self.peek_next_token() == "Display":
                    self.display()
                elif self.peek_next_token() == "Broke":
                    self.broke()
                    break
                else:
                    self.slist()  # Handle other statements
            self.bases()

    # CFG Rules 146-147: <bases> → <base> <bases> | λ
    def bases(self):
        if self.peek_next_token() == "Base":
            self.base()  # Rule 146
            self.bases()
        # Rule 147: λ implicit

    # CFG Rules 133-134: <broke> → Broke ; | λ
    def broke(self):
        if self.peek_next_token() == "Broke":
            self.match_and_advance(["Broke"], "break statement")
            self.match_and_advance([";"], "break statement end")
        # Rule 134: λ implicit

    # CFG Rule 148: <def> → Def : <body>
    def define(self):
        if self.peek_next_token() == "Def":
            self.match_and_advance(["Def"], "default case")
            self.match_and_advance([":"], "default separator")
            self.body(is_main_function=False)

    # CFG Rules 142-144: <condition> → <value> <arith> <op> <value> <arith> <condi>
    def condition(self):
        self.value()
        self.arith()
        self.op()
        self.value()
        self.arith()
        self.condi()

    # CFG Rules 143-144: <condi> → <op> <value> <arith> <condi> | λ
    def condi(self):
        if self.peek_next_token() in ["==", "!=", "<", ">", ">=", "<=", "||", "&&", "!!"]:
            self.op()  # Rule 143
            self.value()
            self.arith()
            self.condi()
        # Rule 144: λ implicit

    # CFG Rules 177-178: <op> → <rel_op> | <log_op>
    def op(self):
        token = self.peek_next_token()
        if token in ["==", "!=", "<", ">", ">=", "<="]:
            self.rel_op()
        elif token in ["||", "&&", "!!"]:
            self.log_op()
        else:
            expected = ["==", "!=", "<", ">", ">=", "<=", "||", "&&", "!!"]
            raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{token}' in operator")

    # CFG Rules 149-154: <rel_op> → == | > <rel2> | < <rel2> | != | >= | <=
    def rel_op(self):
        token = self.peek_next_token()
        if token in ["==", "!=", ">=", "<="]:
            self.match_and_advance(token, "relational operator")  # Rules 149, 152, 153, 154
        elif token == ">":
            self.match_and_advance([">"], "relational operator")  # Rule 150
            self.rel2()
        elif token == "<":
            self.match_and_advance(["<"], "relational operator")  # Rule 151
            self.rel2()

    # CFG Rules 153-154: <rel2> → = | λ
    def rel2(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "relational operator extension")  # Rule 153
        # Rule 154: λ implicit

    # CFG Rules 155-157: <log_op> → || | && | !! (Added !! support)
    def log_op(self):
        token = self.peek_next_token()
        if token in ["||", "&&", "!!"]:
            self.match_and_advance(token, "logical operator")  # Rules 155-157
        else:
            raise SyntaxError(f"Line {self.current_line}: Expected logical operator, found '{token}'")

    # CFG Rules 158-162: <arith_op> → + | - | * | / | %
    def arith_op(self):
        token = self.peek_next_token()
        if token in ["+", "-", "*", "/", "%"]:
            self.match_and_advance(token, "arithmetic operator")  # Rules 158-162
        else:
            raise SyntaxError(f"Line {self.current_line}: Expected arithmetic operator, found '{token}'")

    # CFG Rules 135-136: <arith> → <arith_op> <value> <arith> | λ
    def arith(self):
        if self.peek_next_token() in ["+", "-", "*", "/", "%"]:
            self.arith_op()  # Rule 135
            self.value()
            self.arith()
        # Rule 136: λ implicit

    # CFG Rules 114, 163-168: <var_assign> → Identifier <ass_com> <expression> ;
    def var_assign(self):
        self.match_and_advance(["Identifier"], "variable name")
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "array index open")
            self.match_and_advance(["Linklit"], "array index")
            self.match_and_advance(["]"], "array index close")
            if self.peek_next_token() == "[":
                self.match_and_advance(["["], "2d array index open")
                self.match_and_advance(["Linklit"], "2d array index")
                self.match_and_advance(["]"], "2d array index close")
        self.ass_com()
        self.expression()
        self.match_and_advance([";"], "assignment end")

    def expression(self):
        self.value()
        self.arith()

    # CFG Rules 163-168: <ass_com> → = | += | -= | *= | /= | %=
    def ass_com(self):
        token = self.peek_next_token()
        if token in ["=", "+=", "-=", "*=", "/=", "%="]:
            self.match_and_advance(token, "assignment operator")  # Rules 163-168
        else:
            raise SyntaxError(f"Line {self.current_line}: Expected assignment operator, found '{token}'")

    # CFG Rules 169-172: <loop_stat> → Do { <body> } While ( <condition> ) { <body> } | Put ( <init_state> ; <condition> ; <update_express> ) { <body> <loop_con> }
    def loop_stat(self):
        token = self.peek_next_token()
        if token == "Do":
            self.do_while_loop()  # Rule 171
        elif token == "Put":
            self.for_loop()  # Rule 172

    # CFG Rule 171: <loop_stat> → Do { <body> } While ( <condition> ) { <body> }
    def do_while_loop(self):
        self.match_and_advance(["Do"], "do-while loop")
        self.match_and_advance(["{"], "do-while body open")
        self.body(is_main_function=False)
        self.match_and_advance(["}"], "do-while body close")
        self.match_and_advance(["While"], "do-while condition start")
        self.match_and_advance(["("], "condition open")
        self.condition()
        self.match_and_advance([")"], "condition close")
        self.match_and_advance(["{"], "do-while second body open")
        self.body(is_main_function=False)
        self.match_and_advance(["}"], "do-while second body close")

    # CFG Rule 172: <loop_stat> → Put ( <init_state> ; <condition> ; <update_express> ) { <body> <loop_con> }
    def for_loop(self):
        self.match_and_advance(["Put"], "for loop")
        self.match_and_advance(["("], "for params open")
        self.init_state()
        self.match_and_advance([";"], "init separator")
        self.condition()
        self.match_and_advance([";"], "condition separator")
        self.update_express()
        #self.match_and_advance([";"], "update separator") no ; after ++ or --
        self.match_and_advance([")"], "for params close")
        self.match_and_advance(["{"], "for body open")
        self.body(is_main_function=False)
        self.loop_con()
        self.match_and_advance(["}"], "for body close")

    # CFG Rules 173-176: <init_state> → Link Identifier = Linklit <arith> <add_loop> | Identifier = Linklit <arith> <add_loop>
    def init_state(self):
        token = self.peek_next_token()
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            self.data_type()
            self.match_and_advance(["Identifier"], "variable")
            self.match_and_advance(["="], "assignment")
            self.expression()
            self.arith()
        elif token == "Identifier":
            self.match_and_advance(["Identifier"], "variable")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Linklit"], "Link literal")
            self.arith()

    # CFG Rules 175-176: <add_loop> → , Identifier = Linklit <arith> <add_loop> | λ
    def add_loop(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "init separator")
            self.match_and_advance(["Identifier"], "variable")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(["Linklit"], "Link literal")
            self.arith()
            self.add_loop()
        # Rule 176: λ implicit

    # CFG Rules 179-180: <update_express> → Identifier ++ | Identifier --
    def update_express(self):
        self.match_and_advance(["Identifier"], "variable")
        token = self.peek_next_token()
        if token in ["++", "--"]:
            self.match_and_advance(token, "update operator")  # Rules 179-180
        else:
            raise SyntaxError(f"Line {self.current_line}: Expected '++' or '--', found '{token}'")

    # CFG Rules 181-183: <loop_con> → Broke ; | Con ; | λ
    def loop_con(self):
        token = self.peek_next_token()
        if token == "Broke":
            self.match_and_advance(["Broke"], "break statement")
            self.match_and_advance([";"], "break statement end")
        elif token == "Con":
            self.match_and_advance(["Con"], "continue statement")
            self.match_and_advance([";"], "continue statement end")
        # Rule 183: λ implicit

    # CFG Rule 145: <function_call> → Identifier ( <param> ) ;
    def function_call(self):
        self.match_and_advance(["Identifier"], "function name")
        self.match_and_advance(["("], "param list open")
        self.param()
        self.match_and_advance([")"], "param list close")
        self.match_and_advance([";"], "function call end")

    # CFG Rules 189-191: <param> → <value> <paramA> | λ
    def param(self):
        token = self.peek_next_token()
        if token in ["Identifier", "Linklit", "Bubblelit", "Piecelit", "Fliplit"]:
            self.value()  # Rule 189
            self.paramA()
        # Rule 191: λ implicit

    # CFG Rules 190-191: <paramA> → , <value> <paramA> | λ
    def paramA(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "param separator")  # Rule 190
            self.value()
            self.paramA()
        # Rule 191: λ implicit

    # CFG Rules 153-155: <void> → Revoid ; | Rebrick Linklit ; | λ (Corrected numbering)
    def void(self):
        token = self.peek_next_token()
        print(f"void: token={token}")
        if token == "Revoid":
            self.match_and_advance(["Revoid"], "return void")  # Rule 153
            self.match_and_advance([";"], "return end")
        elif token == "Rebrick":
            self.match_and_advance(["Rebrick"], "return statement")  # Rule 154
            self.match_and_advance(["Linklit"], "return value")  # Assuming 0 as Linklit
            self.match_and_advance([";"], "return end")
        elif token == "}":
            return
        else:
            expected = ["Revoid", "Rebrick", "}"]
            raise SyntaxError(f"Line {self.current_line}: Expected '{', '.join(expected)}', found '{token}' in return statement")
    def match_and_advance(self, expected_tokens, context):
        """
        Matches the current token against a list of expected tokens and advances if matched.
        Raises a SyntaxError with all possible expected tokens if no match is found.

        Args:
            expected_tokens (list or str): A list of valid tokens or a single token as a string.
            context (str): Description of the parsing context for error reporting.
        """
        # Convert single string to list for consistency
        if isinstance(expected_tokens, str):
            expected_tokens = [expected_tokens]
        
        token = self.get_current_token()
        if token is None:
            expected_str = "', '".join(expected_tokens)
            raise SyntaxError(f"Line {self.current_line}: Unexpected end of input, Expected '{expected_str}' in {context}")
        if token in expected_tokens:
            self.advance()
        else:
            expected_str = "', '".join(expected_tokens)
            raise SyntaxError(f"Line {self.current_line}: Expected '{expected_str}', found '{token}' in {context}")

    def get_current_token(self):
        if self.current_index < len(self.tokens):
            token = self.tokens[self.current_index]
            # Find the line containing this token by simulating token consumption
            line_num = 1
            token_idx = 0
            for line in self.lines:
                line_tokens = [t for t in line.split() if t not in ["Space", ""]]
                for t in line_tokens:
                    if token_idx == self.current_index:
                        self.current_line = line_num
                        print(f"get_current_token: index={self.current_index}, token={token}, line={self.current_line}")
                        return token
                    token_idx += 1
                line_num += 1
            self.current_line = line_num  # Fallback if not found
            print(f"get_current_token: index={self.current_index}, token={token}, line={self.current_line}")
            return token
        self.current_line = len(self.lines)
        return None

    def peek_next_token(self):
        return self.tokens[self.current_index] if self.current_index < len(self.tokens) else None

    def peek_two_tokens_ahead(self):
        return self.tokens[self.current_index + 2] if self.current_index + 2 < len(self.tokens) else None

    def next_next_token(self):
        return self.tokens[self.current_index + 1] if self.current_index + 1 < len(self.tokens) else None

    def advance(self):
        self.current_index += 1

    def debug_tokens(self):
        print(f"Current index: {self.current_index}, Line: {self.current_line}")
        print(f"Current token: {self.get_current_token()}")
        print(f"Next token: {self.peek_next_token()}")
        print(f"Two ahead: {self.peek_two_tokens_ahead()}")
        print(f"Tokens remaining: {self.tokens[self.current_index:]}")