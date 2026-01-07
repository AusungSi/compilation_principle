import sys
import os

# 确保能导入 pl0_core 包
sys.path.append(os.getcwd())

from pl0_core.lexer import Lexer
from pl0_core.parser import Parser
from pl0_core.generator import CodeGenerator
from pl0_core.instructions import OpCode

# 测试用例：计算 1 到 5 的和，并输出
source_code = """
program xi;
const a:=5;
var j,sum,x;
     procedure sum1(x);
     var j;
     begin
         j:=1;
         sum:=0;
         while j<=x do
	begin
	   sum:=sum+j;
	   j:=j+1
	end;
	write(sum)
      end
begin
     read(x,j);
     call sum1(j+5);
     write(j)	
end

"""

def test_pcode_generation():
    print(f"{'='*20} 开始编译 {'='*20}")
    
    try:
        # 1. 词法 & 语法分析
        lexer = Lexer(source_code)
        parser = Parser(lexer)
        ast = parser.parse()
        print("✅ AST 构建成功")

        # 2. 代码生成
        generator = CodeGenerator()
        code = generator.generate(ast)
        print("✅ P-Code 生成成功")

        # 3. 格式化输出指令集
        print("\n生成的 P-Code 指令列表:")
        print(f"{'ADDR':<6} {'F':<6} {'L':<6} {'A':<6} {'说明':<15}")
        print("-" * 50)

        for i, instr in enumerate(code):
            # 简单的注释逻辑，帮助理解指令含义
            comment = ""
            if instr.f == OpCode.JMP: comment = f"Jump to {instr.a}"
            elif instr.f == OpCode.JPC: comment = f"Jump if False to {instr.a}"
            elif instr.f == OpCode.INT: comment = f"Alloc {instr.a} vars"
            elif instr.f == OpCode.LIT: comment = f"Push {instr.a}"
            elif instr.f == OpCode.LOD: comment = f"Load var {instr.a}"
            elif instr.f == OpCode.STO: comment = f"Store var {instr.a}"
            elif instr.f == OpCode.CAL: comment = f"Call proc @ {instr.a}"
            elif instr.f == OpCode.OPR and instr.a == 0: comment = "Return"

            # 打印指令
            # 注意: instr.f 是 Enum，要用 .value 获取字符串
            print(f"{i:<6} {instr.f.value:<6} {instr.l:<6} {instr.a:<6} # {comment}")

    except Exception as e:
        print(f"\n❌ 编译失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pcode_generation()