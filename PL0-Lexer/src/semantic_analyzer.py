from .ast_nodes import *
from .symbol_table import SymbolTable, SymbolType, levenshtein_distance
from .token import TokenType

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors = [] # [核心] 错误收集列表

    def _suggest_correction(self, invalid_name):
        all_syms = self.symbol_table.get_all_symbols()
        best_match = None
        min_dist = float('inf')
        
        for sym in all_syms:
            dist = levenshtein_distance(invalid_name, sym.name)
            # 只有当相似度足够高（距离小于3且小于名字长度的一半）才建议
            if dist < 3 and dist < len(invalid_name):
                if dist < min_dist:
                    min_dist = dist
                    best_match = sym.name
        
        if best_match:
            return f". 您是不是想输入 '{best_match}'?"
        return ""

    def analyze(self, node):
        """主入口"""
        self.errors = []
        self.symbol_table = SymbolTable() # 重置符号表
        self.visit(node)
        return self.errors # 返回错误列表给主程序判断

    def log_error(self, msg, node=None):
        """
        记录错误，尽量尝试获取行号
        """
        pos_info = ""
        # 尝试从 AST 节点中提取 token 信息来定位行号
        if hasattr(node, 'token') and node.token:
            pos_info = f"[Line {node.token.line}, Col {node.token.column}] "
        elif hasattr(node, 'op') and node.op: # BinOp, UnaryOp
            pos_info = f"[Line {node.op.line}, Col {node.op.column}] "
        
        self.errors.append(f"{pos_info}语义错误: {msg}")

    def visit(self, node):
        """标准访问者分发模式"""
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        # 默认递归访问所有子节点（如果 AST 结构比较复杂，这里可能需要根据节点类型手动处理）
        pass

    # ================= 结构访问 (作用域管理) =================

    def visit_Program(self, node):
        self.symbol_table.enter_scope()
        self.visit(node.block)
        self.symbol_table.exit_scope()

    def visit_Block(self, node):
        # 1. 定义常量
        for const in node.consts:
            try:
                self.symbol_table.define_const(const.name, const.value)
            except Exception as e:
                # 捕获 SymbolTable 抛出的重复定义异常，转化为语义错误
                self.log_error(str(e), const)

        # 2. 定义变量
        for var in node.vars:
            try:
                self.symbol_table.define_var(var.name)
            except Exception as e:
                self.log_error(str(e), var)

        # 3. 定义过程 (先定义，后递归，支持递归调用)
        for proc in node.procs:
            try:
                # [核心] 这里记录了参数个数 len(proc.params)
                self.symbol_table.define_proc(proc.name, param_count=len(proc.params))
            except Exception as e:
                self.log_error(str(e), proc)

        # 4. 深入过程内部
        for proc in node.procs:
            self.visit(proc)

        # 5. 检查 Body
        self.visit(node.body)

        unused_vars = self.symbol_table.get_unused_variables()
        for sym in unused_vars:
            # 这里我们作为 Warning 输出，不加入 errors 列表导致编译失败
            # 或者你可以加到一个 self.warnings 列表里
            print(f"\033[93m[Warning] 变量 '{sym.name}' 已定义但未使用\033[0m")

    def visit_ProcedureDecl(self, node):
        self.symbol_table.enter_scope()
        
        # 定义参数为局部变量
        for param in node.params:
            try:
                self.symbol_table.define_var(param)
            except Exception as e:
                self.log_error(f"参数名重复: {str(e)}", node)

        self.visit(node.block)
        self.symbol_table.exit_scope()
    
    # ================= 语句检查 =================

    def visit_Compound(self, node):
        for stmt in node.children:
            self.visit(stmt)

    def visit_Assign(self, node):
        # 1. 检查右值表达式
        self.visit(node.right)

        # 2. 检查左值变量
        var_name = node.left.name
        sym, _ = self.symbol_table.lookup(var_name)

        if not sym:
            suggestion = self._suggest_correction(var_name)
            self.log_error(f"使用了未定义的变量 '{var_name}'{suggestion}", node.left)
        else:
            # [核心优化] 检查是否试图赋值给常量或过程
            if sym.type == SymbolType.CONST:
                self.log_error(f"不能给常量 '{var_name}' 赋值", node.left)
            elif sym.type == SymbolType.PROC:
                self.log_error(f"不能给过程名 '{var_name}' 赋值", node.left)

    def visit_Call(self, node):
        # 1. 检查过程名是否存在
        proc_name = node.proc_name
        sym, _ = self.symbol_table.lookup(proc_name)

        if not sym:
            self.log_error(f"调用了未定义的过程 '{proc_name}'", node)
            return # 无法继续检查参数

        if sym.type != SymbolType.PROC:
            self.log_error(f"'{proc_name}' 不是一个过程，无法调用", node)
            return

        # 2. [核心优化] 检查参数个数匹配
        expected_count = sym.param_count
        actual_count = len(node.args)

        if expected_count != actual_count:
            self.log_error(
                f"过程 '{proc_name}' 需要 {expected_count} 个参数，但提供了 {actual_count} 个", 
                node
            )

        # 3. 递归检查实参表达式
        for arg in node.args:
            self.visit(arg)

    def visit_If(self, node):
        self.visit(node.condition)
        self.visit(node.then_stmt)
        if node.else_stmt:
            self.visit(node.else_stmt)

    def visit_While(self, node):
        self.visit(node.condition)
        self.visit(node.body)
    
    def visit_Read(self, node):
        for var in node.vars:
            # 检查 read 的变量是否存在且为 VAR 类型
            sym, _ = self.symbol_table.lookup(var.name)
            if not sym:
                self.log_error(f"Read 语句中变量 '{var.name}' 未定义", var)
            elif sym.type != SymbolType.VAR:
                self.log_error(f"Read 只能读取变量，不能读取 '{var.name}' ({sym.type})", var)

    def visit_Write(self, node):
        for expr in node.exprs:
            self.visit(expr)

    # ================= 表达式检查 =================

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        
        # 除零检查
        if node.op.type == TokenType.SLASH: # 除法
            is_zero = False
            
            # 1. 显式除零： 10 / 0
            if isinstance(node.right, Num) and node.right.value == 0:
                is_zero = True
            
            # 2. 隐式常量除零： const z = 0; a / z;
            elif isinstance(node.right, Var):
                sym, _ = self.symbol_table.lookup(node.right.name, mark_as_used=True)
                if sym and sym.type == SymbolType.CONST and sym.value == 0:
                    is_zero = True
            
            if is_zero:
                self.log_error("检测到除零错误 (Division by Zero)", node.right)

    def visit_UnaryOp(self, node):
        self.visit(node.expr)

    def visit_Var(self, node):
        sym, _ = self.symbol_table.lookup(node.name)
        if not sym:
            suggestion = self._suggest_correction(node.name)
            self.log_error(f"未定义的标识符 '{node.name}'{suggestion}", node)
        else:
            if sym.type == SymbolType.PROC:
                self.log_error(f"过程名 '{node.name}' 不能参与算术运算", node)

    def visit_Num(self, node):
        pass