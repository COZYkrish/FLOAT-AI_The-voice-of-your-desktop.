import ast
import os

# Try to find syntax errors in all Python files
for py_file in sorted(os.listdir('.')):
    if not py_file.endswith('.py') or py_file in ('fix_comments.py', 'find_syntax_errors.py'):
        continue
    
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            ast.parse(f.read())
        print(f'✓ {py_file}')
    except SyntaxError as e:
        print(f'✗ {py_file}: Line {e.lineno} - {e.msg}')
        # Show context
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if e.lineno and e.lineno <= len(lines):
                    print(f'  >>> {lines[e.lineno-1].rstrip()}')
        except:
            pass
