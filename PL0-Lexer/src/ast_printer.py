from .ast_nodes import *

class ASTPrinter:
    def print(self, node):
        self._print_recursive(node, "", True)

    def _print_recursive(self, node, prefix, is_last):
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{self._get_node_label(node)}")

        child_prefix = prefix + ("    " if is_last else "│   ")

        children = self._get_children(node)
        
        count = len(children)
        for i, child in enumerate(children):
            is_last_child = (i == count - 1)
            self._print_recursive(child, child_prefix, is_last_child)

    def _get_node_label(self, node):
        """获取节点显示的文本"""
        if node is None: return "None"
        
        t = type(node).__name__
        
        if isinstance(node, Program):
            return f"\033[1;34mProgram\033[0m: {node.name}"
        elif isinstance(node, Block):
            return f"\033[1;33mBlock\033[0m"
        elif isinstance(node, ConstDecl):
            return f"Const: {node.name} = {node.value}"
        elif isinstance(node, VarDecl):
            return f"Var: {node.name}"
        elif isinstance(node, ProcedureDecl):
            return f"\033[1;35mProcedure\033[0m: {node.name}({', '.join(node.params)})"
        elif isinstance(node, BinOp):
            return f"BinOp: {node.op.value}"
        elif isinstance(node, UnaryOp):
            return f"Unary: {node.op.value}"
        elif isinstance(node, Assign):
            return f"Assign (:=)"
        elif isinstance(node, If):
            return f"If"
        elif isinstance(node, While):
            return f"While"
        elif isinstance(node, Call):
            return f"Call: {node.proc_name}"
        elif isinstance(node, Var):
            return f"Var: {node.name}"
        elif isinstance(node, Num):
            return f"Num: {node.value}"
        elif isinstance(node, Compound):
            return f"Compound Stmt"
        return t

    def _get_children(self, node):
        """定义每个节点有哪些子节点需要展开"""
        if isinstance(node, Program):
            return [node.block]
        elif isinstance(node, Block):
            return node.consts + node.vars + node.procs + [node.body]
        elif isinstance(node, ProcedureDecl):
            return [node.block]
        elif isinstance(node, Compound):
            return node.children
        elif isinstance(node, Assign):
            return [node.left, node.right]
        elif isinstance(node, BinOp):
            return [node.left, node.right]
        elif isinstance(node, UnaryOp):
            return [node.expr]
        elif isinstance(node, If):
            children = [node.condition, node.then_stmt]
            if node.else_stmt: children.append(node.else_stmt)
            return children
        elif isinstance(node, While):
            return [node.condition, node.body]
        elif isinstance(node, Call):
            return node.args
        elif isinstance(node, Read):
            return node.vars
        elif isinstance(node, Write):
            return node.exprs
        
        return []