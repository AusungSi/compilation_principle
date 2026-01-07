class SymbolType:
    CONST = "CONST"
    VAR = "VAR"
    PROC = "PROC"

class Symbol:
    def __init__(self, name, type, level, addr=0, value=0, param_count=0, is_initialized=False):
        self.name = name
        self.type = type
        self.level = level
        
        # 对于 VAR: addr 是栈帧中的相对地址 (Offset)
        # 对于 PROC: addr 是过程入口指令的索引 (Instruction Address)
        self.addr = addr
        
        # 对于 CONST: value 是常量值
        self.value = value
        self.param_count = param_count
        self.referenced = False
        self.is_initialized = is_initialized

    def __repr__(self):
        info = f"{self.level}:{self.addr}"
        if self.type == SymbolType.CONST:
            info += f"={self.value}"
        if self.type == SymbolType.PROC:
            info += f"(params={self.param_count})"
        return f"<{self.type} {self.name} @ {info}>"

class SymbolTable:
    def __init__(self):
        # 作用域栈：每个元素是一个列表，存储该层定义的所有符号
        self.scopes = [] 
        
        # 地址计数器栈：记录每一层当前分配到了哪个地址
        self.addr_counters = []
        
        # 当前层级 (-1 表示尚未开始，主程序是 0)
        self.current_level = -1

    def enter_scope(self):
        """进入新的作用域 (层级+1)"""
        self.scopes.append([])       # 符号列表
        self.addr_counters.append(3) # 地址计数器
        self.current_level += 1

    def exit_scope(self):
        """退出当前作用域 (层级-1)"""
        self.scopes.pop()
        self.addr_counters.pop()
        self.current_level -= 1

    def define_const(self, name, value):
        """定义常量"""
        sym = Symbol(name, SymbolType.CONST, self.current_level, value=value, is_initialized=True)
        self._add_symbol(sym)

    def define_var(self, name):
        """定义变量，自动分配地址"""
        # 获取当前层的可用地址
        addr = self.addr_counters[-1]
        
        sym = Symbol(name, SymbolType.VAR, self.current_level, addr=addr, is_initialized=False)
        self._add_symbol(sym)
        
        # 更新计数器，下一个变量地址+1
        self.addr_counters[-1] += 1

    def define_proc(self, name, param_count=0):
        """
        定义过程
        注意：过程名是定义在'当前层'，但过程内部的代码是在'下一层'
        """
        sym = Symbol(name, SymbolType.PROC, self.current_level, param_count=param_count, is_initialized=True)
        self._add_symbol(sym)
        return sym # 返回符号对象以便后续回填地址

    def _add_symbol(self, symbol):
        """内部方法：添加符号并查重"""
        current_scope = self.scopes[-1]
        for s in current_scope:
            if s.name == symbol.name:
                raise Exception(f"语义错误: 标识符 '{symbol.name}' 在当前层重复定义")
        current_scope.append(symbol)

    def lookup(self, name, mark_as_used=True):
        """
        查找符号
        mark_as_used: 如果为 True，查找成功时将符号标记为已引用
        按层级按顺序查找
        """
        for i in range(len(self.scopes) - 1, -1, -1):
            scope = self.scopes[i]
            for sym in scope:
                if sym.name == name:
                    if mark_as_used:
                        sym.referenced = True
                    return sym, self.current_level - sym.level
        return None, None
    
    def get_unused_variables(self):
        unused = []
        if self.scopes:
            for sym in self.scopes[-1]:
                if sym.type == SymbolType.VAR and not sym.referenced:
                    unused.append(sym)
        return unused

    def get_current_frame_size(self):
        """获取当前栈帧的大小 (用于 INT 指令)"""
        return self.addr_counters[-1]
    
    def get_all_symbols(self):
        """获取当前所有作用域的符号（用于模糊匹配）"""
        all_syms = []
        for scope in self.scopes:
            all_syms.extend(scope)
        return all_syms

    def get_unused_variables(self):
        """获取当前作用域中未使用的变量（在 exit_scope 前调用）"""
        unused = []
        if self.scopes:
            for sym in self.scopes[-1]:
                if sym.type == SymbolType.VAR and not sym.referenced:
                    unused.append(sym)
        return unused
    
def levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]