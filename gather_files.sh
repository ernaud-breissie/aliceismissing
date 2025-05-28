#!/bin/bash

# Define output file
OUTPUT_FILE="all_file.txt"
# Define project root directory
PROJECT_ROOT=$(pwd)

# Clear or create the output file
> "$OUTPUT_FILE"

# Find all matching files and process them
#find "$PROJECT_ROOT" \( -name "*.html" -o -name "*.py" -o -name "*.css" -o -name "*.js" \) -type f | sort | while IFS= read -r file; do
find "$PROJECT_ROOT" \( -name "*.html" -o -name "*.py" -o -name "*.css" \) -type f | sort | while IFS= read -r file; do
    # Get relative path from project root
    rel_path=${file#"$PROJECT_ROOT"/}
    
    # Add file header to output file
    echo "===== $rel_path =====" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # Add file content to output file
    cat "$file" >> "$OUTPUT_FILE"
    
    # Add separator
    echo "" >> "$OUTPUT_FILE"
    echo "----- END OF FILE -----" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
done

echo "All files have been concatenated into $OUTPUT_FILE"

