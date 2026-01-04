import sys
import os
import argparse

# 将当前目录添加到搜索路径，确保能找到 pl0_core
sys.path.append(os.getcwd())

from src.lexer import Lexer
from src.parser import Parser
from src.generator import CodeGenerator
from src.interpreter import Interpreter
from src.ast_printer import ASTPrinter

def print_header(title):
    print(f"\n\033[1;36m{'='*20} {title} {'='*20}\033[0m")

def print_pcode(instructions):
    print(f"\n\033[1;33m[生成的 P-Code 指令]\033[0m")
    print(f"{'ADDR':<6} {'F':<6} {'L':<6} {'A':<6} {'说明':<15}")
    print("-" * 50)
    
    for i, instr in enumerate(instructions):
        # 简单的指令说明注释
        comment = ""
        f_name = instr.f.name if hasattr(instr.f, 'name') else str(instr.f)
        
        if f_name == "JMP": comment = f"Jump to {instr.a}"
        elif f_name == "JPC": comment = f"Jump if False to {instr.a}"
        elif f_name == "INT": comment = f"Alloc {instr.a} vars"
        elif f_name == "LIT": comment = f"Push {instr.a}"
        elif f_name == "LOD": comment = f"Load ({instr.l}, {instr.a})"
        elif f_name == "STO": comment = f"Store ({instr.l}, {instr.a})"
        elif f_name == "CAL": comment = f"Call proc @ {instr.a}"
        elif f_name == "RED": comment = f"Read to ({instr.l}, {instr.a})"
        elif f_name == "WRT": comment = "Write stack top"
        
        print(f"{i:<6} {f_name:<6} {instr.l:<6} {instr.a:<6} # {comment}")
    print("-" * 50)

def compile_and_run(source_code, args):
    try:
        # --- 1. 词法分析 ---
        if args.verbose: print("[1/4] 正在进行词法分析...")
        lexer = Lexer(source_code)
        
        # --- 2. 语法分析 ---
        if args.verbose: print("[2/4] 正在进行语法分析...")
        parser = Parser(lexer)
        ast = parser.parse()
        
        # 如果需要展示 AST
        if args.show_ast:
            print_header("抽象语法树 (AST)")
            printer = ASTPrinter()
            printer.print(ast)

        # --- 3. 代码生成 ---
        if args.verbose: print("[3/4] 正在生成 P-Code...")
        generator = CodeGenerator()
        code = generator.generate(ast)

        # 如果需要展示 P-Code
        if args.show_code:
            print_pcode(code)

        # --- 4. 解释执行 ---
        print_header("程序运行结果")
        interpreter = Interpreter(code, debug_mode=args.debug)
        interpreter.run()

    except Exception as e:
        print(f"\n\033[1;31m[Error] 编译或运行出错:\033[0m {e}")
        if args.traceback:
            import traceback
            traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="PL/0 语言编译器与解释器")
    
    # 命令行参数定义
    parser.add_argument('file', nargs='?', help="PL/0 源文件路径 (.pl0)")
    parser.add_argument('--show-ast', action='store_true', help="显示抽象语法树")
    parser.add_argument('--show-code', action='store_true', help="显示生成的 P-Code 指令")
    parser.add_argument('--debug', action='store_true', help="开启虚拟机调试模式 (显示栈状态)")
    parser.add_argument('--verbose', action='store_true', help="显示编译过程信息")
    parser.add_argument('--traceback', action='store_true', help="出错时显示完整堆栈")

    args = parser.parse_args()

    # 如果没有提供文件，使用默认的测试代码
    if not args.file:
        print("\033[33m提示: 未提供源文件，正在运行内置测试代码...\033[0m")
        # 这是一个经典的递归阶乘测试程序，用于验证复杂的编译器功能
        source_code = """
program factorial_test;
var n, result;

procedure fact(n);
    var temp;
    begin
        if n = 1 then
            result := 1
        else
            begin
                call fact(n-1);
                result := n * result
            end
    end;

begin
    write(10086);
    read(n);
    if n > 0 then
    begin
        call fact(n);
        write(result)
    end
end
"""
        # 默认测试时开启显示
        args.show_ast = True
        args.show_code = True
    else:
        # 读取文件内容
        if not os.path.exists(args.file):
            print(f"错误: 找不到文件 {args.file}")
            return
        with open(args.file, 'r', encoding='utf-8') as f:
            source_code = f.read()

    compile_and_run(source_code, args)

if __name__ == "__main__":
    main()