import sys
from enum import Enum
from .instructions import OpCode, OprCode

class Interpreter:
    def __init__(self, instructions, debug_mode=False):
        self.code = instructions  # CODE 存储器
        self.stack = [0] * 2000   # STACK 存储器 (动态分配数据空间)
        
        # 寄存器定义
        self.p = 0    # P: 程序地址寄存器 (PC)
        self.b = 0    # B: 基地址寄存器 (Base)
        self.t = 0    # T: 栈顶指示器寄存器 (Top)
        self.i = None # I: 指令寄存器
        
        self.debug_mode = debug_mode

    def base(self, l):
        """
        [核心难点] 通过静态链(SL)向上查找定义层的基地址
        说明：
        - 栈帧的第0个单元 (offset 0) 存放静态链 (SL)
        - l 是层差 (调用层与说明层的层差值)
        """
        b1 = self.b
        while l > 0:
            b1 = self.stack[b1] # 沿着 SL 往上找
            l -= 1
        return b1

    def run(self):
        print(f"\n{'='*20} PL/0 虚拟机启动 {'='*20}")
        
        # 初始化寄存器
        self.t = 0  
        self.b = 1  # 栈从索引 1 开始使用 (0号位保留或不用)
        self.p = 0  
        
        # 初始化主程序的栈帧头部 (虽然主程序没有调用者，但为了逻辑统一)
        # 栈结构: [SL, DL, RA]
        self.stack[1] = 0 # SL
        self.stack[2] = 0 # DL
        self.stack[3] = 0 # RA

        try:
            while self.p < len(self.code):
                # 1. 取指 (Fetch)
                self.i = self.code[self.p]
                self.p += 1
                
                f = self.i.f # 功能码
                l = self.i.l # 层差
                a = self.i.a # 位移量/操作数

                # [调试输出]
                if self.debug_mode:
                    self._print_debug_info()

                # 2. 执行 (Execute)
                
                if f == OpCode.LIT:
                    # LIT 0, a: 取常量a放入数据栈栈顶
                    self.t += 1
                    self.stack[self.t] = a

                elif f == OpCode.LOD:
                    # LOD L, a: 取变量(相对地址a, 层差L)放到栈顶
                    self.t += 1
                    base_addr = self.base(l)
                    self.stack[self.t] = self.stack[base_addr + a]

                elif f == OpCode.STO:
                    if l == -1:
                        # 解释：
                        # 编译器的约定是：L=-1 代表要把值写入"即将被创建的下一个栈帧"中。
                        # 此时 self.t 指向栈顶（实参的值）。
                        # STO 执行完后会退栈 (self.t -= 1)。
                        # 稍后执行 CAL 时，新栈帧的 Base 将是 (当前的 self.t) + 1。
                        # 目标变量在新栈帧的偏移是 a。
                        # 所以物理地址推导：
                        # Target = New_Base + a 
                        #        = (Current_T_After_Pop + 1) + a 
                        #        = (self.t - 1 + 1) + a 
                        #        = self.t + a
                        self.stack[self.t + a] = self.stack[self.t]
                    
                    else:
                        # 原有的正常赋值逻辑 (写入当前或外层栈帧)
                        base_addr = self.base(l)
                        self.stack[base_addr + a] = self.stack[self.t]
                    
                    # 无论哪种情况，STO 都要消耗栈顶元素
                    self.t -= 1

                elif f == OpCode.CAL:
                    # CAL L, a: 调用过程
                    # a: 目标程序入口地址
                    # L: 层差
                    
                    # 建立新栈帧头部:
                    # self.t + 1 是新栈帧的基址 (SL)
                    self.stack[self.t + 1] = self.base(l) # SL: 静态链 (定义层的基址)
                    self.stack[self.t + 2] = self.b       # DL: 动态链 (调用者的基址)
                    self.stack[self.t + 3] = self.p       # RA: 返回地址
                    
                    self.b = self.t + 1 # 更新基址寄存器
                    self.p = a          # 跳转

                elif f == OpCode.INT:
                    # INT 0, a: 数据栈栈顶指针增加 a
                    # a 包含了 SL, DL, RA 这 3 个单元
                    self.t += a

                elif f == OpCode.JMP:
                    # JMP 0, a: 无条件转移
                    self.p = a

                elif f == OpCode.JPC:
                    # JPC 0, a: 条件转移 (栈顶为0则转)
                    if self.stack[self.t] == 0:
                        self.p = a
                    self.t -= 1 # 消耗掉用于判断的布尔值

                elif f == OpCode.RED:
                    # RED L, a: 读数据并存入变量 (注意：你的要求是存入变量，不是压栈)
                    print("Input: ", end='', flush=True)
                    try:
                        val = int(input())
                        base_addr = self.base(l)
                        self.stack[base_addr + a] = val
                    except ValueError:
                        print("\n[Runtime Error] 输入格式错误，请输入整数")
                        return

                elif f == OpCode.WRT:
                    # WRT 0, 0: 将栈顶内容输出
                    print(self.stack[self.t]) # 默认换行
                    self.t += 1 # 这里的处理有歧义，通常 WRT 只读不退，或者读完退栈
                    # 既然栈顶是表达式的结果，输出后通常意味着该表达式被"消费"了
                    # 但部分 PL/0 实现 WRT 不退栈，由后续 OPR 0 退栈。
                    # 为了安全，这里我们暂时 **退栈**，防止垃圾数据堆积。
                    # 如果你的生成器在 WRT 后生成了退栈指令，这里就改成不退栈。
                    self.t -= 1 

                elif f == OpCode.OPR:
                    self.exec_opr(a)

        except IndexError:
            print(f"\n[Runtime Error] 栈溢出 (Stack Overflow) at P={self.p-1}")
        except Exception as e:
            print(f"\n[Runtime Error] PC={self.p-1}, Instr={self.i}: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"{'='*20} 程序运行结束 {'='*20}\n")

    def exec_opr(self, k):
        """执行 OPR 指令"""
        if k == OprCode.RET: # 0: Return
            # 恢复栈帧
            top_frame = self.b
            self.p = self.stack[top_frame + 2] # 恢复 PC (RA)
            self.b = self.stack[top_frame + 1] # 恢复 Base (DL)
            self.t = top_frame - 1             # 释放当前栈空间
            if self.p == 0:
                # 将 P 设为代码长度，从而打破 while self.p < len(code) 循环
                self.p = len(self.code) 
                return
            
        elif k == OprCode.NEG: # 1: 取反
            self.stack[self.t] = -self.stack[self.t]

        elif k == OprCode.ADD: # 2: +
            self.t -= 1
            self.stack[self.t] += self.stack[self.t + 1]

        elif k == OprCode.SUB: # 3: -
            self.t -= 1
            self.stack[self.t] -= self.stack[self.t + 1]

        elif k == OprCode.MUL: # 4: *
            self.t -= 1
            self.stack[self.t] *= self.stack[self.t + 1]

        elif k == OprCode.DIV: # 5: /
            self.t -= 1
            if self.stack[self.t + 1] == 0:
                raise Exception("Division by zero")
            self.stack[self.t] //= self.stack[self.t + 1]

        elif k == OprCode.ODD: # 6: odd
            self.stack[self.t] %= 2

        elif k == OprCode.EQL: # 8: =
            self.t -= 1
            self.stack[self.t] = 1 if self.stack[self.t] == self.stack[self.t + 1] else 0

        elif k == OprCode.NEQ: # 9: <>
            self.t -= 1
            self.stack[self.t] = 1 if self.stack[self.t] != self.stack[self.t + 1] else 0

        elif k == OprCode.LSS: # 10: <
            self.t -= 1
            self.stack[self.t] = 1 if self.stack[self.t] < self.stack[self.t + 1] else 0

        elif k == OprCode.GEQ: # 11: >=
            self.t -= 1
            self.stack[self.t] = 1 if self.stack[self.t] >= self.stack[self.t + 1] else 0

        elif k == OprCode.GTR: # 12: >
            self.t -= 1
            self.stack[self.t] = 1 if self.stack[self.t] > self.stack[self.t + 1] else 0

        elif k == OprCode.LEQ: # 13: <=
            self.t -= 1
            self.stack[self.t] = 1 if self.stack[self.t] <= self.stack[self.t + 1] else 0
            
        elif k == OprCode.LINE: # 14: 换行
            print()

    def _print_debug_info(self):
        """打印寄存器和栈状态，用于调试"""
        instr_str = f"{self.i.f.name} {self.i.l}, {self.i.a}"
        # 打印当前执行的指令
        print(f"P: {self.p-1:<3} | {instr_str:<12} | ", end="")
        # 打印寄存器
        print(f"B: {self.b:<3} T: {self.t:<3} | Stack: ", end="")
        # 打印栈的内容 (只打印活动部分)
        print(self.stack[1:self.t+1])

# ==========================================
# 简单的测试入口 (main)
# ==========================================
if __name__ == "__main__":
    from src.instructions import Instruction # 假设你有这个类
    
    # 手动构造一个简单的 P-Code 程序: 计算 1 + 2 并输出
    # 模拟主程序: INT 0 5 (开辟空间, 3个头+2个变量) -> LIT 0 1 -> STO 0 3 -> LIT 0 2 -> STO 0 4 -> LOD 0 3 -> LOD 0 4 -> OPR 0 2 -> WRT 0 0 -> OPR 0 0
    
    code = [
        Instruction(OpCode.INT, 0, 5), # 0: 开栈, 变量从 3, 4 开始
        Instruction(OpCode.LIT, 0, 1), # 1: 压入 1
        Instruction(OpCode.STO, 0, 3), # 2: 存入变量 3
        Instruction(OpCode.LIT, 0, 2), # 3: 压入 2
        Instruction(OpCode.STO, 0, 4), # 4: 存入变量 4
        Instruction(OpCode.LOD, 0, 3), # 5: 取出变量 3
        Instruction(OpCode.LOD, 0, 4), # 6: 取出变量 4
        Instruction(OpCode.OPR, 0, 2), # 7: 加法
        Instruction(OpCode.WRT, 0, 0), # 8: 输出
        Instruction(OpCode.OPR, 0, 0)  # 9: 退栈/结束
    ]

    vm = Interpreter(code, debug_mode=True)
    vm.run()