# test_compiler.py
from pl0_core.lexer import Lexer
from pl0_core.parser import Parser
from pl0_core.ast_printer import ASTPrinter

# 一个包含 PL/0 所有特性的测试程序
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

def test():
    print("------ 1. 词法分析 (Lexer) ------")
    lexer = Lexer(source_code)
    
    # 这里的 Parser 初始化会消耗 tokens，所以如果要看 token 列表，
    # 需要先复制一份 text 或者让 parser 内部自己创建 lexer
    print("Lexer 准备就绪...")

    print("\n------ 2. 语法分析 (Parser) -> AST ------")
    try:
        # 重新初始化 lexer 保证从头开始
        lexer = Lexer(source_code)
        parser = Parser(lexer)
        ast = parser.parse()
        
        print("AST 构建成功！结构如下：\n")
        printer = ASTPrinter()
        printer.print(ast)
        
    except Exception as e:
        print(f"\n❌ 解析出错: {e}")
        # 打印详细错误堆栈，方便调试
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()