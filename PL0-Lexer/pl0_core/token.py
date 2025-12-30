from enum import Enum, auto

class TokenType(Enum):
    # 运算符
    PLUS = auto()          # +
    MINUS = auto()         # -
    TIMES = auto()         # *
    SLASH = auto()         # /
    LPAREN = auto()        # (
    RPAREN = auto()        # )
    EQUAL = auto()         # =
    COMMA = auto()         # ,
    SEMICOLON = auto()     # ;
    ASSIGN = auto()        # :=
    NOT_EQUAL = auto()     # <>
    LESS = auto()          # <
    LESS_EQUAL = auto()    # <=
    GREATER = auto()       # >
    GREATER_EQUAL = auto() # >=
    ODD = auto()           # odd

    # 关键字
    BEGIN = auto()
    END = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    WHILE = auto()
    DO = auto()
    CALL = auto()
    CONST = auto()
    VAR = auto()
    PROCEDURE = auto()
    PROGRAM = auto()
    READ = auto()
    WRITE = auto()

    # 其他
    IDENTIFIER = auto()
    INTEGER = auto()
    EOF = auto()
    ILLEGAL = auto()

# 关键字映射表
KEYWORDS = {
    'begin': TokenType.BEGIN,
    'end': TokenType.END,
    'if': TokenType.IF,
    'then': TokenType.THEN,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'do': TokenType.DO,
    'call': TokenType.CALL,
    'const': TokenType.CONST,
    'var': TokenType.VAR,
    'procedure': TokenType.PROCEDURE,
    'program': TokenType.PROGRAM,
    'read': TokenType.READ,
    'write': TokenType.WRITE,
    'odd': TokenType.ODD
}

class Token:
    def __init__(self, type, value, line, column):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', {self.line}:{self.column})"