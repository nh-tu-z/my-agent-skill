#!/usr/bin/env bash
# install-skill.sh - Install skills from this repository as global or project skills for Antigravity

set -e

TARGET="global"
PROJECT_PATH=""
SKILL_NAME=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --target) TARGET="$2"; shift ;;
        --project-path) PROJECT_PATH="$2"; shift ;;
        --skill-name) SKILL_NAME="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SKILLS_DIR="$REPO_ROOT/skills"

if [ ! -d "$SKILLS_DIR" ]; then
    echo "Error: skills directory not found at $SKILLS_DIR"
    exit 1
fi

if [ "$TARGET" = "global" ]; then
    DEST_DIR="$HOME/.gemini/config/skills"
else
    if [ -z "$PROJECT_PATH" ]; then
        echo "Error: --project-path is required when --target is 'project'"
        exit 1
    fi
    DEST_DIR="$PROJECT_PATH/.agents/skills"
fi

mkdir -p "$DEST_DIR"

echo "=========================================================="
echo "Installing Skills from: $SKILLS_DIR"
echo "Target Scope:           $TARGET"
echo "Destination:            $DEST_DIR"
echo "=========================================================="

if [ -n "$SKILL_NAME" ]; then
    if [ ! -d "$SKILLS_DIR/$SKILL_NAME" ]; then
        echo "Error: Skill '$SKILL_NAME' not found in $SKILLS_DIR"
        exit 1
    fi
    echo "Installing skill: $SKILL_NAME -> $DEST_DIR/$SKILL_NAME"
    cp -r "$SKILLS_DIR/$SKILL_NAME" "$DEST_DIR/"
else
    for skill_path in "$SKILLS_DIR"/*; do
        if [ -d "$skill_path" ]; then
            name="$(basename "$skill_path")"
            echo "Installing skill: $name -> $DEST_DIR/$name"
            cp -r "$skill_path" "$DEST_DIR/"
        fi
    done
fi

echo -e "\nInstallation completed successfully!"

