from .token import TokenType
from .ast_nodes import *
from .instructions import Instruction, OpCode, OprCode
from .symbol_table import SymbolTable, SymbolType

class CodeGenerator:
    def __init__(self):
        self.instructions = [] # 存储生成的 P-Code
        self.symbol_table = SymbolTable()
        self.last_error = None

    def generate(self, node):
        """主入口"""
        self.instructions = []
        # self.symbol_table = SymbolTable()
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
        # 返回当前指令的索引，用于后续回填地址
        return len(self.instructions) - 1

    def visit(self, node):
        """分发器：根据节点类型调用对应的 visit_ 方法"""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise Exception(f"没有为节点 {type(node).__name__} 定义代码生成逻辑")

    # ================= 结构访问 =================

    def visit_Program(self, node):
        # Program 本身也是一个 Block，但我们通常在外层处理
        # 1. 进入主程序作用域 (从 Level -1 -> Level 0)
        self.symbol_table.enter_scope()
        
        # 2. 生成主程序代码
        self.visit(node.block)
        
        # 3. 退出作用域 (保持堆栈平衡，虽然程序结束了)
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
        
        # 1. 生成跳转指令，跳过过程声明部分
        # 此时不知道 Body 从哪开始，先填 0，记录索引
        jmp_idx = self.emit(OpCode.JMP, 0, 0)

        # 2. 定义常量和变量到符号表
        # 注意：要在 enter_scope 之前还是之后？
        # 主程序的 Block 已经在最外层 Scope 了。
        # 子过程的 Block 会被 visit_ProcedureDecl 包裹并在那里 enter_scope。
        # 为了统一，我们在 Block 内部只负责定义，不负责 Scope 管理（由调用者管理 Scope）
        # 但这就要求 Program 进来前要先 enter_scope? 
        # 为了简化，我们假设 Program 进来时已经是 Global Scope。
        # 而 Procedure 进来时已经由 visit_ProcedureDecl 切换了 Scope。
        
        for const in node.consts:
            self.symbol_table.define_const(const.name, const.value)
        
        for var in node.vars:
            self.symbol_table.define_var(var.name)

        # 3. 处理嵌套过程 (Procedure Decls)
        for proc in node.procs:
            # 定义过程符号 (记录过程入口地址，目前还不知道，稍后填)
            proc_sym = self.symbol_table.define_proc(proc.name)
            
            # 记录当前指令地址作为该过程的入口
            proc_sym.addr = len(self.instructions)
            
            self.visit(proc) # 递归生成过程代码

        # 4. 回填 JMP 指令，使其跳到这里 (Body 开始的地方)
        current_addr = len(self.instructions)
        self.instructions[jmp_idx].a = current_addr

        # 5. 开辟数据空间 (INT)
        # 大小 = 当前层分配的变量数 (SymbolTable 会自动维护)
        frame_size = self.symbol_table.get_current_frame_size()
        self.emit(OpCode.INT, 0, frame_size)

        # 6. 生成主体语句代码
        self.visit(node.body)

        # 7. 返回 (OPR 0 0)
        self.emit(OpCode.OPR, 0, OprCode.RET)

    def visit_ProcedureDecl(self, node):
        # 进入新作用域
        self.symbol_table.enter_scope()

        # 定义参数 (参数也是变量，位置在栈底)
        # 注意：PL/0 标准实现中，参数通常由调用者处理或作为局部变量
        # 这里我们简化处理：将参数直接定义为当前层的局部变量

        # self.symbol_table.addr_counters[-1] = 3

        for param in node.params:
            self.symbol_table.define_var(param)

        # 生成 Block 代码
        self.visit(node.block)

        # 退出作用域
        self.symbol_table.exit_scope()

    # ================= 语句访问 =================

    def visit_Compound(self, node):
        for stmt in node.children:
            self.visit(stmt)

    def visit_Assign(self, node):
        # 1. 计算右侧表达式，结果留栈顶
        self.visit(node.right)
        
        # 2. 查找左侧变量
        var_name = node.left.name
        sym, level_diff = self.symbol_table.lookup(var_name)
        
        if not sym:
            raise Exception(f"未定义的变量: {var_name}")
        if sym.type != SymbolType.VAR:
            raise Exception(f"不能赋值给非变量: {var_name}")

        # 3. 生成 STO 指令
        self.emit(OpCode.STO, level_diff, sym.addr)

    def visit_If(self, node):
        # 1. 计算条件
        self.visit(node.condition)
        
        # 2. 生成 JPC (条件不满足则跳转)
        # 目标地址未知，先占位
        jpc_idx = self.emit(OpCode.JPC, 0, 0)
        
        # 3. 生成 Then 部分
        self.visit(node.then_stmt)
        
        # 4. 处理 Else
        if node.else_stmt:
            # Then 执行完需要跳过 Else 部分
            jmp_idx = self.emit(OpCode.JMP, 0, 0)
            
            # 回填 JPC：如果条件假，跳到 Else 开始处 (即当前位置)
            self.instructions[jpc_idx].a = len(self.instructions)
            
            # 生成 Else 部分
            self.visit(node.else_stmt)
            
            # 回填 JMP：Then 执行完跳到 Else 后面
            self.instructions[jmp_idx].a = len(self.instructions)
        else:
            # 没有 Else，JPC 直接跳到 Then 后面
            self.instructions[jpc_idx].a = len(self.instructions)

    def visit_While(self, node):
        # 1. 记录循环开始地址
        start_addr = len(self.instructions)
        
        # 2. 计算条件
        self.visit(node.condition)
        
        # 3. JPC 跳出循环 (占位)
        jpc_idx = self.emit(OpCode.JPC, 0, 0)
        
        # 4. 循环体
        self.visit(node.body)
        
        # 5. JMP 跳回开始
        self.emit(OpCode.JMP, 0, start_addr)
        
        # 6. 回填 JPC (跳出位置)
        self.instructions[jpc_idx].a = len(self.instructions)

    def visit_Call(self, node):
        proc_name = node.proc_name
        sym, level_diff = self.symbol_table.lookup(proc_name)
        
        if not sym or sym.type != SymbolType.PROC:
            raise Exception(f"未定义的过程: {proc_name}")
            
        # --- [关键修改] 参数传递生成逻辑 ---
        # 假设参数在被调用过程中的地址是从 3 开始分配的 (0,1,2 被 SL,DL,RA 占用)
        start_offset = 3 
        
        for i, arg in enumerate(node.args):
            # 1. 计算实参表达式 (结果在栈顶)
            self.visit(arg)
            
            # 2. 生成 STO -1 A 指令
            # -1 表示特殊的“传递给下一层”的操作
            # 3 + i 是第 i 个参数在目标栈帧中的地址
            self.emit(OpCode.STO, -1, start_offset + i)
            
        # 3. 生成 CAL 指令
        self.emit(OpCode.CAL, level_diff, sym.addr)

    def visit_Read(self, node):
        """
        修改后的 Read 生成逻辑，适配 PPT 格式：
        1. RED 0 0  -> 读取数据到栈顶
        2. STO L A  -> 将栈顶数据存入变量
        """
        for var in node.vars:
            # 1. 生成 RED 指令 (只读入到栈顶)
            # PPT 中 RED 的 L 和 A 都是 0
            self.emit(OpCode.RED, 0, 0)

            # 2. 查找变量地址
            sym, level_diff = self.symbol_table.lookup(var.name)
            if not sym: raise Exception(f"未定义的变量: {var.name}")

            # 3. 生成 STO 指令 (将栈顶读到的数存入变量)
            self.emit(OpCode.STO, level_diff, sym.addr)

    def visit_Write(self, node):
        for expr in node.exprs:
            self.visit(expr)
            self.emit(OpCode.WRT, 0, 0)
        
        # 这里的逻辑是每个 write 后都换行，还是 explicit newline?
        # PPT 里有 OPR 0 13 是换行
        self.emit(OpCode.OPR, 0, OprCode.LINE) 

    # ================= 表达式访问 =================

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