from .token import TokenType, Token

class ParserError(Exception):
    pass

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()
        self.errors = []        
        self.output_lines = []  
        self.indent_level = 0   

    def log(self, tag, content=""):
        indent = "  " * self.indent_level
        msg = f"{indent}<{tag}> {content}"
        self.output_lines.append(msg)

    def log_close(self, tag):
        indent = "  " * self.indent_level
        msg = f"{indent}</{tag}>"
        self.output_lines.append(msg)

    def error(self, msg):
        err_msg = f"[语法错误] Line {self.current_token.line}, Col {self.current_token.column}: {msg}"
        self.errors.append(err_msg)
        # 这里可以选择不抛出异常以尝试恢复，或者抛出由上层捕获
        print(f"\033[91m{err_msg}\033[0m")
        raise ParserError(err_msg)

    def eat(self, token_type):
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"期望 {token_type.name}，但遇到 {self.current_token.type.name} ('{self.current_token.value}')")

    def synchronize(self):
        """恐慌模式恢复：跳过token直到遇到同步点"""
        if self.current_token.type == TokenType.EOF:
            return

        self.current_token = self.lexer.get_next_token()

        safe_tokens = {
            TokenType.SEMICOLON, TokenType.END, TokenType.IF, 
            TokenType.WHILE, TokenType.READ, TokenType.WRITE,
            TokenType.BEGIN, TokenType.VAR, TokenType.CONST, 
            TokenType.PROCEDURE, TokenType.EOF
        }

        while self.current_token.type not in [TokenType.EOF]:
            if self.current_token.type == TokenType.SEMICOLON:
                # 遇到分号，消耗掉它并返回，准备解析下一条语句
                self.current_token = self.lexer.get_next_token()
                return
            if self.current_token.type in safe_tokens:
                return
            self.current_token = self.lexer.get_next_token()

    # ================= 核心修改区域 =================

    def parse(self):
        """<prog> → program <id>; <block>"""
        self.log("Program")
        self.indent_level += 1

        try:
            if self.current_token.type == TokenType.PROGRAM:
                self.eat(TokenType.PROGRAM)
                self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.SEMICOLON)
            else:
                self.error("程序必须以 'program' 开始")
        except ParserError:
            self.synchronize()

        # 解析 Block
        self.parse_block()
            
        # 允许程序以 '.' 结束 (标准 PL/0)
        try:
            if self.current_token.type != TokenType.EOF:
                self.error("程序结束后发现多余字符")
        except ParserError:
            pass 

        self.indent_level -= 1
        self.log_close("Program")

    def parse_block(self):
        """
        <block> → [<condecl>][<vardecl>][<proc>]<body>
        改进版：允许乱序解析以便发现更多错误，但会记录顺序错误。
        """
        self.log("Block")
        self.indent_level += 1

        # 用于记录已经解析过的部分，防止重复或检查顺序
        # 0: None, 1: Const, 2: Var, 3: Proc
        last_decl_stage = 0 

        decl_starters = [TokenType.CONST, TokenType.VAR, TokenType.PROCEDURE]

        while self.current_token.type in decl_starters:
            try:
                if self.current_token.type == TokenType.CONST:
                    if last_decl_stage > 1: # 如果在 Var(2) 或 Proc(3) 之后遇到
                        self.error("顺序错误：'const' 必须在 'var' 和 'procedure' 之前")
                    # 即使顺序错了，也继续解析，以便发现后续错误
                    self.parse_condecl()
                    last_decl_stage = max(last_decl_stage, 1) # 更新状态
                
                elif self.current_token.type == TokenType.VAR:
                    if last_decl_stage > 2: # 如果在 Proc(3) 之后
                        self.error("顺序错误：'var' 必须在 'procedure' 之前")
                    self.parse_vardecl()
                    last_decl_stage = max(last_decl_stage, 2)
                
                elif self.current_token.type == TokenType.PROCEDURE:
                    # procedure 是最后一个声明部分，后面可以跟多个 procedure
                    self.parse_proc() 
                    # parse_proc 内部已经处理了 {; proc} 的循环，
                    # 但为了配合外层 while 循环处理乱序情况，这里不需要额外逻辑
                    last_decl_stage = max(last_decl_stage, 3)

            except ParserError:
                self.synchronize()

        # 解析主体 Body
        try:
            self.parse_body()
        except ParserError:
            self.synchronize()

        self.indent_level -= 1
        self.log_close("Block")

    def parse_proc(self):
        """
        <proc> → procedure <id>（[<id>{,<id>}]）;<block>{;<proc>}
        改进：将 Header 和 Block 分开 try-except，确保 Header 错了也能继续解析 Block。
        """
        while True:
            self.log("Procedure")
            self.indent_level += 1
            
            # --- 第一阶段：解析过程头 (Header) ---
            try:
                self.eat(TokenType.PROCEDURE)
                self.eat(TokenType.IDENTIFIER)
                
                # 强制参数括号
                self.eat(TokenType.LPAREN)
                if self.current_token.type == TokenType.IDENTIFIER:
                    self.eat(TokenType.IDENTIFIER)
                    while self.current_token.type == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.RPAREN)
                
                self.eat(TokenType.SEMICOLON)

            except ParserError:
                # 如果头部出错（比如参数不对），恢复到 Block 开始的地方
                self.synchronize()
                # synchronize 可能会停在 BEGIN, VAR, CONST 等位置，正好给下面的 parse_block 用

            # --- 第二阶段：解析过程体 (Block) ---
            # 无论 Header 是否成功，都要尝试解析 Block，以免跳过整个函数体导致后续错位
            try:
                self.parse_block()
            except ParserError:
                self.synchronize()
            
            self.indent_level -= 1
            self.log_close("Procedure")

            # --- 第三阶段：检查是否有后续过程 ---
            # 结构：procedure ... ; block ; procedure ...
            # block 解析完后，后面应该紧跟一个分号
            
            if self.current_token.type == TokenType.SEMICOLON:
                # 预读：如果分号后面是 procedure，则继续循环
                if self.lexer.peek_token_type() == TokenType.PROCEDURE:
                    self.eat(TokenType.SEMICOLON)
                    continue 
                else:
                    # 分号后面不是 procedure，说明过程声明结束
                    # 注意：这个分号不属于 process 声明的一部分，而是分隔符
                    # 在 parse_block 的 while 循环中，如果不吃掉这个分号，
                    # 应该由 parse_block 的逻辑处理（通常 block 结束不带分号，分号是分隔符）
                    # 但在这里，<proc> 规则是 {; <proc>}，所以这个分号是循环的一部分
                    break 
            else:
                break

    def parse_condecl(self):
        """
        <condecl> → const <const>{,<const>}; 
        <const> → <id>:=<integer>
        修改：使用 := 而不是 =
        """
        self.log("ConstDecl")
        self.indent_level += 1
        self.eat(TokenType.CONST)
        while True:
            self.eat(TokenType.IDENTIFIER)
            
            # 修改点：语法要求使用 := (ASSIGN)
            if self.current_token.type == TokenType.EQUAL:
                self.error("常量声明请使用 ':=' 而不是 '='")
                self.eat(TokenType.EQUAL) # 容错处理
            else:
                self.eat(TokenType.ASSIGN)
            
            self.eat(TokenType.INTEGER)
            
            if self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
            else:
                break
        self.eat(TokenType.SEMICOLON)
        self.indent_level -= 1
        self.log_close("ConstDecl")

    def parse_statement(self):
        """
        修改 Call 语句，强制要求括号
        """
        self.log("Statement")
        self.indent_level += 1
        
        tt = self.current_token.type
        
        if tt == TokenType.IDENTIFIER:
            self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.ASSIGN)
            self.parse_exp()
            
        elif tt == TokenType.IF:
            self.eat(TokenType.IF)
            self.parse_lexp()
            self.eat(TokenType.THEN)
            self.parse_statement()
            if self.current_token.type == TokenType.ELSE:
                self.eat(TokenType.ELSE)
                self.parse_statement()
                
        elif tt == TokenType.WHILE:
            self.eat(TokenType.WHILE)
            self.parse_lexp()
            self.eat(TokenType.DO)
            self.parse_statement()
            
        elif tt == TokenType.CALL:
            # call <id>（[<exp>{,<exp>}]）
            self.eat(TokenType.CALL)
            self.eat(TokenType.IDENTIFIER)
            
            # 修改点：强制要求括号
            self.eat(TokenType.LPAREN)
            
            if self._is_exp_start():
                self.parse_exp()
                while self.current_token.type == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    self.parse_exp()
            
            self.eat(TokenType.RPAREN)
                
        elif tt == TokenType.READ:
            self.eat(TokenType.READ)
            self.eat(TokenType.LPAREN)
            self.eat(TokenType.IDENTIFIER)
            while self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.RPAREN)
            
        elif tt == TokenType.WRITE:
            self.eat(TokenType.WRITE)
            self.eat(TokenType.LPAREN)
            self.parse_exp()
            while self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                self.parse_exp()
            self.eat(TokenType.RPAREN)
            
        elif tt == TokenType.BEGIN:
            # Body 作为 Statement 的一部分 (嵌套块)
            self.indent_level -= 1 # 调整缩进，因为 parse_body 会加
            self.parse_body()
            self.indent_level += 1
        
        # 处理空语句（例如分号前的空隙），或者 END 前的空隙
        elif tt == TokenType.END or tt == TokenType.SEMICOLON:
            pass 
            
        else:
            self.error(f"非法的语句开头: {tt.name} ('{self.current_token.value}')")

        self.indent_level -= 1
        self.log_close("Statement")

    # ================= 其他辅助方法保持不变 =================

    def parse_vardecl(self):
        self.log("VarDecl")
        self.indent_level += 1
        self.eat(TokenType.VAR)
        while True:
            self.eat(TokenType.IDENTIFIER)
            if self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
            else:
                break
        self.eat(TokenType.SEMICOLON)
        self.indent_level -= 1
        self.log_close("VarDecl")

    def parse_body(self):
        self.log("Body")
        self.indent_level += 1
        self.eat(TokenType.BEGIN)
        self._safe_parse_statement()
        while self.current_token.type == TokenType.SEMICOLON:
            self.eat(TokenType.SEMICOLON)
            self._safe_parse_statement()
        self.eat(TokenType.END)
        self.indent_level -= 1
        self.log_close("Body")

    def _safe_parse_statement(self):
        try:
            self.parse_statement()
        except ParserError:
            self.synchronize()

    def parse_lexp(self):
        self.log("Condition")
        self.indent_level += 1
        if self.current_token.type == TokenType.ODD:
            self.eat(TokenType.ODD)
            self.parse_exp()
        else:
            self.parse_exp()
            if self.current_token.type in [
                TokenType.EQUAL, TokenType.NOT_EQUAL, 
                TokenType.LESS, TokenType.LESS_EQUAL, 
                TokenType.GREATER, TokenType.GREATER_EQUAL
            ]:
                self.eat(self.current_token.type)
                self.parse_exp()
            else:
                self.error("条件表达式缺少关系运算符")
        self.indent_level -= 1
        self.log_close("Condition")

    def parse_exp(self):
        self.log("Expression")
        self.indent_level += 1
        if self.current_token.type in [TokenType.PLUS, TokenType.MINUS]:
            self.eat(self.current_token.type)
        self.parse_term()
        while self.current_token.type in [TokenType.PLUS, TokenType.MINUS]:
            self.eat(self.current_token.type)
            self.parse_term()
        self.indent_level -= 1
        self.log_close("Expression")

    def parse_term(self):
        self.log("Term")
        self.indent_level += 1
        self.parse_factor()
        while self.current_token.type in [TokenType.TIMES, TokenType.SLASH]:
            self.eat(self.current_token.type)
            self.parse_factor()
        self.indent_level -= 1
        self.log_close("Term")

    def parse_factor(self):
        self.log("Factor")
        self.indent_level += 1
        tt = self.current_token.type
        if tt == TokenType.IDENTIFIER:
            self.eat(TokenType.IDENTIFIER)
        elif tt == TokenType.INTEGER:
            self.eat(TokenType.INTEGER)
        elif tt == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            self.parse_exp()
            self.eat(TokenType.RPAREN)
        else:
            self.error("Factor 语法错误: 期望 ID, Integer 或 (Exp)")
        self.indent_level -= 1
        self.log_close("Factor")

    def _is_exp_start(self):
        tt = self.current_token.type
        return tt in [TokenType.PLUS, TokenType.MINUS, TokenType.IDENTIFIER, TokenType.INTEGER, TokenType.LPAREN]