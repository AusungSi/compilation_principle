from enum import Enum

class OpCode(Enum):
    """
    P-Code 指令集 (F段)
    """
    LIT = "LIT" # Load Constant (将常量放入栈顶)
    LOD = "LOD" # Load Variable (将变量值放入栈顶)
    STO = "STO" # Store Variable (将栈顶值存入变量)
    CAL = "CAL" # Call Procedure (调用过程)
    INT = "INT" # Increment Stack (开辟栈空间)
    JMP = "JMP" # Jump (无条件跳转)
    JPC = "JPC" # Jump Conditional (条件跳转)
    OPR = "OPR" # Operation (算术/逻辑/关系运算)
    
    # 根据你的表格，RED 和 WRT 是独立指令
    RED = "RED" # Read (读入数据)
    WRT = "WRT" # Write (输出数据)

class Instruction:
    def __init__(self, f: OpCode, l: int, a: int):
        self.f = f  # Function code (功能码)
        self.l = l  # Level difference (层差)
        self.a = a  # Address / Value / OprCode (位移量或操作码)

    def __repr__(self):
        # 格式化输出，例如 "LIT 0 5"
        # 使用制表符 \t 对齐，方便阅读
        return f"{self.f.value}\t{self.l}\t{self.a}"

class OprCode:
    """
    OPR 指令对应的 A 段操作码定义
    严格对应你提供的表格
    """
    RET = 0   # 过程调用结束返回
    NEG = 1   # 栈顶元素取反
    ADD = 2   # 次栈顶 + 栈顶
    SUB = 3   # 次栈顶 - 栈顶
    MUL = 4   # 次栈顶 * 栈顶
    DIV = 5   # 次栈顶 / 栈顶
    ODD = 6   # 栈顶元素奇偶判断
    
    # 关系运算 (注意这里与标准PL/0可能不同，严格按你的表来)
    EQL = 7   # =  (次栈顶 == 栈顶)
    NEQ = 8   # <> (次栈顶 != 栈顶)
    LSS = 9   # <  (次栈顶 < 栈顶)
    GEQ = 10  # >= (次栈顶 >= 栈顶)
    GTR = 11  # >  (次栈顶 > 栈顶)
    LEQ = 12  # <= (次栈顶 <= 栈顶)
    
    # 其他
    LINE = 13 # 屏幕输出换行