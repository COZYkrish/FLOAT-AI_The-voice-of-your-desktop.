import os
import re

py_files = [f for f in os.listdir('.') if f.endswith('.py') and os.path.isfile(f)]

for py_file in py_files:
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Use regex to find lines that need commenting
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # If line already starts with #, keep it as is
            if line.lstrip().startswith('#'):
                fixed_lines.append(line)
            # If line contains decorative characters and doesn't look like code, comment it
#             elif '─' in line or '█' in line or '┌' in line or '┐' in line:
                if not line.startswith('#'):
                    fixed_lines.append('# ' + line)
                else:
                    fixed_lines.append(line)
            # If line is empty, keep it
            elif not line.strip():
                fixed_lines.append(line)
            # If line doesn't start with space and doesn't look like executable code
            elif line and line[0] not in (' ', '\t') and not line.strip().startswith(('def ', 'class ', 'import ', 'from ', '@', 'try:', 'except', 'finally:', 'if ', 'for ', 'while ')):
                # Check if it looks like prose/comment
                words = line.split()
                if words and not any(c in line for c in '()[]{}='):
                    # Looks like prose, comment it
                    if not line.startswith('#'):
                        fixed_lines.append('# ' + line)
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fixed_lines))
        
        print(f'✓ {py_file}')
    except Exception as e:
        print(f'✗ {py_file}: {e}')

print('Done!')
