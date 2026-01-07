from .token import TokenType, Token
from .ast_nodes import *

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
        
        prog_name = "unknown"

        try:
            if self.current_token.type == TokenType.PROGRAM:
                self.eat(TokenType.PROGRAM)
                if self.current_token.type == TokenType.IDENTIFIER:
                    prog_name = self.current_token.value # [AST] 记录程序名
                self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.SEMICOLON)
            else:
                self.error("程序必须以 'program' 开始")
        except ParserError:
            self.synchronize()

        # [AST] 解析 Block 并获取返回的节点
        # 注意：这里调用的是修改后会返回 Block 节点的 parse_block
        block_node = self.parse_block()
            
        # 检查结束符
        try:
            if self.current_token.type != TokenType.EOF:
                # 你的代码里如果是 '.' 可以在这里处理
                # self.eat(TokenType.DOT) 
                pass
        except ParserError:
            pass 

        self.indent_level -= 1
        self.log_close("Program")
        
        # [AST] 返回根节点
        return Program(prog_name, block_node)

    def parse_block(self):
        """
        <block> → [<condecl>][<vardecl>][<proc>]<body>
        改进版：允许乱序解析以便发现更多错误，但会记录顺序错误。
        """
        self.log("Block")
        self.indent_level += 1
        
        # [AST] 初始化收集器
        all_consts = []
        all_vars = []
        all_procs = []
        
        decl_starters = [TokenType.CONST, TokenType.VAR, TokenType.PROCEDURE]
        
        # 保留你原有的乱序解析逻辑
        while self.current_token.type in decl_starters:
            try:
                if self.current_token.type == TokenType.CONST:
                    # [AST] extend 列表
                    all_consts.extend(self.parse_condecl())
                    
                elif self.current_token.type == TokenType.VAR:
                    # [AST] extend 列表
                    all_vars.extend(self.parse_vardecl())
                    
                elif self.current_token.type == TokenType.PROCEDURE:
                    # [AST] parse_proc 需要修改为返回 ProcedureDecl 列表
                    procs_list = self.parse_proc() 
                    all_procs.extend(procs_list)
                    
            except ParserError:
                self.synchronize()

        # 解析 Body
        body_node = NoOp()
        try:
            body_node = self.parse_body()
        except ParserError:
            self.synchronize()

        self.indent_level -= 1
        self.log_close("Block")
        
        # [AST] 返回完整的 Block 节点
        return Block(all_consts, all_vars, all_procs, body_node)

    def parse_proc(self):
        """
        <proc> → procedure <id>（[<id>{,<id>}]）;<block>{;<proc>}
        改进：将 Header 和 Block 分开 try-except，确保 Header 错了也能继续解析 Block。
        """
        procs = [] # [AST]
        
        while True:
            self.log("Procedure")
            self.indent_level += 1
            
            # 1. Header
            proc_name = None
            params = []
            try:
                self.eat(TokenType.PROCEDURE)
                proc_name = self.current_token.value
                self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.LPAREN)
                # ... 解析参数 ...
                if self.current_token.type == TokenType.IDENTIFIER:
                    params.append(self.current_token.value)
                    self.eat(TokenType.IDENTIFIER)
                    while self.current_token.type == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        params.append(self.current_token.value)
                        self.eat(TokenType.IDENTIFIER)
                self.eat(TokenType.RPAREN)
                self.eat(TokenType.SEMICOLON)
            except ParserError:
                self.synchronize()

            # 2. Block
            block_node = None
            try:
                block_node = self.parse_block() # 递归调用
            except ParserError:
                self.synchronize()

            self.indent_level -= 1
            self.log_close("Procedure")
            
            # [AST] 如果解析成功，创建节点并加入列表
            if proc_name and block_node:
                procs.append(ProcedureDecl(proc_name, params, block_node))

            # 3. 检查循环
            if self.current_token.type == TokenType.SEMICOLON:
                if self.lexer.peek_token_type() == TokenType.PROCEDURE:
                    self.eat(TokenType.SEMICOLON)
                    continue
                else:
                    # 这里的 break 很重要，不要吃掉分号，
                    # 除非你确定这个分号不属于外层 Block 的 Body 分隔符
                    # 按照 PL/0 惯例，procedure 结束后没有分号，分号是语句分隔符
                    # 但你的文法是 {; <proc>}，所以这里分号属于 proc 循环
                    break
            else:
                break
                
        return procs

    def parse_condecl(self):
        self.log("ConstDecl")
        self.indent_level += 1
        decls = []
        
        self.eat(TokenType.CONST)
        while True:
            name_token = self.current_token
            self.eat(TokenType.IDENTIFIER)
            # ... 省略中间你的检查逻辑 ...
            if self.current_token.type == TokenType.ASSIGN:
                self.eat(TokenType.ASSIGN)
            else:
                self.eat(TokenType.EQUAL) # 你的容错逻辑
                
            val_token = self.current_token
            self.eat(TokenType.INTEGER)
            
            decls.append(ConstDecl(name_token.value, val_token.value)) # [AST]
            
            if self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
            else:
                break
        self.eat(TokenType.SEMICOLON)
        
        self.indent_level -= 1
        self.log_close("ConstDecl")
        return decls

    def parse_statement(self):
        """
        修改 Call 语句，强制要求括号
        """
        self.log("Statement")
        self.indent_level += 1
        
        tt = self.current_token.type
        node = NoOp()
        
        if tt == TokenType.IDENTIFIER:
            var_token = self.current_token
            self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.ASSIGN)
            expr = self.parse_exp()
            # [AST] 创建赋值节点
            node = Assign(Var(var_token), expr)
            
        elif tt == TokenType.IF:
            self.eat(TokenType.IF)
            condition = self.parse_lexp() # 注意：parse_lexp 也需要修改为返回 AST
            self.eat(TokenType.THEN)
            then_stmt = self.parse_statement()
            else_stmt = None
            if self.current_token.type == TokenType.ELSE:
                self.eat(TokenType.ELSE)
                else_stmt = self.parse_statement()
            # [AST] 创建 If 节点
            node = If(condition, then_stmt, else_stmt)
                
        elif tt == TokenType.WHILE:
            self.eat(TokenType.WHILE)
            condition = self.parse_lexp()
            self.eat(TokenType.DO)
            body = self.parse_statement()
            # [AST] 创建 While 节点
            node = While(condition, body)
            
        elif tt == TokenType.CALL:
            call_token = self.current_token
            self.eat(TokenType.CALL)
            proc_name = self.current_token.value
            self.eat(TokenType.IDENTIFIER)
            # 强制括号
            self.eat(TokenType.LPAREN)
            args = []
            if self._is_exp_start():
                args.append(self.parse_exp())
                while self.current_token.type == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    args.append(self.parse_exp())
            self.eat(TokenType.RPAREN)
            # [AST] 创建 Call 节点
            node = Call(proc_name, args, token=call_token)
                
        elif tt == TokenType.READ:
            self.eat(TokenType.READ)
            self.eat(TokenType.LPAREN)
            vars = []
            if self.current_token.type == TokenType.IDENTIFIER:
                vars.append(Var(self.current_token)) # [AST]
                self.eat(TokenType.IDENTIFIER)
                while self.current_token.type == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    vars.append(Var(self.current_token)) # [AST]
                    self.eat(TokenType.IDENTIFIER)
            self.eat(TokenType.RPAREN)
            node = Read(vars)
            
        elif tt == TokenType.WRITE:
            self.eat(TokenType.WRITE)
            self.eat(TokenType.LPAREN)
            exprs = []
            exprs.append(self.parse_exp())
            while self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                exprs.append(self.parse_exp())
            self.eat(TokenType.RPAREN)
            node = Write(exprs)
            
        elif tt == TokenType.BEGIN:
            self.indent_level -= 1 
            node = self.parse_body() # parse_body 会返回 Compound
            self.indent_level += 1
        
        # 处理空语句（例如分号前的空隙），或者 END 前的空隙
        elif tt == TokenType.END or tt == TokenType.SEMICOLON:
            pass 
            
        else:
            self.error(f"非法的语句开头: {tt.name} ('{self.current_token.value}')")

        self.indent_level -= 1
        self.log_close("Statement")
        return node

    # ================= 其他辅助方法保持不变 =================

    def parse_vardecl(self):
        self.log("VarDecl")
        self.indent_level += 1
        
        decls = [] # [AST]
        
        self.eat(TokenType.VAR)
        while True:
            token = self.current_token
            self.eat(TokenType.IDENTIFIER)
            decls.append(VarDecl(token.value)) # [AST] 添加到列表
            
            if self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
            else:
                break
        self.eat(TokenType.SEMICOLON)
        
        self.indent_level -= 1
        self.log_close("VarDecl")
        return decls

    def parse_body(self):
        self.log("Body")
        self.indent_level += 1
        
        self.eat(TokenType.BEGIN)
        statements = [] # [AST] 语句列表
        
        # 使用你原有的 _safe_parse_statement 封装，但需要它返回值
        stmt = self._safe_parse_statement()
        if stmt: statements.append(stmt)
        
        while self.current_token.type == TokenType.SEMICOLON:
            self.eat(TokenType.SEMICOLON)
            stmt = self._safe_parse_statement()
            if stmt: statements.append(stmt)
            
        self.eat(TokenType.END)
        
        self.indent_level -= 1
        self.log_close("Body")
        
        # [AST] 创建 Compound 节点
        compound = Compound()
        compound.children = statements
        return compound

    def _safe_parse_statement(self):
        try:
            return self.parse_statement()
        except ParserError:
            self.synchronize()
            return NoOp()

    def parse_lexp(self):
        self.log("Condition")
        self.indent_level += 1
        
        node = NoOp() # 默认值，防止分支未覆盖

        # 情况 1: odd <exp>
        if self.current_token.type == TokenType.ODD:
            op = self.current_token
            self.eat(TokenType.ODD)
            expr = self.parse_exp() # [AST] 获取表达式子树
            node = UnaryOp(op, expr) # [AST] 创建一元运算节点

        # 情况 2: <exp> <lop> <exp>
        else:
            left = self.parse_exp() # [AST] 获取左侧表达式
            
            # 检查关系运算符
            if self.current_token.type in [
                TokenType.EQUAL, TokenType.NOT_EQUAL, 
                TokenType.LESS, TokenType.LESS_EQUAL, 
                TokenType.GREATER, TokenType.GREATER_EQUAL
            ]:
                op = self.current_token
                self.eat(self.current_token.type)
                right = self.parse_exp() # [AST] 获取右侧表达式
                node = BinOp(left, op, right) # [AST] 创建二元运算节点
            else:
                self.error("条件表达式缺少关系运算符")
                # 出错时，为了让树不断裂，可以临时把左值作为结果，或者返回 NoOp
                node = left 

        self.indent_level -= 1
        self.log_close("Condition")
        return node

    def parse_exp(self):
        self.log("Expression")
        self.indent_level += 1
        
        # 【关键修正】处理一元运算符或直接解析 term，都必须赋值给 node
        if self.current_token.type in [TokenType.PLUS, TokenType.MINUS]:
            op = self.current_token
            self.eat(op.type)
            term = self.parse_term()
            node = UnaryOp(op=op, expr=term)
        else:
            node = self.parse_term() # <--- 确保这里有 node = 

        while self.current_token.type in [TokenType.PLUS, TokenType.MINUS]:
            op = self.current_token
            self.eat(op.type)
            right = self.parse_term()
            node = BinOp(left=node, op=op, right=right)

        self.indent_level -= 1
        self.log_close("Expression")
        return node

    def parse_term(self):
        self.log("Term")
        self.indent_level += 1

        node = self.parse_factor()

        while self.current_token.type in [TokenType.TIMES, TokenType.SLASH]:
            op = self.current_token
            self.eat(self.current_token.type)
            right = self.parse_factor()
            node = BinOp(left=node, op=op, right=right)

        self.indent_level -= 1
        self.log_close("Term")
        return node

    def parse_factor(self):
        self.log("Factor")
        self.indent_level += 1
        
        # 【关键修正】初始化 node，防止进入 else 分支后 node 未定义
        node = NoOp() 
        
        tt = self.current_token.type
        
        if tt == TokenType.IDENTIFIER:
            token = self.current_token
            self.eat(TokenType.IDENTIFIER)
            node = Var(token)
            
        elif tt == TokenType.INTEGER:
            token = self.current_token
            self.eat(TokenType.INTEGER)
            node = Num(token)
            
        elif tt == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.parse_exp()
            self.eat(TokenType.RPAREN)
            
        else:
            self.error("Factor 语法错误")
            # 即使报错，node 也有初始值 NoOp，不会导致 Python 崩溃
            
        self.indent_level -= 1
        self.log_close("Factor")
        return node

    def _is_exp_start(self):
        tt = self.current_token.type
        return tt in [TokenType.PLUS, TokenType.MINUS, TokenType.IDENTIFIER, TokenType.INTEGER, TokenType.LPAREN]