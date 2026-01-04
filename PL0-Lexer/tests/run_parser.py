import sys
import os
from pl0_core.lexer import Lexer
from pl0_core.parser import Parser

def ensure_output_dir():
    """确保 output 目录存在"""
    if not os.path.exists('output'):
        os.makedirs('output')

def main():

    if len(sys.argv) < 2:
        print("用法: python run_parser.py <源文件路径>")
        print("示例: python run_parser.py testcases/test3.pl0")
        sys.exit(1)
        
    filepath = sys.argv[1]
    

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"错误: 文件 '{filepath}' 未找到。")
        sys.exit(1)

    print("-" * 50)
    print(f"正在对 {filepath} 进行语法分析...")
    print("-" * 50)


    lexer = Lexer(source)
    parser = Parser(lexer)
    

    try:
        parser.parse()
    except RecursionError:
        print("错误: 递归深度过大，可能是死循环或语法结构过于复杂。")

    print("-" * 50)
    

    ensure_output_dir()
    output_path = "output/parser_output.txt"
    
    with open(output_path, 'w', encoding='utf-8') as f:

        f.write("=== 语法分析过程 (Parse Log) ===\n")
        for line in parser.output_lines:
            f.write(line + "\n")
        

        f.write("\n=== 语法错误报告 (Syntax Errors) ===\n")
        if parser.errors:
            for err in parser.errors:
                f.write(err + "\n")
            print(f"分析完成，发现 {len(parser.errors)} 个错误。")
        else:
            f.write("无语法错误。")
            print("分析成功，无语法错误！")
            
    print(f"详细分析结果已保存至: {output_path}")

if __name__ == '__main__':
    main()