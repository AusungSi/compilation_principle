class AST:
    """所有 AST 节点的基类"""

    def __init__(self, token=None):
            self.token = token
            self.lineno = token.line if token else 0
            self.column = token.column if token else 0

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

class BinOp(AST):
    """
    二元运算节点
    对应文法：<exp> <lop> <exp> 或 <term> <aop> <term>
    例如：a + b, a > 10
    """
    def __init__(self, left, op, right):
        super().__init__(op)
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"BinOp({self.left}, {self.op.type.name}, {self.right})"

class UnaryOp(AST):
    """
    一元运算节点
    对应文法：odd <exp> 或 -<term>
    """
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def __repr__(self):
        return f"UnaryOp({self.op.type.name}, {self.expr})"

class Num(AST):
    """
    数字常量节点
    对应文法：<integer>
    """
    def __init__(self, token):
        super().__init__(token)
        self.token = token
        self.value = int(token.value)

    def __repr__(self):
        return f"Num({self.value})"

class Var(AST):
    """
    变量引用节点（出现在表达式中）
    对应文法：<factor> -> <id>
    """
    def __init__(self, token):
        self.token = token
        self.name = token.value

    def __repr__(self):
        return f"Var({self.name})"

class Assign(AST):
    """
    赋值语句
    对应文法：<id> := <exp>
    """
    def __init__(self, left_var, right_expr):
        self.left = left_var
        self.right = right_expr

    def __repr__(self):
        return f"Assign({self.left.name} := {self.right})"

class Compound(AST):
    """
    复合语句（代码块）
    对应文法：begin <statement> {; <statement>} end
    """
    def __init__(self):
        self.children = []

    def __repr__(self):
        return f"Compound(len={len(self.children)})"

class If(AST):
    """
    条件语句
    对应文法：if <lexp> then <statement> [else <statement>]
    """
    def __init__(self, condition, then_stmt, else_stmt=None):
        self.condition = condition
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

    def __repr__(self):
        if self.else_stmt:
            return f"If({self.condition} ? {self.then_stmt} : {self.else_stmt})"
        return f"If({self.condition} ? {self.then_stmt})"

class While(AST):
    """
    循环语句
    对应文法：while <lexp> do <statement>
    """
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"While({self.condition} do {self.body})"

class Call(AST):
    """
    过程调用
    对应文法：call <id>([<exp>{,<exp>}])
    """
    def __init__(self, proc_name, args, token=None):
        super().__init__(token)
        self.proc_name = proc_name 
        self.args = args 

    def __repr__(self):
        return f"Call({self.proc_name}, args={self.args})"

class Read(AST):
    """
    读语句
    对应文法：read(<id>{,<id>})
    """
    def __init__(self, vars):
        self.vars = vars 

    def __repr__(self):
        return f"Read({[v.name for v in self.vars]})"

class Write(AST):
    """
    写语句
    对应文法：write(<exp>{,<exp>})
    """
    def __init__(self, exprs):
        self.exprs = exprs 

    def __repr__(self):
        return f"Write({self.exprs})"

class NoOp(AST):
    """空操作（用于处理多余的分号或空语句）"""
    def __repr__(self):
        return "NoOp"

class ConstDecl(AST):
    """常量声明"""
    def __init__(self, name, value):
        self.name = name 
        self.value = value

    def __repr__(self):
        return f"Const({self.name}={self.value})"

class VarDecl(AST):
    """变量声明"""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"VarDecl({self.name})"

class ProcedureDecl(AST):
    """
    过程声明
    对应文法：procedure <id>([params]); <block>
    """
    def __init__(self, name, params, block):
        self.name = name 
        self.params = params
        self.block = block 

    def __repr__(self):
        return f"Proc({self.name}, params={self.params})"

class Block(AST):
    """
    块节点
    对应文法：[<condecl>][<vardecl>][<proc>]<body>
    """
    def __init__(self, consts, vars, procs, body):
        self.consts = consts
        self.vars = vars
        self.procs = procs
        self.body = body

    def __repr__(self):
        return f"Block(C={len(self.consts)}, V={len(self.vars)}, P={len(self.procs)})"

class Program(AST):
    """
    根节点
    对应文法：program <id>; <block>
    """
    def __init__(self, name, block):
        self.name = name
        self.block = block

    def __repr__(self):
        return f"Program({self.name}, {self.block})"