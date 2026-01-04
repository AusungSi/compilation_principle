from .token import Token, TokenType, KEYWORDS

class Lexer:
    """
    PL/0 语言的词法分析器。
    """
    def __init__(self, source_code: str):
        self.source = source_code
        self.pos = -1
        self.current_char = None
        self.line = 1
        self.column = 0
        self.errors = []

        self.single_char_map = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.TIMES,
            '/': TokenType.SLASH,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            ',': TokenType.COMMA,
            ';': TokenType.SEMICOLON,
            '=': TokenType.EQUAL, 
        }

        self._advance()

    def _record_error(self, msg: str, suggestion: str):
        """记录详细的错误信息与建议"""
        self.errors.append({
            'line': self.line,
            'column': self.column,
            'message': msg,
            'suggestion': suggestion
        })

    def _advance(self):
        """读取下一个字符"""
        if self.current_char == '\n':
            self.line += 1
            self.column = 0

        self.pos += 1
        if self.pos < len(self.source):
            self.current_char = self.source[self.pos]
            self.column += 1
        else:
            self.current_char = None

    def _peek(self) -> str | None:
        """查看下一个字符但不移动指针"""
        peek_pos = self.pos + 1
        if peek_pos < len(self.source):
            return self.source[peek_pos]
        return None
    
    # 添加到 Lexer 类中
    def peek_token_type(self):
        """
        预读下一个 Token 的类型，但不移动当前指针。
        用于解决 LL(1) 冲突，例如判断分号后是 procedure 还是 begin。
        """
        # 保存当前状态
        old_pos = self.pos
        old_char = self.current_char
        old_line = self.line
        old_column = self.column
        # 还要保存错误列表，防止预读时产生的错误被记录
        old_errors = list(self.errors)

        # 获取下一个
        token = self.get_next_token()

        # 恢复状态
        self.pos = old_pos
        self.current_char = old_char
        self.line = old_line
        self.column = old_column
        self.errors = old_errors

        return token.type

    def _skip_whitespace(self):
        """跳过空白字符"""
        while self.current_char is not None and self.current_char.isspace():
            self._advance()

    def _make_identifier(self) -> Token:
        """处理标识符和关键字"""
        start_col = self.column
        start_pos = self.pos
        
        while self.current_char is not None and self.current_char.isalnum():
            self._advance()
            
        ident_str = self.source[start_pos:self.pos]
        token_type = KEYWORDS.get(ident_str.lower(), TokenType.IDENTIFIER)
        return Token(token_type, ident_str, self.line, start_col)

    def _make_integer(self) -> Token:
        """处理无符号整数"""
        start_col = self.column
        start_pos = self.pos

        while self.current_char is not None and self.current_char.isdigit():
            self._advance()
        
        num_str = self.source[start_pos:self.pos]
        return Token(TokenType.INTEGER, num_str, self.line, start_col)

    def get_next_token(self) -> Token:
        """核心函数：获取下一个Token"""
        while self.current_char is not None:
            start_col = self.column

            # 1. 空白
            if self.current_char.isspace():
                self._skip_whitespace()
                continue

            # 2. 标识符/关键字
            if self.current_char.isalpha():
                return self._make_identifier()

            # 3. 数字
            if self.current_char.isdigit():
                return self._make_integer()

            # 4. 双字符符号 :=, <>, <=, >=
            if self.current_char == ':':
                if self._peek() == '=':
                    self._advance(); self._advance()
                    return Token(TokenType.ASSIGN, ":=", self.line, start_col)
                else:
                    self._record_error(
                        msg="发现单独的冒号 ':'",
                        suggestion="您是否是指赋值符号 ':=' ？PL/0 中不支持单独使用冒号。"
                    )
                    char_val = self.current_char
                    self._advance()
                    return Token(TokenType.ILLEGAL, char_val, self.line, start_col)
            
            if self.current_char == '<':
                if self._peek() == '>':
                    self._advance(); self._advance()
                    return Token(TokenType.NOT_EQUAL, "<>", self.line, start_col)
                elif self._peek() == '=':
                    self._advance(); self._advance()
                    return Token(TokenType.LESS_EQUAL, "<=", self.line, start_col)
                else:
                    self._advance()
                    return Token(TokenType.LESS, "<", self.line, start_col)

            if self.current_char == '>':
                if self._peek() == '=':
                    self._advance(); self._advance()
                    return Token(TokenType.GREATER_EQUAL, ">=", self.line, start_col)
                else:
                    self._advance()
                    return Token(TokenType.GREATER, ">", self.line, start_col)
            
            # 5. 单字符符号
            if self.current_char in self.single_char_map:
                token_type = self.single_char_map[self.current_char]
                char_val = self.current_char
                self._advance()
                return Token(token_type, char_val, self.line, start_col)

            # 6. 非法字符
            illegal_char = self.current_char
            self._advance()
            error_msg = f"非法字符 '{illegal_char}' 位于行 {self.line}, 列 {start_col}"
            self.errors.append(error_msg)
            return Token(TokenType.ILLEGAL, illegal_char, self.line, start_col)

        return Token(TokenType.EOF, "", self.line, self.column)