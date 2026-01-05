from .token import TokenType
from .ast_nodes import *
from .instructions import Instruction, OpCode, OprCode
from .symbol_table import SymbolTable, SymbolType

class CodeGenerator:
    def __init__(self):
        self.instructions = []
        self.symbol_table = SymbolTable()
        self.last_error = None

    def generate(self, node):
        """主入口"""
        self.instructions = []
        try:
            self.visit(node)
            return self.instructions
        except Exception as e:
            self.last_error = str(e)
            raise e

    def emit(self, f, l, a):
        """生成一条指令并添加到列表"""
        instr = Instruction(f, l, a)
        self.instructions.append(instr)
        return len(self.instructions) - 1

    def visit(self, node):
        """分发器：根据节点类型调用对应的 visit_ 方法"""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"没有为节点 {type(node).__name__} 定义代码生成逻辑")

    def visit_Program(self, node):
        self.symbol_table.enter_scope()
        
        self.visit(node.block)
        
        self.symbol_table.exit_scope()

    def visit_Block(self, node):
        """
        Block 的生成逻辑：
        1. JMP 0, 0   -> 跳过声明部分 (稍后回填)
        2. 定义常量、变量
        3. 生成过程代码 (递归)
        4. 回填 JMP 地址 -> 指向 Body 开始
        5. INT 0, size -> 开辟栈空间
        6. 生成 Body 代码
        7. OPR 0, 0    -> 返回
        """
        
        jmp_idx = self.emit(OpCode.JMP, 0, 0)
        
        for const in node.consts:
            self.symbol_table.define_const(const.name, const.value)
        
        for var in node.vars:
            self.symbol_table.define_var(var.name)

        for proc in node.procs:
            proc_sym = self.symbol_table.define_proc(proc.name)
            
            proc_sym.addr = len(self.instructions)
            
            self.visit(proc)

        current_addr = len(self.instructions)
        self.instructions[jmp_idx].a = current_addr

        frame_size = self.symbol_table.get_current_frame_size()
        self.emit(OpCode.INT, 0, frame_size)

        self.visit(node.body)

        self.emit(OpCode.OPR, 0, OprCode.RET)

    def visit_ProcedureDecl(self, node):
        # 开一个新的符号表
        self.symbol_table.enter_scope()

        # 传入函数参数
        for param in node.params:
            self.symbol_table.define_var(param)

        self.visit(node.block)

        self.symbol_table.exit_scope()


    def visit_Compound(self, node):
        for stmt in node.children:
            self.visit(stmt)

    # 赋值
    def visit_Assign(self, node):
        self.visit(node.right)
        
        var_name = node.left.name
        sym, level_diff = self.symbol_table.lookup(var_name)
        
        if not sym:
            raise Exception(f"未定义的变量: {var_name}")
        if sym.type != SymbolType.VAR:
            raise Exception(f"不能赋值给非变量: {var_name}")

        self.emit(OpCode.STO, level_diff, sym.addr)

    def visit_If(self, node):
        self.visit(node.condition)
        
        jpc_idx = self.emit(OpCode.JPC, 0, 0)
        
        self.visit(node.then_stmt)
        
        if node.else_stmt:
            jmp_idx = self.emit(OpCode.JMP, 0, 0)
            
            self.instructions[jpc_idx].a = len(self.instructions)
            
            self.visit(node.else_stmt)
            
            self.instructions[jmp_idx].a = len(self.instructions)
        else:
            self.instructions[jpc_idx].a = len(self.instructions)

    def visit_While(self, node):
        start_addr = len(self.instructions)
        
        # 计算条件
        self.visit(node.condition)
        
        # 退出
        jpc_idx = self.emit(OpCode.JPC, 0, 0)
        
        self.visit(node.body)
        
        # 跳回起点
        self.emit(OpCode.JMP, 0, start_addr)
        
        self.instructions[jpc_idx].a = len(self.instructions)

    def visit_Call(self, node):
        proc_name = node.proc_name
        sym, level_diff = self.symbol_table.lookup(proc_name)
        
        if not sym or sym.type != SymbolType.PROC:
            raise Exception(f"未定义的过程: {proc_name}")
            
        start_offset = 3 
        
        # 写实参
        for i, arg in enumerate(node.args):
            self.visit(arg)
            
            self.emit(OpCode.STO, -1, start_offset + i)

        # 跳转执行指令    
        self.emit(OpCode.CAL, level_diff, sym.addr)

    def visit_Read(self, node):
        for var in node.vars:
            sym, level_diff = self.symbol_table.lookup(var.name)
            
            if not sym: 
                raise Exception(f"未定义的变量: {var.name}")
            if sym.type != SymbolType.VAR:
                raise Exception(f"Read 只能读取变量: {var.name}")

            self.emit(OpCode.RED, level_diff, sym.addr)

    def visit_Write(self, node):
        for expr in node.exprs:
            self.visit(expr)
            self.emit(OpCode.WRT, 0, 0)
        
        self.emit(OpCode.OPR, 0, OprCode.LINE) 


    def visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        
        op_type = node.op.type
        opr_code = 0
        
        if op_type == TokenType.PLUS: opr_code = OprCode.ADD
        elif op_type == TokenType.MINUS: opr_code = OprCode.SUB
        elif op_type == TokenType.TIMES: opr_code = OprCode.MUL
        elif op_type == TokenType.SLASH: opr_code = OprCode.DIV
        elif op_type == TokenType.EQUAL: opr_code = OprCode.EQL
        elif op_type == TokenType.NOT_EQUAL: opr_code = OprCode.NEQ
        elif op_type == TokenType.LESS: opr_code = OprCode.LSS
        elif op_type == TokenType.LESS_EQUAL: opr_code = OprCode.LEQ
        elif op_type == TokenType.GREATER: opr_code = OprCode.GTR
        elif op_type == TokenType.GREATER_EQUAL: opr_code = OprCode.GEQ
        else:
            raise Exception(f"未知的二元运算符: {op_type}")
            
        self.emit(OpCode.OPR, 0, opr_code)

    def visit_UnaryOp(self, node):
        self.visit(node.expr)
        
        if node.op.type == TokenType.ODD:
            self.emit(OpCode.OPR, 0, OprCode.ODD)
        elif node.op.type == TokenType.MINUS:
            self.emit(OpCode.OPR, 0, OprCode.NEG)

    def visit_Num(self, node):
        self.emit(OpCode.LIT, 0, node.value)

    def visit_Var(self, node):
        sym, level_diff = self.symbol_table.lookup(node.name)
        
        if not sym:
            raise Exception(f"未定义的标识符: {node.name}")
            
        if sym.type == SymbolType.CONST:
            self.emit(OpCode.LIT, 0, sym.value)
        elif sym.type == SymbolType.VAR:
            self.emit(OpCode.LOD, level_diff, sym.addr)
        else:
            raise Exception(f"不能在表达式中使用过程名: {node.name}")