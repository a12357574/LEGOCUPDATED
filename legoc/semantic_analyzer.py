import tkinter as tk
from tkinter import messagebox #dont remove this import, it is required for user input(Create)
class SemanticAnalyzer:
    def __init__(self, tokens, lexemes, lines, user_input_storage, semantic_output_text=None):
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
        self.lines = list(range(1, len(lines) + 1)) if lines and isinstance(lines[0], str) else lines
        self.current_index = 0
        self.current_line = 1 if lines else 1
        self.output = []
        self.symbol_table = {}
        self.display_output = []
        self.user_inputs = user_input_storage or []  # Store user inputs
        self.input_index = 0  # Track which input to use
        self.semantic_output_text = semantic_output_text  # Reference to GUI text box
        self.input_needed = False  # Flag to indicate input is needed
        # Initialize Create handling attributes
        self.create_count = 0
        self.create_vars = []
        self.last_condition_str = ""
        self.last_comparison_str = ""
        self.semantic_output_text = semantic_output_text
        self.scan_create_statements()

    def analyze(self):
        print("Analyze: tokens =", self.tokens)
        print("Analyze: lexemes =", self.lexemes)
        print("Analyze: current_index =", self.current_index)
        self.output = []
        try:
            self.program()
            if self.display_output:
                self.output.extend(self.display_output)
            if self.input_needed:
                self.output.append("Analysis paused: Please submit input and re-run Semantic Analyzer.")
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
        #redundant self.match_and_advance(["}"], "main function body close")
        self.match_and_advance(["Destroy"], "program end")

    def global_declaration(self):
        print(f"global_declaration: Starting at index {self.current_index}")
        while self.current_index < len(self.tokens):
            next_token = self.peek_next_token()
            print(f"global_declaration: next_token={next_token}, index={self.current_index}")
            if next_token in [None, "Destroy", "Subs"] or (next_token == "Link" and self.next_next_token() == "Pane"):
                return  # λ production or main function
            elif next_token in ["Link", "Bubble", "Piece", "Flip", "Const", "Set"]:
                self.declarations()
            else:
                raise ValueError(f"Line {self.current_line}: Invalid token '{next_token}' in global declarations")

    def declarations(self):
        token = self.peek_next_token()
        print(f"declarations: token={token}, index={self.current_index}, next_tokens={self.tokens[self.current_index:self.current_index+3]}")
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            # Check for array declaration
            next_token = self.tokens[self.current_index + 1] if self.current_index + 1 < len(self.tokens) else None
            two_ahead = self.peek_two_tokens_ahead()
            print(f"declarations: token={token}, next_token={next_token}, two_ahead={two_ahead}")
            if two_ahead == "[" or (next_token == "Identifier" and self.tokens[self.current_index + 2] == "[" if self.current_index + 2 < len(self.tokens) else False):
                print(f"declarations: Detected array declaration at index {self.current_index}")
                self.array_declaration()
            else:
                print(f"declarations: Detected variable declaration at index {self.current_index}")
                self.variable_declaration()
        elif token == "Const":
            print(f"declarations: Processing const declaration at index {self.current_index}")
            self.const_declaration()
        elif token == "Set":
            print(f"declarations: Processing struct declaration at index {self.current_index}")
            self.struct_declaration()
        else:
            raise ValueError(f"Line {self.current_line}: Invalid declaration start '{token}'")
        print(f"declarations: Completed, new index={self.current_index}, next_token={self.peek_next_token()}")

    def variable_declaration(self):
        print(f"variable_declaration: Starting at index {self.current_index}, token={self.peek_next_token()}")
        type_token = self.peek_next_token()
        self.match_and_advance(["Link", "Bubble", "Piece", "Flip"], "data type")
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "variable name")
        if self.peek_next_token() == "[":
            raise ValueError(f"Line {self.current_line}: Array declaration '{var_name}' should use array syntax, not variable declaration")
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            value = self.evaluate_expression()
            self.symbol_table[var_name] = {"type": type_token, "value": value}
        else:
            if type_token == "Link" or type_token == "Bubble":
                self.symbol_table[var_name] = {"type": type_token, "value": 0.0}
            elif type_token == "Piece":
                self.symbol_table[var_name] = {"type": type_token, "value": ""}
            elif type_token == "Flip":
                self.symbol_table[var_name] = {"type": type_token, "value": False}
        self.match_and_advance([";"], "declaration end")
        print(f"variable_declaration: Added {var_name} = {self.symbol_table[var_name]} to symbol_table")

    def Link_tail(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            value = self.Link_dec()
            expression = self.Link_express()
            if expression:
                initial_value = value
                value = self.evaluate_expression(value, expression)
                self.output.append(f"Assignment: {initial_value} {self.format_expression(expression)} => {value}")
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


    def subs_functions(self):
        while self.peek_next_token() == "Subs":
            self.subfunction_declaration()

    def subfunction_declaration(self):
        self.match_and_advance(["Subs"], "subfunction start")
        func_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "subfunction name")
        
        # Save function info
        self.match_and_advance(["("], "parameter list open")
        params = self.parameter()
        self.match_and_advance([")"], "parameter list close")
        self.match_and_advance(["{"], "subfunction body open")
        
        # Save the function body tokens
        body_start = self.current_index
        depth = 1
        body_end = body_start
        
        while depth > 0 and body_end < len(self.tokens):
            if self.tokens[body_end] == "{":
                depth += 1
            elif self.tokens[body_end] == "}":
                depth -= 1
            body_end += 1
        
        # Store function info including body tokens
        self.symbol_table[func_name] = {
            "type": "function",
            "params": params,
            "body_tokens": self.tokens[body_start:body_end-1],
            "body_lexemes": self.lexemes[body_start:body_end-1],
            "is_array": False,
            "dimensions": []
        }
        
        self.current_index = body_end - 1
        self.match_and_advance(["}"], "subfunction body close")
        print(f"subfunction_declaration: Stored {func_name} with params={params}, body_tokens={self.symbol_table[func_name]['body_tokens']}")

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
            expression = self.Link_express()
            if expression is not None:
                value = self.evaluate_expression(value, expression)
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
        return self.expression()

    def Link_init(self):
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            val1 = self.value()
            op = self.peek_next_token()
            self.arith_op()
            val2 = self.value()
            expression = self.Link_express()
            result = self.evaluate_expression(val1, (op, val2, expression) if expression else (op, val2))
            return int(result)
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
            expression = self.Link_express()
            if expression:
                value = self.evaluate_expression(value, expression)
            self.symbol_table[var_name] = {"type": "Link", "value": value, "is_array": False, "dimensions": []}
            self.Link_add()

    def Bubble_tail(self):
        # Similar to Link_tail, adjusted for Bubblelit
        if self.peek_next_token() == "=":
            self.match_and_advance(["="], "assignment")
            value = self.Bubble_dec()
            expression = self.Link_express()  # Reusing Link_express for simplicity
            if expression:
                value = self.evaluate_expression(value, expression)
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
            expression = self.Link_express()
            if expression:
                value = self.evaluate_expression(value, expression)
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
        size1 = int(float(self.lexemes[self.current_index]))  # Handle Linklit as float
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
        else:
            # Initialize uninitialized arrays
            if data_type == "Piece":
                values = [""] * size1
            else:
                values = [None] * size1
        self.match_and_advance([";"], "array declaration end")
        self.symbol_table[array_name] = {
            "type": data_type,
            "value": values if values else [None] * (dims[0] if len(dims) == 1 else dims[0] * dims[1]),
            "is_array": True,
            "dimensions": dims
        }
        print(f"array_declaration: Added {array_name} = {self.symbol_table[array_name]} to symbol_table")

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
        if self.peek_next_token() != "{":
            return [""] * dims[0]  # Default for uninitialized array
        self.match_and_advance(["{"], "array values open")
        values = self.Piece_arrayB()
        self.match_and_advance(["}"], "array values close")
        additional = self.Piece_arrayD()
        if len(dims) == 1:
            if additional:
                raise ValueError(f"Line {self.current_line}: Extra initialization for 1D array")
            if len(values) != dims[0]:
                raise ValueError(f"Line {self.current_line}: Array size mismatch, expected {dims[0]}, got {len(values)}")
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
        print(f"body: Starting at index {self.current_index}, tokens={self.tokens[self.current_index:self.current_index+6]}, full_tokens={self.tokens[self.current_index:]}")
        return_value = None

        while self.peek_next_token() and self.peek_next_token() not in ["}", None]:
            token = self.peek_next_token()
            print(f"body: Processing token={token}, lexeme={self.lexemes[self.current_index]}, index={self.current_index}, next_tokens={self.tokens[self.current_index:self.current_index+6]}")
            
            if token in ["Link", "Bubble", "Piece", "Flip", "Const", "Set"]:
                print(f"body: Calling declarations at index {self.current_index} for token={token}")
                self.declarations()
            elif token in ["Ifsnap", "Change", "Do", "Put", "Display", "Create"]:
                self.slist()
            elif token == "Identifier":
                next_token = self.next_next_token()
                if next_token == "(":
                    func_name = self.lexemes[self.current_index]
                    self.function_call()
                else:
                    self.slist()
            elif token == "Rebrick":
                self.match_and_advance(["Rebrick"], "return statement")
                next_token = self.peek_next_token()
                if next_token == "Identifier":
                    var_name = self.lexemes[self.current_index]
                    self.match_and_advance(["Identifier"], "return value")
                    if var_name not in self.symbol_table:
                        raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
                    return_value = self.symbol_table[var_name]["value"]
                elif next_token == "Linklit":
                    return_value = float(self.lexemes[self.current_index])
                    self.match_and_advance(["Linklit"], "return value")
                else:
                    raise ValueError(f"Line {self.current_line}: Expected Identifier or Linklit, found '{next_token}'")
                self.match_and_advance([";"], "return end")
                break
            elif token == "Revoid":
                if is_main_function:
                    self.void()
                break
            else:
                raise ValueError(f"Line {self.current_line}: Unexpected token '{token}' in body")

        if is_main_function:
            self.match_and_advance(["}"], "main function body close")

        print(f"body: Ended at index {self.current_index}")
        return return_value


    
    def statements(self):
        print(f"statements: Starting at index {self.current_index}, token={self.peek_next_token()}")
        self.declarations()  # Route to declarations instead
        print(f"statements: Ended at index {self.current_index}")

    def states(self):
        print(f"states: Starting at index {self.current_index}, token={self.peek_next_token()}")
        self.declarations()  # Route to declarations instead
        print(f"states: Ended at index {self.current_index}")
        
    def slist(self):
        print(f"slist: Starting at index {self.current_index}, token={self.peek_next_token()}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}")
        while self.peek_next_token() in ["Ifsnap", "Change", "Do", "Put", "Display", "Create", "Identifier"]:
            self.stateset()
            print(f"slist: Continuing at index {self.current_index}, token={self.peek_next_token()}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}")
        print(f"slist: Ended at index {self.current_index}")
            # Removed the recursive call to prevent reprocessing
            #self.stateset()
            #self.slist()

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
        print(f"stateset: Starting with token={token}, index={self.current_index}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}")
        
        if token in ["Ifsnap", "Change"]:
            self.condi_stat()
        elif token == "Identifier":
            next_token = self.next_next_token()
            if next_token == "(":
                # Handle function call
                func_name = self.lexemes[self.current_index]
                if func_name not in self.symbol_table:
                    raise ValueError(f"Line {self.current_line}: Undefined function '{func_name}'")
                self.function_call()
            else:
                self.var_assign()
        elif token == "Create":
            self.create()
        elif token == "Display":
            self.display()
        elif token in ["Do", "Put"]:
            self.loop_stat()
        elif token in ["Rebrick","Revoid"]:
            self.void()
        else:
            expected = ["Ifsnap", "Change", "Identifier", "Create", "Display", "Do", "Put", "Rebrick"]
            raise ValueError(f"Line {self.current_line}: Expected one of {expected}, found '{token}'")
        print(f"stateset: Ended with index={self.current_index}, next_token={self.peek_next_token()}")
        
    def scan_create_statements(self):
        """Scan tokens to count Create statements and collect variable names."""
        i = 0
        while i < len(self.tokens):
            if self.tokens[i] == "Create":
                self.create_count += 1
                # Expect Create ( Identifier ) ;
                if i + 2 < len(self.tokens) and self.tokens[i + 1] == "(" and self.tokens[i + 2] == "Identifier":
                    self.create_vars.append(self.lexemes[i + 2])
                    i += 5  # Skip Create ( Identifier ) ;
                else:
                    i += 1
            else:
                i += 1
        print(f"scan_create_statements: Found {self.create_count} Create statements, vars={self.create_vars}")

    def prompt_input(self, prompt_text):
        print(f"prompt_input: Showing prompt: {prompt_text}")
        input_value = []
        root = tk.Tk()
        root.withdraw()
        popup = tk.Toplevel(root)
        popup.title("Input Prompt")
        popup.geometry("300x150")
        popup.resizable(False, False)
        tk.Label(popup, text=prompt_text, font=("Courier", 12), wraplength=280).pack(pady=10)
        entry = tk.Entry(popup, font=("Courier", 12), width=20)
        entry.pack(pady=10)
        def submit():
            value = entry.get().strip()
            print(f"prompt_input: Submitted value='{value}'")
            if value:
                input_value.append(value)
                popup.destroy()
            else:
                messagebox.showerror("Error", "Input cannot be empty")
                input_value.append("")
        tk.Button(popup, text="Submit", command=submit, bg="#00cc00", fg="white", font=("Courier", 12)).pack(pady=10)
        entry.bind("<Return>", lambda event: submit())
        popup.update_idletasks()
        x = (root.winfo_screenwidth() - popup.winfo_width()) // 2
        y = (root.winfo_screenheight() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")
        popup.grab_set()
        root.wait_window(popup)
        root.destroy()
        result = input_value[0] if input_value else ""
        print(f"prompt_input: Returning value='{result}'")
        return result

    def create(self):
        print(f"create: Starting at index={self.current_index}, token={self.peek_next_token()}")
        self.match_and_advance(["Create"], "input statement")
        self.match_and_advance(["("], "input open")
        var_name = self.lexemes[self.current_index]
        print(f"create: var_name={var_name}")
        self.match_and_advance(["Identifier"], "input variable")
        index = None
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "array open")
            print(f"create: Evaluating array index at index={self.current_index}")
            index = self.evaluate_expression()
            print(f"create: Index evaluated to={index}")
            self.match_and_advance(["]"], "array close")
        self.match_and_advance([")"], "input close")
        self.match_and_advance([";"], "input statement end")
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Variable '{var_name}' not declared")
        is_multi_input = self.create_count >= 2 and self.input_index == 0
        var_type = self.symbol_table[var_name]["type"]
        type_hint = {"Link": "integer", "Bubble": "float", "Piece": "string", "Flip": "true/false"}.get(var_type, var_type)
        input_prompt = f"Enter input for '{var_name}' ({type_hint}):" if not is_multi_input else f"Enter inputs for {', '.join(self.create_vars)} (comma-separated, {type_hint}):"
        if self.input_index < len(self.user_inputs):
            input_value = self.user_inputs[self.input_index]
            print(f"create: Using stored input_value='{input_value}' for {var_name}")
            if is_multi_input:
                input_values = [v.strip() for v in input_value.split(",")]
                if len(input_values) != self.create_count:
                    self.display_output.append(f"Error: Expected {self.create_count} inputs, got {len(input_values)}")
                    return
                input_value = input_values[self.create_vars.index(var_name)]
                self.input_index += 1 if self.input_index + 1 == self.create_count else 0
            else:
                self.input_index += 1
        else:
            input_value = self.prompt_input(input_prompt)
            print(f"create: Received input_value='{input_value}' from prompt for {var_name}")
            if not input_value:
                self.display_output.append(f"Error: No input provided for Create('{var_name}').")
                self.input_needed = True
                return
            self.user_inputs.append(input_value)
        try:
            if var_type == "Link":
                value = int(input_value)
            elif var_type == "Bubble":
                value = float(input_value)
            elif var_type == "Piece":
                value = input_value
            elif var_type == "Flip":
                value = input_value.lower() in ["true", "1"]
            else:
                raise ValueError(f"Line {self.current_line}: Unsupported type '{var_type}' for Create")
            print(f"create: Converted input_value='{input_value}' to value={value} for type={var_type}")
        except ValueError as e:
            error_msg = f"Error: Invalid input '{input_value}' for type '{var_type}' in Create('{var_name}')."
            print(f"create: {error_msg} (Exception: {str(e)})")
            self.display_output.append(error_msg)
            return
        if index is not None:
            if not self.symbol_table[var_name].get("is_array"):
                self.display_output.append(f"Error: '{var_name}' is not an array in Create.")
                return
            index = int(index)
            if index < 0 or index >= self.symbol_table[var_name]["dimensions"][0]:
                self.display_output.append(f"Error: Array index {index} out of bounds for '{var_name}'.")
                return
            self.symbol_table[var_name]["value"][index] = value
            print(f"create: Assigned {var_name}[{index}]={value}")
        else:
            self.symbol_table[var_name]["value"] = value
            print(f"create: Assigned {var_name}={value}")

    def display(self):
        print(f"display: Starting at index {self.current_index}, token={self.peek_next_token()}")
        self.match_and_advance(["Display"], "display statement")
        output = []
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
                    raise ValueError(f"Line {self.current_line}: Undefined variable or function '{var_name}'")
                self.match_and_advance(["Identifier"], "variable or function")
                if self.symbol_table[var_name].get("type") == "function":
                    print(f"display: Detected function call to '{var_name}'")
                    saved_index = self.current_index
                    saved_tokens = self.tokens
                    saved_lexemes = self.lexemes
                    saved_display_output = self.display_output
                    self.display_output = []
                    self.function_call(var_name=var_name, is_display=True)
                    saved_display_output.extend(self.display_output)
                    self.current_index = saved_index
                    self.tokens = saved_tokens
                    self.lexemes = saved_lexemes
                    self.display_output = saved_display_output
                else:
                    value = self.symbol_table[var_name]["value"]
                    if isinstance(value, float):
                        if value.is_integer():
                            output.append(str(int(value)))
                        else:
                            output.append(f"{value:.2f}")
                    else:
                        output.append(str(value))
            else:
                value = self.evaluate_expression()
                if isinstance(value, float):
                    if value.is_integer():
                        output.append(str(int(value)))
                    else:
                        output.append(f"{value:.2f}")
                else:
                    output.append(str(value))
            if self.peek_next_token() == ",":
                self.match_and_advance([","], "separator")
        if output:
            self.display_output.append(" ".join(output))
        self.match_and_advance([";"], "display end")
        print(f"display: Output = {''.join(output) if output else 'None'}")

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
        return int(result)

    def out_show(self):
        result = ""
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "output separator")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            value = self.symbol_table[var_name]["value"]
            expression = self.out_dis()
            if expression:
                value = self.evaluate_expression(value, expression)
            result += " " + str(value)
            result += self.out_show()
        return int(result)

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
        print(f"condi_stat: Starting with token={token}, index={self.current_index}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}")
        if token == "Ifsnap":
            self.if_statement()
        elif token == "Change":
            self.switch_statement()
        print(f"condi_stat: Ended at index={self.current_index}, next_token={self.peek_next_token()}")

    def if_statement(self):
        print(f"if_statement: Starting at index={self.current_index}, token={self.peek_next_token()}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}")
        self.match_and_advance(["Ifsnap"], "if statement")
        self.match_and_advance(["("], "condition open")
        condition_result = self.condition()
        print(f"if_statement: Condition result={condition_result}, index={self.current_index}, next_token={self.peek_next_token()}")
        self.match_and_advance([")"], "condition close")
        # Handle unexpected extra parenthesis
        #if self.peek_next_token() == ")":
            #print(f"if_statement: Skipping unexpected extra ')', index={self.current_index}, lexeme={self.lexemes[self.current_index]}")
            #self.match_and_advance([")"], "unexpected extra parenthesis")
        self.match_and_advance(["{"], "if body open")
        if condition_result:
            self.body(is_main_function=False)
        else:
            self.skip_body()  # Skip the if body if condition is false
        self.match_and_advance(["}"], "if body close")
        while self.peek_next_token() == "Snap":
            self.match_and_advance(["Snap"], "else statement")
            self.match_and_advance(["{"], "else body open")
            if not condition_result:
                self.body(is_main_function=False)
            else:
                self.skip_body()  # Skip the else body if condition is true
            self.match_and_advance(["}"], "else body close")
        print(f"if_statement: Ended at index={self.current_index}, next_token={self.peek_next_token()}")
    
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
        print(f"condition: Starting at index={self.current_index}, tokens={self.tokens[self.current_index:self.current_index+5]}")
        # Parse the first comparison
        result = self.comparison()
        # Handle logical operators (||, &&) recursively
        result = self.condi(result)
        print(f"condition: Result={result}, index={self.current_index}")
        return result
    
    def logical_expression(self):
        print(f"logical_expression: Starting at index {self.current_index}, tokens={self.tokens[self.current_index:self.current_index+3]}")
        left = self.evaluate_expression()
        if self.peek_next_token() in ["==", "!=", "<", ">", "<=", ">="]:
            op = self.peek_next_token()
            self.match_and_advance([op], "comparison operator")
            right = self.evaluate_expression()
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise ValueError(f"Line {self.current_line}: Comparison operands must be numeric")
            if op == "==":
                return left == right
            elif op == "!=":
                return left != right
            elif op == "<":
                return left < right
            elif op == ">":
                return left > right
            elif op == "<=":
                return left <= right
            elif op == ">=":
                return left >= right
        return left

    def comparison(self):
        print(f"comparison: Starting at index={self.current_index}, token={self.peek_next_token()}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}, next_tokens={self.tokens[self.current_index:self.current_index+6]}")
        print(f"Debug: tokens at index {self.current_index} = {self.tokens[self.current_index:self.current_index+6]}")
        # Parse the left operand (Identifier, Linklit, or array access)
        val1 = None
        var_name = None
        
        if self.peek_next_token() == "Identifier":
            var_name = self.lexemes[self.current_index]
            val1 = self.value()  # Get variable value (e.g., "XYZ" for name)
            
            # Check for array indexing
            if self.peek_next_token() == "[":
                self.match_and_advance(["["], "array index open")
                index = None
                if self.peek_next_token() == "Identifier":
                    index_name = self.lexemes[self.current_index]
                    self.match_and_advance(["Identifier"], "index variable")
                    if index_name not in self.symbol_table:
                        raise ValueError(f"Line {self.current_line}: Undefined index variable '{index_name}'")
                    index = self.symbol_table[index_name]["value"]
                elif self.peek_next_token() == "Linklit":
                    index = float(self.lexemes[self.current_index])
                    self.match_and_advance(["Linklit"], "index literal")
                else:
                    raise ValueError(f"Line {self.current_line}: Expected Identifier or Linklit for array index, found '{self.peek_next_token()}'")
                self.match_and_advance(["]"], "array index close")
                
                # Validate array access
                if var_name not in self.symbol_table:
                    raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
                if self.symbol_table[var_name].get("is_array", False):
                    if index >= self.symbol_table[var_name]["dimensions"][0]:
                        raise ValueError(f"Line {self.current_line}: Index {index} out of bounds for array '{var_name}'")
                    val1 = self.symbol_table[var_name]["value"][int(index)]
                else:
                    # Treat non-array Piece as indexable string
                    if self.symbol_table[var_name]["type"] != "Piece":
                        raise ValueError(f"Line {self.current_line}: Indexing not supported for non-Piece variable '{var_name}'")
                    if index >= len(val1):
                        raise ValueError(f"Line {self.current_line}: Index {index} out of bounds for string '{var_name}'")
                    val1 = val1[int(index)]  # Get character from string
        else:
            val1 = self.value()  # Handle Linklit or other simple values
        
        # Get the comparison operator
        op = self.peek_next_token()
        print(f"Debug: op={op}, token={self.tokens[self.current_index]}")
        if op not in ["==", "!=", "<", ">", ">=", "<=", "%"]:
            raise ValueError(f"Line {self.current_line}: Expected comparison operator or '%', found '{op}'")
        self.match_and_advance([op], "comparison operator")
        
        if op == "%":
            # Modulo comparison: var % mod_val == check_val
            mod_val = self.value()  # Use value() to handle Identifier or Linklit
            self.match_and_advance(["=="], "equals")
            check_val = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "check value")
            result = (val1 % mod_val) == check_val
        else:
            # Parse the right operand (can be an expression, e.g., num / 2)
            val2 = self.evaluate_expression()
            result = self.evaluate_condition(val1, op, val2)
        
        self.last_condition_str = f"{val1} {op} {val2 if op != '%' else f'% {mod_val} == {check_val}'}"
        self.last_comparison_str = self.last_condition_str
        print(f"comparison: Result={result}, condition={self.last_condition_str}, index={self.current_index}")
        return result

    def condi(self, prev_result):
        # Handle logical operators (||, &&, !!)
        next_token = self.peek_next_token()
        if next_token in ["||", "&&"]:
            op = next_token
            self.match_and_advance([op], "logical operator")
            # Parse the next comparison
            val = self.comparison()
            # Evaluate the logical operation
            if op == "||":
                prev_result = prev_result or val
            elif op == "&&":
                prev_result = prev_result and val
            # Continue checking for more logical operators
            prev_result = self.condi(prev_result)
        elif next_token == "!!":
            self.match_and_advance(["!!"], "logical not")
            prev_result = not prev_result
            prev_result = self.condi(prev_result)
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
        print(f"var_assign: Starting at index {self.current_index}, token={self.peek_next_token()}, lexeme={self.lexemes[self.current_index]}")
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "variable")
        index = None
        if self.peek_next_token() == "[":
            self.match_and_advance(["["], "array open")
            index = self.evaluate_expression()
            self.match_and_advance(["]"], "array close")
        next_token = self.peek_next_token()
        if next_token != "=":
            raise ValueError(f"Line {self.current_line}: Expected '=', found '{next_token}' in assignment")
        self.match_and_advance(["="], "assignment")
        value = self.evaluate_expression()
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
        var_type = self.symbol_table[var_name]["type"]
        if index is not None:
            index = int(index)
            if var_type == "Piece" and not self.symbol_table[var_name].get("is_array"):
                if not isinstance(value, str) or len(value) != 1:
                    raise ValueError(f"Line {self.current_line}: Piece indexing requires a single character")
                current_value = self.symbol_table[var_name]["value"]
                if index < 0 or index >= len(current_value):
                    raise ValueError(f"Line {self.current_line}: Index out of bounds for '{var_name}'")
                new_value = current_value[:index] + value + current_value[index+1:]
                self.symbol_table[var_name]["value"] = new_value
                print(f"var_assign: Assigned {var_name}[{index}]={value}, new string={new_value}")
            elif self.symbol_table[var_name].get("is_array"):
                if index < 0 or index >= self.symbol_table[var_name]["dimensions"][0]:
                    raise ValueError(f"Line {self.current_line}: Array index out of bounds")
                self.symbol_table[var_name]["value"][index] = value
                print(f"var_assign: Assigned {var_name}[{index}]={value}")
            else:
                raise ValueError(f"Line {self.current_line}: '{var_name}' is not an array")
        else:
            self.symbol_table[var_name]["value"] = value
            print(f"var_assign: Assigned {var_name}={value}")
        self.match_and_advance([";"], "assignment end")

    def expression(self):
        value = self.term()
        while self.peek_next_token() in ["+", "-"]:
            op = self.peek_next_token()
            self.match_and_advance([op], "arithmetic operator")
            next_value = self.term()
            if op == "+":
                value += next_value
            elif op == "-":
                value -= next_value
        return value
    
    def term(self):
        value = self.factor()
        while self.peek_next_token() in ["*", "/", "%"]:
            op = self.peek_next_token()
            self.match_and_advance([op], "arithmetic operator")
            next_value = self.factor()
            if op == "*":
                value *= next_value
            elif op == "/":
                # Convert to float for division to preserve decimal points
                if self.tokens[self.current_index - 1] == "Linklit":
                    value = float(int(value) // int(next_value))
                else:
                    value = float(value) / float(next_value)
                # Format to 2 decimal places but keep as float
                    value = float(f"{value:.2f}")
            elif op == "%":
                value = float(value) % float(next_value)
        return value
    
    def factor(self):
        print(f"factor: Starting at index {self.current_index}, token={self.peek_next_token()}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}")
        token = self.peek_next_token()
        if token == "Linklit":
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "number")
            return value
        elif token == "Piecelit":
            value = self.lexemes[self.current_index]
            self.match_and_advance(["Piecelit"], "string literal")
            return value
        elif token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            var_type = self.symbol_table[var_name]["type"]
            if self.peek_next_token() == "[":
                self.match_and_advance(["["], "array open")
                index = self.evaluate_expression()
                self.match_and_advance(["]"], "array close")
                # Validate and convert index
                if isinstance(index, float):
                    if not index.is_integer():
                        raise ValueError(f"Line {self.current_line}: Non-integer index {index} for '{var_name}'")
                    index = int(index)
                if not isinstance(index, int):
                    raise ValueError(f"Line {self.current_line}: Invalid index type {type(index)} for '{var_name}'")
                if var_type == "Piece" and not self.symbol_table[var_name].get("is_array"):
                    value = self.symbol_table[var_name]["value"]
                    if not value:  # Handle empty string
                        raise ValueError(f"Line {self.current_line}: Cannot index empty string '{var_name}'")
                    if index < 0 or index >= len(value):
                        raise ValueError(f"Line {self.current_line}: Index {index} out of bounds for string '{var_name}'")
                    return value[index]
                elif self.symbol_table[var_name].get("is_array"):
                    if index < 0 or index >= self.symbol_table[var_name]["dimensions"][0]:
                        raise ValueError(f"Line {self.current_line}: Array index {index} out of bounds for '{var_name}'")
                    return self.symbol_table[var_name]["value"][index]
                else:
                    raise ValueError(f"Line {self.current_line}: '{var_name}' is not an array")
            return self.symbol_table[var_name]["value"]
        elif token == "(":
            self.match_and_advance(["("], "expression open")
            value = self.evaluate_expression()
            self.match_and_advance([")"], "expression close")
            return value
        elif token == "-":
            self.match_and_advance(["-"], "unary minus")
            return -self.factor()
        elif token == '"':
            self.match_and_advance(['"'], "string open")
            if self.peek_next_token() == '"':
                self.match_and_advance(['"'], "string close")
                return ""
            else:
                value = self.lexemes[self.current_index]
                self.match_and_advance(["Piecelit"], "string content")
                self.match_and_advance(['"'], "string close")
                return value
        raise ValueError(f"Line {self.current_line}: Expected value, found '{token}'")

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
        print(f"do_while_loop: Starting at index {self.current_index}")
        self.match_and_advance(["Do"], "do-while loop")
        self.match_and_advance(["{"], "do-while body open")
        body_start = self.current_index
        self.body(is_main_function=False)
        body_end = self.current_index
        self.match_and_advance(["}"], "do-while body close")
        self.match_and_advance(["While"], "do-while condition start")
        self.match_and_advance(["("], "condition open")
        condition_start = self.current_index
        condition_result = self.condition()
        condition_end = self.current_index
        self.match_and_advance([")"], "condition close")
        self.match_and_advance([";"], "do-while end")
        loop_end = self.current_index  # Index after ;
        while condition_result:
            self.current_index = body_start
            self.body(is_main_function=False)
            self.current_index = condition_start
            condition_result = self.condition()
            # Current index is now at ), match it
            self.match_and_advance([")"], "condition close")
            self.match_and_advance([";"], "do-while end")
        self.current_index = loop_end
        print(f"do_while_loop: Ended at index {self.current_index}")

    def for_loop(self):
        print(f"for_loop: Starting at index {self.current_index}")
        self.match_and_advance(["Put"], "for loop")
        self.match_and_advance(["("], "for params open")
        self.init_state()
        self.match_and_advance([";"], "init separator")
        print(f"for_loop: symbol_table after init_state = {self.symbol_table}")
        condition_start = self.current_index
        condition_end = condition_start
        while self.current_index < len(self.tokens) and self.tokens[condition_end] != ";":
            condition_end += 1
        condition_tokens = self.tokens[condition_start:condition_end]
        condition_lexemes = self.lexemes[condition_start:condition_end]
        self.current_index = condition_end
        self.match_and_advance([";"], "condition separator")
        update_start = self.current_index
        update_end = update_start
        while self.current_index < len(self.tokens) and self.tokens[update_end] != ")":
            update_end += 1
        update_tokens = self.tokens[update_start:update_end]
        update_lexemes = self.lexemes[update_start:update_end]
        self.current_index = update_end
        self.match_and_advance([")"], "for params close")
        self.match_and_advance(["{"], "for body open")
        body_start = self.current_index
        body_end = body_start
        depth = 1
        while depth > 0 and body_end < len(self.tokens):
            token = self.tokens[body_end]
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
            body_end += 1
        body_end -= 1
        body_tokens = self.tokens[body_start:body_end]
        body_lexemes = self.lexemes[body_start:body_end]
        iteration = 0
        while True:
            print(f"for_loop: Iteration {iteration}, condition_start={condition_start}, lexemes={self.lexemes[condition_start:condition_end]}")
            temp_index = self.current_index
            self.current_index = condition_start
            self.tokens[condition_start:condition_end] = condition_tokens
            self.lexemes[condition_start:condition_end] = condition_lexemes
            condition_result = self.logical_expression()
            self.current_index = temp_index
            if not condition_result:
                break
            self.current_index = body_start
            self.tokens[body_start:body_end] = body_tokens
            self.lexemes[body_start:body_end] = body_lexemes
            print(f"for_loop: Executing body at index {self.current_index}, tokens={self.tokens[self.current_index:self.current_index+6]}, lexemes={self.lexemes[self.current_index:self.current_index+6]}")
            self.body(is_main_function=False)
            self.loop_con()
            temp_index = self.current_index
            self.current_index = update_start
            self.tokens[update_start:update_end] = update_tokens
            self.lexemes[update_start:update_end] = update_lexemes
            self.update_express()
            self.current_index = temp_index
            iteration += 1
        self.current_index = body_end
        self.match_and_advance(["}"], "for body close")

    def init_state(self):
        print(f"init_state: Starting at index {self.current_index}, token={self.peek_next_token()}")
        token = self.peek_next_token()
        if token in ["Link", "Bubble", "Piece", "Flip"]:
            data_type = token
            self.match_and_advance([data_type], "data type")
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            self.match_and_advance(["="], "assignment")
            value = self.evaluate_expression()  # Parse 0, i + 1
            self.symbol_table[var_name] = {"type": data_type, "value": value}
            print(f"init_state: Added {var_name} = {{'type': {data_type}, 'value': {value}}} to symbol_table")
        elif token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "variable")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            self.match_and_advance(["="], "assignment")
            value = self.evaluate_expression()  # Parse i + 1
            self.symbol_table[var_name]["value"] = value
            print(f"init_state: Updated {var_name} = {{'type': {self.symbol_table[var_name]['type']}, 'value': {value}}} to symbol_table")
        else:
            raise ValueError(f"Line {self.current_line}: Expected data type or Identifier, found '{token}'")

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
            expression = self.arith()
            if expression:
                value = self.evaluate_expression(value, expression)
            self.symbol_table[var_name] = {"type": "Link", "value": value, "is_array": False, "dimensions": []}
            self.add_loop()

    def update_express(self):
        print(f"update_express: Starting at index {self.current_index}")
        var_name = self.lexemes[self.current_index]
        self.match_and_advance(["Identifier"], "variable")
        next_token = self.peek_next_token()
        if next_token not in ["++", "--"]:
            raise ValueError(f"Line {self.current_line}: Expected '++' or '--', found '{next_token}' in update expression")
        self.match_and_advance([next_token], "increment")
        if var_name not in self.symbol_table:
            raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
        self.symbol_table[var_name]["value"] += 1  # Update "value" key

    def loop_con(self):
        token = self.peek_next_token()
        if token in ["Broke", "Con"]:
            self.match_and_advance(token, "loop control")
            self.match_and_advance([";"], "loop control end")
            # For simplicity, we don't fully implement break/continue here

    def function_call(self, var_name=None, is_display=False):
        func_name = var_name if var_name else self.lexemes[self.current_index]
        print(f"function_call: Calling {func_name}")
        
        # Save state
        saved_state = {
            'index': self.current_index,
            'tokens': self.tokens,
            'lexemes': self.lexemes,
            'symbol_table': self.symbol_table,
            'display_output': self.display_output
        }

        # Initialize params
        params = []
        
        if not is_display:
            # Match function call syntax (in main tokens)
            self.match_and_advance(["Identifier"], "function name")
            self.match_and_advance(["("], "param list open")
            params = self.param()
            self.match_and_advance([")"], "param list close")
            self.match_and_advance([";"], "function call end")
        else:
            # For Display, don't expect ( ) ;
            pass
        
        # Lookup function info
        func_info = saved_state['symbol_table'].get(func_name)
        if not func_info or func_info.get("type") != "function":
            raise ValueError(f"Line {self.current_line}: Undefined function '{func_name}'")
        
        # Create a new symbol table for the function scope
        self.symbol_table = saved_state['symbol_table'].copy()
        
        # Bind parameter values (cal has no parameters, so this is empty)
        param_names = func_info.get("params", [])
        if len(params) != len(param_names):
            raise ValueError(f"Line {self.current_line}: Incorrect number of arguments for '{func_name}'")
        for param_name, param_value in zip(param_names, params):
            if param_name in self.symbol_table:
                self.symbol_table[param_name]["value"] = param_value
            else:
                raise ValueError(f"Line {self.current_line}: Parameter '{param_name}' not found in symbol table")
        
        # Execute function body
        self.tokens = func_info["body_tokens"]
        self.lexemes = func_info["body_lexemes"]
        self.current_index = 0
        
        return_value = self.body(is_main_function=False)
        
        # Restore state
        self.tokens = saved_state['tokens']
        self.lexemes = saved_state['lexemes']
        self.symbol_table = saved_state['symbol_table']
        if not is_display:
            self.display_output = saved_state['display_output']
        
        # Advance past the function call tokens if not in Display
        if not is_display:
            self.current_index = saved_state['index'] + 5
        
        return return_value

    def param(self):
        params = []
        token = self.peek_next_token()
        
        # Base case - no parameters
        if token not in ["Identifier", "Linklit"]:
            return params
            
        # Handle first parameter
        if token == "Identifier":
            var_name = self.lexemes[self.current_index]
            self.match_and_advance(["Identifier"], "parameter")
            if var_name not in self.symbol_table:
                raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
            value = self.symbol_table[var_name]["value"]
            if value is None:
                raise ValueError(f"Line {self.current_line}: Variable '{var_name}' has no value")
            params.append(value)
        elif token == "Linklit":
            value = float(self.lexemes[self.current_index])
            self.match_and_advance(["Linklit"], "parameter")
            params.append(value)
        
        # Handle additional parameters recursively
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "parameter separator")
            params.extend(self.param())
        
        return params


    def paramA(self, params):
        if self.peek_next_token() == ",":
            self.match_and_advance([","], "param separator")
            params.append(self.value())
            self.paramA(params)

    def void(self):
        token = self.peek_next_token()
        print(f"void: token={token}")
        if token == "Revoid":
            self.match_and_advance(["Revoid"], "return void")
            self.match_and_advance([";"], "return end")
        elif token == "Rebrick":
            self.match_and_advance(["Rebrick"], "return statement")
            # Allow both Identifier and Linklit
            next_token = self.peek_next_token()
            if next_token in ["Identifier", "Linklit"]:
                if next_token == "Identifier":
                    var_name = self.lexemes[self.current_index]
                    self.match_and_advance(["Identifier"], "return value")
                    if var_name not in self.symbol_table:
                        raise ValueError(f"Line {self.current_line}: Undefined variable '{var_name}'")
                    return_value = self.symbol_table[var_name]["value"]
                else:  # Linklit
                    return_value = float(self.lexemes[self.current_index])
                    self.match_and_advance(["Linklit"], "return value")
                self.match_and_advance([";"], "return end")
                return return_value
            else:
                raise ValueError(f"Line {self.current_line}: Expected Identifier or Linklit, found '{next_token}' in return statement")

    def evaluate_expression(self):
        print(f"evaluate_expression: Starting at index {self.current_index}, tokens={self.tokens[self.current_index:self.current_index+5]}")
        result = self.term()
        while self.current_index < len(self.tokens) and self.peek_next_token() in ["+", "-"]:
            op = self.peek_next_token()
            self.match_and_advance([op], "operator")
            right = self.term()
            if isinstance(result, str) or isinstance(right, str):
                if op != "+":
                    raise ValueError(f"Line {self.current_line}: Operator '{op}' not supported for strings")
                result = str(result) + str(right)
            else:
                if op == "+":
                    result += right
                else:
                    result -= right
        return result
    
    def format_expression(self, expression):
        if not expression:
            return ""
        op, value = expression[0], expression[1]
        rest = expression[2] if len(expression) > 2 else None
        result = f"{op} {value}"
        if rest:
            result += " " + self.format_expression(rest)
        return int(result)

    def evaluate_condition(self, left, op, right):
        print(f"evaluate_condition: left={left}, op={op}, right={right}, line={self.current_line}")
        if op in ["||", "&&", "!!"]:
            if not isinstance(left, bool) or (op != "!!" and not isinstance(right, bool)):
                raise ValueError(f"Line {self.current_line}: Logical operands must be boolean")
            if op == "||":
                return left or right
            elif op == "&&":
                return left and right
            elif op == "!!":
                return not left
        # Allow string comparisons for == and !=
        if isinstance(left, str) or isinstance(right, str):
            if op not in ["==", "!="]:
                raise ValueError(f"Line {self.current_line}: Operator '{op}' not supported for strings")
            if op == "==":
                return str(left) == str(right)
            elif op == "!=":
                return str(left) != str(right)
        # Numeric comparisons
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise ValueError(f"Line {self.current_line}: Comparison operands must be numeric")
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

    def match_and_advance(self, expected_tokens, token_type):
        raw_token = self.tokens[self.current_index] if self.current_index < len(self.tokens) else None
        print(f"Debug: raw_token={raw_token}, index={self.current_index}")
        print(f"match_and_advance: index={self.current_index}, expected={expected_tokens}, found={self.peek_next_token()}, lexeme={self.lexemes[self.current_index] if self.current_index < len(self.lexemes) else 'None'}, line={self.current_line}")
        if self.peek_next_token() not in expected_tokens:
            raise ValueError(f"Line {self.current_line}: Expected {token_type}, found '{self.peek_next_token()}'")
        self.current_index += 1
        if self.current_index - 1 < len(self.lines):
            try:
                self.current_line = int(float(self.lines[self.current_index - 1]))
            except (ValueError, TypeError):
                pass
        print(f"match_and_advance: Advanced to index={self.current_index}, new_line={self.current_line}")

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
        look_ahead_index = self.current_index + 2
        token = self.tokens[look_ahead_index] if look_ahead_index < len(self.tokens) else None
        print(f"peek_two_tokens_ahead: index={self.current_index}, look_ahead_index={look_ahead_index}, token={token}, lexeme={self.lexemes[look_ahead_index] if look_ahead_index < len(self.lexemes) else 'None'}")
        return token

    def next_next_token(self):
        return self.tokens[self.current_index + 1] if self.current_index + 1 < len(self.tokens) else None

    def advance(self):
        self.current_index += 1
        self.current_line = self.lines[self.current_index] if self.current_index < len(self.lines) else self.current_line
        print(f"advance: New current_index={self.current_index}, token={self.peek_next_token()}")