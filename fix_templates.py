#!/usr/bin/env python
"""Script to truncate template files that have duplicate content."""

import os

# Define the files and their correct line counts
files_to_fix = {
    'inventory/templates/inventory/machines_list.html': 1127,
    'inventory/templates/inventory/engines_list.html': 1058,
    'inventory/templates/inventory/parts_list.html': 1082,
    'inventory/templates/inventory/build_lists_list.html': 1002,
}

base_dir = os.path.dirname(os.path.abspath(__file__))

for filepath, line_count in files_to_fix.items():
    full_path = os.path.join(base_dir, filepath)
    
    # Read the file
    with open(full_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    original_count = len(lines)
    
    # Keep only the first N lines
    if original_count > line_count:
        new_lines = lines[:line_count]
        
        # Write the truncated file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"Fixed {filepath}: {original_count} -> {line_count} lines")
    else:
        print(f"Skipped {filepath}: already at {original_count} lines")

print("Done!")
