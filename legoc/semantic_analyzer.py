class SemanticAnalyzer:
    def __init__(self, tokens, lexemes, lines):
        print("Input tokens before filtering:", tokens)
        print("Input lexemes before filtering:", lexemes)
        # Filter tokens and lexemes together, keeping only pairs where token isn't "Space" or empty
        filtered_pairs = [(t, l) for t, l in zip(tokens, lexemes) if t.strip() not in ["Space", ""]]
        self.tokens = [pair[0] for pair in filtered_pairs]
        self.lexemes = [pair[1] for pair in filtered_pairs]
        print("Tokens after filtering:", self.tokens)
        print("Lexemes after filtering:", self.lexemes)
        print("Token count after filtering:", len(self.tokens))
        print("Lexeme count after filtering:", len(self.lexemes))
        assert len(self.tokens) == len(self.lexemes), "Mismatch between tokens and lexemes"
        print("Initialized tokens:", self.tokens)
        print("Initialized lexemes:", self.lexemes)
        print("Token count:", len(self.tokens))
        self.lines = lines
        self.current_index = 0
        self.current_line = 1
        self.output = []
        self.symbol_table = {}
        self.display_output = []

    def analyze(self):
        print("Analyze: tokens =", self.tokens)
        print("Analyze: lexemes =", self.lexemes)
        print("Analyze: current_index =", self.current_index)
        self.output = []
        try:
            self.program()
            if self.display_output:
                self.output.extend(self.display_output)
        except Exception as e:
            self.output.append(f"Semantic Error: {str(e)}")
        return "\n".join(self.output)

    def program(self):
        print("Starting program(), current_index:", self.current_index)
        self.match_and_advance(["Build"], "program start")
        self.global_declaration()
        self.subs_functions()
        self.match_and_advance(["Link"], "main function start")
        self.match_and_advance(["Pane"], "main function name")
        self.match_and_advance(["("], "main function parameters open")
        self.parameter()
        self.match_and_advance([")"], "main function parameters close")
        self.match_and_advance(["{"], "main function body open")
        self.body(is_main_function=True)
        self.void()
        self.match_and_advance(["}"], "main function body close")
        self.match_and_advance(["Destroy"], "program end")

    def global_declaration(self):
        while self.current_index < len(self.tokens):
            next_token = self.peek_next_token()
            if next_token in [None, "Destroy", "Subs"] or (next_token == "Link" and self.next_next_token() == "Pane"):
                return  # λ production or main function
            elif next_token in ["Link", "Bubble", "Piece", "Flip", "Const", "Set"]:
                self.declarations()
            else:
                raise ValueError(f"Line {self.current_line}: Invalid token '{next_token}' in global declarations")

    def declarations(self):
        token = self.peek_next_token()
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
            raise ValueError(f"Line {self.current_line}: Invalid declaration start '{token}'")

    def variable_declaration(self):
        type_token = self.peek_next_token()
        self.match_and_advance(["Link", "Bubble"], "data type")
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "variable name")
        self.match_and_advance(["="], "assignment")
        
        # Evaluate the expression
        value = self.evaluate_expression()
        self.symbol_table[var_name] = {"type": type_token, "value": value}
        self.match_and_advance([";"], "declaration end")

    def Link_tail(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            value = self.Link_dec()
            expr = self.Link_express()
            if expr:
                initial_value = value
                value = self.evaluate_expression(value, expr)
                self.output.append(f"Assignment: {initial_value} {self.format_expression(expr)} => {value}")
            self.Link_add()
            return value
        return None

    def Link_dec(self):
        token = self.peek_next_token()
        if token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "Link value")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            return self.symbol_table[var_name]["value"]
        elif token == "Linklit":
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "Link value")
            return value
        raise ValueError(f"Line {self.current_line}: Expected Identifier or Linklit, found '{token}'")

    def Link_express(self):
        if self.peek_next_token() in ["+", "-", "*", "/", "%"]:
            op = self.peek_next_token()
            self.arith_op()
            left = self.value()  # This retrieves the value of the identifier
            right = self.value()  # This retrieves the value of the identifier
            return (op, left, right)
        return None

    def subs_functions(self):
        while self.peek_next_token() == "Subs":
            self.subfunction_declaration()

    def subfunction_declaration(self):
        self.match_and_advance(["Subs"], "subfunction start")
        func_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "subfunction name")
        if func_name in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Function '{func_name}' already declared")
        self.match_and_advance(["("], "parameter list open")
        params = self.parameter()
        self.match_and_advance([")"], "parameter list close")
        self.match_and_advance(["{"], "subfunction body open")
        self.body(is_main_function=False)
        self.match_and_advance(["}"], "subfunction body close")
        self.symbol_table[func_name] = {"type": "function", "params": params, "is_array": False, "dimensions": []}

    def parameter(self):
        params = []
        token = self.peek_next_token()
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            param_type = token
            self.data_type()
            param_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "parameter name")
            if param_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Parameter '{param_name}' already declared")
            dims = self.add()
            self.symbol_table[param_name] = {
                "type": param_type,
                "value": None,
                "is_array": bool(dims),
                "dimensions": dims
            }
            params.append(param_name)
            self.pmeter_tail(params)
        return params

    def pmeter_tail(self, params):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "parameter separator")
            self.parameter().extend(params)

    def add(self):
        dims = []
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "array param open")
            dim = self.in_param()
            dims.append(dim if dim else None)
            self.match_and_advance(["]"], "array param close")
            dims.extend(self.add2())
        return dims

    def add2(self):
        dims = []
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "2d array param open")
            dim = self.in_param()
            dims.append(dim if dim else None)
            self.match_and_advance(["]"], "2d array param close")
        return dims

    def in_param(self):
        if self.peek_next_token() == "Identifier":
            dim_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "array index param")
            return dim_name
        return None

    def data_type(self):
        expected = ["Link", "Bubble", "Piece", "Flip"]
        self.match_and_advance(expected, "data type")

    def Link_tail(self):
        next_token = self.peek_next_token()
        if next_token == "=":
            self.match_and_advance(["="], "assignment")
            value = self.Link_dec()
            expr = self.Link_express()
            if expr is not None:
                value = self.evaluate_expression(value, expr)
            self.Link_add()
            return value
        elif next_token == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            value = self.Link_init()
            self.symbol_table[var_name] = {"type": "Link", "value": value, "is_array": False, "dimensions": []}
            self.Link_tail()
        return None

    def Link_dec(self):
        token = self.peek_next_token()
        if token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "Link value")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            return self.symbol_table[var_name]["value"]
        elif token == "Linklit":
            value = int(float(self.lexemes[self.current_index]))  # Convert to integer
            self.match_and_advance(["Linklit"], "Link value")
            return value
        raise ValueError(f"Line {self.current_line}: Expected Identifier or Linklit, found '{token}'")

    def Link_express(self):
        if self.peek_next_token() in ["+", "-", "*", "/", "%"]:
            op = self.peek_next_token()
            self.arith_op()
            value = self.value()
            rest = self.Link_express()
            return (op, value, rest) if rest else (op, value)
        return None

    def Link_init(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            val1 = self.value()
            op = self.peek_next_token()
            self.arith_op()
            val2 = self.value()
            expr = self.Link_express()
            result = self.evaluate_expression(val1, (op, val2, expr) if expr else (op, val2))
            return result
        return None

    def Link_add(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            value = self.Link_dec()
            expr = self.Link_express()
            if expr:
                value = self.evaluate_expression(value, expr)
            self.symbol_table[var_name] = {"type": "Link", "value": value, "is_array": False, "dimensions": []}
            self.Link_add()

    def Bubble_tail(self):
        # Similar to Link_tail, adjusted for Bubblelit
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            value = self.Bubble_dec()
            expr = self.Link_express()  # Reusing Link_express for simplicity
            if expr:
                value = self.evaluate_expression(value, expr)
            self.Bubble_add()
            return value
        elif self.peek_next_token == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            value = self.Link_init()  # Reusing Link_init
            self.symbol_table[var_name] = {"type": "Bubble", "value": value, "is_array": False, "dimensions": []}
            self.Bubble_tail()
        return None

    def Bubble_dec(self):
        token = self.peek_next_token()
        if token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "Bubble value")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            return self.symbol_table[var_name]["value"]
        elif token == "Bubblelit":
            value = float(self.lexemes[self.current_index])  # Keep it as float
            self.match_and_advance(["Bubblelit"], "Bubble value")
            return value
        raise ValueError(f"Line {self.current_line}: Expected Identifier or Bubblelit, found '{token}'")

    def Bubble_add(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            value = self.Bubble_dec()
            expr = self.Link_express()
            if expr:
                value = self.evaluate_expression(value, expr)
            self.symbol_table[var_name] = {"type": "Bubble", "value": value, "is_array": False, "dimensions": []}
            self.Bubble_add()

    def Piece_tail(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(['"'], "string literal open")
            value = self.lexemes[self.current_index]
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.match_and_advance(['"'], "string literal close")
            self.Piece_init()
            return value
        elif self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            value = self.Piece_tail()
            self.symbol_table[var_name] = {"type": "Piece", "value": value, "is_array": False, "dimensions": []}
        return None

    def Piece_init(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(['"'], "string literal open")
            value = self.lexemes[self.current_index]
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.match_and_advance(['"'], "string literal close")
            self.symbol_table[var_name] = {"type": "Piece", "value": value, "is_array": False, "dimensions": []}
            self.Piece_init()

    def Flip_tail(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            value = self.lexemes[self.current_index] == "true"  # Assuming Fliplit is boolean
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.Flip_init()
            return value
        elif self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            value = self.Flip_tail()
            self.symbol_table[var_name] = {"type": "Flip", "value": value, "is_array": False, "dimensions": []}
        return None

    def Flip_init(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            value = self.lexemes[self.current_index] == "true"
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.symbol_table[var_name] = {"type": "Flip", "value": value, "is_array": False, "dimensions": []}
            self.Flip_init()

    def const_declaration(self):
        self.match_and_advance(["Const"], "constant declaration")
        data_type, var_name, value = self.const_elem()
        if var_name in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Constant '{var_name}' already declared")
        self.symbol_table[var_name] = {"type": data_type, "value": value, "is_array": False, "dimensions": [], "is_const": True}
        self.match_and_advance([";"], "constant declaration end")

    def const_elem(self):
        data_type = self.peek_next_token()
        self.data_type()
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "constant name")
        self.match_and_advance(["="], "constant assignment")
        if data_type == "Link":
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "Link literal")
            self.Link_constail()
        elif data_type == "Bubble":
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Bubblelit"], "Bubble literal")
            self.Bubble_constail()
        elif data_type == "Piece":
            self.match_and_advance(['"'], "string literal open")
            value = self.lexemes[self.current_index]
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.match_and_advance(['"'], "string literal close")
            self.Piece_constail()
        elif data_type == "Flip":
            value = self.lexemes[self.current_index] == "true"
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.Flip_constail()
        return data_type, var_name, value

    def Link_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "constant name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Constant '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "Link literal")
            self.symbol_table[var_name] = {"type": "Link", "value": value, "is_array": False, "dimensions": [], "is_const": True}
            self.Link_constail()

    def Bubble_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "constant name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Constant '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Bubblelit"], "Bubble literal")
            self.symbol_table[var_name] = {"type": "Bubble", "value": value, "is_array": False, "dimensions": [], "is_const": True}
            self.Bubble_constail()

    def Piece_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "constant name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Constant '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            self.match_and_advance(['"'], "string literal open")
            value = self.lexemes[self.current_index]
            self.match_and_advance(["Piecelit"], "Piece literal")
            self.match_and_advance(['"'], "string literal close")
            self.symbol_table[var_name] = {"type": "Piece", "value": value, "is_array": False, "dimensions": [], "is_const": True}
            self.Piece_constail()

    def Flip_constail(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "constant separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "constant name")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Constant '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            value = self.lexemes[self.current_index] == "true"
            self.match_and_advance(["Fliplit"], "Flip literal")
            self.symbol_table[var_name] = {"type": "Flip", "value": value, "is_array": False, "dimensions": [], "is_const": True}
            self.Flip_constail()

    def struct_declaration(self):
        self.match_and_advance(["Set"], "struct declaration")
        struct_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "struct name")
        self.match_and_advance(["{"], "struct body open")
        fields = {}
        while self.peek_next_token() in ["Link", "Bubble", "Piece", "Flip"]:
            field_type = self.peek_next_token()
            self.data_type()
            field_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "field name")
            value = None
            if field_type == "Link":
                value = self.Link_tail()
            elif field_type == "Bubble":
                value = self.Bubble_tail()
            elif field_type == "Piece":
                value = self.Piece_tail()
            elif field_type == "Flip":
                value = self.Flip_tail()
            fields[field_name] = {"type": field_type, "value": value}
            self.match_and_advance([";"], "field declaration end")
        self.match_and_advance(["}"], "struct body close")
        self.symbol_table[struct_name] = {"type": "Set", "fields": fields, "is_array": False, "dimensions": []}

    def array_declaration(self):
        data_type = self.peek_next_token()
        self.data_type()
        array_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "array name")
        self.match_and_advance(["["], "array size open")
        size1 = int(self.lexemes[self.current_index])
        self.match_and_advance(["Linklit"], "array size")
        self.match_and_advance(["]"], "array size close")
        dims = [size1]
        dims.extend(self.two_d())
        if array_name in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Array '{array_name}' already declared")
        values = None
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "array initialization")
            if data_type == "Link":
                values = self.Link_arrayA(dims)
            elif data_type == "Bubble":
                values = self.Bubble_arrayA(dims)
            elif data_type == "Piece":
                values = self.Piece_arrayA(dims)
            elif data_type == "Flip":
                values = self.Flip_arrayA(dims)
        self.match_and_advance([";"], "array declaration end")
        self.symbol_table[array_name] = {
            "type": data_type,
            "value": values if values else [None] * (dims[0] if len(dims) == 1 else dims[0] * dims[1]),
            "is_array": True,
            "dimensions": dims
        }

    def two_d(self):
        dims = []
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "2d array open")
            size = int(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "2d array size")
            self.match_and_advance(["]"], "2d array close")
            dims.append(size)
        return dims

    def Link_arrayA(self, dims):
        self.match_and_advance(["{"], "array values open")
        values = self.Link_arrayB()
        self.match_and_advance(["}"], "array values close")
        additional = self.Link_arrayD()
        if len(dims) == 1:
            if additional:
                raise ValueError(f"Line {self.current_line}: Extra initialization for 1D array")
            return values
        elif len(dims) == 2:
            matrix = [values]
            matrix.extend(additional)
            if len(matrix) != dims[0] or any(len(row) != dims[1] for row in matrix):
                raise ValueError(f"Line {self.current_line}: Array dimensions mismatch {dims} vs {len(matrix)}x{len(values)}")
            return matrix
        return values

    def Link_arrayB(self):
        values = []
        if self.peek_next_token() == "Linklit":
            values.append(float(self.lexemes[self.current_index]))
            self.match_and_advance(["Linklit"], "Link literal")
            values.extend(self.Link_arrayC())
        return values

    def Link_arrayC(self):
        values = []
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")
            values.append(float(self.lexemes[self.current_index]))
            self.match_and_advance(["Linklit"], "Link literal")
        return values

    def Link_arrayD(self):
        rows = []
        while self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")
            row = self.Link_arrayB()
            self.match_and_advance(["}"], "nested array close")
            rows.append(row)
        return rows

    def Bubble_arrayA(self, dims):
        self.match_and_advance(["{"], "array values open")
        values = self.Bubble_arrayB()
        self.match_and_advance(["}"], "array values close")
        additional = self.Bubble_arrayD()
        if len(dims) == 1:
            if additional:
                raise ValueError(f"Line {self.current_line}: Extra initialization for 1D array")
            return values
        elif len(dims) == 2:
            matrix = [values]
            matrix.extend(additional)
            if len(matrix) != dims[0] or any(len(row) != dims[1] for row in matrix):
                raise ValueError(f"Line {self.current_line}: Array dimensions mismatch {dims} vs {len(matrix)}x{len(values)}")
            return matrix
        return values

    def Bubble_arrayB(self):
        values = []
        if self.peek_next_token() == "Bubblelit":
            values.append(float(self.lexemes[self.current_index]))
            self.match_and_advance(["Bubblelit"], "Bubble literal")
            values.extend(self.Bubble_arrayC())
        return values

    def Bubble_arrayC(self):
        values = []
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")
            values.append(float(self.lexemes[self.current_index]))
            self.match_and_advance(["Bubblelit"], "Bubble literal")
        return values

    def Bubble_arrayD(self):
        rows = []
        while self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")
            row = self.Bubble_arrayB()
            self.match_and_advance(["}"], "nested array close")
            rows.append(row)
        return rows

    def Piece_arrayA(self, dims):
        self.match_and_advance(["{"], "array values open")
        values = self.Piece_arrayB()
        self.match_and_advance(["}"], "array values close")
        additional = self.Piece_arrayD()
        if len(dims) == 1:
            if additional:
                raise ValueError(f"Line {self.current_line}: Extra initialization for 1D array")
            return values
        elif len(dims) == 2:
            matrix = [values]
            matrix.extend(additional)
            if len(matrix) != dims[0] or any(len(row) != dims[1] for row in matrix):
                raise ValueError(f"Line {self.current_line}: Array dimensions mismatch {dims} vs {len(matrix)}x{len(values)}")
            return matrix
        return values

    def Piece_arrayB(self):
        values = []
        if self.peek_next_token() == "Piecelit":
            values.append(self.lexemes[self.current_index])
            self.match_and_advance(["Piecelit"], "Piece literal")
            values.extend(self.Piece_arrayC())
        return values

    def Piece_arrayC(self):
        values = []
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")
            values.append(self.lexemes[self.current_index])
            self.match_and_advance(["Piecelit"], "Piece literal")
        return values

    def Piece_arrayD(self):
        rows = []
        while self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")
            row = self.Piece_arrayB()
            self.match_and_advance(["}"], "nested array close")
            rows.append(row)
        return rows

    def Flip_arrayA(self, dims):
        self.match_and_advance(["{"], "array values open")
        values = self.Flip_arrayB()
        self.match_and_advance(["}"], "array values close")
        additional = self.Flip_arrayD()
        if len(dims) == 1:
            if additional:
                raise ValueError(f"Line {self.current_line}: Extra initialization for 1D array")
            return values
        elif len(dims) == 2:
            matrix = [values]
            matrix.extend(additional)
            if len(matrix) != dims[0] or any(len(row) != dims[1] for row in matrix):
                raise ValueError(f"Line {self.current_line}: Array dimensions mismatch {dims} vs {len(matrix)}x{len(values)}")
            return matrix
        return values

    def Flip_arrayB(self):
        values = []
        if self.peek_next_token() == "Fliplit":
            values.append(self.lexemes[self.current_index] == "true")
            self.match_and_advance(["Fliplit"], "Flip literal")
            values.extend(self.Flip_arrayC())
        return values

    def Flip_arrayC(self):
        values = []
        while self.peek_next_token() == ",":
            self.match_and_advance([","], "array value separator")
            values.append(self.lexemes[self.current_index] == "true")
            self.match_and_advance(["Fliplit"], "Flip literal")
        return values

    def Flip_arrayD(self):
        rows = []
        while self.peek_next_token() == "{":
            self.match_and_advance(["{"], "nested array open")
            row = self.Flip_arrayB()
            self.match_and_advance(["}"], "nested array close")
            rows.append(row)
        return rows

    def body(self, is_main_function=False):
        while self.peek_next_token() and self.peek_next_token() not in ["}", None]:
            token = self.peek_next_token()
            if token in ["Link", "Bubble", "Piece", "Flip"]:
                self.statements()
                self.slist()
            elif token in ["Ifsnap", "Change", "Do", "Put", "Display", "Create", "Identifier"]:
                self.slist()
            elif token in ["Revoid", "Rebrick"]:  # Allow return anywhere
                self.void()
                return  # Exit the body method, simulating function return
            else:
                raise ValueError(f"Line {self.current_line}: Unexpected token '{token}' in body")
        if is_main_function:
            self.void()

    def statements(self):
        token = self.peek_next_token()
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            self.states()
            self.slist()

    def states(self):
        if self.peek_two_tokens_ahead() == "[":
            self.add_array()
        else:
            self.add_dec()

    def slist(self):
        token = self.peek_next_token()
        if token in ["Ifsnap", "Change", "Do", "Put", "Display", "Create", "Identifier"]:
            self.stateset()
            self.slist()

    def add_dec(self):
        self.variable_declaration()
        if self.peek_next_token() in ["Link", "Bubble", "Piece", "Flip"]:
            self.add_dec()

    def add_array(self):
        self.array_declaration()
        if self.peek_next_token() in ["Link", "Bubble", "Piece", "Flip"]:
            self.add_array()

    def stateset(self):
        token = self.peek_next_token()
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

    def create(self):
        self.match_and_advance(["Create"], "input statement")
        self.match_and_advance(["("], "input open")
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "input variable")
        self.match_and_advance([")"], "input close")
        self.match_and_advance([";"], "input statement end")
        # Simulate input (for now, assign a default value)
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Variable '{var_name}' not declared")
        self.symbol_table[var_name]["value"] = 0  # Placeholder for input

    def display(self):
        self.match_and_advance(["Display"], "display statement")
        output = []
        
        # Handle single or multiple arguments
        while self.peek_next_token() not in [";"]:
            if self.peek_next_token() == '"':
                self.match_and_advance(['"'], "string open")
                string_content = self.lexemes[self.current_index]
                self.match_and_advance(["Piecelit"], "string content")
                self.match_and_advance(['"'], "string close")
                output.append(string_content)
            elif self.peek_next_token() == "Identifier":
                var_name = self.lexemes[self.current_index]
                if var_name not in self.symbol_table:
                    raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
                output.append(str(self.symbol_table[var_name]["value"]))
                self.match_and_advance(["Identifier"], "variable")
            if self.peek_next_token() == ",":
                self.match_and_advance([","], "separator")
        
        self.display_output.append("".join(output))
        self.match_and_advance([";"], "display end")

    def out_print(self):
        token = self.peek_next_token()
        result = ""
        if token == '"':
            self.match_and_advance(['"'], "string literal open")
            string_content = self.lexemes[self.current_index]
            self.match_and_advance(["Piecelit"], "string literal content")
            self.match_and_advance(['"'], "string literal close")
            result += string_content
            result += self.out_show()
        elif token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            indices = self.out_display()
            value = self.symbol_table[var_name]["value"]
            if indices:
                for idx in indices:
                    value = value[int(idx)]
            # Check if the type is Bubble, keep float format
            if self.symbol_table[var_name]["type"] == "Bubble":
                result += f"{value:.2f}"  # Display as float with 2 decimal places
            else:
                result += str(int(value))  # Convert float to int for display
            result += self.out_show()
        return result

    def out_show(self):
        result = ""
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "output separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            value = self.symbol_table[var_name]["value"]
            expr = self.out_dis()
            if expr:
                value = self.evaluate_expression(value, expr)
            result += " " + str(value)
            result += self.out_show()
        return result

    def out_dis(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "output separator")
            self.match_and_advance(['"'], "string literal open")
            string_content = self.lexemes[self.current_index]
            self.match_and_advance(["Piecelit"], "string literal content")
            self.match_and_advance(['"'], "string literal close")
            return ("+", string_content, None)
        elif self.peek_next_token() in ["+", "-", "*", "/", "%"]:
            op = self.peek_next_token()
            self.arith_op()
            value = self.value()
            rest = self.out_dis()
            return (op, value, rest) if rest else (op, value)
        return None

    def out_display(self):
        indices = []
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "array index open")
            indices.append(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "array index")
            self.match_and_advance(["]"], "array index close")
            indices.extend(self.two_d())
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "variable separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            value = self.symbol_table[var_name]["value"]
            indices.append(str(value))
            self.out_display()
        return indices

    def value(self):
        token = self.peek_next_token()
        if token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "value")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            return self.symbol_table[var_name]["value"]  # Get the value from the symbol table
        elif token in ["Linklit", "Bubblelit"]:
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(token, "value")
            return value
        raise ValueError(f"Line {self.current_line}: Expected value, found '{token}'")

    def condi_stat(self):
        token = self.peek_next_token()
        if token == "Ifsnap":
            self.if_statement()
        elif token == "Change":
            self.switch_statement()

    def if_statement(self):
        self.match_and_advance(["Ifsnap"], "if statement")
        self.match_and_advance(["("], "condition open")
        condition_result = self.condition()
        self.match_and_advance([")"], "condition close")
        self.match_and_advance(["{"], "if body open")
        if condition_result:
            self.display()
        else:
            self.skip_body()  # Skip the if body if condition is false
        self.match_and_advance(["}"], "if body close")
        if self.peek_next_token() == "Snap":
            self.match_and_advance(["Snap"], "else statement")
            self.match_and_advance(["{"], "else body open")
            if not condition_result:
                self.display()
            else:
                self.skip_body()  # Skip the else body if condition is true
            self.match_and_advance(["}"], "else body close")
    
    def skip_body(self):
        # Skip tokens until we reach the closing brace of the current block
        brace_count = 1
        while brace_count > 0 and self.current_index < len(self.tokens):
            token = self.peek_next_token()
            if token == "{":
                brace_count += 1
            elif token == "}":
                brace_count -= 1
            self.current_index += 1
        # Back up one step to point at the '}' so match_and_advance can consume it
        self.current_index -= 1

    def snapif(self, prev_condition):
        while self.peek_next_token() == "Snapif" and not prev_condition:
            self.match_and_advance(["Snapif"], "elseif statement")
            self.match_and_advance(["("], "condition open")
            condition_result = self.condition()
            self.match_and_advance([")"], "condition close")
            self.match_and_advance(["{"], "elseif body open")
            if condition_result:
                self.body(is_main_function=False)
            else:
                self.skip_body()
            self.match_and_advance(["}"], "elseif body close")
            if condition_result:
                break

    def snap(self, prev_condition):
        if self.peek_next_token() == "Snap" and not prev_condition:
            self.match_and_advance(["Snap"], "else statement")
            self.match_and_advance(["{"], "else body open")
            self.body(is_main_function=False)
            self.match_and_advance(["}"], "else body close")

    def switch_statement(self):
        self.match_and_advance(["Change"], "switch statement")
        self.match_and_advance(["("], "switch expression open")
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "switch variable")
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
        switch_value = self.symbol_table[var_name]["value"]
        self.match_and_advance([")"], "switch expression close")
        self.match_and_advance(["{"], "switch body open")
        executed = self.base(switch_value)
        if not executed:
            self.define()
        self.match_and_advance(["}"], "switch body close")

    def base(self, switch_value):
        executed = False
        while self.peek_next_token() == "Base":
            self.match_and_advance(["Base"], "case start")
            case_value = self.value()
            self.match_and_advance([";"], "case separator")
            if switch_value == case_value:
                self.body(is_main_function=False)
                executed = True
            else:
                self.skip_body()
            self.broke()
            if executed:
                break
            self.bases(switch_value)
        return executed

    def bases(self, switch_value):
        if self.peek_next_token() == "Base":
            self.base(switch_value)

    def broke(self):
        if self.peek_next_token() == "Broke":
            self.match_and_advance(["Broke"], "break statement")
            self.match_and_advance([";"], "break statement end")

    def define(self):
        if self.peek_next_token() == "Def":
            self.match_and_advance(["Def"], "default case")
            self.match_and_advance([":"], "default separator")
            self.body(is_main_function=False)

    def condition(self):
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "variable")
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
        self.match_and_advance(["%"], "modulo")
        mod_val = float(self.lexemes[self.current_index])
        self.match_and_advance(["Linklit"], "mod value")
        self.match_and_advance(["=="], "equals")
        check_val = float(self.lexemes[self.current_index])
        self.match_and_advance(["Linklit"], "check value")
        return (self.symbol_table[var_name]["value"] % mod_val) == check_val
    
    def logical_expression(self):
        # Handle && and || operators
        left = self.comparison()
        while self.peek_next_token() in ["&&", "||"]:
            op = self.peek_next_token()
            self.match_and_advance([op], "logical operator")
            right = self.comparison()
            if op == "&&":
                result = left and right
                self.output.append(f"Condition: {self.last_condition_str} -> {left}")
                self.output.append(f"Condition: {self.last_comparison_str} -> {right}")
                self.output.append(f"Logical {op}: {left} {op} {right} -> {result}")
                left = result
            elif op == "||":
                result = left or right
                self.output.append(f"Condition: {self.last_condition_str} -> {left}")
                self.output.append(f"Condition: {self.last_comparison_str} -> {right}")
                self.output.append(f"Logical {op}: {left} {op} {right} -> {result}")
                left = result
        return left

    def comparison(self):
        val1 = self.value()
        op = self.peek_next_token()
        self.op()
        val2 = self.value()
        result = self.evaluate_condition(val1, op, val2)
        self.last_condition_str = f"{val1} {op} {val2}"
        self.last_comparison_str = f"{val1} {op} {val2}"  # For compound conditions
        return result

    def condi(self, prev_result):
        if self.peek_next_token() in ["==", "!=", "<", ">", ">=", "<=", "||", "&&", "!!"]:
            op = self.peek_next_token()
            self.op()
            val = self.value()
            arith = self.arith()
            if arith:
                val = self.evaluate_expression(val, arith)
            prev_result = self.evaluate_condition(prev_result, op, val)
            self.condi(prev_result)
        return prev_result

    def op(self):
        token = self.peek_next_token()
        if token in ["==", "!=", "<", ">", ">=", "<=", "||", "&&", "!!"]:
            self.match_and_advance(token, "operator")

    def rel_op(self):
        token = self.peek_next_token()
        if token in ["==", "!=", ">=", "<="]:
            self.match_and_advance(token, "relational operator")
        elif token in [">", "<"]:
            self.match_and_advance(token, "relational operator")
            self.rel2()

    def rel2(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "relational operator extension")

    def log_op(self):
        token = self.peek_next_token()
        if token in ["||", "&&", "!!"]:
            self.match_and_advance(token, "logical operator")

    def arith_op(self):
        token = self.peek_next_token()
        if token in ["+", "-", "*", "/", "%"]:
            self.match_and_advance(token, "arithmetic operator")

    def arith(self):
        if self.peek_next_token() in ["+", "-", "*", "/", "%"]:
            op = self.peek_next_token()
            self.arith_op()
            value = self.value()
            rest = self.arith()
            return (op, value, rest) if rest else (op, value)
        return None

    def var_assign(self):
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "variable name")
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
        op = self.peek_next_token()
        self.ass_com()
        value = self.expression()
        self.match_and_advance([";"], "assignment end")
        current_value = self.symbol_table[var_name]["value"]
        new_value = self.evaluate_assignment(current_value, op, value)
        self.symbol_table[var_name]["value"] = new_value
        self.output.append(f"{var_name}: {current_value} {op} {value} => {new_value}")

    def expression(self):
        val = self.value()
        arith = self.arith()
        if arith:
            initial_val = val
            val = self.evaluate_expression(val, arith)
            self.output.append(f"Expression: {initial_val} {self.format_expression(arith)} => {val}")
        return val

    def ass_com(self):
        token = self.peek_next_token()
        if token in ["=", "+=", "-=", "*=", "/=", "%="]:
            self.match_and_advance(token, "assignment operator")

    def loop_stat(self):
        token = self.peek_next_token()
        if token == "Do":
            self.do_while_loop()
        elif token == "Put":
            self.for_loop()

    def do_while_loop(self):
        self.match_and_advance(["Do"], "do-while loop")
        self.match_and_advance(["{"], "do-while body open")
        self.body(is_main_function=False)
        self.match_and_advance(["}"], "do-while body close")
        self.match_and_advance(["While"], "do-while condition start")
        self.match_and_advance(["("], "condition open")
        condition_result = self.condition()
        self.match_and_advance([")"], "condition close")
        self.match_and_advance(["{"], "do-while second body open")
        if condition_result:
            self.body(is_main_function=False)
        else:
            self.skip_body()
        self.match_and_advance(["}"], "do-while second body close")

    def for_loop(self):
        self.match_and_advance(["Put"], "for loop")
        self.match_and_advance(["("], "for params open")
        self.init_state()
        self.match_and_advance([";"], "init separator")
        # Capture the condition tokens
        condition_start = self.current_index
        condition_end = condition_start
        while self.tokens[condition_end] != ";":
            condition_end += 1
        condition_tokens = self.tokens[condition_start:condition_end]
        condition_lexemes = self.lexemes[condition_start:condition_end]
        self.current_index = condition_end
        self.match_and_advance([";"], "condition separator")
        # Capture the update tokens
        update_start = self.current_index
        update_end = update_start
        while self.tokens[update_end] != ")":
            update_end += 1
        update_tokens = self.tokens[update_start:update_end]
        update_lexemes = self.lexemes[update_start:update_end]
        self.current_index = update_end
        self.match_and_advance([")"], "for params close")
        self.match_and_advance(["{"], "for body open")
        body_start = self.current_index
        # Find the end of the body
        body_end = body_start
        depth = 1
        while depth > 0:
            token = self.tokens[body_end]
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
            body_end += 1
        body_end -= 1  # Point to the closing brace
        # Evaluate the condition dynamically
        while True:
            # Evaluate condition
            temp_index = self.current_index
            self.current_index = condition_start
            self.tokens[condition_start:condition_end] = condition_tokens
            self.lexemes[condition_start:condition_end] = condition_lexemes
            condition_result = self.condition()
            self.current_index = temp_index
            if not condition_result:
                break
            # Execute body
            self.current_index = body_start
            self.body(is_main_function=False)
            self.loop_con()
            # Execute update
            temp_index = self.current_index
            self.current_index = update_start
            self.tokens[update_start:update_end] = update_tokens
            self.lexemes[update_start:update_end] = update_lexemes
            self.update_express()
            self.current_index = temp_index
        self.current_index = body_end
        self.match_and_advance(["}"], "for body close")

    def init_state(self):
        token = self.peek_next_token()
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            data_type = self.peek_next_token()
            self.data_type()
            identifier = self.peek_next_token()
            self.match_and_advance(["Identifier"], "variable")
            # Add to symbol_table immediately
            self.symbol_table[identifier] = {
                "type": data_type,
                "value": None,  # Temporary value
                "is_array": False,
                "dimensions": [],
                "is_const": False
            }
            self.match_and_advance(["="], "assignment")
            value = self.value()
            arith = self.arith()
            if arith:
                value = self.evaluate_expression(value, arith)
            self.symbol_table[identifier]["value"] = value
            # Advance to the semicolon
            while self.peek_next_token() != ";":
                self.advance()
            print(f"Added {identifier} to symbol_table: {self.symbol_table[identifier]}")
        elif token == "Identifier":
            identifier = self.peek_next_token()
            self.match_and_advance(["Identifier"], "variable")
            if identifier not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{identifier}' in loop initialization")
            self.match_and_advance(["="], "assignment")
            value = self.value()
            arith = self.arith()
            if arith:
                value = self.evaluate_expression(value, arith)
            self.symbol_table[identifier]["value"] = value
            while self.peek_next_token() != ";":
                self.advance()
        print(f"Updated {identifier} in symbol_table: {self.symbol_table[identifier]}")
        self.add_loop()

    def add_loop(self):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "init separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            if var_name in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' already declared")
            self.match_and_advance(["="], "assignment")
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "Link literal")
            expr = self.arith()
            if expr:
                value = self.evaluate_expression(value, expr)
            self.symbol_table[var_name] = {"type": "Link", "value": value, "is_array": False, "dimensions": []}
            self.add_loop()

    def update_express(self):
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "variable")
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
        token = self.peek_next_token()
        if token in ["++", "--"]:
            self.match_and_advance(token, "update operator")
            current_value = self.symbol_table[var_name]["value"]
            self.symbol_table[var_name]["value"] = current_value + 1 if token == "++" else current_value - 1

    def loop_con(self):
        token = self.peek_next_token()
        if token in ["Broke", "Con"]:
            self.match_and_advance(token, "loop control")
            self.match_and_advance([";"], "loop control end")
            # For simplicity, we don't fully implement break/continue here

    def function_call(self):
        func_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "function name")
        if func_name not in self.symbol_table or self.symbol_table[func_name]["type"] != "function":
            raise ValueError(f"Line {self.current_line}: Undefined function '{func_name}'")
        self.match_and_advance(["("], "param list open")
        params = self.param()
        self.match_and_advance([")"], "param list close")
        self.match_and_advance([";"], "function call end")
        expected_params = self.symbol_table[func_name]["params"]
        if len(params) != len(expected_params):
            raise ValueError(f"Line {self.current_line}: Parameter count mismatch for '{func_name}'")

    def param(self):
        params = []
        token = self.peek_next_token()
        if token in ["Identifier", "Linklit", "Bubblelit", "Piecelit", "Fliplit"]:
            params.append(self.value())
            self.paramA(params)
        return params

    def paramA(self, params):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "param separator")
            params.append(self.value())
            self.paramA(params)

    def void(self):
        token = self.peek_next_token()
        if token == "Revoid":
            self.match_and_advance(["Revoid"], "return void")
            self.match_and_advance([";"], "return end")
        elif token == "Rebrick":
            self.match_and_advance(["Rebrick"], "return statement")
            return_value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "return value")
            self.match_and_advance([";"], "return end")
            return return_value

    def evaluate_expression(self):
        # Get the first operand
        if self.peek_next_token() == "Linklit":
            result = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "literal")
        elif self.peek_next_token() == "Identifier":
            var_name = self.lexemes[self.current_index]
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            result = self.symbol_table[var_name]["value"]
            self.match_and_advance(["Identifier"], "variable")
        else:
            raise ValueError(f"Line {self.current_line}: Expected operand, found '{self.peek_next_token()}'")

        # Continue while there are operators
        while self.peek_next_token() in ["+", "-", "*", "/"]:
            op = self.peek_next_token()
            self.match_and_advance([op], "operator")
            
            if self.peek_next_token() == "Linklit":
                next_val = float(self.lexemes[self.current_index])
                self.match_and_advance(["Linklit"], "literal")
            elif self.peek_next_token() == "Identifier":
                next_var = self.lexemes[self.current_index]
                if next_var not in self.symbol_table:
                    raise ValueError(f"Line {self.current_line}: Undefined variable '{next_var}'")
                next_val = self.symbol_table[next_var]["value"]
                self.match_and_advance(["Identifier"], "variable")
            else:
                raise ValueError(f"Line {self.current_line}: Expected operand after '{op}'")

            if op == "+":
                result += next_val
            elif op == "-":
                result -= next_val
            elif op == "*":
                result *= next_val
            elif op == "/":
                result /= next_val if next_val != 0 else float('inf')
        
        return result
    
    def format_expression(self, expr):
        if not expr:
            return ""
        op, value = expr[0], expr[1]
        rest = expr[2] if len(expr) > 2 else None
        result = f"{op} {value}"
        if rest:
            result += " " + self.format_expression(rest)
        return result

    def evaluate_condition(self, left, op, right):
        if op == "==":
            return left == right
        elif op == "!=":
            return left != right
        elif op == ">":
            return left > right
        elif op == "<":
            return left < right
        elif op == ">=":
            return left >= right
        elif op == "<=":
            return left <= right
        elif op == "||":
            return left or right
        elif op == "&&":
            return left and right
        elif op == "!!":
            return not left
        raise ValueError(f"Line {self.current_line}: Unknown operator '{op}'")

    def evaluate_assignment(self, current, op, value):
        if op == "=":
            return value
        elif op == "+=":
            return current + value
        elif op == "-=":
            return current - value
        elif op == "*=":
            return current * value
        elif op == "/=":
            if value == 0:
                raise ValueError(f"Line {self.current_line}: Division by zero")
            return current / value
        elif op == "%=":
            if value == 0:
                raise ValueError(f"Line {self.current_line}: Modulo by zero")
            return current % value

    def skip_body(self):
        depth = 0
        while self.current_index < len(self.tokens):
            token = self.peek_next_token()
            if token == "{":
                depth += 1
            elif token == "}":
                if depth == 0:
                    return
                depth -= 1
            self.advance()

    def skip_to_end_of_body(self, start_index):
        self.current_index = start_index
        depth = 0
        while self.current_index < len(self.tokens):
            token = self.peek_next_token()
            if token == "{":
                depth += 1
            elif token == "}":
                if depth == 1:
                    return
                depth -= 1
            self.advance()

    def match_and_advance(self, expected_tokens, context):
        if isinstance(expected_tokens, str):
            expected_tokens = [expected_tokens]
        token = self.get_current_token()
        if token is None:
            raise ValueError(f"Line {self.current_line}: Unexpected end of input in {context}")
        if token in expected_tokens:
            self.advance()
        else:
            raise ValueError(f"Line {self.current_line}: Expected '{', '.join(expected_tokens)}', found '{token}' in {context}")

    def get_current_token(self):
        if self.current_index < len(self.tokens):
            token = self.tokens[self.current_index]
            line_num = 1
            token_idx = 0
            for line in self.lines:
                line_tokens = [t for t in line.split() if t not in ["Space", ""]]
                for _ in line_tokens:
                    if token_idx == self.current_index:
                        self.current_line = line_num
                        return token
                    token_idx += 1
                line_num += 1
            self.current_line = line_num
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