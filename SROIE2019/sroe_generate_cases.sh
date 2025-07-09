#!/bin/bash

# Check if correct number of arguments provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <folder_path> <output_yaml_file>"
    echo "Example: $0 /path/to/folder output.yaml"
    exit 1
fi

FOLDER_PATH="$1"
OUTPUT_FILE="$2"

# Check if folder exists
if [ ! -d "$FOLDER_PATH" ]; then
    echo "Error: Folder '$FOLDER_PATH' does not exist"
    exit 1
fi

# Check if img/ directory exists
if [ ! -d "$FOLDER_PATH/img" ]; then
    echo "Error: img/ directory not found in '$FOLDER_PATH'"
    exit 1
fi

# Check if entities/ directory exists
if [ ! -d "$FOLDER_PATH/entities" ]; then
    echo "Error: entities/ directory not found in '$FOLDER_PATH'"
    exit 1
fi

# Start writing YAML file
echo "cases:" > "$OUTPUT_FILE"

# Process each image file in img/ directory
for img_file in "$FOLDER_PATH/img"/*; do
    # Skip if not a file
    [ -f "$img_file" ] || continue
    
    # Get filename with extension
    filename=$(basename "$img_file")
    
    # Get filename without extension
    name="${filename%.*}"
    
    # Get absolute path to image
    img_path=$(realpath "$img_file")
    
    # Look for matching entity file (trying different extensions)
    entity_path=""
    for ext in txt json xml yaml yml; do
        if [ -f "$FOLDER_PATH/entities/${name}.${ext}" ]; then
            entity_path=$(realpath "$FOLDER_PATH/entities/${name}.${ext}")
            break
        fi
    done
    
    # If no entity file found, try without extension
    if [ -z "$entity_path" ] && [ -f "$FOLDER_PATH/entities/${name}" ]; then
        entity_path=$(realpath "$FOLDER_PATH/entities/${name}")
    fi
    
    # Only add to YAML if entity file exists
    if [ -n "$entity_path" ]; then
        echo "  - name: $name" >> "$OUTPUT_FILE"
        echo "    inputs: $img_path" >> "$OUTPUT_FILE"
        echo "    expected_output: $entity_path" >> "$OUTPUT_FILE"
    else
        echo "Warning: No matching entity file found for '$filename'"
    fi
done

echo "YAML file generated: $OUTPUT_FILE"