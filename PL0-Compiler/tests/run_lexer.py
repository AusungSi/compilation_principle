import sys
from pl0_core.lexer import Lexer
from pl0_core.token import TokenType

def main():
    if len(sys.argv) < 2:
        print("用法: python main.py <源文件名> [输出文件名]")
        print("示例: python main.py test.pl0 output.txt")
        sys.exit(1)

    source_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output/lexical_output.txt"

    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{source_path}'")
        sys.exit(1)

    lexer = Lexer(source_code)
    tokens = []
    
    print(f"正在分析 {source_path} ...")

    while True:
        token = lexer.get_next_token()
        tokens.append(token)
        if token.type == TokenType.EOF:
            break

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            header = f"{'行:列':<12} | {'类型(SYM)':<15} | {'原始值(VAL)':<15}"
            divider = "-" * 50
            
            f.write("PL/0 词法分析结果\n")
            f.write(divider + "\n")
            f.write(header + "\n")
            f.write(divider + "\n")
            
            print("\n" + header)
            print(divider)

            for t in tokens:
                if t.type == TokenType.EOF: continue
                
                pos_str = f"{t.line}:{t.column}"
                line_str = f"{pos_str:<12} | {t.type.name:<15} | {t.value:<15}"
                
                f.write(line_str + "\n")
                print(line_str)
            
            if lexer.errors:
                error_header = "\n\n=== 词法错误报告 ==="
                f.write(error_header + "\n")
                print(error_header)  
                
                for err in lexer.errors:
                    f.write(err + "\n")
                    print(f"ERROR: {err}")
            else:
                f.write("\n分析成功，无词法错误。\n")
                print("\n分析成功，无词法错误。")

        print(f"\n结果已保存至: {output_path}")

    except IOError as e:
        print(f"写入文件失败: {e}")

if __name__ == "__main__":
    main()