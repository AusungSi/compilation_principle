import sys
from enum import Enum
from .instructions import OpCode, OprCode

class Interpreter:
    def __init__(self, instructions, debug_mode=False):
        self.code = instructions  # CODE 存储器
        self.stack = [0] * 2000   # STACK 存储器
        
        self.p = 0    
        self.b = 0    
        self.t = 0    
        self.i = None 
        
        self.debug_mode = debug_mode

    def base(self, l):
        """
        说明：
        - 栈帧的第0个单元 (offset 0) 存放静态链 (SL)
        - l 是层差 (调用层与说明层的层差值)
        """
        b1 = self.b
        while l > 0:
            # 回到上一级
            b1 = self.stack[b1]
            l -= 1
        return b1

    def run(self):
        print(f"\n{'='*20} PL/0 虚拟机启动 {'='*20}")
        
        self.t = 0  
        self.b = 1
        self.p = 0  
        
        self.stack[1] = 0 # SL
        self.stack[2] = 0 # DL
        self.stack[3] = 0 # RA

        try:
            while self.p < len(self.code):
                # 取指
                self.i = self.code[self.p]
                self.p += 1
                
                # 解码
                f = self.i.f 
                l = self.i.l 
                a = self.i.a 

                if self.debug_mode:
                    self._print_debug_info()
                
                # 常量压入栈顶
                if f == OpCode.LIT:
                    self.t += 1
                    self.stack[self.t] = a

                # 读取变量到栈顶
                elif f == OpCode.LOD:
                    self.t += 1
                    base_addr = self.base(l)
                    self.stack[self.t] = self.stack[base_addr + a]

                # 栈顶数据存入变量
                elif f == OpCode.STO:
                    if l == -1:
                        self.stack[self.t + a] = self.stack[self.t]
                    
                    else:
                        base_addr = self.base(l)
                        self.stack[base_addr + a] = self.stack[self.t]
                    
                    self.t -= 1

                elif f == OpCode.CAL:

                    # 在栈顶上方建立新的栈帧
                    self.stack[self.t + 1] = self.base(l) # SL: 静态链 
                    self.stack[self.t + 2] = self.b       # DL: 动态链
                    self.stack[self.t + 3] = self.p       # RA: 返回地址
                    
                    self.b = self.t + 1 # 更新基址寄存器
                    self.p = a          # 跳转

                elif f == OpCode.INT:
                    self.t += a

                elif f == OpCode.JMP:
                    self.p = a

                elif f == OpCode.JPC:
                    if self.stack[self.t] == 0:
                        self.p = a
                    self.t -= 1

                elif f == OpCode.RED:
                    print("Input: ", end='', flush=True)
                    try:
                        val = int(input())
                        base_addr = self.base(l)
                        self.stack[base_addr + a] = val
                    except ValueError:
                        print("\n[Runtime Error] 输入格式错误，请输入整数")
                        return

                elif f == OpCode.WRT:
                    print(self.stack[self.t])
                    self.t += 1
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
        if k == OprCode.RET:
            top_frame = self.b
            self.p = self.stack[top_frame + 2] 
            self.b = self.stack[top_frame + 1] 
            self.t = top_frame - 1            
            if self.p == 0:
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

        print(f"P: {self.p-1:<3} | {instr_str:<12} | ", end="")

        print(f"B: {self.b:<3} T: {self.t:<3} | Stack: ", end="")

        print(self.stack[1:self.t+1])

if __name__ == "__main__":
    from src.instructions import Instruction
       
    code = [
        Instruction(OpCode.INT, 0, 5), 
        Instruction(OpCode.LIT, 0, 1), 
        Instruction(OpCode.STO, 0, 3), 
        Instruction(OpCode.LIT, 0, 2), 
        Instruction(OpCode.STO, 0, 4), 
        Instruction(OpCode.LOD, 0, 3), 
        Instruction(OpCode.LOD, 0, 4), 
        Instruction(OpCode.OPR, 0, 2), 
        Instruction(OpCode.WRT, 0, 0), 
        Instruction(OpCode.OPR, 0, 0)  
    ]

    vm = Interpreter(code, debug_mode=True)
    vm.run()