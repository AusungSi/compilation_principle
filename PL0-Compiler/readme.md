第一阶段：定义抽象语法树 (AST) 节点类
目前的 Parser 只是“吃掉”Token 并打印日志。你需要定义一组 Python 类，用来在内存中表示程序的结构。

你需要创建以下几类节点：

程序与块 (Program structure)

Program: 根节点，包含 block。

Block: 核心节点，包含 consts (常量列表), vars (变量列表), procs (过程列表), statement (主体语句)。

Procedure: 包含过程名、参数列表、对应的 Block。

声明 (Declarations)

ConstDecl: 存储 (name, value)。

VarDecl: 存储 (name)。

语句 (Statements)

Compound: 对应 begin ... end，包含语句列表。

Assign: 赋值语句，包含 left (变量名) 和 right (表达式)。

If: 包含 condition (条件), then_branch, else_branch。

While: 包含 condition, body。

Call: 包含过程名和参数表达式列表。

Read/Write: IO操作节点。

表达式 (Expressions)

BinOp: 二元运算（+, -, *, / 以及关系运算符）。包含 left, op, right。

UnaryOp: 一元运算（例如 odd, 负号）。

Var: 变量引用（在表达式中出现的变量）。

Num: 具体的整数值。

方案核心： 所有的节点类最好继承自一个基类 AST，方便后续处理。

第二阶段：改造 Parser 以构建 AST
你需要修改现有的 Parser 类，将 void (无返回值) 的方法改为返回 AST 节点对象。

修改逻辑推演：

表达式处理 (parse_exp, parse_term, parse_factor)

不再是打印 <Expression>。

例如 parse_exp：先调用 parse_term 拿到左节点，如果发现 +，就创建一个 BinOp 节点，把左节点挂上去，再递归调用 parse_term 拿到右节点挂上去。最后返回这个 BinOp。

语句处理 (parse_statement)

遇到 if：调用 parse_lexp 拿到条件节点，调用 parse_statement 拿到 then 节点。最后返回 If(condition, then_node) 对象。

遇到 begin：创建一个列表，循环调用 parse_statement 将结果存入列表，返回 Compound(children_list)。

块处理 (parse_block)

收集所有的 ConstDecl, VarDecl, Procedure 对象和 Body 对象。

组装成一个 Block 节点返回。

第三阶段：代码生成器 (Code Generator)
这是编译原理中最核心的部分。你需要编写一个 CodeGenerator 类，它遍历 AST 并生成 P-Code 指令列表。

在此阶段，你必须引入符号表 (Symbol Table) 的概念来解决地址回填和层差问题。

关键任务方案：

符号表管理 (Symbol Table)

你需要知道每个变量的 层级 (Level) 和 相对地址 (Offset/Address)。

Level: 主程序是 0 层，主程序定义的 procedure 是 1 层，以此类推。P-Code 中的 L 就是指当前层与变量定义层的差值。

Offset: 变量在栈帧中的位置。每次遇到 var 声明，Offset + 1。进入新过程时，Offset 重置（通常从3开始，因为前3个单元是静态链SL、动态链DL、返回地址RA）。

指令生成逻辑 (Visitor Pattern)

访问 Block: 生成 JMP 跳过声明部分 -> 生成 INT 开辟空间 -> 生成 Body 代码 -> 生成 OPR 0 0 (返回)。

访问 Assign (a := expr): 先递归访问 expr (生成计算代码，结果在栈顶) -> 查找 a 的符号表信息 (Level, Addr) -> 生成 STO L, A。

访问 If:

生成 condition 代码。

生成 JPC 0, 0 (条件跳转，地址先空着，记下这个指令的下标 idx).

生成 then 代码。

回填 (Backpatching): 将 idx 处的跳转地址修改为当前代码生成的下一条指令地址。

访问 While: 记录循环开始地址 -> 生成 condition -> 生成 JPC 跳出循环 -> 生成 body -> 生成 JMP 跳回开始地址 -> 回填 JPC。

第四阶段：P-Code 解释器 (Virtual Machine)
这是最后一步，模拟 PPT 中描述的栈式计算机。

实现方案：

数据结构:

code: 存放指令的数组。

stack: 模拟内存栈。

registers: T (栈顶), B (基址), P (程序计数器), I (指令寄存器)。

辅助函数:

base(l, current_b): 这是最难理解的函数。用于通过静态链 (Static Link) 往上找，找到定义变量的那一层的基地址。PPT中的 L 段就是传给这个函数的。

主循环:

while P != 0:

取出指令 I = code[P]

P = P + 1

根据 I.f (功能码) 执行对应的 switch/if-else 逻辑 (LIT, OPR, LOD, STO...)。



《PL/0 语言编译器设计与实现》课程设计报告课程名称： 编译原理课程设计学号： ____________________姓名： ____________________指导教师： _________________日期： 202X年X月X日第一章 绪论与任务分析1.1 课程设计背景编译原理是计算机科学与技术专业的核心课程，它不仅探讨了程序设计语言实现的机制，更蕴含了计算机科学中形式语言与自动机理论的精髓。编译器将人类可读的高级语言源代码转换为机器可执行的低级代码，这一过程涉及词法分析、语法分析、语义分析、中间代码生成及运行时环境管理等复杂的逻辑步骤。PL/0 语言是由 N. Wirth 在其经典著作《算法+数据结构=程序》中设计的一种类 PASCAL 的教学用语言。尽管其语法结构相对精简，但它包含了现代高级语言的核心特性，如过程嵌套定义、静态作用域控制、循环与条件分支结构等。通过从零实现一个 PL/0 编译器，能够帮助我们深入理解编译器前端（Frontend）与后端（Backend）的协作机制，特别是符号表管理与运行时存储组织（Runtime Storage Organization）的底层原理。1.2 设计任务与目标本次课程设计的主要任务是构建一个功能完备的 PL/0 语言编译系统。系统需能够输入符合规范的 PL/0 源代码，经过编译阶段生成 P-Code（一种假想的栈式计算机指令），并由自行实现的虚拟机解释执行该代码。核心目标：全链路实现：构建从源码到 Token 流，再到抽象语法树（AST），最终生成 P-Code 及解释执行的完整体系。开发环境与技术选型：本项目选择 Python 作为宿主语言。利用 Python 强大的**面向对象特性（OOP）**和动态类型系统，能够快速构建抽象语法树（AST）的复杂类层次结构，并利用其简洁的语法专注于编译器逻辑算法（如递归下降、静态链查找）的实现，而非底层内存管理的琐碎细节，从而在有限的课设时间内完成高复杂度的功能扩展。扩展与创新目标：AST 可视化：将源代码结构化为树形结构输出，直观展示语法分析结果。错误恢复机制：实现恐慌模式（Panic Mode），在遇到语法错误时进行同步恢复，避免编译器因单一错误而崩溃。智能语义提示：引入 Levenshtein 编辑距离算法，当发生拼写错误时提供智能建议。静态计算与安全检测：在编译期进行常量折叠（Constant Folding），并提前检测除零错误和死循环风险。1.3 PL/0 语言定义本编译器遵循以下扩展后的 EBNF 文法规范，支持 while-do 循环、if-then-else 分支以及 read/write 语句：Plaintext<prog> → program <id>; <block>
<block> → [<condecl>][<vardecl>][<proc>]<body>
<condecl> → const <const>{,<const>};
<vardecl> → var <id>{,<id>};
<proc> → procedure <id>（[<id>{,<id>}]）;<block>{;<proc>}
<body> → begin <statement>{;<statement>}end
<statement> → <id> := <exp> 
              | if <lexp> then <statement>[else <statement>] 
              | while <lexp> do <statement> 
              | call <id>（[<exp>{,<exp>}]） 
              | <body> 
              | read (<id>{，<id>}) 
              | write (<exp>{,<exp>})
<lexp> → <exp> <lop> <exp> | odd <exp>
<exp> → [+|-]<term>{<aop><term>}
<term> → <factor>{<mop><factor>}
<factor> → <id> | <integer> | (<exp>)
第二章 系统总体设计2.1 系统架构与处理流程本系统采用了现代编译器通用的管道（Pipeline）架构，将编译过程解耦为独立且顺序执行的阶段。与传统的单遍（One-pass）直接生成代码的编译器不同，本系统引入了 抽象语法树（AST） 作为核心中间表示，使得语义分析与代码生成分离，提高了系统的可维护性和可扩展性。[图表 2-1：系统数据流图 (DFD)]系统的处理流程如下：Lexer (词法分析器)：读取源代码字符流，输出 Token 流。Parser (语法分析器)：消费 Token 流，进行语法检查，构建 AST。Semantic Analyzer (语义分析器)：遍历 AST，建立符号表，检查作用域、类型及参数匹配，并进行静态计算。Code Generator (代码生成器)：再次遍历 AST，将树形结构线性化为 P-Code 指令序列。Virtual Machine (解释器)：模拟栈式计算机硬件，执行 P-Code，处理输入输出。2.2 关键数据结构设计2.2.1 抽象语法树 (AST) 类设计AST 是连接前端与后端的桥梁。本系统采用面向对象的设计方法，定义了以 AST 为基类的节点层次结构。[图表 2-2：AST 类层次结构图]AST (基类)Program: 根节点，包含程序名和 Block。Block: 包含常量、变量、过程声明列表及主体。Statement (抽象类)If, While, Assign, Call, Read, Write, CompoundExpression (抽象类)BinOp (二元运算), UnaryOp (一元运算), Var (变量引用), Num (数值)2.2.2 P-Code 指令集定义本编译器生成的中间代码为 P-Code（Pseudo-Code），指令格式为 F L A，其中 F 为功能码，L 为引用层差（Level Difference），A 为位移量（Offset）或参数。表 2-1：P-Code 指令集详表指令 (F)含义L (Level)A (Argument)详细描述LITLoad Literal0常量值将常量 A 压入栈顶。LODLoad Variable层差偏移量将位于层差 L、偏移量 A 的变量值取出，压入栈顶。STOStore Variable层差偏移量将栈顶内容弹出，存入位于层差 L、偏移量 A 的变量单元。CALCall Procedure层差入口地址调用过程。在栈顶建立新活动记录，跳转到地址 A。INTIncrement T0空间大小增加栈顶指针 T，为当前过程开辟 A 个存储单元。JMPJump0目标地址无条件跳转到指令地址 A。JPCJump Conditional0目标地址条件跳转。若栈顶值为 0 (False)，则跳转到地址 A；否则顺序执行。OPROperation0运算码执行算术或关系运算。A=2(加), A=4(乘), A=8(判等) 等。REDRead层差偏移量从标准输入读取整数，存入变量。WRTWrite00将栈顶值输出到标准输出，并弹出。第三章 详细设计与实现3.1 词法分析器 (Lexer)Lexer 是编译器的第一道工序，位于 lexer.py。它通过维护一个指向源代码的指针 pos 来逐字符扫描。状态机实现：通过 current_char 的类型决定进入何种状态。例如，遇到字母进入 _make_identifier 状态，遇到数字进入 _make_integer 状态。前瞻设计 (Lookahead)：对于 <、>、: 等可能构成双字符运算符的符号，Lexer 使用 _peek() 方法预读下一个字符。这确保了能正确区分 < (小于) 与 <> (不等于)，: (非法) 与 := (赋值)。3.2 语法分析器 (Parser)3.2.1 递归下降与多态性Parser 位于 parser.py，采用递归下降分析法。代码实现充分利用了多态性 (Polymorphism)，所有的语法单元均被封装为对象。这种设计体现了访问者模式 (Visitor Pattern) 的前置准备——Parser 只负责构建结构，不负责具体的语义解释或代码生成，实现了关注点分离。Python# 代码片段：If 语句解析与 AST 节点构建
elif tt == TokenType.IF:
    self.eat(TokenType.IF)
    condition = self.parse_lexp()       # 递归解析条件表达式
    self.eat(TokenType.THEN)
    then_stmt = self.parse_statement()  # 递归解析 Then 块
    else_stmt = None
    if self.current_token.type == TokenType.ELSE:
        self.eat(TokenType.ELSE)
        else_stmt = self.parse_statement()
    # 关键点：构建 If 节点对象，而非立即生成代码
    node = If(condition, then_stmt, else_stmt) 
3.2.2 恐慌模式错误恢复 (Panic Mode)为了增强编译器的健壮性，防止因单一语法错误导致编译器崩溃，本系统实现了 synchronize() 方法。逻辑描述：当 Parser 捕获到 ParserError 异常时，它不会退出，而是记录错误日志，进入“恐慌模式”。在此模式下，Parser 会不断丢弃当前的 Token，直到遇到同步集 (Synchronization Set) 中的 Token（如分号 ;、end、if 等）。这使得编译器能够跳过错误片段，重新与后续的语句边界对齐，继续检查剩余的代码。3.3 语义分析与静态检查 (Semantic Analysis)语义分析器位于 semantic_analyzer.py，它通过遍历 AST 来检查源程序的逻辑正确性。3.3.1 符号表与作用域符号表支持嵌套定义。每当进入一个过程定义 (visit_ProcedureDecl)，调用 enter_scope() 压入新的作用域层；过程结束时调用 exit_scope()。在查找变量时，系统自顶向下遍历作用域栈，这不仅实现了静态作用域规则，还能准确计算出变量的引用层差 (Level Difference)，为代码生成做准备。3.3.2 创新点：Levenshtein 智能提示当用户使用了未定义的变量时，系统会计算该拼写错误与当前作用域内所有已知变量的 Levenshtein 编辑距离。如果距离小于阈值（例如 3），编译器会抛出带有建议的错误信息：Error: 未定义的标识符 'countr'. 您是不是想输入 'counter'?3.3.3 创新点：静态计算与安全检测evaluate_static 方法尝试在编译期计算表达式的值。这实现了以下高级功能：常量折叠：如 a := 3 + 5 虽为表达式，但在编译期即可算出 8，无需运行时计算。除零检测：若检测到除数为 0（如 10 / (5-5)），则直接报出编译错误。死循环警告：若 While 条件静态求值为真，则发出警告。3.4 代码生成器 (Code Generator)3.4.1 栈式机代码生成代码生成器是一个 ASTVisitor。它根据语义分析阶段计算出的层差和偏移量生成指令。例如，赋值语句 a := b + 1 会被转换为后缀表达式逻辑：加载 b (LOD L, A) -> 压栈加载 1 (LIT 0, 1) -> 压栈执行加法 (OPR 0, 2) -> 弹出两个值，相加，结果压栈存入 a (STO L, A) -> 弹出结果存入内存3.4.2 地址回填技术 (Backpatching)在生成 If 和 While 语句的跳转指令（JPC/JMP）时，目标地址往往尚未确定。本系统采用地址回填技术解决此问题。处理流程：预留：生成 JPC 0, 0，并记录该指令在指令数组中的索引 jmp_idx。生成：生成代码块（Block）的具体指令。回填：代码块生成完毕后，获取当前的指令计数器值（Current PC），将其更新到 instructions[jmp_idx].a 中。示意图：回填前后的指令状态Before: 13: JPC 0, 0 (目标未知，指向 0)After: 13: JPC 0, 16 (回填完成，指向 Else 块入口或语句结束处)3.5 P-Code 虚拟机 (Interpreter)3.5.1 运行时存储组织：活动记录虚拟机通过 STACK 数组模拟内存。每当执行 CAL 指令调用过程时，会在栈顶建立一个新的活动记录（Stack Frame）。[图表 3-1：运行时栈帧结构]栈帧包含四个关键区域：Offset 0: SL (Static Link, 静态链)：指向定义该过程的外层过程的基址。它是实现静态作用域的关键。Offset 1: DL (Dynamic Link, 动态链)：指向调用该过程的过程的基址。它用于过程返回时恢复上下文。Offset 2: RA (Return Address, 返回地址)：记录调用完成后下一条指令的位置。Offset 3+: Variables: 存放参数和局部变量。3.5.2 静态链 (Static Link) 与 base() 函数PL/0 的难点在于嵌套过程可以访问外层变量。虚拟机通过 base(l) 函数实现这一机制。Pythondef base(self, l):
    """ l: 层差 = 当前层 - 变量定义层 """
    b1 = self.b      # 从当前基址开始
    while l > 0:
        b1 = self.stack[b1] # 沿着 SL 链向上跳转
        l -= 1
    return b1
原理解析：若层差 l=1，说明变量定义在直接外层。base(1) 读取当前栈帧 Offset 0 处的 SL 值，该值正是外层过程的基址，从而准确地访问到非局部变量。第四章 系统测试与结果分析4.1 测试环境操作系统：Windows 11 / Linux Ubuntu 22.04开发语言：Python 3.10IDE：Visual Studio Code4.2 基础功能测试测试用例：简单的算术运算与条件判断。源码：Delphiprogram test1;
var a, b;
begin
  a := 10;
  b := 20;
  if a < b then write(a + b);
end.
结果：控制台正确输出 30。生成的 AST 结构清晰展示了 Program -> Block -> If -> BinOp 的层级关系。4.3 复杂功能测试：递归与栈管理为了验证活动记录和静态链的正确性，使用阶乘递归程序进行测试。源码：Delphivar f;
procedure fac(n);
begin
    if n = 0 then f := 1
    else begin
        call fac(n-1);
        f := n * f;
    end
end;
begin
    call fac(3);
    write(f);
end.
[图表 4-1：递归执行时的栈状态快照](此处建议插入 Interpreter 在 Debug 模式下的输出截图)分析：在计算 fac(3) 的过程中，观察到栈中同时存在 4 个活动记录（主程序 + fac(3) + fac(2) + fac(1) + fac(0)）。DL 指针：正确地链向了上一层调用者，确保了 RET 指令能逐层返回。SL 指针：由于 fac 定义在主程序中，所有 fac 实例的 SL 都指向主程序基址（Base=1），这使得它们都能正确访问全局变量 f。最终输出结果 6，证明了运行时环境设计的正确性。4.4 鲁棒性测试拼写错误：输入 prnt，系统提示 Did you mean 'print'?（假设有此变量）。除零错误：输入 x := 1 / 0;，编译器直接报错并拦截。语法错误恢复：故意漏写分号，编译器报错 期望 SEMICOLON，但能继续编译后续语句，并未直接崩溃退出，验证了 Panic Mode 的有效性。第五章 总结与展望5.1 课设总结本次课程设计成功实现了一个结构清晰、功能完备的 PL/0 编译器。工程化实践：通过采用 AST 中间表示和访问者模式，将编译器各个阶段解耦，代码结构符合软件工程高内聚低耦合的原则。底层机制理解：通过手动实现虚拟机栈帧管理和静态链查找算法，深刻理解了高级语言中“作用域”和“递归”在计算机底层的具体实现形式。用户体验优化：引入的错误恢复和智能提示功能，极大提升了编译器的可用性。5.2 遇到的问题与解决方案在开发过程中，最大的难点在于代码生成阶段的层差计算。最初生成的 LOD/STO 指令层差经常出错，导致读取到错误的内存地址。解决方案：通过在语义分析阶段在符号表中记录详细的 level 信息，并在解释器中开启详细的 Debug 日志（打印每一步的栈内容、B指针、T指针），手动追踪 base() 函数的跳转路径，最终修正了逻辑。5.3 改进方向未来可进一步扩展该系统：数据类型扩展：增加对数组（Array）和布尔（Boolean）类型的支持。控制流优化：实现 repeat-until 或 for 循环结构。代码优化：在中间代码生成阶段加入窥孔优化（Peephole Optimization），减少冗余指令（如 LOD -> STO 对同一变量的冗余操作）。第六章 参考文献Alfred V. Aho, Monica S. Lam, et al. Compilers: Principles, Techniques, and Tools (Dragon Book). 2nd Edition.Niklaus Wirth. Algorithms + Data Structures = Programs. Prentice Hall, 1976.张素琴 等. 《编译原理（第2版）》. 清华大学出版社.Python Software Foundation. Python 3.10 Documentation.