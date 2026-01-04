from .ast_nodes import *
from .symbol_table import SymbolTable, SymbolType, levenshtein_distance
from .token import TokenType

class SemanticAnalyzer:
    """
    语义分析器 (Semantic Analyzer)
    
    负责对抽象语法树 (AST) 进行静态语义检查，确保程序的语义正确性。
    在此阶段不生成代码，而是收集错误 (Errors) 和警告 (Warnings)。

    已实现的功能特性 (Features Implemented):
    
    1. 基础检查 (Basic Checks):
       - [Error] 变量/常量/过程的重复定义检测 (Duplicate Definition)
       - [Error] 未声明标识符的使用检测 (Undefined Identifier)
       - [Error] 非法类型赋值 (如给 Const 或 Procedure 赋值)

    2. 作用域与生命周期 (Scope & Lifetime):
       - [Warning] 作用域遮蔽检测 (Shadowing): 内层变量遮挡外层同名变量
       - [Warning] 未使用变量检测 (Unused Variable): 定义但从未被引用的局部/全局变量
       - [Error] 未初始化变量检测 (Uninitialized Variable): 变量在使用前未进行赋值

    3. 静态计算与控制流分析 (Static Evaluation & Control Flow):
       - [Error] 常量折叠与增强除零检测 (Constant Folding): 
         支持在编译期计算常量表达式 (如 10/(5-5)) 并拦截除零错误。
       - [Warning] 不可达代码检测 (Unreachable Code):
         检测恒为假的 IF/WHILE 条件 (如 if 0=1 then ...)。
       - [Warning] 死循环检测 (Infinite Loop):
         检测恒为真的 WHILE 条件 (如 while 1=1 do ...)。

    4. 过程调用检查 (Procedure Checks):
       - [Error] 参数个数匹配检查 (Parameter Count Mismatch)
       - [Error] 调用类型检查 (防止 call 变量)
    """
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

            shadowed_sym, _ = self.symbol_table.lookup(const.name)
            if shadowed_sym:
                print(f"\033[93m[Warning] 常量 '{const.name}' 遮蔽了外层作用域的同名标识符\033[0m")

            try:
                self.symbol_table.define_const(const.name, const.value)
            except Exception as e:
                # 捕获 SymbolTable 抛出的重复定义异常，转化为语义错误
                self.log_error(str(e), const)

        # 2. 定义变量
        for var in node.vars:

            shadowed_sym, _ = self.symbol_table.lookup(var.name)
            if shadowed_sym:
                print(f"\033[93m[Warning] 变量 '{var.name}' 遮蔽了外层作用域的同名标识符\033[0m")

            try:
                self.symbol_table.define_var(var.name)
            except Exception as e:
                self.log_error(str(e), var)

        # 3. 定义过程 (先定义，后递归，支持递归调用)
        for proc in node.procs:
            try:
                # [关键修改] 传入 param_count 参数
                # len(proc.params) 就是该过程定义时的参数列表长度
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
            print(f"\033[93m[Warning] 变量 '{sym.name}' 已定义但未使用 (Unused Variable)\033[0m")

    def visit_ProcedureDecl(self, node):
        self.symbol_table.enter_scope()
        
        # 定义参数为局部变量
        for param in node.params:

            shadowed_sym, _ = self.symbol_table.lookup(param)
            if shadowed_sym:
                print(f"\033[93m[Warning] 过程参数 '{param}' 遮蔽了外层作用域的同名标识符\033[0m")
            
            try:
                self.symbol_table.define_var(param)
                sym, _ = self.symbol_table.lookup(param)
                if sym: sym.is_initialized = True
            except Exception as e:
                self.log_error(f"参数名重复: {str(e)}", node)

        self.visit(node.block)
        self.symbol_table.exit_scope()
    
    # ================= 语句检查 =================

    def visit_Compound(self, node):
        for stmt in node.children:
            self.visit(stmt)

    def visit_Assign(self, node):
        # 1. 先检查右值表达式 (顺序很重要，比如 a := a + 1，此时右边的 a 必须是已初始化的)
        self.visit(node.right)

        # 2. 检查左值变量
        var_name = node.left.name
        sym, _ = self.symbol_table.lookup(var_name)

        if not sym:
            # (原有的报错逻辑)
            suggestion = self._suggest_correction(var_name)
            self.log_error(f"使用了未定义的变量 '{var_name}'{suggestion}", node.left)
        else:
            if sym.type == SymbolType.CONST:
                self.log_error(f"不能给常量 '{var_name}' 赋值", node.left)
            elif sym.type == SymbolType.PROC:
                self.log_error(f"不能给过程名 '{var_name}' 赋值", node.left)
            else:
                # [新增] 成功赋值后，将该变量标记为已初始化
                sym.is_initialized = True

    def visit_Call(self, node):
        # 1. 检查过程名是否存在
        proc_name = node.proc_name
        sym, _ = self.symbol_table.lookup(proc_name)

        if not sym:
            self.log_error(f"调用了未定义的过程 '{proc_name}'", node)
            return # 无法继续检查，直接返回

        if sym.type != SymbolType.PROC:
            self.log_error(f"'{proc_name}' 不是一个过程，无法调用", node)
            return

        # 2. [新增] 检查参数个数匹配
        expected_count = sym.param_count
        actual_count = len(node.args)

        if expected_count != actual_count:
            self.log_error(
                f"过程 '{proc_name}' 需要 {expected_count} 个参数，但提供了 {actual_count} 个", 
                node
            )

        # 3. 递归检查实参表达式 (确保实参里没有未定义变量等错误)
        for arg in node.args:
            self.visit(arg)

    def visit_If(self, node):
        self.visit(node.condition) # 检查内部是否有未定义变量
        
        cond_val = self.evaluate_static(node.condition)
        
        # 0 代表假
        if cond_val == 0:
            print(f"\033[93m[Warning] IF 条件恒为假，Then 分支将永远不会执行\033[0m")
        
        self.visit(node.then_stmt)
        
        if node.else_stmt:
            # 非 0 代表真 (注意：inf 也是非0，所以不用特判)
            if cond_val is not None and cond_val != 0:
                 print(f"\033[93m[Warning] IF 条件恒为真，Else 分支将永远不会执行\033[0m")
            self.visit(node.else_stmt)

    def visit_While(self, node):
        self.visit(node.condition)
        
        cond_val = self.evaluate_static(node.condition)
        
        if cond_val == 0:
            print(f"\033[93m[Warning] While 循环条件恒为假，循环体将不会执行\033[0m")
        elif cond_val is not None and cond_val != 0:
            print(f"\033[93m[Warning] 检测到死循环 (Infinite Loop)，循环条件恒为真\033[0m")

        self.visit(node.body)
    
    def visit_Read(self, node):
        for var in node.vars:
            sym, _ = self.symbol_table.lookup(var.name)
            if not sym:
                self.log_error(f"Read 语句中变量 '{var.name}' 未定义", var)
            elif sym.type != SymbolType.VAR:
                self.log_error(f"Read 只能读取变量，不能读取 '{var.name}' ({sym.type})", var)
            else:
                # [新增] 从输入流读取值后，变量也被视为已初始化
                sym.is_initialized = True

    def visit_Write(self, node):
        for expr in node.exprs:
            self.visit(expr)

    # ================= 表达式检查 =================

    def visit_BinOp(self, node):
        self.visit(node.left)
        self.visit(node.right)
        
        # [修改] 增强版除零检查
        if node.op.type == TokenType.SLASH: # 如果是除法
            # 尝试计算右操作数（分母）的值
            denom_val = self.evaluate_static(node.right)
            
            # 情况1: 确切算出是 0 (例如: 10/0, 10/(5-5), 10/const_zero)
            if denom_val == 0:
                self.log_error("检测到除零错误 (编译期静态检测)", node.right)
            
            # 情况2: 算出是 inf (说明右边表达式内部已经发生了除零，例如 10/(1/0))
            # 这种情况下，递归访问 node.right 时已经报过错了，这里可以忽略
            elif denom_val == float('inf'):
                pass

    def visit_UnaryOp(self, node):
        self.visit(node.expr)

    def visit_Var(self, node):
        sym, level_diff = self.symbol_table.lookup(node.name)
        
        if not sym:
            suggestion = self._suggest_correction(node.name)
            self.log_error(f"未定义的标识符 '{node.name}'{suggestion}", node)
        else:
            if sym.type == SymbolType.PROC:
                self.log_error(f"过程名 '{node.name}' 不能参与算术运算", node)
            
            # [修改] 未初始化检查逻辑
            elif sym.type == SymbolType.VAR:
                # 只有当变量属于"当前作用域" (level_diff == 0) 时，才严格检查初始化
                # 如果 level_diff > 0 (说明是外层/全局变量)，因为我们还没分析主程序体，无法确定它是否被赋值，
                # 所以为了避免误报，我们要放过它。
                if level_diff == 0 and not sym.is_initialized:
                    self.log_error(f"变量 '{node.name}' 可能在使用前未初始化", node)

    def visit_Num(self, node):
        pass

    def evaluate_static(self, node):
        """
        [增强版] 支持算术运算和关系运算的静态求值
        返回: 
            - 整数值 (算术运算结果)
            - 1 或 0 (关系运算结果，1为真，0为假)
            - None (无法计算)
        """
        # 1. 基础值
        if isinstance(node, Num):
            return node.value
        
        elif isinstance(node, Var):
            sym, _ = self.symbol_table.lookup(node.name)
            if sym and sym.type == SymbolType.CONST:
                # [修复] 强制转 int，避免字符串类型导致的错误
                return int(sym.value)
            return None 
            
        # 2. 一元运算 (支持 odd)
        elif isinstance(node, UnaryOp):
            val = self.evaluate_static(node.expr)
            if val is None: return None
            
            if node.op.type == TokenType.MINUS: return -val
            # [新增] odd 运算：奇数返回 1，偶数返回 0
            if node.op.type == TokenType.ODD: return 1 if (val % 2 != 0) else 0
            return val
            
        # 3. 二元运算 (支持算术 + 关系)
        elif isinstance(node, BinOp):
            left_val = self.evaluate_static(node.left)
            right_val = self.evaluate_static(node.right)
            
            if left_val is None or right_val is None:
                return None
                
            tt = node.op.type
            
            # --- 算术 ---
            if tt == TokenType.PLUS: return left_val + right_val
            if tt == TokenType.MINUS: return left_val - right_val
            if tt == TokenType.TIMES: return left_val * right_val
            if tt == TokenType.SLASH:
                if right_val == 0: return float('inf')
                return int(left_val / right_val)
            
            # --- [新增] 关系运算 (严格适配你的 <lop> 规则) ---
            if tt == TokenType.EQUAL:         return 1 if left_val == right_val else 0
            if tt == TokenType.NOT_EQUAL:     return 1 if left_val != right_val else 0
            if tt == TokenType.LESS:          return 1 if left_val < right_val else 0
            if tt == TokenType.LESS_EQUAL:    return 1 if left_val <= right_val else 0
            if tt == TokenType.GREATER:       return 1 if left_val > right_val else 0
            if tt == TokenType.GREATER_EQUAL: return 1 if left_val >= right_val else 0
            
            return None
            
        return None