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