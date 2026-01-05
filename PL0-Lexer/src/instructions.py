from enum import Enum

class OpCode(Enum):
    """
    P-Code 指令集 (F段)
    """
    LIT = "LIT" # 将常量放入栈顶
    LOD = "LOD" # 将变量值放入栈顶
    STO = "STO" # 将栈顶值存入变量
    CAL = "CAL" # 调用过程
    INT = "INT" # 开辟栈空间
    JMP = "JMP" # 无条件跳转
    JPC = "JPC" # 条件跳转
    OPR = "OPR" # 算术/逻辑/关系运算
    RED = "RED" # 读入数据
    WRT = "WRT" # 输出数据

class Instruction:
    def __init__(self, f: OpCode, l: int, a: int):
        self.f = f  # 功能码
        self.l = int(l)  # 层差
        self.a = int(a)  # 位移量或操作码

    def __repr__(self):
        return f"{self.f.value}\t{self.l}\t{self.a}"

class OprCode:
    """
    OPR 指令对应的 A 段操作码定义
    严格对应你提供的表格
    """
    RET = 0   
    NEG = 1   
    ADD = 2   
    SUB = 3   
    MUL = 4   
    DIV = 5   
    ODD = 6   
    EQL = 7   
    NEQ = 8   
    LSS = 9   
    GEQ = 10  
    GTR = 11  
    LEQ = 12  
    LINE = 13 